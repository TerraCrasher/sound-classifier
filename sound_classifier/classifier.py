"""
AST (Audio Spectrogram Transformer) 기반 사운드 분류 엔진
설정: data/config.json
"""

import os
import json
import shutil
import warnings
import numpy as np
import torch
from tqdm import tqdm
from transformers import ASTForAudioClassification, ASTFeatureExtractor

warnings.filterwarnings("ignore")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "config.json")

# ── 기본값 (config.json 없을 때 사용) ──
DEFAULT_CONFIG = {
    "model": {
        "name": "MIT/ast-finetuned-audioset-10-10-0.4593",
        "chunk_seconds": 10.0,
        "min_duration": 0.1,
        "top_k": 3
    },
    "suppress": {
        "silence_factor": 0.1,
        "generic_factor": 0.15,
        "music_short_duration": 3.0,
        "music_short_factor": 0.2,
        "music_dominance_ratio": 2.0,
        "music_weak_factor": 0.4,
        "speech_short_duration": 0.5,
        "speech_short_factor": 0.5
    },
    "generic_labels": [
        "sound effect", "sound", "noise", "white noise",
        "environmental noise", "static", "outside"
    ],
    "music_keywords": [
        "music", "musical instrument", "singing", "song",
        "choir", "orchestra", "guitar", "piano", "drum",
        "bass", "violin", "flute", "trumpet", "harp",
        "synthesizer", "keyboard", "harmonica", "accordion",
        "banjo", "sitar", "organ", "mandolin", "ukulele"
    ]
}


