#!/usr/bin/env node
// مُشغِّل إضافة «العربية»: يجد Python البيئة sarf والخادم المثبّت على الجهاز، ثم يشغّله.
// الأداة نفسها (النماذج والبيانات) تُثبَّت مرة واحدة بملف التثبيت؛ والإضافة تربطها بـ Claude.
const fs = require("fs"), path = require("path"), os = require("os");
const { spawn } = require("child_process");
const home = os.homedir(), win = process.platform === "win32";
const ok = (p) => { try { return !!p && fs.existsSync(p); } catch { return false; } };

let py = null, server = null;
try {
  const j = JSON.parse(fs.readFileSync(path.join(home, ".sarf", "launch.json"), "utf8"));
  py = j.python; server = j.server;
} catch {}

const envs = win
  ? [path.join(home, "miniconda3"), path.join(home, "anaconda3"),
     path.join(process.env.LOCALAPPDATA || "", "miniconda3"), "C:\\ProgramData\\miniconda3", "C:\\ProgramData\\anaconda3"]
      .map((b) => path.join(b, "envs", "sarf", "python.exe"))
  : ["/opt/homebrew/Caskroom/miniconda/base", path.join(home, "miniconda3"), path.join(home, "anaconda3"),
     "/opt/miniconda3", "/opt/anaconda3", "/opt/homebrew/anaconda3", path.join(home, "opt", "anaconda3")]
      .map((b) => path.join(b, "envs", "sarf", "bin", "python"));
const servers = [path.join(home, ".sarf", "app", "sarf_mcp.py"), path.join(home, "claude", "sarf_mcp.py")];

if (!ok(py)) py = envs.find(ok);
if (!ok(server)) server = servers.find(ok);
if (!py || !server) {
  process.stderr.write(
    "[arabiyya] لم أجد الأداة مثبّتة على هذا الجهاز. شغّل ملف التثبيت من https://github.com/ikagi07/arabiyya-mcp ثم أعد تشغيل Claude.\n" +
    `python: ${py || "-"}  server: ${server || "-"}\n`);
  process.exit(1);
}

const child = spawn(py, [server], {
  stdio: "inherit",
  cwd: path.dirname(server),
  env: { ...process.env, PYTHONUNBUFFERED: "1", PYTHONIOENCODING: "utf-8" },
});
child.on("error", (e) => { process.stderr.write(`[arabiyya] ${e.message}\n`); process.exit(1); });
child.on("exit", (code) => process.exit(code ?? 0));
for (const s of ["SIGINT", "SIGTERM"]) process.on(s, () => child.kill(s));
