#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يبني مدوّنة إعرابية «فضّية» (وسومها مستخرجة آليًّا لا يدويّة) من نصوص كتب إعراب الشعر والحديث.

المدخل: ملفات نصية (.txt) لكتب إعراب تصدّرها من مكتبتك، على الصيغة المعتادة:
    «٢ - صدر البيت ... عجزه»  ثم  «الإعراب: كلمة: وصفها الإعرابي. كلمة: وصفها …»
المخرج: ملف JSONL محلي: كل سطر بيت بكلماته ووسوم كل كلمة. لا يُنشر ولا يُضمّ إلى المستودع.
الوسوم تبقى «فضّية» حتى تُراجَع عيّنة منها يدويًّا؛ ويُقاس بها النموذج بعد التحقق فقط.

التشغيل:  python build_irab_books.py كتاب.txt [كتاب2.txt …] --out ~/.sarf/corpora/books_irab.jsonl
"""
import argparse, json, re, sys
from pathlib import Path

MARKS = re.compile("[ً-ٰٟـ]")
AR = "ء-ي"
# ترتيب الأولوية: الأخصّ أولًا. القيمة = الوسم المقابل لأسماء MASAQ.
ROLES = [("جار ومجرور", "جار ومجرور"), ("حرف جر", "حرف جر"), ("حرف عطف", "حرف عطف"), ("اسم مجرور", "اسم مجرور"),
         ("نائب فاعل", "نائب فاعل"), ("فاعل", "فاعل"), ("مفعول به", "مفعول به"), ("مفعول مطلق", "مفعول مطلق"),
         ("مفعول لأجله", "مفعول لأجله"), ("مفعول فيه", "ظرف"), ("ظرف", "ظرف"), ("مبتدأ", "مبتدأ"), ("خبر", "خبر"),
         ("مضاف إليه", "مضاف إليه"), ("مضاف", "مضاف"), ("معطوف", "معطوف"), ("بدل", "بدل"), ("توكيد", "توكيد"),
         ("صفة", "نعت"), ("نعت", "نعت"), ("حال", "حال"), ("تمييز", "تمييز"), ("منادى", "منادى"),
         ("اسم إن", "اسم إن"), ("خبر إن", "خبر إن"), ("اسم كان", "اسم كان"), ("خبر كان", "خبر كان")]


def norm(s):
    s = MARKS.sub("", s)
    return re.sub("[إأآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")


def role_of(desc):
    first = re.split(r"\s(?:أو|وقيل|وهو|ويجوز)\s|[،.]", desc, maxsplit=1)[0] + " " + desc[:90]   # البدء بالوجه الأول
    first = re.split(r"\sأو\s", first)[0]
    for key, lab in ROLES:
        if re.search(r"(?<![%s])%s(?![%s])" % (AR, key, AR), first):
            return lab
    return None


ENTRY = re.compile(r"(?:^|[.\n،]\s*)([%s]{1,25}):\s" % AR)


def parse_irab(text):
    """يجزّئ «كلمة: وصف.» إلى أزواج (الكلمة، الوصف)."""
    ms = list(ENTRY.finditer(text))
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out.append((m.group(1), text[m.end():end].strip()))
    return out


VERSE = re.compile(r"^\s*[\d٠-٩]+\s*[-–]\s*(.+?)\s*\.\.\.\s*(.+?)\s*$", re.M)


def build(text):
    """يمسح الكتاب بيتًا بيتًا: يلتقط البيت ثم أقرب «الإعراب:» بعده حتى البيت التالي."""
    verses = [(m.start(), m.end(), m.group(1), m.group(2)) for m in VERSE.finditer(text)]
    out = []
    for i, (s, e, a, b) in enumerate(verses):
        nxt = verses[i + 1][0] if i + 1 < len(verses) else len(text)
        seg = text[e:nxt]
        k = seg.find("الإعراب:")
        if k < 0:
            continue
        words = (a + " " + b).split()
        labs = [[] for _ in words]
        nw = [norm(w) for w in words]
        pos = 0
        for head, desc in parse_irab(seg[k + 8:]):
            h = norm(head)
            r = role_of(desc)
            for j in range(pos, len(words)):          # الترتيب محفوظ: لا نرجع إلى الوراء
                if nw[j] == h or (len(h) > 2 and (h.endswith(nw[j]) or nw[j].endswith(h)) and len(nw[j]) > 1):
                    if r and r not in labs[j]:
                        labs[j].append(r)
                    pos = j + 1
                    break
        cover = sum(1 for l in labs if l) / max(1, len(words))
        out.append({"verse": " ".join(words), "words": words, "labels": labs, "coverage": round(cover, 2)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=str(Path.home() / ".sarf" / "corpora" / "books_irab.jsonl"))
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for p in a.files:
            for v in build(Path(p).read_text(encoding="utf-8")):
                v["source"] = Path(p).name
                f.write(json.dumps(v, ensure_ascii=False) + "\n")
                n += 1
    print(f"{n} بيتًا → {a.out}")


if __name__ == "__main__":
    main()
