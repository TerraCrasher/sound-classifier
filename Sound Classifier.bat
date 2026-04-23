@echo off
chcp 65001 >nul
title Sound Classifier
cd /d "%~dp0"
venv\Scripts\python.exe run_classify.py %*
pause