"""
오디오 파일 로드 / 변환 유틸리티
"""

import os
import numpy as np
import soundfile as sf
from scipy import signal

SUPPORTED_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".aiff", ".aif"}
TARGET_SR = 16000


def load_audio(file_path: str, target_sr: int = TARGET_SR):
    """
    오디오 파일 → 모노 float32 + 16 kHz 리샘플링

    Returns
    -------
    (waveform: np.ndarray, sample_rate: int, duration: float)
    """
    try:
        data, sr = sf.read(file_path, dtype="float32")
    except Exception:
        # mp3 등 soundfile 미지원 포맷 → pydub 폴백
        data, sr = _load_with_pydub(file_path)

    # 스테레오 → 모노
    if data.ndim > 1:
        data = data.mean(axis=1)

    # 리샘플링
    if sr != target_sr:
        num_samples = int(len(data) * target_sr / sr)
        data = signal.resample(data, num_samples)
        sr = target_sr

    # 정규화 (클리핑 방지)
    peak = np.abs(data).max()
    if peak > 0:
        data = data / peak

    duration = len(data) / sr
    return data, sr, duration


def _load_with_pydub(file_path: str):
    """pydub 폴백 로더 (mp3 등)"""
    try:
        from pydub import AudioSegment
    except ImportError:
        raise RuntimeError(
            f"'{file_path}' 로드 실패.\n"
            "mp3 파일 지원을 위해 pydub + ffmpeg를 설치하세요:\n"
            "  pip install pydub\n"
            "  + ffmpeg 설치 (https://ffmpeg.org)"
        )

    audio = AudioSegment.from_file(file_path)
    samples = np.array(audio.get_array_of_samples(), dtype="float32")
    samples = samples / (2 ** 15)  # 16-bit 정규화

    if audio.channels > 1:
        samples = samples.reshape(-1, audio.channels).mean(axis=1)

    return samples, audio.frame_rate


def scan_audio_files(root_dir: str, exclude_dirs: set = None) -> list:
    """
    지정 디렉토리에서 오디오 파일 재귀 탐색

    Args:
        root_dir: 탐색 루트 경로
        exclude_dirs: 제외할 디렉토리명 (기본: venv, output 등)

    Returns:
        오디오 파일 경로 리스트 (정렬됨)
    """
    if exclude_dirs is None:
        exclude_dirs = {"venv", "output", "__pycache__", ".git"}

    audio_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fname in filenames:
            if os.path.splitext(fname)[1].lower() in SUPPORTED_EXTENSIONS:
                audio_files.append(os.path.join(dirpath, fname))

    return sorted(audio_files)