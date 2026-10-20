# تثبيت خادمي nusus والعربية (arabiyya) وربطهما بـ Claude Desktop على ويندوز 11
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Step($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }
function Fail($t) { Write-Host "`n$t" -ForegroundColor Red; Read-Host 'اضغط Enter للإغلاق'; exit 1 }

# ---------- 1. Node.js (لخادم nusus) ----------
Step 'فحص Node.js'
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node -and (Test-Path 'C:\Program Files\nodejs\node.exe')) { $env:Path += ';C:\Program Files\nodejs' ; $node = Get-Command node -ErrorAction SilentlyContinue }
$needNode = $true
if ($node) {
  $v = (& node -v) -replace '^v',''
  if ([int]($v.Split('.')[0]) -ge 20) { $needNode = $false; Write-Host "Node $v" }
}
if ($needNode) {
  Write-Host 'تثبيت Node.js LTS عبر winget...'
  winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
  $env:Path += ';C:\Program Files\nodejs'
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail 'تعذّر تثبيت Node.js. أرسل هذه الرسالة إلى Claude.' }
}

# ---------- 2. conda ----------
Step 'البحث عن conda'
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
  Write-Host 'تثبيت Miniconda عبر winget...'
  winget install -e --id Anaconda.Miniconda3 --accept-package-agreements --accept-source-agreements
  $conda = $condaCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $conda) { Fail 'تعذّر العثور على conda بعد التثبيت. أرسل هذه الرسالة إلى Claude.' }
}
Write-Host $conda

# ---------- 3. بيئة sarf ----------
Step 'إنشاء بيئة sarf (Python 3.11)'
$envList = & $conda env list
if (-not ($envList | Select-String -Pattern '^sarf\s')) {
  # قناة conda-forge المجانية، فلا يلزم قبول شروط قنوات Anaconda
  & $conda create -y -n sarf --override-channels -c conda-forge python=3.11
  if ($LASTEXITCODE -ne 0) { Fail 'تعذّر إنشاء بيئة sarf. أرسل ما فوق هذه الرسالة إلى Claude.' }
}
$pyOut = & $conda run -n sarf python -c "import sys; print(sys.executable)"
if (-not $pyOut) { Fail 'لم أجد Python البيئة sarf. أرسل ما فوق هذه الرسالة إلى Claude.' }
$Py = ($pyOut | Select-Object -Last 1).Trim()
if (-not (Test-Path $Py)) { Fail "لم أجد Python البيئة: $Py" }
$Scripts = Join-Path (Split-Path $Py) 'Scripts'
Write-Host $Py

Step 'تثبيت CAMeL Tools وmcp'
& $Py -m pip install -U pip
& $Py -m pip install -U torch --index-url https://download.pytorch.org/whl/cpu
& $Py -m pip install -U camel-tools mcp beautifulsoup4
if ($LASTEXITCODE -ne 0) { Fail 'فشل تثبيت CAMeL Tools. أرسل ما فوق هذه الرسالة إلى Claude.' }

Step 'تثبيت PyArud (العروض)'
& $Py -m pip install -U --ignore-requires-python --no-deps pyarud

Step 'تثبيت قطرب (التصريف) وpyarrow وStanza (الإعراب)'
& $Py -m pip install -U libqutrub pyarrow stanza onnxruntime tqdm JPype1
& $Py -m pip install -U --no-deps catt-tashkeel

Step 'تنزيل بيانات CAMeL (قد يستغرق دقائق)'
& (Join-Path $Scripts 'camel_data.exe') -i light
& (Join-Path $Scripts 'camel_data.exe') -i disambig-bert-unfactored-msa

# ---------- 4. نسخ الخادم ----------
Step 'نسخ ملف الخادم'
$Dest = Join-Path $env:USERPROFILE 'claude'
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item (Join-Path $Here 'sarf_mcp.py') (Join-Path $Dest 'sarf_mcp.py') -Force
foreach ($f in 'sarf_ilal.py','diac_model.py','train_diacritizer.py','build_poetry_index.py','build_lexicon_index.py','build_corpus_index.py','import_shamela.py','setup_sarf_data.py','openiti_catalog.tsv') {
  Copy-Item (Join-Path $Here $f) (Join-Path $Dest $f) -Force
}
$Server = Join-Path $Dest 'sarf_mcp.py'
Write-Host $Server

Step 'اختبار سريع'
& $Py -c "from camel_tools.morphology.database import MorphologyDB; from camel_tools.morphology.analyzer import Analyzer; a=Analyzer(MorphologyDB.builtin_db()).analyze('\u0643\u062a\u0628')[0]; print('OK:', a['diac'], a['root'])"

Step 'تجهيز البيانات: القرآن والمعاجم والشعر والمدوّنة والنماذج'
& $Py (Join-Path $Dest 'setup_sarf_data.py')

# ---------- 5. إعدادات Claude Desktop ----------
Step 'ربط الخادمين بـ Claude Desktop'
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
servers["nusus"] = {"command": "cmd", "args": ["/c", "npx", "-y", "nusus-mcp"]}
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
$mergeFile = Join-Path $env:TEMP 'sarf_merge_config.py'
Set-Content -Path $mergeFile -Value $merge -Encoding UTF8
$done = $false
foreach ($c in $configs) {
  if ((Test-Path $c) -or (Test-Path (Split-Path $c))) {
    if (Test-Path $c) { Copy-Item $c "$c.bak" -Force }
    & $Py $mergeFile $c $Py $Server
    $done = $true
  }
}
if (-not $done) { & $Py $mergeFile $configs[0] $Py $Server }

Write-Host "`nتم. أغلق Claude تمامًا (من أيقونته بجانب الساعة: Quit) ثم افتحه." -ForegroundColor Green
Read-Host 'اضغط Enter للإغلاق'
