#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يقيس اكتشاف مواضع الخلاف (أداة wujuh_irab) على المجموعة الذهبية: كم من مواضع الخلاف الموثّقة فيها اكتشفت الأداة (الاستدعاء)،
وكم مما اقترحته في الذهبي (الدقة). يُقاس على الجمل التي عُلّم خلافها (بسيط، تراثي، قرآن)؛ و«جديد» و«ثالث» يُقاسان على مواضع كُتبت قبل التشغيل (NMAP وTMAP).
القياس على مستوى الجملة والمسألة: (الجملة، معرّف المدخل في السجلّ).
التشغيل:  python eval/gold_irab/measure_khilaf.py"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

# وجوه المجموعة الذهبية ← مداخل السجلّ (None: وجه لم يُوثَّق فلا مدخل له)
WMAP = {("s11", "مُحَمَّدٌ"): "wajh-badal-bayan", ("h03", "زَيْدًا"): "wajh-itbaa", ("h05", "زَيْدٌ"): "wajh-makhsus",
        ("h06", "مَا"): "wajh-ma-taajjub", ("h08", "زَيْدًا"): "wajh-ishtighal", ("h10", "وَتَشْرَبَ"): "wajh-la-takul",
        ("h13", "فَإِذَا"): "wajh-idha-fujaiyya", ("h14", "هُوَ"): "wajh-fasl-mubtada", ("h15", "قِفَا"): "wajh-qifa",
        ("q02", "خَيْرًا"): "wajh-khayran", ("q02", "فَمَنْ"): "wajh-khabar-shart", ("q03", "ذَا"): "wajh-man-dha",
        ("q05", "وَشُرَكَاءَكُمْ"): "wajh-shurakaakum", ("q06", "هَٰذَانِ"): "wajh-inna-hadhan", ("q06", "لَسَاحِرَانِ"): "wajh-inna-hadhan",
        ("q10", "النَّاسُ"): "wajh-ayyuha-nas", ("q11", "فَصَبْرٌ"): "wajh-sabr", ("t02", "مَنِ"): "wajh-khabar-shart",
        ("t06", "اللَّهُ"): None, ("q08", "وَالسَّمَاءَ"): "wajh-ishtighal", ("t06", "إِلَّا"): "wajh-itbaa"}

# «جديد»: مواضع الخلاف المتوقعة من السجلّ، كُتبت قبل تشغيل الأداة على هذه الجمل (فهي اختبار لم يُضبط عليه)
NMAP = {"n01": ["insaf-30"], "n03": ["insaf-79"], "n04": ["insaf-75", "wajh-la-takul"], "n05": ["insaf-76"], "n09": ["insaf-53"],
        "n10": ["insaf-14", "wajh-makhsus"], "n11": ["insaf-15", "wajh-ma-taajjub"], "n12": ["insaf-45"], "n13": ["insaf-34"],
        "n14": ["wajh-itbaa"], "n15": ["insaf-100", "wajh-fasl-mubtada"], "n17": ["wajh-khabar-shart", "insaf-84"],
        "n22": ["wajh-badal-bayan"], "n28": ["insaf-76"], "n32": ["insaf-12", "wajh-ishtighal"]}

# «ثالث» (23 أكتوبر): كُتبت كذلك قبل تشغيل الأداة. وما يحتمله النص من مسألة أخرى (TOK) لا يُعدّ ادّعاءً ولا فوتًا:
# «اللهم» منادى مفرد علم أيضًا، و«العلم طلبته» بلا شكل يحتمل النصب.
TMAP = {"m02": ["insaf-10"], "m03": ["insaf-12", "wajh-ishtighal"], "m04": ["insaf-15", "wajh-ma-taajjub"],
        "m05": ["insaf-14", "wajh-makhsus"], "m06": ["insaf-30"], "m07": ["insaf-82"], "m09": ["insaf-56"],
        "m10": ["insaf-37"], "m11": ["insaf-39"], "m12": ["insaf-40"], "m13": ["insaf-47"], "m14": ["insaf-23"],
        "m15": ["insaf-85"], "m16": ["insaf-53"], "m17": ["insaf-45"], "m18": ["wajh-itbaa"], "m19": ["insaf-34"],
        "m20": ["insaf-100", "wajh-fasl-mubtada"], "m21": ["insaf-76"], "m22": ["insaf-75", "wajh-la-takul"],
        "m23": ["insaf-79"], "m24": ["wajh-khabar-shart", "insaf-84"], "m25": ["wajh-badal-bayan"],
        "m26": ["wajh-man-dha"], "m27": ["wajh-idha-fujaiyya"], "m28": ["wajh-ishtighal"]}
