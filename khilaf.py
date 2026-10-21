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
