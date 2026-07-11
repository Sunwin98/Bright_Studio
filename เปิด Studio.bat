@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Bright Studio
echo Starting Bright Studio...
set "PY312=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%PY312%" (
  "%PY312%" run.py
) else (
  py -3.12 run.py
  if errorlevel 1 python run.py
)
pause
