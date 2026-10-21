# -*- coding: utf-8 -*-
"""سجلّ الوجوه واستخراج الأقوال من نص المسألة (khilaf.py)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import khilaf as K

INSAF_34 = ("٣٤- مسألة: [القول في العامل في المستثنى النصب] ١ اختلف مذهب الكوفيين فالعامل في المستثنى النصب نحو \"قام القوم إلا زيدًا\" "
            "فذهب بعضهم إلى أن العامل فيه \"إلا\"، وإليه ذهب أبو العباس المبرد وأبو إسحاق الزجاج من البصريين، "
            "وذهب الفراء ومن تابعه من الكوفيين إلى أن \"إلا\" مركبة من إن ولا. وحكي عن الكسائي أنه قال: إنما نصب المستثنى لأنه مشبه بالمفعول. "
            "وذهب البصريون إلى أن العامل في المستثنى هو الفعل.")


class TestViews(unittest.TestCase):
    def test_all_forms(self):
        v = K.views(INSAF_34)
        qs = [q for q, _ in v]
        self.assertEqual(len(v), 4)
        self.assertIn("المبرد", qs[0])                       # «وإليه ذهب» يضاف إلى القول السابق
        self.assertTrue(qs[1].startswith("الفراء"))
        self.assertTrue(qs[2].startswith("الكسائي"))           # «وحكي عن»
        self.assertEqual(qs[3], "البصريون")
        self.assertTrue(v[3][1].startswith("أن العامل في المستثنى هو الفعل"))

    def test_second_opinion_named(self):
        t = "وذهب البصريون إلى أنها معربة، وإليه ذهب أبو الحسن الأخفش في أحد القولين. وذهب في القول الثاني إلى أنها دلائل الإعراب."
        self.assertTrue(K.views(t)[-1][0].startswith("أبو الحسن الأخفش في القول الثاني"))


class TestRegistry(unittest.TestCase):
    def test_registry_has_no_book_text(self):
        """السجلّ المنشور بنية فقط: لا نصوص أقوال من الكتب، والأقوال نصها يُقرأ من المدوّنة المحلية."""
        reg = K.load_registry()
        self.assertTrue(reg)
        for e in reg:
            if e["kind"] in ("مسألة", "مسألة-تبيين"):
                self.assertNotIn("aqwal", e)
            else:
                self.assertTrue(e["sources"], e["id"])
        self.assertEqual(sum(e["kind"] == "مسألة" for e in reg), 118)                 # مسائل الإنصاف كلها
        self.assertTrue(all(e["qailun"] for e in reg if e["kind"] == "مسألة"))        # ولكل منها قائلوها من نصها

    def test_tabyin_views(self):
        t = "٣١ - مسألة [الاسم الواقع بعد لولا] الاسمُ الواقعُ بعد لولا يرتفعُ بالابتداءِ وقالَ الكوفيون فيه قولين: أحدُهما يرتفع بنفس لولا."
        v = K.views_tabyin(t)
        self.assertEqual([q for q, _ in v], ["القول المقدَّم عند العكبري", "الكوفيون"])


if __name__ == "__main__":
    unittest.main()
