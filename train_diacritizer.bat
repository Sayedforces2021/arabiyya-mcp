@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PY=%USERPROFILE%\miniconda3\envs\sarf\python.exe
if not exist "%PY%" set PY=%LOCALAPPDATA%\miniconda3\envs\sarf\python.exe
echo == تثبيت مكتبة التدريب على كرت الشاشة (نحو 3 غيغابايت) ==
"%PY%" -m pip install -U torch --index-url https://download.pytorch.org/whl/cu126
echo == تدريب مشكِّل الشعر (ساعات، ويُستأنف إن انقطع) ==
"%PY%" "%USERPROFILE%\claude\train_diacritizer.py"
echo.
echo انتهى. التقرير في %USERPROFILE%\.sarf\models\diac_ca\report.txt
pause
