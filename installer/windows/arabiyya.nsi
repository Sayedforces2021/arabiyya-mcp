; معالج تثبيت «العربية» لويندوز (NSIS). يُبنى بـ: makensis -DROOT=../.. arabiyya.nsi
Unicode True
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"

!ifndef ROOT
  !define ROOT "../.."
!endif
!ifndef VERSION
  !define VERSION "1.3.0"
!endif

Name "العربية"
OutFile "arabiyya-setup-windows.exe"
InstallDir "$PROFILE\claude"
RequestExecutionLevel user
BrandingText "أداة العربية — سيد حسن رجب"
ShowInstDetails nevershow
SetCompressor /SOLID lzma

VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1025 "ProductName" "العربية"
VIAddVersionKey /LANG=1025 "FileDescription" "معالج تثبيت أداة العربية"
VIAddVersionKey /LANG=1025 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1025 "LegalCopyright" "MIT — سيد حسن رجب"

!define MUI_ICON "arabiyya.ico"
!define MUI_UNICON "arabiyya.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "wizard.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "wizard.bmp"
!define MUI_ABORTWARNING
!define MUI_ABORTWARNING_TEXT "أتريد إيقاف التثبيت؟"

!define MUI_WELCOMEPAGE_TITLE "مرحبًا بك في «العربية»"
!define MUI_WELCOMEPAGE_TEXT "ستثبّت هذه النافذة أداة «العربية» وتربطها بتطبيق Claude تلقائيًّا، فيجيب Claude عن أسئلتك في النحو والصرف والعروض والمعاجم من مصادرها التراثية.$\r$\n$\r$\nما الذي سيحدث؟ تنزيل بيئة Python والمكتبات والبيانات، وتحتاج إلى نحو 4 غيغابايت من المساحة وإلى اتصال بالإنترنت. وتستغرق من 30 إلى 60 دقيقة بحسب سرعة الاتصال. ولا تحتاج أن تفعل شيئًا أثناء ذلك.$\r$\n$\r$\nلا تُغلق النافذة ولا تُطفئ الجهاز حتى ينتهي التثبيت."

!define MUI_FINISHPAGE_TITLE "اكتمل التثبيت"
!define MUI_FINISHPAGE_TEXT "رُبطت أداة «العربية» بتطبيق Claude.$\r$\n$\r$\nافتح Claude وجرّب أن تكتب له: «أعرب: العلمُ نورٌ».$\r$\n$\r$\nلتظهر الأداة يلزم إعادة تشغيل Claude: اترك الخيار أدناه مفعّلًا، أو أغلقه تمامًا (من أيقونته بجانب الساعة: Quit) ثم افتحه."

!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_RUN_TEXT "أعد تشغيل Claude الآن (احفظ عملك فيه أولًا)"
!define MUI_FINISHPAGE_RUN_FUNCTION RestartClaude

!insertmacro MUI_PAGE_WELCOME
Page custom PacksCreate PacksLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!define MUI_UNCONFIRMPAGE_TEXT_TOP "ستُزال أداة «العربية» من جهازك ومن إعدادات Claude."
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Arabic"

Var LastMsg
Var Ticks
Var Line
Var Tmp
Var Pct
Var Msg
Var Bar
Var Mins
Var RbFull
Var RbQuick
Var SkipArg

Function PacksCreate
  !insertmacro MUI_HEADER_TEXT "اختيار الحزم" "اختر ما تنزّله من البيانات"
  nsDialogs::Create 1018
  Pop $0
  ${NSD_CreateRadioButton} 0 6u 100% 12u "كامل (موصى به): الأدوات السبع والثلاثون كلها — نحو 4 غيغابايت"
  Pop $RbFull
  ${NSD_AddStyle} $RbFull ${WS_GROUP}
  ${NSD_Check} $RbFull
  ${NSD_CreateRadioButton} 0 26u 100% 24u "سريع: القرآن والمعاجم والشعر والمدوّنة وكتب اللغة، بلا دلالة الألفاظ والتشكيل الآلي والإعراب — نحو 2.5 غيغابايت"
  Pop $RbQuick
  ${NSD_CreateLabel} 0 62u 100% 36u "الأدوات المتعلقة بما تتركه لا تعمل. وتستطيع إضافته في أي وقت بتشغيل المعالج من جديد؛ فهو يتخطى ما نُزّل ويكمل الناقص."
  Pop $0
  nsDialogs::Show
