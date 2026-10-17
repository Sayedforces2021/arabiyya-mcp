# سكربت التثبيت الصامت الذي يشغّله معالج ويندوز (arabiyya-setup-windows.exe).
# لا يسأل المستخدم ولا يفتح نوافذ: يكتب تقدّمه في ملف حالة يقرؤه المعالج.
# صيغة أسطر الملف: "NN|رسالة" (NN بين 10 و99)، وفي النهاية "DONE|" أو "FAIL|سبب".
param(
  [string]$Status = (Join-Path $env:TEMP 'arabiyya_status.txt'),
  [string]$AppDir = (Join-Path $env:USERPROFILE 'claude'),
  [string]$Skip = ''   # حزم بيانات تُترك، مثل: semantic,catt,stanza
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$Log = Join-Path $env:USERPROFILE 'arabiyya_install_log.txt'
try { Start-Transcript -Path $Log -Force | Out-Null } catch {}
$utf16 = New-Object System.Text.UnicodeEncoding($false, $false)
[IO.File]::WriteAllText($Status, '', $utf16)

function Say([int]$n, [string]$t) { [IO.File]::AppendAllText($Status, ("{0}|{1}`r`n" -f $n, $t), $utf16) }
function Check([string]$what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)" } }

try {
  # ---------- 1. conda ----------
  Say 10 'البحث عن بيئة Python'
  $condaCandidates = @(
    "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
    "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
    "$env:LOCALAPPDATA\miniconda3\Scripts\conda.exe",
    "$env:LOCALAPPDATA\anaconda3\Scripts\conda.exe",
    'C:\ProgramData\miniconda3\Scripts\conda.exe',
    'C:\ProgramData\anaconda3\Scripts\conda.exe'
  )
  $conda = $condaCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $conda) {
    Say 12 'تنزيل Miniconda وتثبيته (نحو 100 ميغابايت)'
    $inst = Join-Path $env:TEMP 'Miniconda3-latest-Windows-x86_64.exe'
    Invoke-WebRequest 'https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe' -OutFile $inst -UseBasicParsing
    Start-Process $inst -ArgumentList '/InstallationType=JustMe', '/RegisterPython=0', '/AddToPath=0', '/S', "/D=$env:USERPROFILE\miniconda3" -Wait
    $conda = $condaCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $conda) { throw 'Miniconda was not found after installation' }
  }

  # ---------- 2. بيئة sarf ----------
  Say 18 'إنشاء بيئة Python 3.11 للأداة'
  $envList = & $conda env list
  if (-not ($envList | Select-String -Pattern '^sarf\s')) {
    & $conda create -y -n sarf --override-channels -c conda-forge python=3.11
    Check 'conda create'
  }
  $pyOut = & $conda run -n sarf python -c "import sys; print(sys.executable)"
  if (-not $pyOut) { throw 'Python of env sarf was not found' }
  $Py = ($pyOut | Select-Object -Last 1).Trim()
  if (-not (Test-Path $Py)) { throw "Python not found: $Py" }
  $Scripts = Join-Path (Split-Path $Py) 'Scripts'

  Say 24 'تثبيت أدوات الذكاء الاصطناعي (PyTorch)'
  & $Py -m pip install -U pip
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  & $Py -c "import torch" 2>$null
  $hasTorch = ($LASTEXITCODE -eq 0)
  $ErrorActionPreference = $old
  if (-not $hasTorch) {
    & $Py -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    Check 'pip install torch'
  }

  Say 36 'تثبيت أدوات التحليل الصرفي (CAMeL Tools)'
  & $Py -m pip install camel-tools mcp beautifulsoup4
  Check 'pip install camel-tools'

  Say 46 'تثبيت أدوات العروض والتصريف والإعراب'
  & $Py -m pip install --ignore-requires-python --no-deps pyarud
  & $Py -m pip install libqutrub pyarrow stanza onnxruntime tqdm
  Check 'pip install libqutrub/stanza'
  & $Py -m pip install --no-deps catt-tashkeel

  Say 54 'تنزيل بيانات التحليل الصرفي (قد يستغرق دقائق)'
  & (Join-Path $Scripts 'camel_data.exe') -i light
  Check 'camel_data light'
  & (Join-Path $Scripts 'camel_data.exe') -i disambig-bert-unfactored-msa
  Check 'camel_data bert'

  # ---------- 3. البيانات ----------
  $Server = Join-Path $AppDir 'sarf_mcp.py'
  if (-not (Test-Path $Server)) { throw "Server file missing: $Server" }
  Say 62 'تجهيز القرآن والمعاجم والشعر والمدوّنة (أطول خطوة، لا تُغلق النافذة)'
  $names = @{ quran='المدوّنة القرآنية'; maajim='المعاجم التراثية'; poetry='شواهد الشعر'; corpus='المدوّنة التراثية';
              semantic='النموذج الدلالي (يحسب دقائق)'; lughawiyyat='كتب الفروق والأضداد'; catt='مشكِّل النصوص'; stanza='محلل الإعراب' }
  $dataArgs = @((Join-Path $AppDir 'setup_sarf_data.py'))
  if ($Skip) { $dataArgs += @('--skip', $Skip) }
  & $Py @dataArgs | ForEach-Object {
    $line = "$_"
    if ($line -match '^\[ARABIYYA_STEP (\d+)/(\d+) (\w+)\]') {
      $i = [int]$Matches[1]; $n = [int]$Matches[2]
      $pct = 62 + [int](32 * ($i - 1) / $n)
      Say $pct ("تجهيز {0} (الحزمة {1} من {2})" -f $names[$Matches[3]], $i, $n)
    }
    $line
  }
  if ($LASTEXITCODE -ne 0) { throw "setup_sarf_data failed (exit code $LASTEXITCODE)" }

  # ---------- 4. الربط بـ Claude Desktop ----------
  Say 96 'ربط الأداة بتطبيق Claude'
  $configs = @("$env:APPDATA\Claude\claude_desktop_config.json")
  Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -Filter 'Claude_*' -ErrorAction SilentlyContinue | ForEach-Object {
    $configs += (Join-Path $_.FullName 'LocalCache\Roaming\Claude\claude_desktop_config.json')
  }
  $merge = @'
