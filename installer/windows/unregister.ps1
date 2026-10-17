# يُزيل خادم arabiyya من إعدادات Claude Desktop (يُشغَّله إلغاء التثبيت).
$configs = @("$env:APPDATA\Claude\claude_desktop_config.json")
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -Filter 'Claude_*' -ErrorAction SilentlyContinue | ForEach-Object {
  $configs += (Join-Path $_.FullName 'LocalCache\Roaming\Claude\claude_desktop_config.json')
}
foreach ($c in $configs) {
  if (-not (Test-Path $c)) { continue }
  try {
    $cfg = Get-Content $c -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($cfg.mcpServers -and $cfg.mcpServers.PSObject.Properties['arabiyya']) {
      $cfg.mcpServers.PSObject.Properties.Remove('arabiyya')
      $json = $cfg | ConvertTo-Json -Depth 30
      [IO.File]::WriteAllText($c, $json, (New-Object System.Text.UTF8Encoding($false)))
    }
  } catch {}
}
