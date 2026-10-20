#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يُجري المحلّل المدرَّب (~/.sarf/models/irab_parser/model.pt) على جمل اختبار ويطبع أعلى الوسوم لكل كلمة.
الغرض: مقارنة المحلّل الجديد بأداة irab القديمة على الجمل ذات الخلل المعروف. قراءة فقط؛ لا يعدّل شيئًا.
التشغيل:  python eval/irab_probe.py [--out ~/.sarf/models/irab_parser] [--top 3] [جمل…]"""
import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
import train_irab as T

DEFAULT = [
    "ذهبتُ إلى السوقِ لأشتريَ خبزًا",            # لام التعليل (لا لام الأمر)
    "لِيُنفقْ ذو سعةٍ من سعتِه",                 # لام الأمر
    "مَن يجتهدْ ينجحْ",                            # مَن الشرطية
    "مَن جاءَ؟",                                   # مَن الاستفهامية
    "إنّ البيتَ لا عمادَ له",                       # «عماد» اسم لا النافية للجنس، لا اسم إنّ
    "ما قامَ القومُ إلا زيدًا",                    # استثناء
    "استوى الماءُ والخشبةَ",                       # مفعول معه
    "جاء الأميرُ والجيشُ",                         # عطف
    "كتب الطالبُ الدرسَ",                          # فاعل/مفعول
    "كتبَ الدرسَ الطالبُ",                         # تقديم المفعول
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path.home() / ".sarf" / "models" / "irab_parser"))
    ap.add_argument("--model", default=T.MODEL_NAME)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--json", default=None, help="اكتب النتائج JSON إلى هذا الملف")
    ap.add_argument("sentences", nargs="*")
    a = ap.parse_args()
    out = Path(a.out)
    labels = json.loads((out / "labels.json").read_text(encoding="utf-8"))
    lab2i = {l: i for i, l in enumerate(labels)}
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)
    base = AutoModel.from_pretrained(a.model)
    model = T.Tagger(base, len(labels))
    st = torch.load(out / "model.pt", map_location="cpu")
    model.load_state_dict(st["model"]); thr = st["thr"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev).eval()
    sents = a.sentences or DEFAULT
    results = []
    for s in sents:
        words = s.split()
        plain = [T.MARKS.sub("", w) if hasattr(T, "MARKS") else w for w in words]
        b = {"plain": plain, "diac": words, "labels": [[] for _ in words], "src": "M"}
        enc, _y, m = T.encode([b], tok, lab2i, "plain")
        enc = {k: v.to(dev) for k, v in enc.items()}
        with torch.no_grad():
            p = torch.sigmoid(model(**enc).float()).cpu()[0][m[0]]
        rows = []
        print("\n" + s)
        for w, pw in zip(words, p):
            top = sorted(((float(pw[i]), labels[i]) for i in range(len(labels)) if not labels[i].startswith(("ن:", "ك:"))), reverse=True)[: a.top]
            mark = " ✔" if top and top[0][0] >= thr else " ؟"
            print(f"  {w:<14} " + "  |  ".join(f"{l} {sc:.2f}" for sc, l in top) + mark)
            rows.append({"word": w, "top": [{"label": l, "p": round(sc, 3)} for sc, l in top]})
        results.append({"sentence": s, "threshold": thr, "words": rows})
    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
