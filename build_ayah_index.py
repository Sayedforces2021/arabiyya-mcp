"""فهرس الآيات في كتب إعراب القرآن: لكل آية صفحتها في كل كتاب.

يُبنى من فهارس الكتب في الشاملة 4 المثبّتة (عناوين مثل «[سورة البقرة (٢) : الآيات ٩٣ إلى ٩٤]»،
و«قال تعالى: (… (٢))»، أو اسم السورة ثم أرقام الآيات). وما فهرسه بالسور وحدها يُحفظ بمدى صفحات السورة،
ويُعيَّن موضع الآية فيه وقت السؤال بالبحث عن ألفاظها في تلك الصفحات.

الناتج data/khilaf/ayah_index.jsonl: بنية بلا نصوص (المعرّف، والسورة، والآيات، والجزء والصفحة).
    python build_ayah_index.py [--root E:/shamela4_1]
"""
import argparse, json, os, re, sqlite3, sys

import bisect

import build_corpus_index as bci
from import_shamela import Shamela, clean_body, default_root

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "khilaf", "ayah_index.jsonl")
QURAN = os.path.join(os.path.expanduser("~"), ".sarf", "quran-morphology.txt")

# كتب إعراب القرآن ومعانيه المستوردة إلى المدوّنة (رقم الشاملة ← المعرّف)
BOOKS = {
    23634: "0207Shamela.23634", 922: "0311Shamela.922", 23587: "0338Shamela.23587", 940: "0338Shamela.940",
    5538: "0437Shamela.5538", 36506: "0535Shamela.36506", 23585: "0543Shamela.23585", 22928: "0616Shamela.22928",
    147312: "0643Shamela.147312", 95571: "0742Shamela.95571", 23591: "0745Shamela.23591", 9057: "0756Shamela.9057",
    7501: "0761Shamela.7501", 12753: "0926Shamela.12753", 2163: "1403Shamela.2163", 22916: "1405Shamela.22916",
    23584: "1450Shamela.23584", 9617: "1450Shamela.9617", 2505: "1439Shamela.2505",
}

SURAS = ("الفاتحة البقرة آل_عمران النساء المائدة الأنعام الأعراف الأنفال التوبة يونس هود يوسف الرعد إبراهيم الحجر النحل "
         "الإسراء الكهف مريم طه الأنبياء الحج المؤمنون النور الفرقان الشعراء النمل القصص العنكبوت الروم لقمان السجدة "
         "الأحزاب سبأ فاطر يس الصافات ص الزمر غافر فصلت الشورى الزخرف الدخان الجاثية الأحقاف محمد الفتح الحجرات ق "
         "الذاريات الطور النجم القمر الرحمن الواقعة الحديد المجادلة الحشر الممتحنة الصف الجمعة المنافقون التغابن الطلاق "
         "التحريم الملك القلم الحاقة المعارج نوح الجن المزمل المدثر القيامة الإنسان المرسلات النبأ النازعات عبس التكوير "
         "الانفطار المطففين الانشقاق البروج الطارق الأعلى الغاشية الفجر البلد الشمس الليل الضحى الشرح التين العلق القدر "
         "البينة الزلزلة العاديات القارعة التكاثر العصر الهمزة الفيل قريش الماعون الكوثر الكافرون النصر المسد الإخلاص "
         "الفلق الناس").split()
ALIASES = {"الحمد": 1, "أم الكتاب": 1, "فاتحة الكتاب": 1, "براءة": 9, "بني إسرائيل": 17, "المؤمن": 40, "حم السجدة": 41,
           "حم عسق": 42, "حم السجدة فصلت": 41, "الملائكة": 35, "الدهر": 76, "هل أتى": 76, "عم": 78, "عم يتساءلون": 78,
           "ألم نشرح": 94, "الانشراح": 94, "اقرأ": 96, "لم يكن": 98, "الزلزال": 99, "تبت": 111, "اللهب": 111, "التوحيد": 112,
           "تبارك": 67, "ن": 68, "سأل سائل": 70, "المجادلة": 58, "الطلاق": 65, "المنافقين": 63, "الكافرين": 109, "قل يا أيها الكافرون": 109}
NAME2NUM = {n.replace("_", " "): i + 1 for i, n in enumerate(SURAS)}
NAME2NUM.update(ALIASES)

DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
TASHKEEL = re.compile("[\u064b-\u0652\u0670\u0640]")


def sura_lengths():
    n = {}
    with open(QURAN, encoding="utf-8") as f:
        for line in f:
            loc = line.split("\t", 1)[0].split(":")
            if len(loc) >= 2 and loc[0].isdigit():
                s, a = int(loc[0]), int(loc[1])
                n[s] = max(n.get(s, 0), a)
    return n


def norm(t):
    t = TASHKEEL.sub("", t or "").translate(DIG)
    return re.sub("[أإآ]", "ا", t).replace("ة", "ه").replace("ى", "ي")




