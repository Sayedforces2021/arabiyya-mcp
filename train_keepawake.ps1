# يشغّل التدريب ويمنع ويندوز من النوم ما دام التدريب يعمل (يزول المنع بانتهائه).
param([string]$Py, [string]$Script)
Add-Type -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);' -Name K -Namespace W
[void][W.K]::SetThreadExecutionState([uint32]2147483649)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
& $Py $Script
exit $LASTEXITCODE
