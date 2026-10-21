# -*- coding: utf-8 -*-
"""فهرس الآيات في كتب إعراب القرآن (build_ayah_index.py) واختيار موضع الكلام على الكلمة (khilaf.py)."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_ayah_index as B
import khilaf as K


class TestParseTitles(unittest.TestCase):
    def test_sura_titles(self):
        cases = {"[سورة سبإ (٣٤) : آية ٣٣]": 34, "١٣ شرح إعراب سورة الرعد": 13, "(٢) سورة البقرة مدنية وهي": 2,
                 "البقرة": 2, "أم الكتاب": 1, "ومن سورة (يتساءلون) النبإ": 78, "سورة والصافات": 37,
                 "ومن سورة النساء القصرى وهى: سورة الطلاق": 65, "إعراب سورة القتال": 47, "شرح مشكل اعراب حم السجدة": 41}
        for t, n in cases.items():
            self.assertEqual(B.parse_sura(t), n, t)

    def test_verse_titles_are_not_suras(self):
        # «فأتوا بسورة من مثله (٢٣)»: آية فيها لفظ السورة، لا عنوان سورة
        for t in ("قال تعالى: (وإن كنتم في ريب مما نزلنا على عبدنا فأتوا بسورة من مثله (٢٣))",
                  "قوله تعالى: (سورة أنزلناها وفرضناها)", "قوله: (والشمس والقمر حسبانا) :"):
            self.assertIsNone(B.parse_sura(t), t)

    def test_ambiguous_name_follows_order(self):
        self.assertEqual(B.parse_sura("سورة القيمة", 97), 98)     # «القيمة» في الزجاج هي البينة
        self.assertEqual(B.parse_sura("ومن سورة السجدة", 40), 41)  # بعد غافر: حم السجدة
        self.assertEqual(B.parse_sura("تفسير مشكل اعراب سورة قل أو حي"), 72)

    def test_unknown_sura_title_cuts(self):
        self.assertEqual(B.parse_sura("سورة لا يعرفها الفهرس"), 0)

    def test_ayat(self):
        self.assertEqual(B.parse_ayat("[سورة البقرة (٢) : الآيات ٩٣ إلى ٩٤]"), (93, 94))
        self.assertEqual(B.parse_ayat("[سورة سبإ (٣٤) : آية ٣٣]"), (33, 33))
        self.assertEqual(B.parse_ayat("١٧٥"), (175, 175))
        self.assertEqual(B.parse_ayat("(٤٢)"), (42, 42))
        self.assertEqual(B.parse_ayat("قال تعالى: (الحمد لله رب العالمين (٢) الرحمن الرحيم (٣))"), (2, 3))
        self.assertIsNone(B.parse_ayat("المقدمة"))


@unittest.skipUnless(os.path.exists(B.OUT), "فهرس الآيات لم يُبنَ")
class TestIndexFile(unittest.TestCase):
    def setUp(self):
        with open(B.OUT, encoding="utf-8") as f:
            self.rows = [json.loads(l) for l in f]

    def test_structure_only(self):
        keys = {"uri", "shamela", "kind", "sura", "from", "to", "ord", "ord_end", "pid", "pid_end", "vol", "page", "vol_end", "page_end"}
        for r in self.rows:
            self.assertEqual(set(r), keys)                  # بنية بلا نصوص
            self.assertTrue(1 <= r["sura"] <= 114)
            self.assertLessEqual(r["ord"], r["ord_end"])
            if r["kind"] == "aya":
                self.assertLessEqual(r["from"], r["to"])

    def test_books_known(self):
        self.assertEqual({r["uri"] for r in self.rows} - set(B.BOOKS.values()), set())
        self.assertEqual(set(K.IRAB_AUTHORS) >= {r["uri"] for r in self.rows}, True)


class TestFind(unittest.TestCase):
    def test_prefers_discussion_over_quoted_verse(self):
        ayah = [K._loose(w) for w in "قالوا ان هذان لساحران يريدان".split()]
        text = "قالوا إن هذان لساحران يريدان أن يخرجاكم. قوله: هذان فيه أوجه، أحدها أن إن بمعنى نعم وما بعدها مبتدأ وخبر."
        sc, i = K._find(K._tokens(text), ayah, "هذان")
        self.assertGreater(K._tokens(text)[i][0], text.index("قوله"))

    def test_loose_ignores_uthmani(self):
        self.assertEqual(K._loose("ٱلصَّلَوٰةَ"), K._loose("الصلاة"))
        self.assertEqual(K._loose("هَٰذَٰنِ"), K._loose("هذان"))


if __name__ == "__main__":
    unittest.main()
