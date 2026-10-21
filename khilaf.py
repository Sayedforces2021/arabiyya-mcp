# -*- coding: utf-8 -*-
"""وجوه الإعراب وخلاف النحاة من نصوص الكتب، لا من الذاكرة.

يقرأ مسائل «الإنصاف» من المدوّنة المحلية (~/.sarf/corpus.db): يجد المسألة بصفحتها المطبوعة، ويستخرج أقوالها
(«ذهب الكوفيون إلى أن…، وذهب البصريون إلى أن…») بقائليها، ويبحث عن الكتب الأخرى في النحو التي تناقش المسألة نفسها.
السجلّ المنشور (data/khilaf/wujuh.jsonl) يحمل البنية وحدها (المسألة، والموضع، والقائلون، والصفحات)؛ ونصوص الأقوال
تُقرأ من المدوّنة وقت السؤال، فلا تُنشر نصوص الكتب."""
import json
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "data", "khilaf", "wujuh.jsonl")
INSAF_URI = "0577AbuBarakatAnbari.InsafFiMasail"
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
VIEW = re.compile(r"(?:^|(?<=[\s.،]))و?ذهب\s+(.{2,70}?)\s+إلى\s+(.+?)(?=(?:\s|[.،])و?ذهب\s|[.؛]\s|$)")
STOP = re.compile(r"أما الكوفيون فاحتجوا|أما البصريون فاحتجوا|فاحتجوا|واحتجوا|وحجتهم")


def corpus_path():
    return os.path.join(os.path.expanduser("~"), ".sarf", "corpus.db")


def connect():
    p = corpus_path()
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True) if os.path.exists(p) else None


def insaf_book(con):
    r = con.execute("SELECT id, title, author FROM books WHERE uri = ?", (INSAF_URI,)).fetchone()
    return r


def insaf_text(con, masala, vol, page):
    """نص المسألة من أولها إلى ما قبل احتجاج الفريقين، بجزئه وصفحته؛ أو None إن لم توجد في صفحتها."""
    b = insaf_book(con)
    if not b:
        return None
    rows = con.execute("SELECT vol, page, text FROM paras WHERE book = ? AND vol = ? AND page BETWEEN ? AND ? ORDER BY id",
                       (b[0], vol, page - 1, page + 2)).fetchall()
    n = str(masala).translate(AR_DIGITS)
    for i, (v, p, t) in enumerate(rows):
        m = re.search(r"(?<![٠-٩])%s\s*-?\s*مسألة" % n, t)
        if m:
            text = " ".join(r[2] for r in rows[i:i + 3])[m.start() - (0 if i else 0):]
            text = text[text.find(n):]
            s = STOP.search(text)
            return {"vol": v, "page": p, "text": (text[:s.start()] if s else text[:900]).strip()}
    return None


def clean_qail(q):
    q = re.split(r"[.،؛]", q)[0]
    q = re.sub(r"\s+في أحد القولين$", "", q.strip())
    return q.strip()


VIEW2 = re.compile(
    r"(?P<a>(?:^|(?<=[\s.،]))[وف]?ذهب\s+(?P<aq>.{2,90}?)\s+إلى\s+(?P<av>.+?)(?=(?:\s|[.،])[وف]?ذهب\s|(?:\s|[.،])وإليه ذهب|(?:\s|[.،])وحُ?كي|[.؛]\s|$))"
    r"|(?P<b>وإليه ذهب\s+(?P<bq>.{2,90}?)(?=[.،]|\s+وذهب|$))"
    r"|(?P<c>وحُ?كي عن\s+(?P<cq>.{2,40}?)\s+أنه قال[:،]?\s*(?P<cv>.+?)(?=(?:\s|[.،])وحُ?كي|(?:\s|[.،])[وف]?ذهب\s|$))")


def views(text):
    """[(القائل، القول)] من نص المسألة؛ القول نص الكتاب كما هو. الصيغ: «ذهب X إلى Y»، و«وإليه ذهب X» (يضاف قائلًا للقول
    السابق)، و«وحُكي عن X أنه قال: Y»."""
    out = []
    for m in VIEW2.finditer(text or ""):
        if m.group("a"):
            q, v = clean_qail(m.group("aq")), m.group("av").strip(" .،")
            if q.startswith("في ") and out:     # «وذهب في القول الثاني»: القائل من قبله
                q = f"{out[-1][0].split('وإليه ذهب')[-1].strip()} {q}"
            if q and v:
                out.append((q, v))
        elif m.group("b") and out:
            q0, v0 = out[-1]
            out[-1] = (f"{q0}، وإليه ذهب {clean_qail(m.group('bq'))}", v0)
        elif m.group("c"):
            out.append((f"{clean_qail(m.group('cq'))} (حكاية)", m.group("cv").strip(" .،")))
    return out


