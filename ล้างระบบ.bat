@echo off
echo Clearing old background processes...
taskkill /F /IM bright-studio-win_x64.exe 2>nul
taskkill /F /IM heaven-send-studio-win_x64.exe 2>nul
taskkill /F /IM backend.exe 2>nul

echo Clearing Neutralino temp directory...
if exist "dist\bright-studio\.tmp" (
    rmdir /S /Q "dist\bright-studio\.tmp"
    echo Done.
) else (
    echo No temp folder found.
)

echo System cleared successfully! Please try opening the app again.
pause