INCIPITS = {"المؤمنين": 23, "عسق": 42, "حم عسق": 42, "المحرم": 66, "الطول": 40, "القتال": 47, "سبإ": 34, "اذا الشمس كورت": 81,
            "كورت": 81, "انفطرت": 82, "اذا السماء انفطرت": 82, "انشقت": 84, "اذا السماء انشقت": 84, "يتساءلون": 78,
            "الهاكم": 102, "ارايت": 107, "انا انزلناه": 97, "قل اوحي": 72, "قل او حي": 72, "نون والقلم": 68, "نون": 68, "اذا زلزلت": 99,
            "ام القران": 1, "النساء القصري": 65, "سال سائل": 70, "هل اتي": 76, "عم يتساءلون": 78, "حم الدخان": 44,
            "البريه": 98, "السجده": (32, 41), "الفتح": (48, 110), "الدين": 107, "ابي لهب": 111, "ابو لهب": 111, "المنفكين": 98, "القيمه": (75, 98), "قريش": 106, "لايلاف": 106, "اقتربت": 54, "الساعه": 54,
            "تنزيل": 32, "الم تنزيل": 32, "سبح": 87, "سبح اسم ربك": 87, "الغاشيه": 88, "والفجر": 89, "الكوثر": 108,
            "التطفيف": 83, "الويل": 83, "النصر": 110, "اذا جاء نصر الله": 110, "الصمد": 112, "الاخلاص": 112}
CAND = {}
for k, v in NAME2NUM.items():
    CAND.setdefault(norm(k), set()).add(v)
for k, v in INCIPITS.items():
    CAND.setdefault(norm(k), set()).update(v if isinstance(v, tuple) else (v,))
SUFFIXES = re.compile(r"\s*(عليه|عليها|عليهم|صلي الله|جل ذكره|مكيه|مدنيه|وهي|واياتها|وهو|وهما|اياتها).*$")


def _lookup(phrase):
    w = phrase.split()
    for k in (4, 3, 2, 1):
        if len(w) >= k:
            c = " ".join(w[:k])
            for v in (c, c[1:] if c.startswith("و") and len(c) > 3 else None):
                if v and v in CAND:
                    return CAND[v]
    return None


def sura_candidates(title):
    """أرقام السورة المحتملة في العنوان (مجموعة)، أو None إن لم يكن عنوان سورة.
    وإن بدا عنوان سورة ولم يُعرف اسمها أعيدت مجموعة فارغة، فيتوقف الإسناد إلى السورة السابقة."""
    t = norm(title).strip()
    if re.match(r"^\W*(و?قوله|قال)", t):
        return None                                  # «قال تعالى: (… فأتوا بسورة …)» آية لا عنوان سورة
    m = re.match(r"^[\[\(]?\s*(\d+)\s*[\]\)]?\s*-?\s*(?:شرح|تفسير|سوره)", t)
    if m and 1 <= int(m.group(1)) <= 114:
        return {int(m.group(1))}
    m = re.search(r"(?:^|[\s\[\(])سوره\s*[^\(\[:]*?\((\d+)\)", t)
    if m and 1 <= int(m.group(1)) <= 114:
        return {int(m.group(1))}
    head = re.sub(r"[\[\]\(\)«»:\-–*﵇﵍]", " ", t)
    head = re.sub(r"\s+", " ", re.sub(r"\d+", " ", head)).strip()
    words = head.split()
    if "سوره" in words[:5]:
        rest = " ".join(words[words.index("سوره") + 1:])
    elif len(re.sub(r"^((ومن|من|تفسير|شرح|اعراب|مشكل)\s+)+", "", head).split()) <= 3:
        rest = re.sub(r"^((ومن|من|تفسير|شرح|اعراب|مشكل)\s+)+", "", head)
    else:
        return None
    rest = SUFFIXES.sub("", rest).strip()
    opts = [rest] + [norm(x) for x in re.findall(r"[\(\[]([^\)\]]+)[\)\]]", title)]
    for o in opts:
        o = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", o)).strip()
        c = _lookup(o)
        if c:
            return c
    return set() if "سوره" in words[:5] else None


def parse_sura(title, prev=0):
    c = sura_candidates(title)
    if c is None:
        return None
    if not c:
        return 0                                     # عنوان سورة مجهولة: يقطع الإسناد
    after = sorted(x for x in c if x >= prev)
    return after[0] if after else min(c)


