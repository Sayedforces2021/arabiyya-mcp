' يشغّل سكربت PowerShell دون إظهار أي نافذة، ولا ينتظر انتهاءه (ينتظره المعالج بقراءة ملف الحالة).
Set sh = CreateObject("WScript.Shell")
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & WScript.Arguments(0) & """ -Status """ & WScript.Arguments(1) & """ -AppDir """ & WScript.Arguments(2) & """"
If WScript.Arguments.Count > 3 Then cmd = cmd & " -Skip """ & WScript.Arguments(3) & """"
sh.Run cmd, 0, False