import json, os, sys
path, py, server = sys.argv[1:4]
cfg = {}
if os.path.exists(path):
    with open(path, encoding="utf-8-sig") as f:
        txt = f.read().strip()
        cfg = json.loads(txt) if txt else {}
ext_dir = os.path.join(os.path.dirname(path), "Claude Extensions")
has_ext = os.path.isdir(ext_dir) and any("arabiyya" in d for d in os.listdir(ext_dir))
os.makedirs(os.path.expanduser("~/.sarf"), exist_ok=True)
with open(os.path.expanduser("~/.sarf/launch.json"), "w", encoding="utf-8") as f:
    json.dump({"python": py, "server": server}, f, ensure_ascii=False)
servers = cfg.setdefault("mcpServers", {})
servers.pop("sarf", None)
if has_ext:
    servers.pop("arabiyya", None)
else:
    servers["arabiyya"] = {"command": py, "args": [server]}
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print("updated:", path)
'@
  $mergeFile = Join-Path $env:TEMP 'arabiyya_merge_config.py'
  [IO.File]::WriteAllText($mergeFile, $merge, (New-Object System.Text.UTF8Encoding($false)))
  $done = $false
  foreach ($c in $configs) {
    if ((Test-Path $c) -or (Test-Path (Split-Path $c))) {
      if (Test-Path $c) { Copy-Item $c "$c.bak" -Force }
      & $Py $mergeFile $c $Py $Server
      Check 'merge config'
      $done = $true
    }
  }
  if (-not $done) { & $Py $mergeFile $configs[0] $Py $Server; Check 'merge config' }

  [IO.File]::AppendAllText($Status, "DONE|`r`n", $utf16)
  try { Stop-Transcript | Out-Null } catch {}
  exit 0
}
catch {
  $msg = ($_.Exception.Message -split "`n")[0]
  [IO.File]::AppendAllText($Status, "FAIL|$msg`r`n", $utf16)
  try { Stop-Transcript | Out-Null } catch {}
  exit 1
}