def parse_ayat(title):
    """(من، إلى) أرقام الآيات في العنوان، أو None."""
    t = norm(title).strip()
    m = re.search(r"الايات\s*(\d+)\s*(?:الي|إلى|-)\s*(\d+)", t) or re.search(r"ايه\s*(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2)) if m.lastindex == 2 else int(m.group(1))
        return (min(a, b), max(a, b))               # «الآيات ٨٤ إلى ٨٣» خطأ طباعي
    if re.fullmatch(r"\(?\s*(\d+)\s*\)?\.?", t):
        a = int(re.sub(r"\D", "", t)); return (a, a)
    nums = [int(x) for x in re.findall(r"\((\d+)\)", t)]
    if nums and ("تعالي" in t or "قوله" in t or len(t) > 15):
        return (min(nums), max(nums))
    return None


def toc(sh, bid):
    """[(رقم العنوان، رقم الصفحة الداخلي، النص)] بترتيب الكتاب."""
    import jpype
    J = jpype.JClass
    if not hasattr(sh, "_titles"):
        r = J("org.apache.lucene.index.DirectoryReader").open(J("org.apache.lucene.store.NIOFSDirectory").open(
            J("java.nio.file.Paths").get(os.path.join(sh.root, "database", "store", "title"))))
        sh._readers.append(r)
        sh._titles = J("org.apache.lucene.search.IndexSearcher")(r)
    s = sh._titles
    q = sh._Prefix(sh._Term("id", f"{bid}-"))
    sf = s.storedFields()
    text = {}
    for sd in s.search(q, max(1, int(s.count(q)))).scoreDocs:
        d = sf.document(sd.doc)
        text[int(d.get("id").split("-", 1)[1])] = d.get("body") or ""
    db = os.path.join(sh.root, "database", "book", f"{bid % 1000:03d}", f"{bid}.db")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    pages = dict(con.execute("SELECT id, page FROM title"))
    con.close()
    return [(i, pages.get(i), text[i]) for i in sorted(text) if pages.get(i) is not None]


def book_index(sh, bid, lens):
    nums = sh.page_numbers(bid)
    pids = sorted(nums)
    texts = sh.page_texts(bid)          # الصفحات التي دخلت المدوّنة (كما في import_shamela.book_paras): ترتيبها = ترتيب فقراتها
    kept = [i for i in sorted(texts) if (lambda t: t and bci.TOKEN.search(t))(clean_body(texts[i]))]
    last_pid = pids[-1] if pids else 0
    entries, sura = [], None
    for tid, pid, title in toc(sh, bid):
        s = parse_sura(title, sura or 0)
        if s and sura and s < sura and re.search(r"ايه|الايات", norm(title)):
            s = sura                                 # خطأ طباعي في عنوان الآيات («[سورة البقرة (٢) : آية ١١١]» في سورة يوسف)
        if s == 0:
            sura = None
            continue
        if s:
            sura = s
            entries.append({"kind": "sura", "sura": s, "pid": pid})
            ay = parse_ayat(title) if "ايه" in norm(title) or "الايات" in norm(title) else None
            if ay:
                entries.append({"kind": "aya", "sura": s, "from": ay[0], "to": ay[1], "pid": pid})
            continue
        ay = parse_ayat(title)
        if sura and ay and 1 <= ay[0] <= ay[1] <= lens.get(sura, 0):
            entries.append({"kind": "aya", "sura": sura, "from": ay[0], "to": ay[1], "pid": pid})
    # نهاية كل مدخل: صفحة المدخل التالي من جنسه (أو نهاية السورة)
    out = []
    for kind in ("sura", "aya"):
        es = [e for e in entries if e["kind"] == kind]
        if kind == "sura":           # السورة الواحدة قد تتكرر عناوينها (عنوان ثم عنوان الآيات)، فيؤخذ أولها
            seen, es2 = set(), []
            for e in es:
                if e["sura"] not in seen:
                    seen.add(e["sura"]); es2.append(e)
            es = es2
        for i, e in enumerate(es):
            nxt = next((x["pid"] for x in es[i + 1:] if x["pid"] > e["pid"]), last_pid + 1)
            end_pid = max(e["pid"], nxt if kind == "sura" else nxt)          # صفحة الآية التالية قد تبدأ بها آيتنا أيضًا
            v0, p0 = nums.get(e["pid"], (None, None))
            v1, p1 = nums.get(min(end_pid, last_pid), (None, None))
            o0 = bisect.bisect_left(kept, e["pid"])
            o1 = max(o0, bisect.bisect_right(kept, min(end_pid, last_pid)) - 1)
            out.append({"kind": kind, "sura": e["sura"], "from": e.get("from"), "to": e.get("to"), "ord": o0, "ord_end": o1,
                        "pid": e["pid"], "pid_end": min(end_pid, last_pid), "vol": v0, "page": p0, "vol_end": v1, "page_end": p1})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--book", type=int, action="append", default=[])
    a = ap.parse_args(argv)
    sh = Shamela(a.root or default_root())
    lens = sura_lengths()
    rows, report = [], []
    for bid in (a.book or BOOKS):
        idx = book_index(sh, bid, lens)
        ayat = {(e["sura"], x) for e in idx if e["kind"] == "aya" for x in range(e["from"], e["to"] + 1)}
        suras = {e["sura"] for e in idx if e["kind"] == "sura"}
        report.append((bid, BOOKS[bid], len(suras), len(ayat)))
        for e in idx:
            rows.append({"uri": BOOKS[bid], "shamela": bid, **{k: v for k, v in e.items()}})
    if not a.book:
        with open(OUT, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for bid, uri, ns, na in report:
        print(f"{uri}\tالسور {ns}\tالآيات {na}", flush=True)


if __name__ == "__main__":
    main()
