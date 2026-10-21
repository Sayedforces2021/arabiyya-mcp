#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يقيس المحلّلَين على المجموعة الذهبية (gold.jsonl): المحلّل المدرَّب (~/.sarf/models/irab_parser) وأداة irab القديمة (Stanza + القواعد).
قراءة فقط؛ لا يدرّب ولا يضبط شيئًا. المجموعة لم يراجعها مختص بعد، فالأرقام مؤقتة.

ما يُقاس لكل كلمة (والجملة تُعطى للأداتين بلا شكل):
- الباب: باب الكلمة الأصلي (فاعل، مفعول به، فعل مضارع، حرف…) بعد طرح السوابق واللواحق. يُقبل البديل المذكور في الذهبي («أو بدل»، «(أو عطف بيان)»).
- الحرف: الحرف العامل في الكلمة أو المتصل بها (جر، جزم، نصب، ناسخ، لا النافية للجنس، شرط، معية، سببية)، ومنه لام التعليل ولام الأمر.
- الحكم: مرفوع أو منصوب أو مجرور أو مجزوم أو مبني؛ للأداة القديمة فقط، لأن وسوم المحلّل المدرَّب (ماساق) لا تحمل الحكم.
الكلمات التي ليس لها إعراب ذهبي واحد (q06) لا تُحسب.

