#!/bin/bash
# تثبيت صامت تشغّله نافذة «العربية» على ماك. يكتب التقدّم في ملف حالة: "NN|رسالة" ثم DONE| أو FAIL|سبب
# usage: install_wizard.sh STATUS_FILE APP_SRC_DIR [SKIP_PACKS]   مثل: semantic,catt,stanza
STATUS="${1:-/tmp/arabiyya_status.txt}"
SRC="${2:-$(cd "$(dirname "$0")" && pwd)}"
SKIP="${3:-}"
DIR="$HOME/.sarf/app"
LOG="$HOME/.sarf/install_log.txt"
mkdir -p "$HOME/.sarf"
: > "$STATUS"
exec >>"$LOG" 2>&1
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
say(){ printf '%s|%s\n' "$1" "$2" >> "$STATUS"; echo "== $1 $2"; }
fail(){ printf 'FAIL|%s\n' "$1" >> "$STATUS"; echo "FAIL: $1"; exit 1; }
trap 'fail "حدث خطأ غير متوقع"' ERR
set -e

say 10 "نسخ ملفات الأداة"
mkdir -p "$DIR/brand"
cp "$SRC"/*.py "$SRC"/openiti_catalog.tsv "$DIR"/
cp "$SRC"/brand/*.svg "$DIR/brand/" 2>/dev/null || true
mkdir -p "$DIR/data/khilaf" && cp "$SRC"/data/khilaf/*.jsonl "$DIR/data/khilaf/"
SERVER="$DIR/sarf_mcp.py"
CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

say 12 "البحث عن بيئة Python"
CONDA=""
for c in "$(command -v conda 2>/dev/null)" /opt/anaconda3/bin/conda "$HOME/anaconda3/bin/conda" \
         /opt/homebrew/anaconda3/bin/conda "$HOME/miniconda3/bin/conda" /opt/miniconda3/bin/conda \
         /opt/homebrew/Caskroom/miniconda/base/bin/conda; do
  if [ -n "$c" ] && [ -x "$c" ]; then CONDA="$c"; break; fi
done
if [ -z "$CONDA" ]; then
  say 14 "تنزيل Miniconda وتثبيته (نحو 100 ميغابايت)"
  case "$(uname -m)" in arm64) F=Miniconda3-latest-MacOSX-arm64.sh;; *) F=Miniconda3-latest-MacOSX-x86_64.sh;; esac
  curl -fsSL "https://repo.anaconda.com/miniconda/$F" -o "/tmp/$F" || fail "تعذّر تنزيل Miniconda، راجع الإنترنت"
  bash "/tmp/$F" -b -p "$HOME/miniconda3" || fail "تعذّر تثبيت Miniconda"
  CONDA="$HOME/miniconda3/bin/conda"
fi

say 18 "إنشاء بيئة Python 3.11 للأداة"
if ! "$CONDA" env list | grep -qE '^sarf[[:space:]]'; then
  "$CONDA" create -y -n sarf --override-channels -c conda-forge python=3.11 || fail "تعذّر إنشاء بيئة Python"
fi
PY="$("$CONDA" run -n sarf python -c 'import sys; print(sys.executable)' | tail -1)"
[ -x "$PY" ] || fail "لم أجد Python في البيئة"
BIN="$(dirname "$PY")"

say 36 "تثبيت أدوات التحليل الصرفي (CAMeL Tools)"
if ! "$PY" -m pip install camel-tools mcp beautifulsoup4; then
  BREW="$(command -v brew || echo /opt/homebrew/bin/brew)"
  if [ -x "$BREW" ]; then
    "$BREW" install cmake boost
    "$PY" -m pip install camel-tools mcp beautifulsoup4 || fail "تعذّر تثبيت CAMeL Tools"
  else
    CONDA_DIR="$(dirname "$(dirname "$CONDA")")"
    "$CONDA" install -y -n sarf --override-channels -c conda-forge cmake boost-cpp || true
    "$PY" -m pip install camel-tools mcp beautifulsoup4 || fail "تعذّر تثبيت CAMeL Tools (يلزم Homebrew)"
  fi
fi

say 46 "تثبيت أدوات العروض والتصريف والإعراب"
"$PY" -m pip install --ignore-requires-python --no-deps pyarud
"$PY" -m pip install libqutrub pyarrow stanza onnxruntime tqdm || fail "تعذّر تثبيت أدوات التصريف"
"$PY" -m pip install --no-deps catt-tashkeel

say 54 "تنزيل بيانات التحليل الصرفي (قد يستغرق دقائق)"
"$BIN/camel_data" -i light || fail "تعذّر تنزيل بيانات CAMeL"
"$BIN/camel_data" -i disambig-bert-unfactored-msa || fail "تعذّر تنزيل نموذج CAMeL"

say 62 "تجهيز القرآن والمعاجم والشعر والمدوّنة (أطول خطوة، لا تُغلق النافذة)"
DATA_ARGS=("$DIR/setup_sarf_data.py")
[ -n "$SKIP" ] && DATA_ARGS+=(--skip "$SKIP")
"$PY" "${DATA_ARGS[@]}" | while IFS= read -r line; do
  echo "$line"
  if [[ "$line" =~ ^\[ARABIYYA_STEP\ ([0-9]+)/([0-9]+)\ ([a-z]+)\] ]]; then
    i=${BASH_REMATCH[1]}; n=${BASH_REMATCH[2]}
    case "${BASH_REMATCH[3]}" in
      quran) nm="المدوّنة القرآنية";; maajim) nm="المعاجم التراثية";; poetry) nm="شواهد الشعر";;
      corpus) nm="المدوّنة التراثية";; semantic) nm="النموذج الدلالي (يحسب دقائق)";;
      lughawiyyat) nm="كتب الفروق والأضداد";; catt) nm="مشكِّل النصوص";; stanza) nm="محلل الإعراب";; *) nm="";;
    esac
    say $((62 + 32 * (i - 1) / n)) "تجهيز $nm (الحزمة $i من $n)"
  fi
done

say 96 "ربط الأداة بتطبيق Claude"
mkdir -p "$(dirname "$CONFIG")"
cp "$CONFIG" "$CONFIG.bak" 2>/dev/null || true
"$PY" - "$CONFIG" "$PY" "$SERVER" <<'EOF'
import json, sys, os
path, py, server = sys.argv[1:4]
cfg = {}
if os.path.exists(path):
    with open(path, encoding="utf-8-sig") as f:
        t = f.read().strip()
        cfg = json.loads(t) if t else {}
ext_dir = os.path.join(os.path.dirname(path), "Claude Extensions")
has_ext = os.path.isdir(ext_dir) and any("arabiyya" in d for d in os.listdir(ext_dir))
with open(os.path.expanduser("~/.sarf/launch.json"), "w", encoding="utf-8") as f:
    json.dump({"python": py, "server": server}, f, ensure_ascii=False)
srv = cfg.setdefault("mcpServers", {})
srv.pop("sarf", None)
if has_ext: srv.pop("arabiyya", None)
else: srv["arabiyya"] = {"command": py, "args": [server]}
with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
EOF
trap - ERR
echo "DONE|" >> "$STATUS"