FunctionEnd

Function PacksLeave
  ${NSD_GetState} $RbQuick $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $SkipArg "semantic,catt,stanza"
  ${Else}
    StrCpy $SkipArg ""
  ${EndIf}
FunctionEnd

Function RestartClaude
  Exec 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$INSTDIR\restart_claude.ps1"'
FunctionEnd

; ----- يقرأ آخر سطر في ملف الحالة (UTF-16) إلى $Line -----
Function ReadLastLine
  StrCpy $Line ""
  ClearErrors
  FileOpen $0 "$TEMP\arabiyya_status.txt" r
  IfErrors rl_done
  rl_loop:
    ClearErrors
    FileReadUTF16LE $0 $1
    IfErrors rl_close
    StrCpy $2 $1 1
    StrCmp $2 "$\r" rl_loop
    StrCmp $2 "$\n" rl_loop
    StrCmp $2 "" rl_loop
    StrCpy $Line $1
    Goto rl_loop
  rl_close:
    FileClose $0
  rl_done:
  ; نزع نهاية السطر
  rl_trim:
    StrCpy $2 $Line 1 -1
    StrCmp $2 "$\r" rl_cut
    StrCmp $2 "$\n" rl_cut
    Goto rl_end
  rl_cut:
    StrCpy $Line $Line -1
    Goto rl_trim
  rl_end:
FunctionEnd

Function ClaudeInstalled
  ; يضع 1 في $0 إن وجد Claude Desktop
  StrCpy $0 0
  IfFileExists "$LOCALAPPDATA\AnthropicClaude\*.*" found
  IfFileExists "$APPDATA\Claude\*.*" found
  FindFirst $1 $2 "$LOCALAPPDATA\Packages\Claude_*"
  StrCmp $2 "" nomsix found_msix
  found_msix:
    FindClose $1
    Goto found
  nomsix:
    FindClose $1
    Goto end
  found:
    StrCpy $0 1
  end:
FunctionEnd

