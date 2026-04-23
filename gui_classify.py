"""
Sound Classifier — 분류 GUI
  튜닝 슬라이더 조절 → 분류 시작 → 프로그레스
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import json
import os
import sys
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from sound_classifier.classifier import SoundClassifier
from sound_classifier.category_map import get_category

DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
AUDIO_EXT = {'.wav', '.flac', '.ogg', '.mp3', '.aiff'}

DEFAULT_SUPPRESS = {
    "silence_factor": 0.1,
    "generic_factor": 0.15,
    "music_short_duration": 3.0,
    "music_short_factor": 0.2,
    "music_dominance_ratio": 2.0,
    "music_weak_factor": 0.4,
    "speech_short_duration": 0.5,
    "speech_short_factor": 0.5,
}

PRESETS = {
    "🎮 게임 SFX 중심": {
        "silence_factor": 0.05, "generic_factor": 0.1,
        "music_short_duration": 3.0, "music_short_factor": 0.1,
        "music_dominance_ratio": 1.5, "music_weak_factor": 0.3,
        "speech_short_duration": 0.5, "speech_short_factor": 0.3,
    },
    "🎵 음악 중심": {
        "silence_factor": 0.1, "generic_factor": 0.15,
        "music_short_duration": 1.0, "music_short_factor": 0.8,
        "music_dominance_ratio": 5.0, "music_weak_factor": 0.9,
        "speech_short_duration": 0.5, "speech_short_factor": 0.3,
    },
    "🌿 환경음/폴리": {
        "silence_factor": 0.2, "generic_factor": 0.3,
        "music_short_duration": 3.0, "music_short_factor": 0.2,
        "music_dominance_ratio": 2.0, "music_weak_factor": 0.4,
        "speech_short_duration": 0.5, "speech_short_factor": 0.5,
    },
    "🎙️ 보이스 중심": {
        "silence_factor": 0.1, "generic_factor": 0.15,
        "music_short_duration": 3.0, "music_short_factor": 0.2,
        "music_dominance_ratio": 2.0, "music_weak_factor": 0.4,
        "speech_short_duration": 1.0, "speech_short_factor": 0.9,
    },
}

SLIDER_DEFS = [
    ("silence_factor",        "🔇 Silence 억제",        0.0, 1.0,  0.05, "무음 구간의 억제 강도"),
    ("generic_factor",        "🏷️ Generic 억제",        0.0, 1.0,  0.05, "일반적 태그 억제"),
    ("music_short_duration",  "🎵 Music 짧은기준(초)",  0.5, 10.0, 0.5,  "이 길이 이하면 음악 태그 억제"),
    ("music_short_factor",    "🎵 Music 짧은 억제",     0.0, 1.0,  0.05, "짧은 파일의 음악 태그 억제"),
    ("music_dominance_ratio", "🎵 Music 지배비율",      1.0, 5.0,  0.1,  "음악이 이 배수 이상이면 유지"),
    ("music_weak_factor",     "🎵 Music 약한 억제",     0.0, 1.0,  0.05, "지배적이지 않은 음악 억제"),
    ("speech_short_duration", "🗣️ Speech 짧은기준(초)", 0.1, 5.0,  0.1,  "이 길이 이하면 음성 태그 억제"),
    ("speech_short_factor",   "🗣️ Speech 짧은 억제",   0.0, 1.0,  0.05, "짧은 파일의 음성 태그 억제"),
]


def scan_audio_files(folder):
    files = []
    for root, _, names in os.walk(folder):
        for name in names:
            if os.path.splitext(name)[1].lower() in AUDIO_EXT:
                files.append(os.path.join(root, name))
    return sorted(files)


class ClassifyGUI(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("🔊 Sound Classifier")
        self.geometry("420x800")
        self.minsize(380, 650)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.slider_widgets = {}
        self.is_classifying = False
        self.config = self._load_config()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── Config ──────────────────────────

    def _load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"suppress": DEFAULT_SUPPRESS.copy()}

    def _save_config_from_sliders(self):
        if "suppress" not in self.config:
            self.config["suppress"] = {}
        for key, (var, _) in self.slider_widgets.items():
            self.config["suppress"][key] = round(var.get(), 3)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("저장 오류", str(e))
            return False

    def _set_status(self, text):
        self.status_label.configure(text=text)

    # ─── UI Build ────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_folder_bar()   # row 0
        self._build_tuning()       # row 1, 2
        self._build_action_bar()   # row 3

        self.status_label = ctk.CTkLabel(
            self, text="Ready", anchor="w",
            font=("", 11), text_color="gray60")
        self.status_label.grid(
            row=4, column=0, sticky="ew", padx=12, pady=(0, 6))

    def _build_folder_bar(self):
        f = ctk.CTkFrame(self)
        f.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="📂 입력 폴더",
                     font=("", 12, "bold")).grid(
            row=0, column=0, padx=(10, 5), pady=8)
        self.input_var = ctk.StringVar()
        ctk.CTkEntry(
            f, textvariable=self.input_var, height=32,
            placeholder_text="분류할 사운드 파일이 있는 폴더"
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=8)
        ctk.CTkButton(
            f, text="찾기", width=60, height=32,
            command=self._pick_folder
        ).grid(row=0, column=2, padx=(0, 10), pady=8)

    def _pick_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.input_var.set(path)

    def _build_tuning(self):
        ctk.CTkLabel(
            self, text="⚙️ 튜닝 설정",
            font=("", 16, "bold")
        ).grid(row=1, column=0, pady=(10, 0), padx=15, sticky="w")

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        scroll.grid_columnconfigure(0, weight=1)

        # 프리셋
        pf = ctk.CTkFrame(scroll, fg_color="transparent")
        pf.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        pf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pf, text="프리셋:",
                     font=("", 12)).grid(row=0, column=0, padx=(0, 5))
        self.preset_var = ctk.StringVar(value="선택...")
        ctk.CTkOptionMenu(
            pf, variable=self.preset_var,
            values=list(PRESETS.keys()),
            command=self._apply_preset, width=200
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkFrame(scroll, height=2, fg_color="gray40").grid(
            row=1, column=0, sticky="ew", pady=5)

        # 슬라이더
        suppress = self.config.get("suppress", DEFAULT_SUPPRESS)
        for i, (key, label, lo, hi, step, desc) in enumerate(SLIDER_DEFS):
            sf = ctk.CTkFrame(scroll, fg_color="transparent")
            sf.grid(row=i + 2, column=0, sticky="ew", pady=4)
            sf.grid_columnconfigure(0, weight=1)

            cur = suppress.get(key, DEFAULT_SUPPRESS[key])
            var = ctk.DoubleVar(value=cur)
            val_lbl = ctk.CTkLabel(
                sf, text=f"{cur:.2f}", width=50,
                font=("", 12, "bold"))
            self.slider_widgets[key] = (var, val_lbl)

            ctk.CTkLabel(sf, text=label, font=("", 12),
                         anchor="w").grid(row=0, column=0, sticky="w")
            val_lbl.grid(row=0, column=1, sticky="e")

            n_steps = max(1, int((hi - lo) / step))
            ctk.CTkSlider(
                sf, from_=lo, to=hi,
                number_of_steps=n_steps, variable=var,
                command=self._make_slider_cb(key)
            ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 1))

            ctk.CTkLabel(sf, text=desc, font=("", 10),
                         text_color="gray50").grid(
                row=2, column=0, columnspan=2, sticky="w")

        # 저장 / 리셋
        bf = ctk.CTkFrame(scroll, fg_color="transparent")
        bf.grid(row=len(SLIDER_DEFS) + 2, column=0,
                sticky="ew", pady=(10, 0))
        bf.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(bf, text="💾 저장", height=36,
                      command=self._on_save).grid(
            row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(bf, text="↩️ 리셋", height=36,
                      fg_color="gray30", hover_color="gray40",
                      command=self._reset_config).grid(
            row=0, column=1, padx=(5, 0), sticky="ew")

    def _make_slider_cb(self, key):
        def cb(value):
            _, val_lbl = self.slider_widgets[key]
            val_lbl.configure(text=f"{value:.2f}")
        return cb

    def _build_action_bar(self):
        af = ctk.CTkFrame(self)
        af.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 5))
        af.grid_columnconfigure(1, weight=1)

        self.classify_btn = ctk.CTkButton(
            af, text="🔍 분류 시작", width=130, height=40,
            font=("", 14, "bold"), command=self._start_classify)
        self.classify_btn.grid(row=0, column=0, padx=(10, 10), pady=8)

        self.progress = ctk.CTkProgressBar(af, height=20)
        self.progress.grid(row=0, column=1, sticky="ew", padx=5, pady=8)
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(
            af, text="", width=80, font=("", 12))
        self.progress_label.grid(row=0, column=2, padx=(5, 10), pady=8)

    # ─── Actions ─────────────────────────

    def _on_save(self):
        if self._save_config_from_sliders():
            self._set_status("✅ config.json 저장 완료")

    def _apply_preset(self, name):
        if name not in PRESETS:
            return
        for key, val in PRESETS[name].items():
            if key in self.slider_widgets:
                var, lbl = self.slider_widgets[key]
                var.set(val)
                lbl.configure(text=f"{val:.2f}")
        self._set_status(f"📋 프리셋 적용: {name}")

    def _reset_config(self):
        for key, val in DEFAULT_SUPPRESS.items():
            if key in self.slider_widgets:
                var, lbl = self.slider_widgets[key]
                var.set(val)
                lbl.configure(text=f"{val:.2f}")
        self.preset_var.set("선택...")
        self._set_status("↩️ 기본값으로 리셋")

    # ─── Classification ──────────────────

    def _start_classify(self):
        if self.is_classifying:
            return
        input_dir = self.input_var.get().strip()
        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showwarning("입력 폴더",
                                   "유효한 입력 폴더를 선택하세요.")
            return
        if not self._save_config_from_sliders():
            return

        self.is_classifying = True
        self.classify_btn.configure(state="disabled", text="⏳ 분류 중...")
        self.progress.set(0)
        self.progress_label.configure(text="준비 중...")

        thread = threading.Thread(
            target=self._classify_thread, daemon=True)
        thread.start()

    def _classify_thread(self):
        try:
            input_dir = self.input_var.get().strip()
            files = scan_audio_files(input_dir)

            if not files:
                self.after(0, lambda: self._set_status(
                    "⚠️ 오디오 파일이 없습니다"))
                self.after(0, self._classify_done)
                return

            total = len(files)
            self.after(0, lambda: self._set_status("🔄 모델 로딩 중..."))

            classifier = SoundClassifier()

            self.after(0, lambda: self._set_status(
                f"🔍 분류 시작: {total}개 파일"))

            success = 0
            for i, file_path in enumerate(files):
                try:
                    result = classifier.classify_file(file_path)

                    if "error" in result:
                        print(f"[SKIP] {os.path.basename(file_path)}: "
                              f"{result['error']}")
                        continue

                    top_label = result["top_tag"]
                    cat = get_category(
                        classifier.category_map, top_label)

                    tags = result["tags"]
                    classifier.db.insert(
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
                except Exception as e:
                    print(f"[SKIP] {file_path}: {e}")

                prog = (i + 1) / total
                self.after(0, self._update_progress, prog, i + 1, total)

            classifier.close()

            self.after(0, lambda: self._set_status(
                f"✅ 분류 완료: {success}/{total}개 성공"))
            self.after(0, self._classify_done)

        except Exception as e:
            self.after(0, lambda: self._set_status(
                f"❌ 분류 오류: {e}"))
            self.after(0, self._classify_done)

    def _update_progress(self, prog, cur, total):
        self.progress.set(prog)
        self.progress_label.configure(text=f"{cur}/{total}")

    def _classify_done(self):
        self.is_classifying = False
        self.classify_btn.configure(state="normal", text="🔍 분류 시작")

    # ─── Cleanup ─────────────────────────

    def _on_close(self):
        if self.is_classifying:
            if not messagebox.askyesno(
                    "종료", "분류가 진행 중입니다. 종료할까요?"):
                return
        self.destroy()


if __name__ == "__main__":
    app = ClassifyGUI()
    app.mainloop()