# -*- coding: utf-8 -*-
"""التقاليب: ومعها كلام ابن جني في «الخصائص» على تقاليب الجذر إن تكلّم فيها (الاشتقاق الأكبر)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sarf_mcp as M

HAVE = os.path.exists(M.MAAJIM_DB) and os.path.exists(M.CORPUS_DB)


@unittest.skipUnless(HAVE, "فهرس المعاجم أو المدوّنة غير مبني")
class TestIbnJinni(unittest.TestCase):
    def test_jbr(self):
        ij = M.taqalib("جبر")["في الخصائص لابن جني"]
        self.assertEqual(ij[0]["الموضع"], "ج2 ص137")
        self.assertIn("للقوة والشدة", ij[0]["النص"])

    def test_klm_in_numeric_order(self):
        places = [x["الموضع"] for x in M.taqalib("كلم")["في الخصائص لابن جني"]]
        self.assertEqual(places[0], "ج1 ص14")
        self.assertEqual(places, sorted(places, key=lambda s: tuple(int(n) for n in s.replace("ج", "").split(" ص"))))

    def test_index_pages_skipped(self):
        # فهرس الطبعة في ج2 ص504 يذكر «تقاليب "ج ب ر"» برقم صفحتها، وليس كلامًا لابن جني
        self.assertNotIn("ج2 ص504", [x["الموضع"] for x in M.taqalib("جبر")["في الخصائص لابن جني"]])

    def test_root_without_his_discussion(self):
        self.assertNotIn("في الخصائص لابن جني", M.taqalib("كتب"))


if __name__ == "__main__":
    unittest.main()
