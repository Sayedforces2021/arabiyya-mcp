# يغيّر اسم الأداة في إعدادات Claude من sarf إلى arabiyya
import json, os, glob, sys, shutil
paths = [os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json")]
paths += glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages", "Claude_*", "LocalCache", "Roaming", "Claude", "claude_desktop_config.json"))
done = False
for p in paths:
    if not os.path.exists(p):
        continue
    with open(p, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    srv = cfg.setdefault("mcpServers", {})
    if "sarf" in srv:
        shutil.copy(p, p + ".bak")
        srv["arabiyya"] = srv.pop("sarf")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print("تم:", p)
        done = True
    elif "arabiyya" in srv:
        print("الاسم مغيَّر من قبل:", p)
        done = True
if not done:
    print("لم أجد إعداد sarf.")