# ── «التبيين عن مذاهب النحويين» للعكبري (ت 616): يقدّم قوله (وهو قول البصريين في الغالب، «عندنا»)، ثم «وقال الكوفيون…» ──
TABYIN_URI = "0616Shamela.13786"
_HARAKAT = re.compile("[ً-ْـ]")
KNOWN_QAIL = ("الكوفيون", "البصريون", "الفراء", "الكسائي", "الأخفش", "سيبويه", "المبرد", "الزجاج", "ابن السراج", "ثعلب",
              "هشام", "قوم", "آخرون", "بعضهم", "أبو علي", "الفارسي", "ابن كيسان", "يونس", "الخليل", "المازني", "الجرمي",
              "بعض الكوفيين", "بعض البصريين", "أبو عمرو", "الرماني", "السيرافي", "ابن جني", "قطرب")


def _bare(s):
    return _HARAKAT.sub("", s or "")


def tabyin_masail(con):
    """[{masala، page، title}] من عناوين التبيين («٣٠ - مسألة [العنوان]»)."""
    r = con.execute("SELECT id FROM books WHERE uri = ?", (TABYIN_URI,)).fetchone()
    if not r:
        return []
    out, seen = [], set()
    for pid, page, t in con.execute("SELECT id, page, text FROM paras WHERE book = ? ORDER BY id", (r[0],)):
        for m in re.finditer(r"(?<![٠-٩])([٠-٩]{1,3})\s*-\s*مسألة:?\s*(?:\[([^\]]{2,90})\]|\(([^)]{2,90})\))", t):
            n = int(m.group(1).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))
            if n not in seen:
                seen.add(n)
                out.append({"masala": n, "page": page, "title": re.sub(r"[()]", "", _bare(m.group(2) or m.group(3))).strip()})
    return out


def tabyin_text(con, masala, page):
    r = con.execute("SELECT id FROM books WHERE uri = ?", (TABYIN_URI,)).fetchone()
    if not r:
        return None
    rows = con.execute("SELECT page, text FROM paras WHERE book = ? AND page BETWEEN ? AND ? ORDER BY id", (r[0], page - 1, page + 2)).fetchall()
    n = str(masala).translate(AR_DIGITS)
    for i, (p, t) in enumerate(rows):
        m = re.search(r"(?<![٠-٩])%s\s*-\s*مسألة" % n, t)
        if m:
            text = " ".join(x[1] for x in rows[i:i + 3])
            text = text[text.find(n):]
            s = re.search(r"والدّ?لالة على|والدّ?ليل على|واحتجّ|واحتج|وحجّة|وحجة", text)
            return {"page": p, "text": (text[:s.start()] if s else text[:900]).strip()}
    return None


def views_tabyin(text):
    """القول المقدَّم في المسألة، ثم «وقال X…» / «فقال X…» / «وذهب X إلى…» لقائلين معروفين."""
    body = re.sub(r"^.*?مسألة:?\s*(?:\[[^\]]*\]|\([^)]*\))\s*", "", _bare(text or ""), count=1)
    sents = [x.strip(" ،") for x in re.split(r"(?<=[.؟])\s+|[،,]?\s+(?=[وف](?:قال|قالت|ذهب)\s+(?:%s))" % "|".join(KNOWN_QAIL), body) if x.strip(" ،")]
    out = []
    if sents:
        out.append(("القول المقدَّم عند العكبري" + (" («عندنا»: البصريون)" if "عندنا" in _bare(sents[0]) else ""), sents[0]))
    names = "|".join(sorted(KNOWN_QAIL, key=len, reverse=True))
    for s_ in sents[1:]:
        b = _bare(s_)
        m = re.match(r"^[وف]?(?:قال|قالت|ذهب)\s+((?:%s)(?:\s+و(?:%s))?)\s*:?\s*(?:إلى\s+)?(.+)$" % (names, names), b)
        if m:
            out.append((m.group(1), m.group(2).strip(" .")))
    return out


# ── كتب الخلاف المبثوث في الأبواب (الهمع، الارتشاف): الموضع بالصفحة، والنص مقتطفًا وقت السؤال ──
SPREAD_BOOKS = {"hama": ("0911Suyuti.HamcHawamic", "همع الهوامع في شرح جمع الجوامع", "السيوطي"),
                "irtishaf": ("0745Shamela.16595", "ارتشاف الضرب من لسان العرب", "أبو حيان")}