التشغيل:  python eval/gold_irab/measure.py [--only parser|old] [--out ~/.sarf/models/irab_parser]
يكتب results.md وresults.json بجانبه."""
import argparse, difflib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

MARKS = re.compile(r"[ً-ْٰـ]")
def bare(s): return MARKS.sub("", s or "").replace("ٱ", "ا")
def norm(s): return re.sub("[أإآ]", "ا", bare(s)).replace("ى", "ي").replace("ة", "ه")

# ── الأبواب: الأطول أولًا حتى لا يُقرأ «نائب فاعل» «فاعلًا» ──
ROLES = [("نائب فاعل", "نائب فاعل"), ("مفعول به", "مفعول به"), ("مفعول مطلق", "مفعول مطلق"), ("مفعول لأجله", "مفعول لأجله"),
         ("مفعول معه", "مفعول معه"), ("مضاف إليه", "مضاف إليه"), ("اسم مجرور", "اسم مجرور"), ("اسم كان", "اسم كان"),
         ("خبر كان", "خبر كان"), ("اسم إن", "اسم إن"), ("خبر إن", "خبر إن"), ("اسم أن", "اسم إن"), ("خبر أن", "خبر إن"),
         ("اسم لا", "اسم لا"), ("خبر لا", "خبر"), ("مبتدأ", "مبتدأ"), ("المخصوص بالمدح", "مبتدأ"), ("خبر", "خبر"),
         ("ضمير فصل", "ضمير فصل"), ("نصب اسمها", "اسم إن"), ("فاعل", "فاعل"), ("حال", "حال"), ("تمييز", "تمييز"), ("نعت", "نعت"), ("صفة", "نعت"),
         ("عطف بيان", "عطف بيان"), ("بدل", "بدل"), ("معطوف", "معطوف"), ("توكيد", "توكيد"), ("ظرف", "ظرف"),
         ("منادى", "منادى"), ("مستثنى", "مستثنى"), ("فعل ماض", "فعل ماض"), ("فعل مضارع", "فعل مضارع"), ("فعل أمر", "فعل أمر"),
         ("جواب الشرط", "فعل مضارع"), ("فعل الشرط", "فعل مضارع")]
ROLES_N = [(norm(k), v) for k, v in ROLES]
VERBS = {"فعل ماض", "فعل مضارع", "فعل أمر"}
# أنواع الحروف: (نمط، نوع)
PARTS = [("حرف جزم", "جزم"), ("لام الأمر", "جزم"), ("ناهية", "جزم"), ("نفي وجزم", "جزم"), ("حرف جر", "جر"), ("حرف جرّ", "جر"),
         ("لام التعليل", "جر"), ("نصب (الأفعال)", "نصب"), ("مصدري ونصب", "نصب"), ("حرف نصب", "نصب"), ("فاء السببية", "سببية"), ("واو المعية", "معية"),
         ("توكيد ونصب", "ناسخ"), ("ناسخ", "ناسخ"), ("نافية للجنس", "نافية للجنس"), ("حرف عطف", "عطف"), ("عاطفة", "عطف"),
         ("حرف نداء", "نداء"), ("حرف استثناء", "استثناء"), ("أداة استثناء", "استثناء"), ("أداة حصر", "حصر"), ("استفهام", "استفهام"), ("حرف شرط", "شرط"),
         ("امتناع لوجود", "شرط"), ("جواب لولا", "جواب"), ("رابطة لجواب", "جواب"), ("حرف نفي", "نفي"), ("كافة ومكفوفة", "كافة"),
         ("تنبيه", "تنبيه"), ("استئنافية", "استئناف"), ("تفريعية", "عطف"), ("الفجائية", "فجاءة"), ("حرف غير عامل", "غير عامل"),
         ("أداة تحقيق", "تحقيق"), ("المزحلقة", "توكيد")]
PARTS_N = [(norm(k), v) for k, v in PARTS]
# جمل الربط والتفصيل التي لا تصف الكلمة نفسها
LINK = re.compile(r"^و?(الجار والمجرور|الجمله|المصدر|فاعله|وعلامه|علامه|هو مضاف|منع من|حرك|خبره محذوف|الميم|الالف فارقه|النون للوقايه|ها حرف)")
CLITIC = re.compile(r"^و?ال(تاء|هاء|كاف|ياء|واو|الف)\s|^و?(نا)\s")
# الحروف العاملة وما يتصل بها: هي التي يُقاس فيها الحرف، لأن وسوم ماساق لا تفرّق بين غير العاملة (نفي، استثناء، حصر، استئناف…)
GOV = {"جر", "جزم", "نصب", "ناسخ", "نافية للجنس", "شرط", "معية", "سببية"}
HUKM = [("مجزوم", "مجزوم"), ("منصوب", "منصوب"), ("مرفوع", "مرفوع"), ("مجرور", "مجرور"), ("مبني", "مبني")]


def first_role(clause):
    """أول باب في العبارة، والبدائل المذكورة بعد «أو»."""
    c = norm(clause)
    hits = []
    for k, v in ROLES_N:
        for m in re.finditer(re.escape(k), c):
            if not any(a <= m.start() < b for a, b, _ in hits):
                hits.append((m.start(), m.end(), v))
    hits.sort()
    if not hits:
        return None, set()
    main = hits[0][2]
    alts = {v for s, e, v in hits[1:] if re.search(r"او\s*$|\(او\s*$", c[:s][-8:])}
    return main, alts


def part_of(clause):
    """نوع الحرف بترتيب الأولوية في PARTS («حرف نفي وجزم» جزم، و«حرف توكيد ونصب» ناسخ)، وموضعه في العبارة."""
    c = norm(clause)
    for k, v in PARTS_N:
        i = c.find(k)
        if i >= 0:
            return v, min(c.find(k2) for k2, v2 in PARTS_N if c.find(k2) >= 0)
    return None, -1


def role_pos(clause):
    c = norm(clause)
    ps = [c.find(k) for k, _ in ROLES_N if c.find(k) >= 0]
    return min(ps) if ps else -1


def analyse(text):
    """من وصف إعراب الكلمة (ذهبيًّا كان أو من الأداة القديمة): الباب وبدائله، ونوع الحرف، والحكم."""
    t = re.sub(r"^فعل وفاعل:\s*", "", text or "")
    clauses = [x.strip() for x in re.split(r"[،,]", t) if x.strip()]
    role, alts, part, hukm, clitic_role, parts = None, set(), None, None, None, []
    for cl in clauses:
        c = norm(cl)
        if LINK.search(c):
            continue
        if c.startswith("جار ومجرور"):  # «جار ومجرور متعلق بمحذوف حال»: الكلمة اسم مجرور بحرف متصل
            role, alts, part, hukm = role or "اسم مجرور", set() if role is None else alts, part or "جر", hukm or "مجرور"
            parts.append("جر")
            continue
        p, ppos = part_of(cl)
        rp = role_pos(cl)
        if p:
            parts.append(p)
        is_part = bool(re.match(r"^(و?ال(واو|فاء|لام)\s|حرف|اداه|لا\s|ما\s|نافيه|كافه)", c)) and not re.search(r"\s(فعل|اسم مجرور|مفعول|مبتدا|فاعل)", c)
        if not re.match(r"^و?(اسم|ضمير|نكره)", c) and (is_part or (p and (rp < 0 or ppos <= rp))):
            part = part or p or "حرف"
            continue
        if CLITIC.search(c):
            r, _ = first_role(cl)
            if not r and "محل جر" in c:
                r = "اسم مجرور"
            clitic_role = clitic_role or r
            continue
        if role is None:
            role, alts = first_role(cl)
            for k, v in HUKM:
                if norm(k) in c:
                    hukm = v
                    break
            if role and p and not part:
                part = p
    if role is None:
        role = clitic_role or ("حرف" if part else None)
        alts = set()
    if re.search(r"\(او [^)]*\)|او [^،]*$", norm(text or "")):
        for m in re.finditer(r"او ([^)،]+)", norm(text or "")):
            r, _ = first_role(m.group(1))
            if r:
                alts.add(r)
    return {"role": role, "alts": sorted(alts - {role}), "part": part, "parts": sorted(set(parts)), "hukm": hukm}


# ── المحلّل المدرَّب: وسوم ماساق فقط (بلا سابقة ق: ولا ن: ولا ك:) ──
MASAQ_MAP = {"اسم حرف ناسخ": "اسم إن", "اسم فعل ناسخ": "اسم كان", "اسم لا النافية للجنس": "اسم لا", "خبر حرف ناسخ": "خبر إن",
             "خبر فعل ناسخ": "خبر كان", "ش:خبر": "خبر", "ش:خبر حرف ناسخ": "خبر إن", "ش:خبر فعل ناسخ": "خبر كان", "ش:نائب فاعل": "نائب فاعل",
             "مبتدأ مؤخر": "مبتدأ", "اسم معطوف": "معطوف", "ظرف زمان": "ظرف", "ظرف مكان": "ظرف", "فعل ماضٍ": "فعل ماض",
             "فعل ماضٍ مبني للمجهول": "فعل ماض", "فعل ماضٍ ناسخ": "فعل ماض", "فعل مضارع مبني للمجهول": "فعل مضارع",
             "فعل مضارع ناسخ": "فعل مضارع", "اسم لا محل له من الإعراب": "ضمير فصل"}  # وسم ماساق لضمير الفصل
MASAQ_PART = {"حرف جر": "جر", "حرف جرّ": "جر", "حرف جزم": "جزم", "حرف نصب (الأفعال)": "نصب", "حرف مصدري ونصب": "نصب",
              "حرف مصدري": "مصدري", "حرف مصدري ناسخ": "ناسخ", "حرف ناسخ (إنّ وأخواتها)": "ناسخ", "حرف ناسخ (إنّ وأخوتها)": "ناسخ",
              "لا النافية للجنس": "نافية للجنس", "حرف عطف": "عطف", "حرف نداء": "نداء", "حرف استثناء": "استثناء", "حرف استفهام": "استفهام",
              "حرف شرط": "شرط", "حرف غير عامل": "غير عامل", "كافة ومكفوفة": "كافة", "أداة تحقيق": "تحقيق", "ما العاملة عمل ليس": "ناسخ"}
PURE = {"يا", "لا", "الي", "في", "هل", "لم", "لن", "الا", "لولا", "انما", "عن", "علي", "قد", "ثم", "او", "بل", "ان"}  # حروف لا تكون أسماء
PRON_SUFFIX = ("ه", "ها", "هم", "هما", "هن", "ك", "كم", "كما", "كن", "ي", "نا", "ني")


def pick(word, sc, thr):
    """الباب الأصلي من وسوم المحلّل: أعلى وسم باب درجةً، إلا أن تكون الكلمة حرفًا، أو يكون الأعلى وظيفةَ ضميرها المتصل (مضاف إليه، مفعول به)."""
    on = [(s, l) for s, l in sc if s >= thr] or sc[:1]
    roles = [(s, MASAQ_MAP.get(l, l)) for s, l in on if l not in MASAQ_PART and MASAQ_MAP.get(l, l)]
    parts = [MASAQ_PART[l] for s, l in on if l in MASAQ_PART][:2]
    w = norm(word)
    w = w[1:] if len(w) > 3 and w[0] in "وف" else w
    if w in PURE and parts:
        role = "حرف"
    elif w in ("ما", "من") and on[0][1] in MASAQ_PART:
        role = "حرف"
    elif roles:
        role = roles[0][1]
        verbs = [r for _, r in roles if r in VERBS]
        if verbs and role in ("فاعل", "مفعول به", "اسم كان") and w.endswith(PRON_SUFFIX + ("ت", "تم", "وا", "ا", "ن")):
            role = verbs[0]  # «ذهبتُ»: فعل وفاعل، والباب الأصلي للفعل
        elif len(roles) > 1 and role in ("مضاف إليه", "مفعول به") and w.endswith(PRON_SUFFIX):
            role = roles[1][1]
    else:
        role = "حرف" if parts else None
    return role, parts, [l for _, l in on]


def parser_predict(gold, out):
    import torch
    import train_irab as T
    from transformers import AutoModel, AutoTokenizer
    labels = json.loads((out / "labels.json").read_text(encoding="utf-8"))
    lab2i = {l: i for i, l in enumerate(labels)}
    tok = AutoTokenizer.from_pretrained(T.MODEL_NAME)
    model = T.Tagger(AutoModel.from_pretrained(T.MODEL_NAME), len(labels))
    st = torch.load(out / "model.pt", map_location="cpu")
    model.load_state_dict(st["model"]); thr = st["thr"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev).eval()
    res = {}
    for g in gold:
        words = g["text"].split()
        plain = [bare(w) for w in words]
        enc, _y, m = T.encode([{"plain": plain, "diac": words, "labels": [[] for _ in words], "src": "M"}], tok, lab2i, "plain")
        enc = {k: v.to(dev) for k, v in enc.items()}
        with torch.no_grad():
            p = torch.sigmoid(model(**enc).float()).cpu()[0][m[0]]
        rows = []
        for pw in p:
            sc = sorted(((float(pw[i]), labels[i]) for i in range(len(labels)) if not labels[i].startswith(("ن:", "ك:", "ق:"))), reverse=True)
            role, parts, on = pick(words[len(rows)], sc, thr)
            rows.append({"role": role, "part": parts[0] if parts else None, "parts": parts, "hukm": None, "raw": " + ".join(on)})
        res[g["id"]] = rows
    return res, thr


def old_predict(gold):
    import sarf_mcp as S
    res = {}
    for g in gold:
        r = S.irab(g["text"], detail=False)
        toks = []
        for s_ in r.get("الجمل", []):
            for row in s_["الإعراب"]:
                desc = "، ".join(p["الإعراب"] for p in row["الأجزاء"]) if "الأجزاء" in row else row["الإعراب"]
                toks.append((row["الكلمة"], desc))
        words = [norm(w) for w in g["text"].split()]
        tw = [norm(t) for t, _ in toks]
        out = [None] * len(words)
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, words, tw, autojunk=False).get_opcodes():
            if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
                for a, b in zip(range(i1, i2), range(j1, j2)):
                    out[a] = toks[b]
            elif op == "replace":  # كلمة قسّمها المحلّل أكثر من قطعة: تُجمع أوصافها
                for a in range(i1, i2):
                    seg = [toks[b] for b in range(j1, j2) if tw[b] and tw[b] in words[a]]
                    if seg:
                        out[a] = (" ".join(t for t, _ in seg), "، ".join(d for _, d in seg))
        rows = []
        for o in out:
            if o is None:
                rows.append({"role": None, "part": None, "parts": [], "hukm": None, "raw": "— (لم تُعرب)"})
            else:
                a = analyse(o[1])
                rows.append({"role": a["role"], "part": a["part"], "parts": a["parts"], "hukm": a["hukm"], "raw": o[1]})
        res[g["id"]] = rows
    return res


def gov_ok(ga, p):
    """الحرف العامل: كل حرف عامل في الذهبي يجب أن تذكره الأداة، ولا تزيد حرفًا عاملًا ليس فيه (لام الأمر مكان لام التعليل، والعطف مكان المعية…)."""
    G = set(ga["parts"]) & GOV
    if not G:
        return None
    P = set(p.get("parts") or [])
    return G <= P and (P & GOV) <= G


def bucket(g):
    """القرآن قسمان: ما في تدريب المحلّل المدرَّب (يقيس الحفظ) وما خرج عنه (يقيس التعميم)."""
    if g["genre"] != "قرآن":
        return g["genre"]
    return "قرآن (خارج التدريب)" if g.get("parser_split") == "test" else "قرآن (في التدريب)"


def score(gold, preds):
    tot = Counter(); ok = Counter(); by_genre = defaultdict(Counter); conf = Counter(); wrong = []
    for g in gold:
        for k, w in enumerate(g["words"]):
            ga = analyse(w["irab"])
            if not ga["role"] or re.search("اوجه متعدده|اجازه", norm(w["irab"])):
                continue
            p = preds[g["id"]][k]
            good_role = p["role"] == ga["role"] or p["role"] in ga["alts"]
            tot["باب"] += 1; ok["باب"] += good_role
            by_genre[bucket(g)]["n"] += 1; by_genre[bucket(g)]["ok"] += good_role
            if not good_role:
                conf[f"{ga['role']} ← {p['role']}"] += 1
            gp = gov_ok(ga, p)
            if gp is not None:
                tot["حرف"] += 1; ok["حرف"] += gp
            if ga["hukm"] and p.get("hukm") is not None:
                tot["حكم"] += 1; ok["حكم"] += p["hukm"] == ga["hukm"]
            if not good_role or gp is False:
                wrong.append({"id": g["id"], "word": w["w"], "gold": ga, "pred": {x: p.get(x) for x in ("role", "parts", "hukm")}, "raw": p["raw"]})
    acc = {k: (ok[k], tot[k], round(ok[k] / tot[k], 3) if tot[k] else None) for k in ("باب", "حرف", "حكم")}
    genre = {k: (v["ok"], v["n"], round(v["ok"] / v["n"], 3)) for k, v in by_genre.items()}
    return {"acc": acc, "genre": genre, "confusions": conf.most_common(), "errors": wrong}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path.home() / ".sarf" / "models" / "irab_parser"))
    ap.add_argument("--only", choices=["parser", "old"])
    a = ap.parse_args()
    gold = [json.loads(l) for l in (HERE / "gold.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    systems = {}
    if a.only != "old":
        p, thr = parser_predict(gold, Path(a.out))
        systems["المحلّل المدرَّب"] = p
    if a.only != "parser":
        systems["أداة irab القديمة"] = old_predict(gold)
    report = {name: score(gold, pr) for name, pr in systems.items()}
    (HERE / "results.json").write_text(json.dumps({"report": report, "predictions": systems}, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# نتائج القياس على المجموعة الذهبية", "",
         f"{len(gold)} جملة. **المجموعة لم يراجعها مختص بعد، فالأرقام مؤقتة.** تُعطى الجمل للأداتين بلا شكل.",
         "الباب: باب الكلمة الأصلي بعد طرح السوابق واللواحق. الحرف: الحرف العامل في الكلمة أو المتصل بها (جر، جزم، نصب، ناسخ، لا النافية للجنس، شرط، معية، سببية)، "
         "فيُحسب خطأً أن تُغفله الأداة أو تضع مكانه غيره؛ وغير العامل (نفي، استثناء، استئناف…) لا يُقاس، لأن وسوم ماساق تجمعه في «حرف غير عامل». "
         "الحكم: للأداة القديمة فقط، لأن وسوم المحلّل المدرَّب لا تحمله. ولا تكتشف أيٌّ من الأداتين مواضع الخلاف بعدُ، فلم يُقَس ذلك.", "",
         "**القرآن قسمان:** «في التدريب» آيات من سور درّب عليها المحلّل المدرَّب، فرقمه فيها يقيس الحفظ؛ "
         "و«خارج التدريب» آيات من سور الاختبار (رقمها يُختم بـ7) لم يرها في تدريبه، فهي التي يُقاس بها تعميمه ويُقارن فيها بالأداة القديمة.", "",
         "| المقياس | " + " | ".join(report) + " |", "|---|" + "---|" * len(report)]
    for k in ("باب", "حرف", "حكم"):
        L.append(f"| {k} | " + " | ".join(f"{r['acc'][k][0]}/{r['acc'][k][1]} ({r['acc'][k][2]})" if r["acc"][k][1] else "—" for r in report.values()) + " |")
    for gname in ("بسيط", "تراثي", "قرآن (في التدريب)", "قرآن (خارج التدريب)"):
        L.append(f"| الباب: {gname} | " + " | ".join(f"{r['genre'][gname][0]}/{r['genre'][gname][1]} ({r['genre'][gname][2]})" if gname in r["genre"] else "—" for r in report.values()) + " |")
    watch = [g for g in gold if g["parser_watch"]]
    L += ["", "## الجمل المراقَبة (الأخطاء المعروفة)", ""]
    for g in watch:
        L.append(f"### {g['id']} · {g['text']}" + (f" — {g['note']}" if g["note"] else ""))
        L.append("")
        L.append("| الكلمة | الذهبي | " + " | ".join(systems) + " |")
        L.append("|---|---|" + "---|" * len(systems))
        for k, w in enumerate(g["words"]):
            ga = analyse(w["irab"])
            cells = []
            for pr in systems.values():
                p = pr[g["id"]][k]
                good = p["role"] == ga["role"] or p["role"] in ga["alts"]
                goodp = gov_ok(ga, p) is not False
                pp = "، ".join(p.get("parts") or [])
                cells.append(f"{p['role'] or '—'}{' / ' + pp if pp else ''} {'✔' if good and goodp else '✘'}")
            gp_ = "، ".join(ga["parts"])
            L.append(f"| {w['w']} | {ga['role'] or '—'}{' / ' + gp_ if gp_ else ''} | " + " | ".join(cells) + " |")
        L.append("")
    for name, r in report.items():
        L += [f"## أكثر الخلط: {name}", ""] + [f"- الذهبي {c.split(' ← ')[0]} ← قالت الأداة {c.split(' ← ')[1]}: {n}" for c, n in r["confusions"][:12]] + [""]
    (HERE / "results.md").write_text("\n".join(L), encoding="utf-8")
    for name, r in report.items():
        print(name, r["acc"], r["genre"])


if __name__ == "__main__":
    main()