Section "Install"
  ; ---- 1) هل Claude موجود؟ ----
  Call ClaudeInstalled
  ${If} $0 == 0
    MessageBox MB_YESNO|MB_ICONEXCLAMATION "لم أجد تطبيق Claude على هذا الجهاز.$\r$\n$\r$\nالأداة تعمل من داخل Claude. يمكنك إكمال التثبيت الآن ثم تنزيل Claude من الموقع claude.ai/download بعد ذلك.$\r$\n$\r$\nأتريد المتابعة؟" IDYES +2
    Abort
  ${EndIf}

  ; ---- 2) نسخ ملفات الأداة ----
  !insertmacro MUI_HEADER_TEXT "جارٍ التثبيت" "نسخ ملفات الأداة"
  SetOutPath "$INSTDIR"
  File "${ROOT}/sarf_mcp.py"
  File "${ROOT}/sarf_ilal.py"
  File "${ROOT}/diac_model.py"
  File "${ROOT}/train_diacritizer.py"
  File "${ROOT}/build_poetry_index.py"
  File "${ROOT}/build_lexicon_index.py"
  File "${ROOT}/build_corpus_index.py"
  File "${ROOT}/setup_sarf_data.py"
  File "${ROOT}/openiti_catalog.tsv"
  File "unregister.ps1"
  File "restart_claude.ps1"
  SetOutPath "$INSTDIR\brand"
  File "${ROOT}/brand/arabiyya-icon.svg"
  File "${ROOT}/brand/arabiyya-icon-small.svg"
  File "${ROOT}/brand/arabiyya-mark.svg"

  InitPluginsDir
  File "/oname=$PLUGINSDIR\install.ps1" "install_wizard.ps1"
  File "/oname=$PLUGINSDIR\run.vbs" "run.vbs"

  ; ---- 3) تشغيل التثبيت الصامت ومتابعة تقدّمه ----
  Delete "$TEMP\arabiyya_status.txt"
  Exec 'wscript.exe //B "$PLUGINSDIR\run.vbs" "$PLUGINSDIR\install.ps1" "$TEMP\arabiyya_status.txt" "$INSTDIR" "$SkipArg"'

  FindWindow $Bar "#32770" "" $HWNDPARENT
  GetDlgItem $Bar $Bar 1004
  SendMessage $Bar 1030 10 99      ; PBM_SETRANGE32: من 10 إلى 99
  SendMessage $Bar 1026 10 0       ; PBM_SETPOS

  StrCpy $LastMsg ""
  StrCpy $Ticks 0
  poll:
    Sleep 1000
    IntOp $Ticks $Ticks + 1
    Call ReadLastLine
    StrCmp $Line "" nostatus
    StrCpy $Tmp $Line 4
    StrCmp $Tmp "DONE" finished
    StrCmp $Tmp "FAIL" failed
    StrCpy $Pct $Line 2
    StrCpy $Msg $Line "" 3
    IntOp $Mins $Ticks / 60
    ${If} $Msg != $LastMsg
      DetailPrint "$Msg"
      StrCpy $LastMsg $Msg
      SendMessage $Bar 1026 $Pct 0
    ${EndIf}
    ${If} $Mins > 0
      !insertmacro MUI_HEADER_TEXT "جارٍ التثبيت (مضت $Mins دقيقة)" "$Msg"
    ${Else}
      !insertmacro MUI_HEADER_TEXT "جارٍ التثبيت" "$Msg"
    ${EndIf}
  nostatus:
    ; مهلة قصوى: أربع ساعات
    ${If} $Ticks > 14400
      MessageBox MB_ICONSTOP "طال التثبيت أكثر من المعتاد فأوقفتُه.$\r$\nراجع اتصالك بالإنترنت ثم أعد المحاولة."
      Abort
    ${EndIf}
    Goto poll

  failed:
    StrCpy $Msg $Line "" 5
    MessageBox MB_ICONSTOP "تعذّر إكمال التثبيت.$\r$\n$\r$\nالسبب: $Msg$\r$\n$\r$\nحُفظ سجلٌّ مفصّل في:$\r$\n$PROFILE\arabiyya_install_log.txt$\r$\n$\r$\nأرسله إلى سيد حسن (x.com/ikagi07) ليساعدك."
    Abort

  finished:
    SendMessage $Bar 1026 99 0
    DetailPrint "اكتمل التثبيت"

  ; ---- 4) مُزيل التثبيت وإدخاله في «التطبيقات المثبّتة» ----
  WriteUninstaller "$INSTDIR\uninstall-arabiyya.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "DisplayName" "العربية"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "Publisher" "سيد حسن رجب"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "DisplayIcon" "$INSTDIR\uninstall-arabiyya.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "URLInfoAbout" "https://ikagi07.github.io/arabiyya-mcp/"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "UninstallString" '"$INSTDIR\uninstall-arabiyya.exe"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya" "NoRepair" 1
SectionEnd

Section "Uninstall"
  nsExec::Exec 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$INSTDIR\unregister.ps1"'
  Delete "$INSTDIR\*.py"
  Delete "$INSTDIR\openiti_catalog.tsv"
  Delete "$INSTDIR\unregister.ps1"
  Delete "$INSTDIR\restart_claude.ps1"
  RMDir /r "$INSTDIR\brand"
  Delete "$INSTDIR\uninstall-arabiyya.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arabiyya"
  MessageBox MB_YESNO|MB_ICONQUESTION "أتريد حذف بيانات الأداة أيضًا (المعاجم والمدوّنة والنماذج)؟$\r$\nتشغل نحو غيغابايتين، وستُنزَّل من جديد إن أعدت التثبيت." IDNO +2
  RMDir /r "$PROFILE\.sarf"
SectionEnd
