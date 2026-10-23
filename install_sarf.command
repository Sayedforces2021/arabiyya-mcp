#!/bin/bash
# تثبيت أداة العربية (arabiyya) وربطها بـ Claude Desktop
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
# تُنسخ الأداة إلى مجلد دائم، فلا تتعطل إذا نُقل مجلد التنزيل أو حُذف
DIR="$HOME/.sarf/app"
mkdir -p "$DIR"
if [ "$SRC" != "$DIR" ]; then
  cp "$SRC"/*.py "$SRC"/openiti_catalog.tsv "$DIR"/
  mkdir -p "$DIR/brand" && cp "$SRC"/brand/*.svg "$DIR/brand/" 2>/dev/null || true
  # سجلّ الخلاف ووجوه الإعراب (أداة wujuh_irab)
  mkdir -p "$DIR/data/khilaf" && cp "$SRC"/data/khilaf/*.jsonl "$DIR/data/khilaf/"
fi
SERVER="$DIR/sarf_mcp.py"
CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

echo "== البحث عن conda =="
CONDA=""
for c in "$(command -v conda 2>/dev/null)" /opt/anaconda3/bin/conda "$HOME/anaconda3/bin/conda" \
         /opt/homebrew/anaconda3/bin/conda "$HOME/miniconda3/bin/conda" /opt/miniconda3/bin/conda \
         /opt/homebrew/Caskroom/miniconda/base/bin/conda; do
  if [ -n "$c" ] && [ -x "$c" ]; then CONDA="$c"; break; fi
done
if [ -z "$CONDA" ]; then echo "لم أجد conda. أرسل هذه الرسالة إلى Claude."; read -p "اضغط Enter للإغلاق"; exit 1; fi
echo "$CONDA"

echo "== إنشاء بيئة sarf (Python 3.11) =="
if ! "$CONDA" env list | grep -qE '^sarf[[:space:]]'; then
  "$CONDA" create -y -n sarf python=3.11
fi
PY="$("$CONDA" run -n sarf python -c 'import sys; print(sys.executable)')"
BIN="$(dirname "$PY")"
echo "$PY"

echo "== تثبيت CAMeL Tools وmcp =="
if ! "$PY" -m pip install -U camel-tools mcp beautifulsoup4; then
  echo "فشل التثبيت؛ أحاول تثبيت cmake وboost عبر Homebrew ثم أعيد"
  if command -v brew >/dev/null 2>&1 || [ -x /opt/homebrew/bin/brew ]; then
    BREW="$(command -v brew || echo /opt/homebrew/bin/brew)"
    "$BREW" install cmake boost
    "$PY" -m pip install -U camel-tools mcp beautifulsoup4
  else
    echo "Homebrew غير موجود. أرسل هذه الرسالة إلى Claude."; read -p "اضغط Enter للإغلاق"; exit 1
  fi
fi

echo "== تثبيت PyArud (العروض) =="
"$PY" -m pip install -U --ignore-requires-python --no-deps pyarud

echo "== تثبيت قطرب (التصريف) وpyarrow =="
"$PY" -m pip install -U libqutrub pyarrow stanza onnxruntime tqdm JPype1
"$PY" -m pip install -U --no-deps catt-tashkeel

echo "== تنزيل بيانات CAMeL (قد يستغرق دقائق) =="
"$BIN/camel_data" -i light
"$BIN/camel_data" -i disambig-bert-unfactored-msa

echo "== اختبار سريع =="
"$PY" - <<'EOF'
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
a = Analyzer(MorphologyDB.builtin_db()).analyze("كتب")[0]
print("OK:", a["diac"], a["root"], a["pattern"])
EOF

echo "== تجهيز البيانات: القرآن والمعاجم والشعر والنموذج الدلالي =="
"$PY" "$DIR/setup_sarf_data.py"

echo "== ربط الخادم بـ Claude Desktop =="
cp "$CONFIG" "$CONFIG.bak" 2>/dev/null || true
"$PY" - "$CONFIG" "$PY" "$SERVER" <<'EOF'
import json, sys, os
path, py, server = sys.argv[1:4]
cfg = {}
if os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
ext_dir = os.path.join(os.path.dirname(path), "Claude Extensions")
has_ext = os.path.isdir(ext_dir) and any("arabiyya" in d for d in os.listdir(ext_dir))
os.makedirs(os.path.expanduser("~/.sarf"), exist_ok=True)
with open(os.path.expanduser("~/.sarf/launch.json"), "w", encoding="utf-8") as f:
    json.dump({"python": py, "server": server}, f, ensure_ascii=False)
srv = cfg.setdefault("mcpServers", {})
srv.pop("sarf", None)
if has_ext:
    srv.pop("arabiyya", None)  # الإضافة مثبّتة فلا حاجة إلى السطر اليدوي
else:
    srv["arabiyya"] = {"command": py, "args": [server]}
with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print("أُضيفت أداة العربية (arabiyya) إلى", path)
EOF

echo
echo "تم. نُسخت الأداة إلى $DIR، فيمكنك حذف مجلد التنزيل."
echo "أغلق Claude تمامًا (⌘Q) ثم افتحه."
read -p "اضغط Enter للإغلاق"
