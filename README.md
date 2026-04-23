

# 🔊 Sound Classifier

AI 기반 사운드 파일 자동 분류 도구

AST (Audio Spectrogram Transformer) 모델을 사용하여 정리되지 않은 사운드 파일을 자동으로 분류합니다.

## 특징

- **AST 모델**: AudioSet 527클래스 자동 분류
- **GPU 지원**: CUDA 자동 감지
- **스마트 억제**: Silence/Generic/Music/Speech 지능형 필터링
- **외부 튜닝**: config.json으로 파라미터 조절
- **프리셋**: 게임효과음/환경음/음악/음성 프리셋 제공
- **폴더 정리**: 분류 결과를 폴더 구조로 자동 복사/이동
- **중복 스킵**: 이미 분류된 파일 자동 건너뛰기
- **GUI**: 분류 GUI + 사운드 브라우저 GUI

## 설치

### 요구사항

- Python 3.10 이상
- GPU 권장 (CPU도 가능)

### 설치 방법

```bash
git clone https://github.com/TerraCrasher/sound-classifier.git
cd sound-classifier
Install.bat 실행
```

### mp3 지원 (선택)

```bash
venv\Scripts\pip.exe install pydub
```

## 폴더 구조

```
SoundClassifier/
├── Install.bat                # 설치 스크립트
├── Sound Classifier.bat       # CLI 런처
├── Sound Classifier GUI.bat   # 분류 GUI 런처
├── Sound Browser GUI.bat      # 브라우저 런처
├── run_classify.py            # CLI 메인
├── gui_classify.py            # 분류 GUI
├── gui_browser.py             # 사운드 브라우저 GUI
├── db_viewer.py               # DB 조회/검색/CSV 내보내기
├── requirements.txt
├── LICENSE.txt
├── sound_classifier/
│   ├── __init__.py
│   ├── classifier.py          # AST 분류 엔진
│   ├── category_map.py        # AudioSet Ontology 자동 매핑
│   ├── tag_db.py              # SQLite DB 관리
│   └── utils.py               # 오디오 로드/변환 유틸
└── data/
    └── config.json            # 튜닝 설정 (자동 생성)
```

## 사용법

### Windows 바로 실행

| BAT 파일 | 기능 |
|----------|------|
| `Sound Classifier.bat` | CLI 메뉴 |
| `Sound Classifier GUI.bat` | 분류 GUI |
| `Sound Browser GUI.bat` | 브라우저 (검색/미리듣기) |

### CLI 메뉴

```bash
python run_classify.py
```

```
==================================================
🔊 Sound Classifier v2.0.0 (AST)
==================================================
  1. 폴더 분류 실행
  2. 분류 결과 → 폴더로 복사
  3. 분류 결과 → 폴더로 이동
  4. 분류 + 폴더 복사 (한번에)
  5. DB 조회
  6. 튜닝 설정
  0. 종료
```

### Python API

```python
from sound_classifier.classifier import SoundClassifier

classifier = SoundClassifier()

# 단일 파일 분류
result = classifier.classify_file("path/to/sound.wav")

# 폴더 일괄 분류
classifier.classify_folder("path/to/sounds/")

# 분류 결과 → 폴더로 정리
classifier.organize_files(output_dir="output", mode="copy")

classifier.close()
```

## 튜닝

### 프리셋

| 프리셋 | 용도 |
|--------|------|
| 🎮 게임 효과음 | 짧은 효과음 중심 |
| 🌿 환경음/폴리 | 자연/환경 사운드 |
| 🎵 음악/보컬 | 음악 파일 분류 |
| 🗣️ 음성/대사 | 음성/대화 분류 |

CLI에서 `6. 튜닝 설정` 선택 또는 `data/config.json` 직접 편집:

```json
{
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
    }
}
```

### 억제 파라미터

| 파라미터 | 설명 | 범위 |
|----------|------|------|
| silence_factor | 무음 구간 억제 강도 | 0.0~1.0 |
| generic_factor | 일반적 태그 억제 강도 | 0.0~1.0 |
| music_short_duration | 음악 억제 기준 길이(초) | 0.1~10.0 |
| music_short_factor | 짧은 파일 음악 억제 | 0.0~1.0 |
| music_dominance_ratio | 음악 우세 기준 배율 | 1.0~5.0 |
| music_weak_factor | 비우세 음악 억제 | 0.0~1.0 |
| speech_short_duration | 음성 억제 기준 길이(초) | 0.1~5.0 |
| speech_short_factor | 짧은 파일 음성 억제 | 0.0~1.0 |

## 분류 카테고리

AudioSet Ontology 기반 자동 매핑 (527클래스 → 대분류/중분류):

| 대분류 | 예시 |
|--------|------|
| 사람 | Speech, Singing, Laughter |
| 자연 | Wind, Rain, Thunder |
| 동물 | Bird, Dog, Cat |
| 음악 | Music, Guitar, Piano |
| 사물 | Engine, Door, Glass |
| 효과음 | Explosion, Whoosh, Crack |
| 환경 | Silence, Background |

## 지원 포맷

| 포맷 | 기본 지원 | 추가 설치 |
|------|-----------|-----------|
| wav | ✅ | - |
| flac | ✅ | - |
| ogg | ✅ | - |
| aiff | ✅ | - |
| mp3 | ⚠️ | `pydub` |

## 라이선스

MIT License
```

---
