"""استيراد كتب من مكتبة الشاملة المثبّتة على الجهاز (الإصدار الرابع) إلى المدوّنة التراثية ~/.sarf/corpus.db.

يقرأ ملفات الشاملة نفسها قراءةً فقط، ولا يكتب فيها شيئًا:
- نص الصفحة من فهرس Lucene الذي يبحث فيه برنامج الشاملة (database/store/page)، بقارئ جافا المضمَّن في البرنامج (عبر JPype).
- الجزء ورقم الصفحة المطبوع من ملف الكتاب (database/book/NNN/<id>.db).
كل صفحة من الشاملة تصير فقرة في المدوّنة بجزئها وصفحتها كما يعرضها برنامج الشاملة. ويُحفظ المتن وحده؛ الحاشية (كلام المحقق)
لا تُدرج حتى لا يُنسب إلى المصنّف ما ليس له.

المتطلبات: برنامج الشاملة 4 مثبّتًا، وحزمة JPype1 (pip install JPype1).
التشغيل:
    python import_shamela.py 6972                 # المغني
    python import_shamela.py 6972 7362 --genre نحو --root E:\\shamela4_1
    python import_shamela.py 6972 --db نسخة.db     # التجربة على قاعدة أخرى
الكتاب يُضاف بمعرّف «<وفاة المؤلف>Shamela.<رقم الكتاب>» مثل 0761Shamela.6972، فيُحذف عند الحاجة بـ corpus_remove_book.
"""
import argparse, glob, html, os, re, sqlite3, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_corpus_index as bci

TAG = re.compile(r"<[^>]+>")
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def clean_body(s):
    s = html.unescape(TAG.sub("", s or ""))
    s = s.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def to_int(x):
    try:
        return int(str(x).translate(DIGITS).strip())
    except (TypeError, ValueError):
        return None


class Shamela:
    """قارئ لمكتبة الشاملة 4 على الجهاز (قراءة فقط)."""

    def __init__(self, root):
        self.root = root
        import jpype
        if not jpype.isJVMStarted():
            jvm = glob.glob(os.path.join(root, "app", "win", "64", "jre", "*", "bin", "server", "jvm.dll")) or [None]
            jars = glob.glob(os.path.join(root, "app", "lucene", "*", "*.jar"))
            if not jars:
                raise SystemExit(f"لم أجد مكتبات Lucene في {root}\\app\\lucene؛ تحقق من مسار الشاملة (--root).")
            jpype.startJVM(jvm[0], classpath=jars, convertStrings=True) if jvm[0] else jpype.startJVM(classpath=jars, convertStrings=True)
        J = jpype.JClass
        self._Term, self._Prefix, self._Term_q = J("org.apache.lucene.index.Term"), J("org.apache.lucene.search.PrefixQuery"), J("org.apache.lucene.search.TermQuery")
        Paths, FS, DR, IS = (J("java.nio.file.Paths"), J("org.apache.lucene.store.NIOFSDirectory"),
                             J("org.apache.lucene.index.DirectoryReader"), J("org.apache.lucene.search.IndexSearcher"))
        self._readers = []

        def searcher(name):
            r = DR.open(FS.open(Paths.get(os.path.join(root, "database", "store", name))))
            self._readers.append(r)
            return IS(r)
        self.pages, self.books = searcher("page"), searcher("book")

    def book_card(self, bid):
        td = self.books.search(self._Term_q(self._Term("id", str(bid))), 1)
        if not td.scoreDocs:
            return None
        return self.books.storedFields().document(td.scoreDocs[0].doc).get("body_store") or ""

    def page_texts(self, bid):
        """{رقم الصفحة الداخلي: المتن} لكل صفحات الكتاب."""
        q = self._Prefix(self._Term("id", f"{bid}-"))
        n = max(1, int(self.pages.count(q)))
        out, sf = {}, self.pages.storedFields()
        for sd in self.pages.search(q, n).scoreDocs:
            d = sf.document(sd.doc)
            pid = d.get("id")
            if not pid or not pid.startswith(f"{bid}-"):
                continue
            out[int(pid.split("-", 1)[1])] = d.get("body") or ""
        return out

    def page_numbers(self, bid):
        """{رقم الصفحة الداخلي: (الجزء، الصفحة المطبوعة)} من ملف الكتاب."""
        db = os.path.join(self.root, "database", "book", f"{bid % 1000:03d}", f"{bid}.db")
        if not os.path.exists(db):
            raise FileNotFoundError(f"ملف الكتاب غير موجود: {db} (هل الكتاب منزَّل في الشاملة؟)")
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = {i: (part, page) for i, part, page in con.execute("SELECT id, part, page FROM page")}
        con.close()
        return rows


