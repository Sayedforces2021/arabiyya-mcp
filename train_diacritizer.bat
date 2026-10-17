@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PY=%USERPROFILE%\miniconda3\envs\sarf\python.exe
if not exist "%PY%" set PY=%LOCALAPPDATA%\miniconda3\envs\sarf\python.exe
set APP=%USERPROFILE%\claude
if not exist "%APP%\train_diacritizer.py" set APP=%~dp0
"%PY%" -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
if errorlevel 1 (
  echo == تثبيت مكتبة التدريب على كرت الشاشة ^(نحو 3 غيغابايت^) ==
  "%PY%" -m pip install -U torch --index-url https://download.pytorch.org/whl/cu126
)
echo == تدريب مشكِّل الشعر ^(ساعات؛ لا ينام الجهاز، ويعيد المحاولة وحده إن تعثّر^) ==
set TRY=1
:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%APP%\train_keepawake.ps1" -Py "%PY%" -Script "%APP%\train_diacritizer.py"
if not errorlevel 1 goto done
if %TRY% GEQ 5 goto failed
set /a TRY+=1
echo.
echo == تعثّر التدريب؛ أعيد المحاولة بعد نصف دقيقة ^(المحاولة %TRY% من 5^) وسيُستأنف من آخر نقطة ==
timeout /t 30 /nobreak >nul
goto run
:failed
echo.
echo تعذّر الإكمال بعد 5 محاولات. أرسل آخر سطور هذه النافذة، وسجلّ التدريب في %USERPROFILE%\.sarf\train_diac\train.log
pause
exit /b 1
:done
echo.
echo انتهى. التقرير في %USERPROFILE%\.sarf\models\diac_ca\report.txt
pause