TOK = {("m13", "insaf-45"), ("m28", "insaf-12")}


def main():
    import sarf_mcp as S, khilaf as K
    reg = {e["id"] for e in K.load_registry()}
    gold = [json.loads(l) for l in (HERE / "gold.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    new = [g for g in gold if g["genre"] == "جديد"]
    third = [g for g in gold if g["genre"] == "ثالث"]
    gold = [g for g in gold if g["genre"] not in ("جديد", "ثالث")]
    G, outside, P = set(), [], set()
    GN, PN, EXTRA = {(sid, e) for sid, es in NMAP.items() for e in es}, set(), set()
    for g in new:
        for it in S.wujuh_irab(g["text"], other_books=False).get("المواضع", []):
            (EXTRA if it["المعرّف"].startswith("tabyin-") else PN).add((g["id"], it["المعرّف"]))
    for g in gold:
        for k in g["khilaf"]:
            if k["kind"] == "عامل":
                eid = f"insaf-{k['source']['masala']}"
            else:
                eid = WMAP.get((g["id"], k["word"]), "?")
            if eid in reg:
                G.add((g["id"], eid))
            else:
                outside.append((g["id"], k["word"], k["issue"], eid))
        r = S.wujuh_irab(g["text"], other_books=False)
        for it in r.get("المواضع", []):
            (EXTRA if it["المعرّف"].startswith("tabyin-") else P).add((g["id"], it["المعرّف"]))
    GT, PT = {(sid, e) for sid, es in TMAP.items() for e in es}, set()
    for g in third:
        for it in S.wujuh_irab(g["text"], other_books=False).get("المواضع", []):
            if not it["المعرّف"].startswith("tabyin-") and (g["id"], it["المعرّف"]) not in TOK:
                PT.add((g["id"], it["المعرّف"]))
    tp = G & P
    rep = {"المواضع الموثّقة في السجلّ": len(G), "اكتُشف منها": len(tp), "الاستدعاء": round(len(tp) / max(1, len(G)), 3),
           "اقتراحات الأداة": len(P), "الدقة": round(len(tp) / max(1, len(P)), 3), "مواضع خارج السجلّ": len(outside),
           "فاته": sorted(G - P), "ادّعاء بلا أصل في الذهبي": sorted(P - G), "خارج السجلّ": outside,
           "مسائل التبيين المضافة (بعد تعليم الذهبي، فلا تُحسب)": sorted(EXTRA),
           "جديد (لم يُضبط عليه)": {"المتوقع": len(GN), "اكتُشف": len(GN & PN), "الاستدعاء": round(len(GN & PN) / max(1, len(GN)), 3),
                                    "الاقتراحات": len(PN), "الدقة": round(len(GN & PN) / max(1, len(PN)), 3),
                                    "فاته": sorted(GN - PN), "ادّعاء": sorted(PN - GN)},
           "ثالث (لم يُضبط عليه)": {"المتوقع": len(GT), "اكتُشف": len(GT & PT), "الاستدعاء": round(len(GT & PT) / max(1, len(GT)), 3),
                                    "الاقتراحات": len(PT), "الدقة": round(len(GT & PT) / max(1, len(PT)), 3),
                                    "فاته": sorted(GT - PT), "ادّعاء": sorted(PT - GT)}}
    (HERE / "results_khilaf.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
