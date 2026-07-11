@echo off
set "PY312=%LocalAppData%\Programs\Python\Python312\python.exe"

echo Building Backend with PyInstaller...
if exist "%PY312%" (
  "%PY312%" -m PyInstaller backend.spec --noconfirm --distpath build_pyi
) else (
  py -3.12 -m PyInstaller backend.spec --noconfirm --distpath build_pyi
)

echo Building Frontend with Neutralino...
call neu.cmd build --release

echo Copying Backend to Neutralino dist...
xcopy /E /I /Y build_pyi\backend dist\bright-studio\backend

echo Done: dist\bright-studio\
