# يعيد تشغيل Claude Desktop ليقرأ الأداة (يعمل مع النسخة العادية ونسخة متجر Microsoft)
Stop-Process -Name Claude -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$app = Get-StartApps | Where-Object { $_.Name -like 'Claude*' } | Select-Object -First 1
if ($app) { Start-Process ("shell:AppsFolder\" + $app.AppID) }
