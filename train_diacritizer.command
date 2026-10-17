#!/bin/bash
# تدريب مشكِّل الشعر على ماك (كرت أبل). يمنع النوم، ويعيد المحاولة حتى 5 مرات، ويُستأنف من آخر نقطة.
export PYTHONUTF8=1
DIR="$HOME/.sarf/app"; [ -f "$DIR/train_diacritizer.py" ] || DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(python3 - <<'P'
import json,os
try: print(json.load(open(os.path.expanduser("~/.sarf/launch.json")))["python"])
except Exception: print("")
P
)"
[ -x "$PY" ] || { echo "لم أجد بيئة العربية. ثبّت الأداة أولًا."; read -p "اضغط Enter"; exit 1; }
for try in 1 2 3 4 5; do
  caffeinate -dimsu "$PY" "$DIR/train_diacritizer.py" && { echo; echo "انتهى. التقرير في ~/.sarf/models/diac_ca/report.txt"; read -p "اضغط Enter"; exit 0; }
  echo; echo "== تعثّر التدريب؛ أعيد المحاولة بعد نصف دقيقة (المحاولة $((try+1)) من 5) =="; sleep 30
done
echo "تعذّر الإكمال بعد 5 محاولات. أرسل آخر سطور النافذة؛ والسجلّ في ~/.sarf/train_diac/train.log"; read -p "اضغط Enter"; exit 1
