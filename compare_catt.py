"""يوازن مشكِّل الشعر المدرَّب بـ CATT (المشكِّل الحالي) على العينة نفسها، ويضيف النتيجة إلى التقرير.
يُشغَّل بعد train_diacritizer.py إن تعذّرت الموازنة بـ CATT فيه."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import train_diacritizer as T
D = T.D


def chunks(text, n=400):
    """CATT لا يقبل أكثر من نحو ألف حرف، فيُقطَّع السطر على حدود الكلمات."""
    out, buf = [], ""
    for w in text.split(" "):
        if buf and len(buf) + 1 + len(w) > n:
            out.append(buf)
            buf = w
        else:
            buf = (buf + " " + w) if buf else w
    if buf:
        out.append(buf)
    return out


def main():
    from catt_tashkeel import CATTEncoderDecoder
    ed = CATTEncoderDecoder()
    catt = lambda l: " ".join(ed.do_tashkeel(c, verbose=False) for c in chunks(D.strip_diac(l)))
    te = T.fetch("test")[:300]
    _, pte = T.poetry()
    pte = pte[:300]
    rep_path = os.path.join(T.OUT, "report.json")
    report = json.load(open(rep_path, encoding="utf-8"))
    report.pop("الموازنة بـ CATT", None)
    T.log("الموازنة بـ CATT: 300 سطر نثر و300 بيت")
    report["الموازنة: CATT على 300 سطر من Tashkeela"] = T.der_wer([catt(l) for l in te], te)
    report["الموازنة: CATT على الأبيات نفسها"] = T.der_wer([catt(l) for l in pte], pte)
    report["تاريخ الموازنة بـ CATT"] = time.strftime("%Y-%m-%d %H:%M")
    json.dump(report, open(rep_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(T.OUT, "report.txt"), "w", encoding="utf-8") as f:
        for k, v in report.items():
            f.write(f"{k}: {v}\n")
    for k in ("الموازنة: CATT على الأبيات نفسها", "الموازنة: النموذج الجديد على الأبيات نفسها",
              "الموازنة: CATT على 300 سطر من Tashkeela", "الموازنة: النموذج الجديد على السطور نفسها"):
        T.log(k, report.get(k))


if __name__ == "__main__":
    main()
