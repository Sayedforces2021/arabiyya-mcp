# -*- coding: utf-8 -*-
"""الميزان: ما لم يعرفه المحلّل الصرفي يُطابَق على القوالب، وضبطُ السائل حَكَمٌ على قراءات المحلّل."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sarf_mcp as M
import sarf_ilal as I


def first(word):
    q = M.mizan(word)["القراءات"][0]
    return q["الجذر"], q["الوزن"]


class TestSkeleton(unittest.TestCase):
    def test_roots_from_broken_plural(self):
        self.assertIn("وزن", I.skeleton_roots("موازين"))

    def test_bare_skeleton_needs_two_fixed_letters(self):
        # «فَعِلَة» تحتمله كل كلمة من أربعة أحرف، فلا يُطابَق عليه غير المشكول
        self.assertEqual(I.skeleton_roots("وجهة", None, 2), [])


class TestMizan(unittest.TestCase):
    def test_mawazin_is_plural_of_mizan(self):
        # المحلّل لا يعرف «مَوازِين»، فكان يعيد «مُوازٍ» من «و ز ي»
        self.assertEqual(first("موازين"), ("و ز ن", "مَفاعِيل"))

    def test_typed_vowels_rule(self):
        # «مَوازِن» بفتح الميم جمع تكسير، و«مُوازِن» بضمها اسم فاعل
        self.assertEqual(first("مَوازِن"), ("و ز ن", "مَفاعِل"))
        self.assertEqual(first("مُوازِن"), ("و ز ن", "مُفاعِل"))

    def test_faalaa(self):
        self.assertEqual(first("حمراء"), ("ح م ر", "فَعْلاء"))

    def test_known_words_untouched(self):
        self.assertEqual(first("ميزان"), ("و ز ن", "مِفْعال"))
        self.assertEqual(first("داعٍ"), ("د ع و", "فاعِلٌ"))   # المنوّن اسم، لا فعل من «د و ع»


if __name__ == "__main__":
    unittest.main()
