# -*- coding: utf-8 -*-
"""قواعد أداة irab التي كانت تعمل في غير موضعها، كشفتها مجموعة «ثالث» (eval/gold_irab):
توقّفٌ على «لم يكن»، ولام الجحود تُعدّ لام تعليل، و«مذ» قبل المرفوع حرف جر، و«سوى» حرف جر يقينًا،
والاسم بعد «يكن» فاعل، والاسم بعد «إذا» الفجائية فاعل."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sarf_mcp as M


def rows(s):
    out = {}
    for row in M.irab(s)["الجمل"][0]["الإعراب"]:
        parts = row.get("الأجزاء") or [row]
        out[M._strip_tashkeel(row["الكلمة"])] = (" ؛ ".join(p["الإعراب"] for p in parts), [p["اليقين"] for p in parts])
    return out


class TestIrabRules(unittest.TestCase):
    def test_lam_juhud_and_kana_ism(self):
        for s in ("لَمْ يَكُنِ الظَّالِمُ لِيُفْلِحَ", "لم يكن الظالم ليفلح"):   # كان يتوقف بلا شكل (الجزم في فرع الأسماء)
            r = rows(s)
            self.assertIn("لام الجحود", r["ليفلح"][0])
            self.assertTrue(r["الظالم"][0].startswith("اسم يكن"))

    def test_lam_talil_unchanged(self):
        self.assertIn("لام التعليل", rows("ذهبت إلى السوق لأشتري خبزا")["لأشتري"][0])

    def test_mudh_before_marfu(self):
        r = rows("مَا رَأَيْتُهُ مُذْ يَوْمَانِ")
        self.assertIn("مبتدأ", r["مذ"][0])
        self.assertTrue(r["يومان"][0].startswith("خبر"))
        self.assertIn("حرف جر", rows("ما رأيته مذ يومين")["مذ"][0])

    def test_siwa_not_certain_preposition(self):
        self.assertNotIn("بقاعدة", rows("جَاءَ الْقَوْمُ سِوَى زَيْدٍ")["سوى"][1])

    def test_noun_after_fujaiyya_is_mubtada(self):
        self.assertTrue(rows("خَرَجْتُ فَإِذَا الْبَابُ مُغْلَقٌ")["الباب"][0].startswith("مبتدأ"))

    def test_kana_with_pronoun_subject(self):
        # «كنتُ» اسمها التاء، فما بعدها خبرها
        self.assertTrue(rows("كنت الفائز")["الفائز"][0].startswith("خبر"))

    def test_raf_ishtighal_detected(self):
        ids = {it["المعرّف"] for it in M.wujuh_irab("الْعِلْمُ طَلَبْتُهُ", other_books=False)["المواضع"]}
        self.assertIn("wajh-ishtighal", ids)
        self.assertNotIn("insaf-12", ids)


if __name__ == "__main__":
    unittest.main()
