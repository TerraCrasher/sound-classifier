@echo off
chcp 65001 >nul
title Sound Classifier - 설치
cd /d "%~dp0"

echo ========================================
echo  Sound Classifier 설치
echo ========================================
echo.

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo    https://www.python.org/downloads/ 에서 설치하세요.
    pause
    exit /b
)

:: venv 생성
if not exist "venv" (
    echo 📦 가상환경 생성 중...
    python -m venv venv
    echo ✅ 가상환경 생성 완료
) else (
    echo ✅ 가상환경 이미 존재
)

echo.
echo 📥 패키지 설치 중...
venv\Scripts\pip.exe install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt

echo.
echo ========================================
echo  ✅ 설치 완료!
echo ========================================
echo.
echo  실행 방법:
echo    Sound Classifier.bat     - CLI
echo    Sound Classifier GUI.bat - 분류 GUI
echo    Sound Browser GUI.bat    - 브라우저
echo.
pause