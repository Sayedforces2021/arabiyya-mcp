@echo off
chcp 65001 >nul
set PY=%USERPROFILE%\miniconda3\envs\sarf\python.exe
if not exist "%PY%" set PY=%LOCALAPPDATA%\miniconda3\envs\sarf\python.exe
if not exist "%PY%" set PY=%USERPROFILE%\anaconda3\envs\sarf\python.exe
set PYTHONUTF8=1
"%PY%" "%~dp0rename_arabiyya.py"
echo.
echo أغلق Claude تماما (Quit) ثم افتحه.
pause
