"""اختبارات مسار المدوّنة التراثية: التحليل ← البناء ← البحث ← الحذف، على قاعدة مصغّرة مؤقتة.

التشغيل:  python tests/test_corpus.py      (أو pytest tests/test_corpus.py)

- لا تنزّل شيئًا من الإنترنت، ولا تمسّ ~/.sarf الحقيقية: يُوجَّه HOME إلى مجلد مؤقت قبل الاستيراد.
- لا تتطلب camel_tools: تُستبدل وحداتها بنسخ وهمية، لأن الاختبار لا يستعمل المحلل الصرفي.
- الاختبارات الموسومة expectedFailure توثّق عيوبًا معروفة لم تُصلح بعد؛ إذا أُصلح العيب صار الاختبار «نجاحًا غير متوقع»
  فيُزال الوسم.
"""
import os, sys, sqlite3, tempfile, types, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── عزل البيئة قبل استيراد أي وحدة تحسب مساراتها عند التحميل ──
TMP = tempfile.mkdtemp(prefix="arabiyya_test_")
os.environ["HOME"] = TMP
os.environ["USERPROFILE"] = TMP
SARF = os.path.join(TMP, ".sarf")
os.makedirs(SARF, exist_ok=True)


def _stub(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m


try:
    import camel_tools  # noqa: F401
except ImportError:
    _stub("camel_tools")
    _stub("camel_tools.morphology")
    _stub("camel_tools.morphology.database", MorphologyDB=object)
    _stub("camel_tools.morphology.analyzer", Analyzer=object)
    _stub("camel_tools.tokenizers")
    _stub("camel_tools.tokenizers.word", simple_word_tokenize=lambda s: s.split())

import build_corpus_index as bci  # noqa: E402

# كتابان مصطنعان بصيغة OpenITI: صفحتان في الأول، وعلامة الصفحة في آخرها كما في OpenITI.
BOOK_A = """######OpenITIArabic#
#META# 000.BookTITLE :: كتاب الاختبار الأول
#META# 000.AuthorNAME :: مؤلف أول
#META#Header#End#
# بَابُ الْمَفْعُولِ مَعَهُ وَذَهَبَ الْكُوفِيُّونَ إِلَى أَنَّهُ مَنْصُوبٌ عَلَى الْخِلَافِ
~~ وَهٰذَا قَوْلُ الْفَرَّاءِ PageV01P010
# وَقَالَ الزَّجَّاجُ بِفِعْلٍ مُضْمَرٍ تَقْدِيرُهُ لَابَسَ زَرْنَبَقٌ PageV01P011
"""
BOOK_B = """######OpenITIArabic#
#META# 000.BookTITLE :: كتاب الاختبار الثاني
#META# 000.AuthorNAME :: مؤلف ثان
#META#Header#End#
# الْمَفْعُولُ مَعَهُ مَنْصُوبٌ بِالْفِعْلِ الَّذِي قَبْلَهُ بِتَوَسُّطِ الْوَاوِ قُرْطُبَانٌ PageV02P200
"""
URI_A, URI_B = "0100TestA.KitabA", "0700TestB.KitabB"


def _write(name, text):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def _build_db():
    """يبني corpus.db بدالة main نفسها، مقصورةً على الكتابين المصطنعين (بلا تنزيل)."""
    src = os.path.join(TMP, "src")
    os.makedirs(src, exist_ok=True)
    for uri, text in ((URI_A, BOOK_A), (URI_B, BOOK_B)):
        with open(os.path.join(src, uri + ".Test-ara1"), "w", encoding="utf-8") as f:
            f.write(text)
    saved = bci.CORPUS
    bci.CORPUS = [("نحو", "x", "data/" + URI_A + ".Test-ara1"), ("نحو", "x", "data/" + URI_B + ".Test-ara1")]
    try:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            bci.main(src)
    finally:
        bci.CORPUS = saved
    return os.path.join(SARF, "corpus.db")


class TestParse(unittest.TestCase):
    def test_marker_on_continuation_line(self):
        meta, paras = bci.parse(_write("a.txt", BOOK_A))
        self.assertEqual(meta.get("BookTITLE"), "كتاب الاختبار الأول")
        self.assertEqual((paras[0][0], paras[0][1]), (1, 10))   # علامة الصفحة في سطر «~~» من الفقرة نفسها

    def test_marker_on_first_line_of_paragraph(self):
        """كانت علامة الصفحة في السطر الأول من الفقرة («# نص… PageV01P011») تُعالَج قبل إنشاء الفقرة، فتأخذ الفقرة
        صفحة العلامة التالية (زائدة بواحد). مثال حقيقي: بيت «والله أسماك سمى مباركا» في الإنصاف ج1 ص14 عند الشاملة،
        وكان يُفهرس على ص15."""
        _m, paras = bci.parse(_write("a1.txt", BOOK_A))
        self.assertEqual((paras[1][0], paras[1][1]), (1, 11))

    def test_marker_before_text_on_first_line(self):
        """علامة في أول السطر تختم الصفحة السابقة، فالفقرة التي بعدها تبدأ في الصفحة التالية."""
        text = BOOK_A.split("#META#Header#End#")[0] + "#META#Header#End#\n# أول PageV01P001\n# PageV01P002 ثان\n~~ تتمة PageV01P003\n"
        _m, paras = bci.parse(_write("a3.txt", text))
        self.assertEqual([(v, p, t) for v, p, t in paras], [(1, 1, "أول"), (1, 3, "ثان تتمة")])

    def test_continuation_joined_and_original_text_kept(self):
        _m, paras = bci.parse(_write("a2.txt", BOOK_A))
        first = paras[0][2]
        self.assertIn("وَهٰذَا قَوْلُ الْفَرَّاءِ", first)        # سطر ~~ ضُمّ إلى فقرته
        self.assertIn("الْمَفْعُولِ", first)                     # الحركات محفوظة في النص الأصلي
        self.assertNotIn("PageV", first)


class TestCorpusPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = _build_db()
        import sarf_mcp
        cls.S = sarf_mcp
        assert sarf_mcp.CORPUS_DB == cls.db, (sarf_mcp.CORPUS_DB, cls.db)

    def rows(self, word, clitics=True, **kw):
        con, _vs, rows = self.S._corpus_rows(word, clitics, kw.get("genre"), None, None, kw.get("book"), 50)
        con.close()
        return rows

    def test_stored_text_is_original(self):
        con = sqlite3.connect(self.db)
        t = con.execute("SELECT text FROM paras WHERE book=1 ORDER BY id LIMIT 1").fetchone()[0]
        con.close()
        self.assertIn("الْمَفْعُولِ", t)

    def test_search_ignores_diacritics(self):
        self.assertTrue(self.rows("المفعول"))
        self.assertTrue(self.rows("الْمَفْعُولُ"))

    def test_search_returns_volume_and_page(self):
        pages = {(r[2], r[3]) for r in self.rows("الفراء")}
        self.assertEqual(pages, {(1, 10)})

    def test_clitics(self):
        self.assertTrue(self.rows("الواو"))        # «بِتَوَسُّطِ الْوَاوِ»
        self.assertTrue(self.rows("فعل"))          # «بِالْفِعْلِ» ← بال + فعل

    def test_concordance_phrase(self):
        """العبارة المركّبة («المفعول معه») تُطابَق كلمةً كلمة، وكانت تعيد صفرًا من السياقات."""
        out = self.S.corpus_concordance("المفعول معه", window=3)
        ctx = out["السياقات"]
        self.assertEqual(len(ctx), 2)
        self.assertEqual(ctx[0]["الكلمة"], "الْمَفْعُولِ مَعَهُ")
        self.assertIn("ج1 ص10", ctx[0]["المصدر"])

    def test_concordance_single_word_still_works(self):
        ctx = self.S.corpus_concordance("الزجاج", window=2)["السياقات"]
        self.assertEqual([c["الكلمة"] for c in ctx], ["الزَّجَّاجُ"])

    def test_cite_without_volume(self):
        """كتاب بلا أجزاء (مثل المغني من الشاملة) يُستشهد به بالصفحة وحدها، وكانت تسقط."""
        self.assertEqual(self.S._cite(None, 615), "، ص615")
        self.assertEqual(self.S._cite(1, 200), "، ج1 ص200")
        self.assertEqual(self.S._cite(None, None), "")

    @unittest.expectedFailure
    def test_dagger_alif_query(self):
        """عيب معروف: الفهرس يحذف الألف الخنجرية (ٰ) والاستعلام لا يحذفها، فلا تُوجد «هٰذا» المكتوبة بها."""
        self.assertTrue(self.rows("هذا"))      # الضابط: الكلمة نفسها بلا ألف خنجرية توجد («وَهٰذَا» في الكتاب الأول)
        self.assertTrue(self.rows("هٰذا"))


class TestAddRemove(unittest.TestCase):
    """الإضافة والحذف على قاعدة مستقلة، حتى لا يتأثر بها اختبار البحث."""

    def setUp(self):
        self.db = _build_db()
        import sarf_mcp
        self.S = sarf_mcp
        meta, paras = bci.parse(_write("c.txt", BOOK_B.replace("0700", "0800").replace("قُرْطُبَانٌ", "")))
        con = sqlite3.connect(self.db)
        bid = con.execute("SELECT MAX(id) FROM books").fetchone()[0] + 1
        pid = con.execute("SELECT MAX(id) FROM paras").fetchone()[0]
        _t, _n, counts, _ = bci.insert_book(con, bid, pid, "نحو", "0800TestC.KitabC", meta, paras)
        con.executemany("INSERT INTO freq(token, n) VALUES (?, ?) ON CONFLICT(token) DO UPDATE SET n = n + excluded.n",
                        counts.items())
        con.commit()
        con.close()

    def freq(self, tok):
        con = sqlite3.connect(self.db)
        r = con.execute("SELECT n FROM freq WHERE token=?", (tok,)).fetchone()
        con.close()
        return r[0] if r else None

    def test_remove_clears_text_and_index(self):
        before = len(self.S._corpus_rows("قرطبان", False, None, None, None, None, 50)[2])
        self.assertEqual(before, 1)
        out = self.S.corpus_remove_book(URI_B)
        self.assertEqual(out.get("حُذف"), "كتاب الاختبار الثاني")
        con, _v, rows = self.S._corpus_rows("قرطبان", False, None, None, None, None, 50)
        con.close()
        self.assertEqual(rows, [])
        con = sqlite3.connect(self.db)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM paras WHERE book=2").fetchone()[0], 0)
        con.close()
        # الكتابان الآخران باقيان في البحث
        con, _v, rows = self.S._corpus_rows("الزجاج", False, None, None, None, None, 50)
        con.close()
        self.assertEqual(len(rows), 1)

    def test_remove_unknown_book(self):
        self.assertIn("تنبيه", self.S.corpus_remove_book("0000No.Such"))

    def test_remove_keeps_rare_words_of_other_books(self):
        """كان الحذف يُجري «DELETE FROM freq WHERE n < 2» على الجدول كله، فيمحو تكرار كلمات نادرة في كتب أخرى."""
        self.assertEqual(self.freq("زرنبق"), None)      # في البناء الأول لا يُحفظ ما تكراره < 2
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO freq(token, n) VALUES ('زرنبق', 1)")   # كما تفعل corpus_add_book لكلمة نادرة
        con.commit()
        con.close()
        self.S.corpus_remove_book(URI_B)
        self.assertEqual(self.freq("زرنبق"), 1)


class TestPoetryRanking(unittest.TestCase):
    """«قفا نبك»: كان search_poetry يعيد الأبيات بترتيب التخزين، فيتقدّم من ضمّن الصدر في شعره على امرئ القيس،
    فنُسب البيت إلى غير قائله."""

    @classmethod
    def setUpClass(cls):
        import sarf_mcp
        cls.S = sarf_mcp

    def test_original_first(self):
        q = self.S._norm("قفا نبك من ذكرى حبيب ومنزل")
        rows = [  # بالترتيب الذي أعادته المدوّنة فعلًا
            ("قفا نبك من ذكرى حبيبٍ ومنزلِ", "#", "أبو العباس الجراوي", None, "بحر الطويل", "خليلي دعوى برحت بخفاء", "قصيدة عامه"),
            ("قفا نبك من ذكرى حبيب ومنزل", "وأضنى لذاك القول منهم وأدرد", "الأحنف العكبري", "العصر العباسي", "بحر الطويل", "سهرت وما مثلي ينام ويرقد", "قصيدة عامه"),
            ("وَأَخلَقَ فيها عُمرَهُ فَكَأَنَّهُ", "قِفا نَبكِ مِن ذِكرى حَبيبٍ وَمَنزِلِ", "ابن عنين", None, "بحر الطويل", "ولما رأينا المغربي", "قصيدة عامه"),
            ("قِفا نَبكِ مِن ذِكرى حَبيبٍ وَمَنزِلِ", "بِسِقطِ اللِوى بَينَ الدَخولِ فَحَومَلِ", "امرؤ القيس", "العصر الجاهلي", "بحر الطويل", "قفا نبك من ذكرى حبيب ومنزِل", "قصيدة المعلقات"),
        ]
        rows.sort(key=lambda r: self.S._poetry_rank(q, *r))
        self.assertEqual(rows[0][2], "امرؤ القيس")
        self.assertEqual(rows[-1][2], "ابن عنين")                  # ما جاء في العجز تضمين، يتأخر
        self.assertEqual(self.S._poetry_where(q, rows[-1][0], rows[-1][1]), "العجز")

    def test_quotation_is_not_attribution(self):
        self.assertTrue(self.S._is_quotation("( قفا نبك من ذكرى حبيـبٍ و منـزلِ", "معارضة معلقة امرئ القيس"))
        self.assertTrue(self.S._is_quotation("قفا نبك", "معارضة معلقة امرئ القيس"))
        self.assertFalse(self.S._is_quotation("قِفا نَبكِ مِن ذِكرى حَبيبٍ وَمَنزِلِ", "قفا نبك من ذكرى حبيب ومنزِل"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