def parse_card(card):
    """العنوان والمؤلف وسنة الوفاة من بطاقة الكتاب في الشاملة («الكتاب: …» «المؤلف: …»)."""
    title = re.search(r"الكتاب:\s*([^\r\n]+)", card or "")
    author = re.search(r"(?:المؤلف|المصنف|إعداد):\s*([^\r\n]+)", card or "")
    title = title.group(1).strip(" -") if title else ""
    author = author.group(1).strip() if author else ""
    died = None
    for pat in (r"المتوفى\s*:?\s*([\d٠-٩]{2,4})", r"\(ت\s*([\d٠-٩]{2,4})", r"[-–]\s*([\d٠-٩]{2,4})\s*هـ\s*\)"):
        m = re.search(pat, author)
        if m:
            died = to_int(m.group(1))
            break
    short = re.sub(r"\s*\((?:ت|المتوفى|[\d٠-٩]).*$", "", author).strip()
    return title, short or author, died


def book_paras(sh, bid):
    texts, nums = sh.page_texts(bid), sh.page_numbers(bid)
    paras, unnumbered = [], 0
    for pid in sorted(texts):
        t = clean_body(texts[pid])
        if not t or not bci.TOKEN.search(t):
            continue
        part, page = nums.get(pid, (None, None))
        vol, page = to_int(part), to_int(page)
        if page is None:
            unnumbered += 1
        paras.append([vol, page, t])
    return paras, unnumbered


def import_book(sh, con, bid, genre, died=None):
    card = sh.book_card(bid)
    if card is None:
        return {"تنبيه": f"الكتاب {bid} غير موجود في فهرس الشاملة على هذا الجهاز."}
    title, author, d = parse_card(card)
    died = died or d
    if not died:
        return {"تنبيه": f"لم أستخرج سنة وفاة مؤلف «{title}» من بطاقته؛ أعد التشغيل مع --died.", "البطاقة": card[:300]}
    uri = f"{died:04d}Shamela.{bid}"
    if con.execute("SELECT 1 FROM books WHERE uri=?", (uri,)).fetchone():
        return {"تنبيه": f"«{title}» في المدوّنة من قبل ({uri})."}
    paras, unnumbered = book_paras(sh, bid)
    if not paras:
        return {"تنبيه": f"لم أجد نصًّا لصفحات الكتاب {bid}."}
    try:
        b = (con.execute("SELECT MAX(id) FROM books").fetchone()[0] or 0) + 1
        p = con.execute("SELECT MAX(id) FROM paras").fetchone()[0] or 0
        _t, ntok, counts, _ = bci.insert_book(con, b, p, genre, uri, {"BookTITLE": title, "AuthorNAME": author}, paras)
        con.executemany("INSERT INTO freq(token, n) VALUES (?, ?) ON CONFLICT(token) DO UPDATE SET n = n + excluded.n",
                        counts.items())
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"أُضيف": title, "المؤلف": author, "الوفاة": died, "المعرّف": uri, "الصفحات": len(paras),
            "صفحات بلا رقم": unnumbered, "الكلمات": ntok}


def main(argv=None):
    ap = argparse.ArgumentParser(description="استيراد كتب الشاملة 4 المثبّتة إلى المدوّنة التراثية")
    ap.add_argument("books", nargs="+", type=int, help="أرقام الكتب في الشاملة (مثل 6972 للمغني)")
    ap.add_argument("--root", default=os.environ.get("SHAMELA_ROOT", r"E:\shamela4_1"), help="مجلد الشاملة 4")
    ap.add_argument("--db", default=os.path.join(os.path.expanduser("~"), ".sarf", "corpus.db"))
    ap.add_argument("--genre", default="نحو")
    ap.add_argument("--died", type=int, default=None, help="سنة وفاة المؤلف إن لم تُستخرج من البطاقة (لكتاب واحد)")
    a = ap.parse_args(argv)
    if not os.path.exists(a.db):
        raise SystemExit(f"المدوّنة غير موجودة: {a.db}")
    sh = Shamela(a.root)
    con = sqlite3.connect(a.db, timeout=60)
    try:
        for bid in a.books:
            print(import_book(sh, con, bid, a.genre, a.died if len(a.books) == 1 else None), flush=True)
    finally:
        con.close()


if __name__ == "__main__":
    main()
