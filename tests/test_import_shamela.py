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


if __name__ == "__main__":
    unittest.main(verbosity=1)