def _load_config():
    """config.json 로드. 없으면 기본값으로 자동 생성."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"⚙️  설정 로드: {CONFIG_PATH}")
        return cfg
    else:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
        print(f"⚙️  기본 설정 생성: {CONFIG_PATH}")
        return DEFAULT_CONFIG


class SoundClassifier:

    SAMPLE_RATE = 16000

    # ─────────────────────────────────────────────
    #  초기화
    # ─────────────────────────────────────────────
    def __init__(self):
        # ── config 로드 ──
        self.cfg = _load_config()
        model_cfg = self.cfg["model"]
        suppress_cfg = self.cfg["suppress"]

        self.CHUNK_SEC = model_cfg["chunk_seconds"]
        self.MIN_DURATION = model_cfg["min_duration"]
        self.TOP_K = model_cfg["top_k"]

        # 억제 파라미터
        self.silence_factor = suppress_cfg["silence_factor"]
        self.generic_factor = suppress_cfg["generic_factor"]
        self.music_short_dur = suppress_cfg["music_short_duration"]
        self.music_short_fac = suppress_cfg["music_short_factor"]
        self.music_dom_ratio = suppress_cfg["music_dominance_ratio"]
        self.music_weak_fac = suppress_cfg["music_weak_factor"]
        self.speech_short_dur = suppress_cfg["speech_short_duration"]
        self.speech_short_fac = suppress_cfg["speech_short_factor"]

        # 제네릭 라벨 / 음악 키워드
        self._generic_labels = set(self.cfg["generic_labels"])
        self._music_keywords = tuple(self.cfg["music_keywords"])

        # ── 모델 로드 ──
        model_name = model_cfg["name"]
        print(f"🔄 AST 모델 로딩 중... ({model_name})")
        print("   (최초 실행 시 모델 다운로드 ~300MB)")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.feature_extractor = ASTFeatureExtractor.from_pretrained(model_name)
        self.model = ASTForAudioClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

        self.class_names = [
            self.model.config.id2label[i]
            for i in range(self.model.config.num_labels)
        ]

        # ── 후처리용 인덱스 캐싱 ──
        self._silence_idx = [
            i for i, n in enumerate(self.class_names)
            if n.lower() == "silence"
        ]
        self._speech_idx = [
            i for i, n in enumerate(self.class_names)
            if "speech" in n.lower()
        ]
        self._music_all_idx = [
            i for i, n in enumerate(self.class_names)
            if any(kw in n.lower() for kw in self._music_keywords)
        ]
        self._generic_idx = [
            i for i, n in enumerate(self.class_names)
            if n.lower() in self._generic_labels
        ]

        # ── 카테고리 매핑 & DB ──
        from sound_classifier.category_map import build_category_map
        from sound_classifier.tag_db import TagDB

        self.category_map = build_category_map(self.class_names)
        self.db = TagDB()

        gpu_label = (
            f"GPU: {torch.cuda.get_device_name(0)}"
            if torch.cuda.is_available() else "CPU 모드"
        )
        print(f"✅ AST 모델 로드 완료 ({gpu_label}, 클래스: {len(self.class_names)}개)")
        self._print_config()

    def _print_config(self):
        """현재 튜닝 설정 요약 출력"""
        s = self.cfg["suppress"]
        print(f"   ├─ Silence 억제: ×{s['silence_factor']}")
        print(f"   ├─ Generic 억제: ×{s['generic_factor']}")
        print(f"   ├─ Music 억제:   <{s['music_short_duration']}s → ×{s['music_short_factor']}"
              f"  | 비우세 → ×{s['music_weak_factor']} (기준 {s['music_dominance_ratio']}배)")
        print(f"   └─ Speech 억제:  <{s['speech_short_duration']}s → ×{s['speech_short_factor']}")

    # ─────────────────────────────────────────────
    #  내부 추론
    # ─────────────────────────────────────────────
    def _infer_chunk(self, waveform):
        inputs = self.feature_extractor(
            waveform,
            sampling_rate=self.SAMPLE_RATE,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.model(**inputs).logits[0]
            probs = torch.sigmoid(logits).cpu().numpy()

        return probs

    # ─────────────────────────────────────────────
    #  후처리 (config 값 사용)
    # ─────────────────────────────────────────────
    def _postprocess(self, probs, duration):
        probs = probs.copy()

        # ① Silence 억제
        for idx in self._silence_idx:
            probs[idx] *= self.silence_factor

        # ② 제네릭 억제
        for idx in self._generic_idx:
            probs[idx] *= self.generic_factor

        # ③ Music 스마트 억제
        music_all_set = set(self._music_all_idx)
        music_max = max((probs[i] for i in self._music_all_idx), default=0)
        non_music_max = max(
            (probs[i] for i in range(len(probs)) if i not in music_all_set),
            default=0
        )

        if music_max > 0 and non_music_max > 0:
            if duration < self.music_short_dur:
                for idx in self._music_all_idx:
                    probs[idx] *= self.music_short_fac
            elif music_max < non_music_max * self.music_dom_ratio:
                for idx in self._music_all_idx:
                    probs[idx] *= self.music_weak_fac

        # ④ 짧은 파일 Speech 억제
        if duration < self.speech_short_dur:
            for idx in self._speech_idx:
                probs[idx] *= self.speech_short_fac

        return probs

    # ─────────────────────────────────────────────
    #  단일 파일 분류
    # ─────────────────────────────────────────────
    def classify_file(self, file_path, top_k=None):
        from sound_classifier.utils import load_audio

        if top_k is None:
            top_k = self.TOP_K

        try:
            waveform, sr, duration = load_audio(file_path)

            if duration < self.MIN_DURATION:
                return self._make_result(file_path, 0.0, "Silence", 1.0)

            chunk_samples = int(self.CHUNK_SEC * sr)

            if len(waveform) > chunk_samples * 1.5:
                chunk_probs = []
                for start in range(0, len(waveform), chunk_samples):
                    chunk = waveform[start:start + chunk_samples]
                    if len(chunk) < sr:
                        continue
                    chunk_probs.append(self._infer_chunk(chunk))

                probs = (
                    np.max(chunk_probs, axis=0)
                    if chunk_probs
                    else self._infer_chunk(waveform)
                )
            else:
                probs = self._infer_chunk(waveform)

            probs = self._postprocess(probs, duration)

            top_idx = np.argsort(probs)[-top_k:][::-1]
            tags = [
                {"label": self.class_names[i], "score": round(float(probs[i]), 4)}
                for i in top_idx
            ]

            # 제네릭 태그 1위 → 구체적 태그로 승격
            if tags and tags[0]["label"].lower() in self._generic_labels:
                for i in range(1, len(tags)):
                    if tags[i]["label"].lower() not in self._generic_labels:
                        tags[0], tags[i] = tags[i], tags[0]
                        break

            return {
                "file": file_path,
                "duration": round(duration, 2),
                "tags": tags,
                "confidence": tags[0]["score"],
                "top_tag": tags[0]["label"],
            }

        except Exception as e:
            return {
                "file": file_path,
                "error": str(e),
                "tags": [],
                "confidence": 0.0,
                "top_tag": "Error",
            }

    # ─────────────────────────────────────────────
    #  폴더 일괄 분류
    # ─────────────────────────────────────────────
    def classify_folder(self, folder_path, force=False):
        from sound_classifier.utils import scan_audio_files
        from sound_classifier.category_map import get_category

        files = scan_audio_files(folder_path)

        if not files:
            print(f"⚠️ 오디오 파일이 없습니다: {folder_path}")
            return

        # 중복 파일 스킵
        if not force:
            analyzed = self.db.get_analyzed_paths()
            new_files = [f for f in files if f not in analyzed]
            skipped = len(files) - len(new_files)
            if skipped > 0:
                print(f"⏭️ 이미 분류됨: {skipped}개 스킵")
            if not new_files:
                print("✅ 새로 분류할 파일이 없습니다.")
                return
            files = new_files

        print(f"\n📂 {len(files)}개 파일 분류 시작\n")

        success = 0
        errors = 0

        for fpath in tqdm(files, desc="🔊 분류 중", unit="file"):
            result = self.classify_file(fpath)

            if "error" in result:
                errors += 1
                tqdm.write(f"  ❌ {os.path.basename(fpath)}: {result['error']}")
                continue

            top_label = result["top_tag"]
            cat = get_category(self.category_map, top_label)

            tags = result["tags"]
            self.db.insert(
                file_path=result["file"],
                file_name=os.path.basename(result["file"]),
                duration=result["duration"],
                category_main=f"{cat['large']}/{cat['medium']}",
                tag_1=tags[0]["label"] if len(tags) > 0 else "",
                tag_2=tags[1]["label"] if len(tags) > 1 else "",
                tag_3=tags[2]["label"] if len(tags) > 2 else "",
                confidence=result["confidence"],
            )
            success += 1

        print(f"\n📊 분류 완료: ✅ {success}개 성공, ❌ {errors}개 실패")

# ─────────────────────────────────────────────
    #  분류 결과 → 폴더 구조로 복사/이동
    # ─────────────────────────────────────────────
    def organize_files(self, output_dir="output", mode="copy"):
        entries = self.db.get_all()

        if not entries:
            print("⚠️ DB에 분류된 파일이 없습니다. 먼저 분류를 실행하세요.")
            return

        print(f"\n📦 {len(entries)}개 파일 → '{output_dir}' ({mode})\n")

        done = 0
        skipped = 0
        action_fn = shutil.copy2 if mode == "copy" else shutil.move

        for row in tqdm(entries, desc=f"📁 {mode} 중", unit="file"):
            src = row[1]
            category = row[4]

            if not os.path.exists(src):
                tqdm.write(f"  ⚠️ 파일 없음 (스킵): {src}")
                skipped += 1
                continue

            safe_category = self._safe_dirname(category) if category else "기타"
            dest_dir = os.path.join(output_dir, *safe_category.split("/"))
            os.makedirs(dest_dir, exist_ok=True)

            filename = os.path.basename(src)
            dest = os.path.join(dest_dir, filename)

            # 동일 파일명이 이미 존재하면 해시 비교
            if os.path.exists(dest):
                src_hash = self._file_hash(src)
                dest_hash = self._file_hash(dest)
                if src_hash == dest_hash:
                    tqdm.write(f"  ⏭️ 동일 파일 스킵: {filename}")
                    skipped += 1
                    continue
                else:
                    dest = self._unique_path(dest)

            try:
                action_fn(src, dest)
                done += 1
            except Exception as e:
                tqdm.write(f"  ❌ {filename}: {e}")
                skipped += 1

        print(f"\n📊 정리 완료: ✅ {done}개 {mode}, ⚠️ {skipped}개 스킵")

    # ─────────────────────────────────────────────
    #  정리 / 유틸
    # ─────────────────────────────────────────────
    def close(self):
        if hasattr(self, "db") and self.db:
            self.db.close()

    @staticmethod
    def _make_result(path, dur, tag, score):
        return {
            "file": path,
            "duration": dur,
            "tags": [{"label": tag, "score": score}],
            "confidence": score,
            "top_tag": tag,
        }

    @staticmethod
    def _safe_dirname(name):
        for ch in ['<', '>', ':', '"', '\\', '|', '?', '*']:
            name = name.replace(ch, '_')
        return name.strip()

    @staticmethod
    def _unique_path(path):
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    @staticmethod
    def _file_hash(path, chunk_size=8192):
        """파일 MD5 해시 계산"""
        import hashlib
        h = hashlib.md5()
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()