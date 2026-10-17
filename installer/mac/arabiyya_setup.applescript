-- معالج تثبيت «العربية» لماك (AppleScript). يُبنى بـ build_mac.sh
use framework "Foundation"
use scripting additions

on run
	set appPath to POSIX path of (path to me)
	set payload to appPath & "Contents/Resources/payload"
	set statusFile to "/tmp/arabiyya_status.txt"
	
	set welcome to "ستثبّت هذه النافذة أداة «العربية» وتربطها بتطبيق Claude تلقائيًّا." & return & return & "تنزيل بيئة Python والمكتبات والبيانات، وتحتاج إلى نحو 4 غيغابايت من المساحة وإلى اتصال بالإنترنت، وتستغرق من 30 إلى 60 دقيقة. لا تُغلق النافذة ولا تُطفئ الجهاز حتى ينتهي التثبيت."
	set skipArg to ""
	try
		display dialog welcome & return & return & "اختر ما تنزّله:" & return & "• كامل: الأدوات السبع والثلاثون كلها، نحو 4 غيغابايت." & return & "• سريع: بلا دلالة الألفاظ والتشكيل الآلي والإعراب، نحو 2.5 غيغابايت (تضيفها لاحقًا بإعادة تشغيل المعالج)." with title "العربية" buttons {"إلغاء", "سريع", "كامل"} default button "كامل" cancel button "إلغاء" with icon note
		if button returned of result is "سريع" then set skipArg to "semantic,catt,stanza"
	on error
		return
	end try
	
	do shell script "rm -f " & quoted form of statusFile & "; touch " & quoted form of statusFile
	do shell script "nohup bash " & quoted form of (payload & "/install_wizard.sh") & " " & quoted form of statusFile & " " & quoted form of payload & " " & quoted form of skipArg & " >/dev/null 2>&1 &"
	
	set progress total steps to 90
	set progress completed steps to 0
	set progress description to "جارٍ تثبيت العربية"
	set progress additional description to "بدء التثبيت…"
	
	set ticks to 0
	set lastMsg to ""
	repeat
		delay 2
		set ticks to ticks + 2
		try
			set stLine to do shell script "tail -n 1 " & quoted form of statusFile & " | tr -d '\\r' | iconv -f UTF-8 -t UTF-8 2>/dev/null"
		on error
			set stLine to ""
		end try
		if stLine starts with "DONE" then exit repeat
		if stLine starts with "FAIL" then
			set reason to text 6 thru -1 of stLine
			set progress total steps to 0
			display dialog "تعذّر إكمال التثبيت." & return & return & "السبب: " & reason & return & return & "سجلٌّ مفصّل في: ~/.sarf/install_log.txt" & return & "أرسله إلى سيد حسن (x.com/ikagi07) ليساعدك." with title "العربية" buttons {"حسنًا"} default button "حسنًا" with icon stop
			return
		end if
		if stLine is not "" and (character 3 of stLine) is "|" then
			set pct to (text 1 thru 2 of stLine) as integer
			set msg to text 4 thru -1 of stLine
			set progress completed steps to pct - 10
			set mins to ticks div 60
			if mins > 0 then
				set progress additional description to msg & "  (مضت " & mins & " دقيقة)"
			else
				set progress additional description to msg
			end if
		end if
		if ticks > 14400 then
			display dialog "طال التثبيت أكثر من المعتاد. راجع اتصالك بالإنترنت ثم أعد المحاولة." with title "العربية" buttons {"حسنًا"} with icon stop
			return
		end if
	end repeat
	
	set progress completed steps to 90
	display dialog "اكتمل التثبيت." & return & return & "لتظهر الأداة يلزم إعادة تشغيل Claude (احفظ عملك فيه أولًا). وبعدها جرّب أن تكتب له: «أعرب: العلمُ نورٌ»." with title "العربية" buttons {"لاحقًا", "أعد تشغيل Claude"} default button "أعد تشغيل Claude" with icon note
	if button returned of result is "أعد تشغيل Claude" then
		try
			tell application "Claude" to quit
			delay 3
			do shell script "open -a Claude"
		end try
	end if
end run
