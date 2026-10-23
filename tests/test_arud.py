# -*- coding: utf-8 -*-
"""التقطيع العروضي: البيت المصرَّع تأتي عروضه على صورة ضربه، وتقطيع القصيدة لا ينهار على بيت مختل."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sarf_mcp as M

SHAWQI = "قُمْ لِلْمُعَلِّمِ وَفِّهِ التَّبْجِيلا * كادَ المُعَلِّمُ أَنْ يَكُونَ رَسُولا"


class TestMusarra(unittest.TestCase):
    def test_musarra_opening_is_metrical(self):
        # عروض مقطوعة في الكامل لا تجوز إلا في المصرَّع، وهذا مطلع مصرَّع
        r = M.scan_verse(SHAWQI)
        self.assertTrue(r["موزون"])
        self.assertIn("التصريع", r)
        self.assertNotIn("ملاحظات المحلل", r)
        self.assertTrue(all(f["سليمة"] for f in r["الصدر"]["التفعيلات"]))

    def test_unrhymed_sadr_stays_broken(self):
        # الصورة نفسها في صدرٍ رويّه غير رويّ العجز ليست تصريعًا
        r = M.scan_verse("قُمْ لِلْمُعَلِّمِ وَفِّهِ التَّعْظِيما * كادَ المُعَلِّمُ أَنْ يَكُونَ رَسُولا")
        self.assertFalse(r["موزون"])
        self.assertNotIn("التصريع", r)

    def test_plain_verse_untouched(self):
        r = M.scan_verse("قِفا نَبْكِ مِنْ ذِكْرى حَبِيبٍ ومَنْزِلِ * بِسِقْطِ اللِّوى بَيْنَ الدَّخولِ فَحَوْمَلِ")
        self.assertTrue(r["موزون"])
        self.assertNotIn("التصريع", r)


class TestHazajWafir(unittest.TestCase):
    # مجزوء الوافر إذا عُصبت تفعيلاته كلها صار على لفظ الهزج؛ ولا يفرق بينهما إلا «مفاعَلَتن» سالمة
    def test_all_mafailun_is_hazaj_with_note(self):
        r = M.scan_verse("وَعَهدي بِصُحونَ الدا * ر تَمشي بَينَها الشَمسُ")  # أشجع السلمي، من الهزج
        self.assertEqual(r["البحر"], "بحر الهزج")
        self.assertEqual(r["بحر محتمل"]["البحر"], "مجزوء الوافر")

    def test_mufaalatun_stays_wafir(self):
        r = M.scan_verse("فَأَربَعَةٌ لِأَربَعَةٍ * لِكُلِّ طَبيعَةٍ رِطلُ")  # أبو نواس: مفاعَلَتن سالمة
        self.assertEqual(r["البحر"], "مجزوء الوافر")
        self.assertNotIn("بحر محتمل", r)

    def test_poem_decides_by_all_verses(self):
        hz = "إِلَى كَمْ نَحْنُ فِي ضِيقٍ * وَفِي عَزْلٍ وَفِي أَزْلِ"
        self.assertEqual(M.scan_poem("وَعَهدي بِصُحونَ الدا * ر تَمشي بَينَها الشَمسُ\n" + hz)["البحر الغالب"], "بحر الهزج")
        self.assertEqual(M.scan_poem("فَأَربَعَةٌ لِأَربَعَةٍ * لِكُلِّ طَبيعَةٍ رِطلُ\n" + hz)["البحر الغالب"], "بحر الوافر")


class TestScanPoem(unittest.TestCase):
    def test_poem_with_musarra_opening(self):
        p = M.scan_poem(SHAWQI + "\nأَعَلِمْتَ أَشْرَفَ أَوْ أَجَلَّ مِنَ الَّذِي * يَبْنِي وَيُنْشِئُ أَنْفُسًا وَعُقُولا")
        self.assertEqual(p["البحر الغالب"], "بحر الكامل")
        self.assertEqual(p["الموزون منها"], 2)
        self.assertEqual(p["أبيات تستحق المراجعة"], [])
        self.assertIn("التصريع", p["الأبيات"][0])


if __name__ == "__main__":
    unittest.main()