SCHOOLS = ("الكوفيون", "الكوفيين", "البصريون", "البصريين", "سيبويه", "الأخفش", "الفراء", "الكسائي", "المبرد", "الزجاج",
           "الفارسي", "ابن مالك", "ابن السراج", "ابن عصفور", "الجمهور", "الأكثرون", "ثعلب", "هشام")


def _book_id(con, uri):
    r = con.execute("SELECT id FROM books WHERE uri = ?", (uri,)).fetchone()
    return r[0] if r else None


def find_passages(con, uri, terms, limit=3):
    """الفقرات في الكتاب التي يجتمع فيها مصطلح المسألة وذكر المذاهب، مرتّبة بعدد ذكر المصطلح والقائلين."""
    import build_corpus_index as bci
    bid = _book_id(con, uri)
    if bid is None:
        return []
    names = [bci.norm(x) for x in SCHOOLS]
    cands = {}
    for term in terms:
        ph = " ".join(bci.norm(w) for w in term.split())
        q = f'"{ph}" AND (الكوفيون OR الكوفيين OR البصريون OR البصريين OR سيبويه OR الأخفش OR الفراء OR الكسائي)'
        try:
            rows = con.execute("SELECT p.id, p.vol, p.page, p.text FROM paras p WHERE p.book = ? AND p.id IN "
                               "(SELECT rowid FROM paras_fts WHERE paras_fts MATCH ?)", (bid, q)).fetchall()
        except sqlite3.OperationalError:
            continue
        for pid, vol, page, text in rows:
            n = bci.norm(text)
            score = 3 * n.count(ph) + sum(n.count(x) for x in names) + (5 if n.find(ph) < 200 else 0)
            if pid not in cands or cands[pid][0] < score:
                cands[pid] = (score, vol, page, term)
    best = sorted(cands.items(), key=lambda x: -x[1][0])[:limit]
    return [{"vol": v, "page": p, "term": t, "score": sc} for pid, (sc, v, p, t) in best]


def excerpt(con, uri, vol, page, term, size=700):
    """مقتطف من صفحة الكتاب يبدأ قبيل أول ذكر للمصطلح، ومن ذُكر فيه من النحاة."""
    import build_corpus_index as bci
    bid = _book_id(con, uri)
    if bid is None:
        return None
    rows = con.execute("SELECT text FROM paras WHERE book = ? AND vol IS ? AND page = ? ORDER BY id", (bid, vol, page)).fetchall()
    text = " ".join(r[0] for r in rows)
    if not text:
        return None
    n = bci.norm(text)
    ph = " ".join(bci.norm(w) for w in term.split())
    i = n.find(ph)
    # موضع الحرف في النص الأصلي: بعدّ الحروف غير الحركات
    if i < 0:
        start = 0
    else:
        k = 0
        start = 0
        for j, c in enumerate(text):
            if not _HARAKAT.match(c):
                if k == i:
                    start = j
                    break
                k += 1
    start = max(0, text.rfind(" ", 0, max(0, start - 120)) + 1)
    piece = text[start:start + size]
    end = max(piece.rfind("."), piece.rfind("،"))
    piece = piece[:end + 1] if end > size * 0.6 else piece
    who = [x for x in SCHOOLS if bci.norm(x) in bci.norm(piece)]
    return {"text": piece.strip(), "who": list(dict.fromkeys(who))}


def other_sources(con, terms, exclude_book=None, limit=8):
    """كتب النحو الأخرى التي تذكر المسألة: فقرة فيها مصطلحها مع ذكر الكوفيين والبصريين. أول موضع من كل كتاب، والأقدم أولًا."""
    import build_corpus_index as bci
    seen, out = set(), []
    for term in terms:
        ph = " ".join(bci.norm(w) for w in term.split())
        q = f'"{ph}" AND (الكوفيون OR الكوفيين) AND (البصريون OR البصريين)'
        try:
            rows = con.execute(
                "SELECT b.id, b.title, b.author, b.died, p.vol, p.page FROM paras p JOIN books b ON b.id = p.book "
                "WHERE p.id IN (SELECT rowid FROM paras_fts WHERE paras_fts MATCH ?) AND b.genre = 'نحو' ORDER BY b.died, p.id",
                (q,)).fetchall()
        except sqlite3.OperationalError:
            continue
        for bid, title, author, died, vol, page in rows:
            if bid in seen or bid == exclude_book:
                continue
            seen.add(bid)
            out.append({"book": title, "author": author, "died": died, "vol": vol, "page": page})
            if len(out) >= limit:
                return out
    return out


def load_registry():
    if not os.path.exists(REGISTRY):
        return []
    with open(REGISTRY, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
