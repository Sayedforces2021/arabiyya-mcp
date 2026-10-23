# -*- coding: utf-8 -*-
"""تخريج الشاهد: إذا خالفت نسبةُ كتب المدوّنة نسبةَ «أشعار» قُدّمت نسبة الكتب ما دام في «أشعار» بيتٌ لصاحبها."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sarf_mcp as M

HAVE_DATA = os.path.exists(M.POETRY_DB) and os.path.exists(M.CORPUS_DB)


@unittest.skipUnless(HAVE_DATA, "فهرس الشعر أو المدوّنة غير مبني")
class TestAttribution(unittest.TestCase):
    def poet(self, verse):
        n = M.takhrij_shahid(verse, limit=6)["النسبة"]
        return n["الشاعر"] if isinstance(n, dict) else n

    def test_hemistich_goes_to_books_poet(self):
        # الشطر عجزٌ عند المتنبي، وضمّنه أديب إسحاق صدرًا؛ والكتب تنسبه إلى المتنبي
        self.assertEqual(self.poet("تجري الرياح بما لا تشتهي السفن"), "المتنبي")

    def test_full_verse_unchanged(self):
        self.assertEqual(self.poet("ما كل ما يتمنى المرء يدركه تجري الرياح بما لا تشتهي السفن"), "المتنبي")
        self.assertEqual(self.poet("قفا نبك من ذكرى حبيب ومنزل"), "امرؤ القيس")

    def test_aradi(self):
        self.assertEqual(self.poet("أضاعوني وأي فتى أضاعوا"), "العرجي")


if __name__ == "__main__":
    unittest.main()
