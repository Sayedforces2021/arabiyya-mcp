# -*- coding: utf-8 -*-
"""البحث بالكلمة: quran_word بلا مرجع آية (مع الرسم العثماني)، وmaajim بالكلمة بدل الجذر."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sarf_mcp as M


@unittest.skipUnless(os.path.exists(M.QURAN_FILE), "المدوّنة القرآنية غير منزّلة")
class TestQuranWord(unittest.TestCase):
    def places(self, w):
        return [x["الموضع"] for x in M.quran_word(word=w).get("المواضع", [])]

    def test_word_without_ref(self):
        self.assertEqual(self.places("سيارة"), ["12:10:13", "12:19:2"])
        self.assertEqual(self.places("السيارة"), ["12:10:13", "12:19:2"])

    def test_uthmani_spellings(self):
        self.assertIn("2:3:5", self.places("الصلاة"))      # ٱلصَّلَوٰةَ
        self.assertIn("17:34:17", self.places("مسؤولا"))   # مَسْـُٔولًا
        self.assertIn("1:1:3", self.places("الرحمن"))      # ٱلرَّحْمَٰنِ
        self.assertIn("2:2:2", self.places("الكتاب"))      # ٱلْكِتَٰبُ

    def test_no_false_proclitic(self):
        # «كتابا» لا تطابق «تابا» بنزع الكاف
        self.assertNotIn("4:16:6", self.places("كتابا"))

    def test_word_within_ref(self):
        r = M.quran_word(ref="12:19", word="سيارة")
        self.assertEqual([w["الموضع"] for w in r["الكلمات"]], ["12:19:2"])

    def test_needs_ref_or_word(self):
        self.assertIn("تنبيه", M.quran_word())


@unittest.skipUnless(os.path.exists(M.MAAJIM_DB), "فهرس المعاجم غير مبني")
class TestMaajimWord(unittest.TestCase):
    def test_word_gives_root(self):
        self.assertEqual(M.maajim(word="السيارة", books=["مقاييس"])["جذرها عند الأداة"], "س ي ر")

    def test_word_in_root_slot(self):
        self.assertEqual(M.maajim(root="استقامة", books=["مقاييس"])["المادة"], "ق و م")

    def test_root_unchanged(self):
        r = M.maajim(root="عرب", books=["مقاييس"])
        self.assertNotIn("جذرها عند الأداة", r)
        self.assertEqual(r["المواد"][0]["الموضع"], "ج4 ص299")


if __name__ == "__main__":
    unittest.main()
