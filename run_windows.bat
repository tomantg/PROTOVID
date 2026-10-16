@echo off
setlocal
cd /d "%~dp0"
if exist "dist\PROTOVID.exe" (start "" "dist\PROTOVID.exe" & exit /b 0)
if exist ".venv\Scripts\pythonw.exe" (start "" ".venv\Scripts\pythonw.exe" "protovid.py" & exit /b 0)
echo PROTOVID has not been built. Run build_windows.bat first.
pause
exit /b 1
