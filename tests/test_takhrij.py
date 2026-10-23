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


@unittest.skipUnless(HAVE_DATA, "فهرس الشعر أو المدوّنة غير مبني")
class TestAttributionInBooks(unittest.TestCase):
    def books(self, verse):
        return M.takhrij_shahid(verse, limit=4).get("قائله في كتب المدوّنة", [])

    def test_full_name_and_early_books(self):
        # «عبد الله بن معاوية» كان يُقطع «عبد» عند «الله»، و«الحيوان» يرد فيه البيت أولًا في عنوان باب،
        # و«عيون الأخبار» يسمّي الشاعر قبل بيتين من القطعة
        b = self.books("وعين الرضا عن كل عيب كليلة ولكن عين السخط تبدي المساويا")
        self.assertEqual(b[0]["الشاعر"], "عبد الله بن معاوية")
        self.assertGreaterEqual(b[0]["عدد الكتب"], 4)
        self.assertIn("الحيوان", b[0]["أقدمها"])

    def test_no_anonymous_names(self):
        for v in ("وعين الرضا عن كل عيب كليلة ولكن عين السخط تبدي المساويا",
                  "ستبدي لك الأيام ما كنت جاهلا ويأتيك بالأخبار من لم تزود"):
            names = {x["الشاعر"] for x in self.books(v)}
            self.assertFalse(names & {"عبد", "الاول", "الأول", "الذي يقول"}, names)


if __name__ == "__main__":
    unittest.main()
