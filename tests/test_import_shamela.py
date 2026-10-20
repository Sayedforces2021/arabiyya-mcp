"""اختبارات الدوال الخالصة في import_shamela (لا تحتاج برنامج الشاملة ولا جافا): python tests/test_import_shamela.py"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import import_shamela as I


class TestCard(unittest.TestCase):
    def test_died_from_mutawaffa(self):
        t, a, d = I.parse_card("الكتاب: مغني اللبيب عن كتب الأعاريب\rالمؤلف: عبد الله بن يوسف، ابن هشام (المتوفى: ٧٦١هـ)\rالمحقق: د. مازن")
        self.assertEqual((t, a, d), ("مغني اللبيب عن كتب الأعاريب", "عبد الله بن يوسف، ابن هشام", 761))

    def test_died_from_range(self):
        self.assertEqual(I.parse_card("الكتاب: الإنصاف\rالمؤلف: أبو البركات الأنباري (٥١٣ - ٥٧٧ هـ)")[2], 577)

    def test_died_from_t(self):
        self.assertEqual(I.parse_card("الكتاب: التبيين\rالمؤلف: أبو البقاء العكبري (ت ٦١٦ هـ)")[2], 616)

    def test_no_died(self):
        self.assertIsNone(I.parse_card("الكتاب: س\rالمؤلف: معاصر")[2])


class TestText(unittest.TestCase):
    def test_clean_body_strips_markup_keeps_tashkil(self):
        self.assertEqual(I.clean_body('<span data-type="title" id=toc-1>بَابُ</span>\rنَصٌّ &amp; آخر'), "بَابُ نَصٌّ & آخر")

    def test_to_int(self):
        self.assertEqual(I.to_int("٦١٥"), 615)
        self.assertEqual(I.to_int("2"), 2)
        self.assertIsNone(I.to_int(None))
        self.assertIsNone(I.to_int("المقدمة"))


class TestRemove(unittest.TestCase):
    """remove_book: حذف كامل في معاملة، ولا يمس تكرار كلمات الكتب الأخرى (خلافًا لـ corpus_remove_book القديمة)."""

    def test_remove_keeps_other_books(self):
        import sqlite3
        con = sqlite3.connect(":memory:")
        con.executescript("""CREATE TABLE books(id INTEGER PRIMARY KEY, uri TEXT, title TEXT, author TEXT, died INTEGER, genre TEXT, tokens INTEGER);
            CREATE TABLE paras(id INTEGER PRIMARY KEY, book INTEGER, vol INTEGER, page INTEGER, text TEXT);
            CREATE VIRTUAL TABLE paras_fts USING fts5(body, content='', tokenize='unicode61 remove_diacritics 0');
            CREATE TABLE freq(token TEXT PRIMARY KEY, n INTEGER) WITHOUT ROWID;""")
        pid = 0
        for bid, uri, text in ((1, "0100A.A", "زَرْنَبَقٌ وَكَلِمَةٌ"), (2, "0200B.B", "قُرْطُبَانٌ وَكَلِمَةٌ")):
            _t, _n, counts, pid = I.bci.insert_book(con, bid, pid, "نحو", uri, {"BookTITLE": uri}, [[1, bid, text]])
            con.executemany("INSERT INTO freq(token, n) VALUES (?, ?) ON CONFLICT(token) DO UPDATE SET n = n + excluded.n", counts.items())
        con.commit()
        I.remove_book(con, 2)
        hit = lambda w: con.execute("SELECT count(*) FROM paras_fts WHERE paras_fts MATCH ?", (f'"{w}"',)).fetchone()[0]
        self.assertEqual(hit("قرطبان"), 0)
        self.assertEqual(hit("زرنبق"), 1)
        self.assertEqual(con.execute("SELECT n FROM freq WHERE token='زرنبق'").fetchone(), (1,))
        self.assertEqual(con.execute("SELECT n FROM freq WHERE token='وكلمه'").fetchone(), (1,))
        self.assertIsNone(con.execute("SELECT n FROM freq WHERE token='قرطبان'").fetchone())
        self.assertEqual(con.execute("SELECT count(*) FROM books").fetchone(), (1,))


class FakeShamela:
    """بديل عن مكتبة الشاملة للاختبار: كتاب واحد رقمه 7362 بصفحتين."""
    def book_card(self, bid):
        return "الكتاب: الإنصاف في مسائل الخلاف\rالمؤلف: أبو البركات الأنباري (٥١٣ - ٥٧٧ هـ)" if bid == 7362 else None

    def page_texts(self, bid):
        return {1: "<span>مُقَدِّمَة</span>", 10: "وَاللَّهُ أَسْمَاكَ سُمًى مُبَارَكًا ... آثَرَكَ اللَّهُ بِهِ إِيثَارَكَا"}

    def page_numbers(self, bid):
        return {1: ("1", 5), 10: ("1", 14)}


class TestReplace(unittest.TestCase):
    def setUp(self):
        import sqlite3
        self.con = con = sqlite3.connect(":memory:")
        con.executescript("""CREATE TABLE books(id INTEGER PRIMARY KEY, uri TEXT, title TEXT, author TEXT, died INTEGER, genre TEXT, tokens INTEGER);
            CREATE TABLE paras(id INTEGER PRIMARY KEY, book INTEGER, vol INTEGER, page INTEGER, text TEXT);
            CREATE VIRTUAL TABLE paras_fts USING fts5(body, content='', tokenize='unicode61 remove_diacritics 0');
            CREATE TABLE freq(token TEXT PRIMARY KEY, n INTEGER) WITHOUT ROWID;""")
        _t, _n, counts, _ = I.bci.insert_book(con, 1, 0, "نحو", "0577AbuBarakatAnbari.InsafFiMasail",
                                              {"BookTITLE": "الإنصاف في مسائل الخلاف بين النحويين"},
                                              [[1, 15, "والله أسماك سمى مباركا آثرك الله به إيثاركا"]])
        con.executemany("INSERT INTO freq VALUES (?, ?)", counts.items())
        con.commit()
        self._ids = I.openiti_shamela_ids
        I.openiti_shamela_ids = lambda db: {"0577AbuBarakatAnbari.InsafFiMasail": 7362}

    def tearDown(self):
        I.openiti_shamela_ids = self._ids

    def test_replace_keeps_uri_and_fixes_page(self):
        rep = I.replace_openiti(FakeShamela(), self.con, ":memory:")
        self.assertIn("استُبدل", rep[0]["الحال"])
        rows = self.con.execute("SELECT b.uri, p.vol, p.page FROM paras p JOIN books b ON b.id=p.book ORDER BY p.id").fetchall()
        self.assertEqual(rows, [("0577AbuBarakatAnbari.InsafFiMasail", 1, 5), ("0577AbuBarakatAnbari.InsafFiMasail", 1, 14)])
        self.assertEqual(self.con.execute("SELECT count(*) FROM books").fetchone(), (1,))
        hit = self.con.execute("SELECT count(*) FROM paras_fts WHERE paras_fts MATCH '\"ايثاركا\"'").fetchone()[0]
        self.assertEqual(hit, 1)                                  # القديم حُذف من الفهرس، والجديد فُهرس
        self.assertEqual(self.con.execute("SELECT n FROM freq WHERE token='ايثاركا'").fetchone(), (1,))

    def test_replace_is_idempotent(self):
        I.replace_openiti(FakeShamela(), self.con, ":memory:")
        I.replace_openiti(FakeShamela(), self.con, ":memory:")
        self.assertEqual(self.con.execute("SELECT count(*) FROM paras").fetchone(), (2,))

    def test_import_twice_is_refused(self):
        self.assertIn("أُضيف", I.import_book(FakeShamela(), self.con, 7362, "نحو"))
        self.assertIn("تنبيه", I.import_book(FakeShamela(), self.con, 7362, "نحو"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
