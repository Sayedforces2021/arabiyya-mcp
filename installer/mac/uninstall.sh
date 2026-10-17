#!/bin/bash
CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
python3 - "$CONFIG" <<'EOF'
import json,sys,os
p=sys.argv[1]
if os.path.exists(p):
    c=json.load(open(p,encoding="utf-8-sig") ); c.get("mcpServers",{}).pop("arabiyya",None)
    json.dump(c,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
EOF
rm -rf "$HOME/.sarf/app" "$HOME/.sarf/launch.json"
