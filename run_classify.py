"""Sound Classifier 실행 — AST 버전"""
import os
import sys
import warnings
import json


# ── 불필요한 경고 억제 ──
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

PRESETS = {
    "1": {
        "name": "🎮 게임 효과음",
        "suppress": {
            "silence_factor": 0.1,
            "generic_factor": 0.15,
            "music_short_duration": 3.0,
            "music_short_factor": 0.2,
            "music_dominance_ratio": 2.0,
            "music_weak_factor": 0.4,
            "speech_short_duration": 0.5,
            "speech_short_factor": 0.5
        }
    },
    "2": {
        "name": "🌿 환경음/폴리",
        "suppress": {
            "silence_factor": 0.2,
            "generic_factor": 0.3,
            "music_short_duration": 3.0,
            "music_short_factor": 0.2,
            "music_dominance_ratio": 2.0,
            "music_weak_factor": 0.4,
            "speech_short_duration": 0.5,
            "speech_short_factor": 0.5
        }
    },
    "3": {
        "name": "🎵 음악/보컬",
        "suppress": {
            "silence_factor": 0.1,
            "generic_factor": 0.15,
            "music_short_duration": 1.0,
            "music_short_factor": 0.8,
            "music_dominance_ratio": 1.2,
            "music_weak_factor": 0.8,
            "speech_short_duration": 0.3,
            "speech_short_factor": 0.8
        }
    },
    "4": {
        "name": "🗣️ 음성/대사",
        "suppress": {
            "silence_factor": 0.1,
            "generic_factor": 0.15,
            "music_short_duration": 3.0,
            "music_short_factor": 0.2,
            "music_dominance_ratio": 2.0,
            "music_weak_factor": 0.4,
            "speech_short_duration": 0.1,
            "speech_short_factor": 1.0
        }
    },
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "config.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)
    print(f"✅ 설정 저장: {CONFIG_PATH}")


def print_current_config(cfg):
    s = cfg["suppress"]
    print(f"\n  현재 설정:")
    print(f"  ├─ Silence 억제:  ×{s['silence_factor']}")
    print(f"  ├─ Generic 억제:  ×{s['generic_factor']}")
    print(f"  ├─ Music 짧은기준: {s['music_short_duration']}s")
    print(f"  ├─ Music 짧은억제: ×{s['music_short_factor']}")
    print(f"  ├─ Music 지배비율: {s['music_dominance_ratio']}배")
    print(f"  ├─ Music 약한억제: ×{s['music_weak_factor']}")
    print(f"  ├─ Speech 짧은기준: {s['speech_short_duration']}s")
    print(f"  └─ Speech 짧은억제: ×{s['speech_short_factor']}")


def edit_config():
    cfg = load_config()
    if not cfg:
        print("⚠️ config.json 없음. 분류를 먼저 실행하세요.")
        return

    while True:
        print("\n" + "=" * 50)
        print("⚙️ 튜닝 설정")
        print("=" * 50)

        print_current_config(cfg)

        print(f"\n  프리셋:")
        for k, v in PRESETS.items():
            print(f"    {k}. {v['name']}")

        print(f"\n  M. 수동 조절")
        print(f"  0. 돌아가기")
        print("-" * 50)

        sel = input("  선택: ").strip()

        if sel == "0":
            break
        elif sel.upper() == "M":
            manual_edit(cfg)
        elif sel in PRESETS:
            cfg["suppress"] = PRESETS[sel]["suppress"].copy()
            print(f"\n  ✅ 프리셋 적용: {PRESETS[sel]['name']}")
            print_current_config(cfg)
            save_config(cfg)
        else:
            print("  ⚠️ 잘못된 입력")


def manual_edit(cfg):
    s = cfg["suppress"]
    params = [
        ("silence_factor",       "Silence 억제",    0.0, 1.0),
        ("generic_factor",       "Generic 억제",    0.0, 1.0),
        ("music_short_duration", "Music 짧은기준(초)", 0.1, 10.0),
        ("music_short_factor",   "Music 짧은억제",  0.0, 1.0),
        ("music_dominance_ratio","Music 지배비율",   1.0, 5.0),
        ("music_weak_factor",    "Music 약한억제",   0.0, 1.0),
        ("speech_short_duration","Speech 짧은기준(초)", 0.1, 5.0),
        ("speech_short_factor",  "Speech 짧은억제",  0.0, 1.0),
    ]

    print("\n  ── 수동 조절 (Enter=현재값 유지) ──\n")

    for key, label, min_v, max_v in params:
        current = s[key]
        val = input(f"  {label} [{current}] ({min_v}~{max_v}): ").strip()
        if val:
            try:
                val = float(val)
                if min_v <= val <= max_v:
                    s[key] = val
                else:
                    print(f"    ⚠️ 범위 초과, 현재값 유지")
            except ValueError:
                print(f"    ⚠️ 숫자가 아님, 현재값 유지")

    print_current_config(cfg)
    save_config(cfg)

def main():
    print("=" * 50)
    print("🔊 Sound Classifier v2.0.0 (AST)")
    print("=" * 50)
    print("  1. 🔊 폴더 분류 실행")
    print("  2. 📂 분류 결과 → 폴더로 복사")
    print("  3. 📦 분류 결과 → 폴더로 이동")
    print("  4. ⚡ 분류 + 폴더 복사 (한번에)")
    print("  5. 🔍 DB 조회")
    print("  6. ⚙️ 튜닝 설정")
    print("  0. ❌ 종료")
    print("-" * 50)

    choice = input("선택: ").strip()

    # ── classifier 로드 (모델은 __init__에서 자동 로드) ──
    from sound_classifier.classifier import SoundClassifier
    classifier = SoundClassifier()

    if choice == "1":
        folder = input("📂 분류할 사운드 폴더 경로: ").strip().strip('"')
        if not os.path.isdir(folder):
            print(f"❌ 폴더를 찾을 수 없습니다: {folder}")
            return
        force = input("🔄 이미 분류된 파일도 재분류? (y/N): ").strip().lower() == 'y'
        classifier.classify_folder(folder, force=force)

    elif choice == "2":
        out = input("📂 출력 폴더 (Enter=output): ").strip().strip('"') or "output"
        classifier.organize_files(output_dir=out, mode="copy")

    elif choice == "3":
        print("⚠️ 이동 시 원본이 삭제됩니다!")
        confirm = input("계속? (yes 입력): ").strip()
        if confirm != "yes":
            print("취소됨")
            return
        out = input("📂 출력 폴더 (Enter=output): ").strip().strip('"') or "output"
        classifier.organize_files(output_dir=out, mode="move")

    elif choice == "4":
        folder = input("📂 분류할 사운드 폴더 경로: ").strip().strip('"')
        if not os.path.isdir(folder):
            print(f"❌ 폴더를 찾을 수 없습니다: {folder}")
            return
        out = input("📂 출력 폴더 (Enter=output): ").strip().strip('"') or "output"
        force = input("🔄 이미 분류된 파일도 재분류? (y/N): ").strip().lower() == 'y'
        classifier.classify_folder(folder, force=force)
        classifier.organize_files(output_dir=out, mode="copy")

        # DB 조회는 classifier 불필요
    elif choice == "5":
        from db_viewer import db_viewer_main
        db_viewer_main()
        main()
        return

    elif choice == "6":
        edit_config()
        main()
        return

    elif choice == "0":
        print("\n✅ 종료!")
        return

    else:
        print("⚠️ 잘못된 입력")

    classifier.close()
    print("\n✅ 완료!")
    input("\n아무 키나 누르면 메뉴로 돌아갑니다...")
    main()


if __name__ == "__main__":
    main()