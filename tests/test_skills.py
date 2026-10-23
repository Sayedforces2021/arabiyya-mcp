# -*- coding: utf-8 -*-
"""مهارات الإضافة: رأس كل مهارة YAML صحيح باسمها ووصفها، وكل أداة تذكرها موجودة في الخادم.
(وصفٌ فيه «: » بلا علامتي تنصيص يفسد الرأس، كما وقع في مهارة setup.)"""
import glob, os, re, unittest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
TOOLS = set(re.findall(r"^def (\w+)\(", open(os.path.join(ROOT, "sarf_mcp.py"), encoding="utf-8").read(), re.M))


def front(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", t, re.S)
    return t, (yaml.safe_load(m.group(1)) if m else None)


class TestSkills(unittest.TestCase):
    def test_front_matter(self):
        self.assertGreaterEqual(len(SKILLS), 8)
        for p in SKILLS:
            _t, fm = front(p)
            name = os.path.basename(os.path.dirname(p))
            self.assertIsInstance(fm, dict, p)
            self.assertEqual(fm.get("name"), name, p)
            self.assertGreater(len(fm.get("description") or ""), 40, p)

    def test_tool_calls_exist(self):
        # ما يُذكر في المهارة على صورة استدعاء («`mizan(…)`») أو اسمٍ فيه شرطة سفلية يجب أن يكون أداة في الخادم
        for p in SKILLS:
            t, _fm = front(p)
            called = set(re.findall(r"`([a-z_]+)\(", t)) | {x for x in re.findall(r"`([a-z]+_[a-z_]+)`", t)}
            unknown = sorted(c for c in called if c not in TOOLS)
            self.assertEqual(unknown, [], p)


if __name__ == "__main__":
    unittest.main()
