#!/bin/bash
# يُشغَّل على ماك: ./build_mac.sh REPO_ROOT OUT_DIR
set -e
ROOT="${1:?repo root}"; OUT="${2:?out dir}"
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$OUT/العربية.app"
rm -rf "$APP"; mkdir -p "$OUT"
osacompile -o "$APP" "$HERE/arabiyya_setup.applescript"
P="$APP/Contents/Resources/payload"; mkdir -p "$P/brand"
cp "$ROOT"/{sarf_mcp,sarf_ilal,diac_model,train_diacritizer,build_poetry_index,build_lexicon_index,build_corpus_index,setup_sarf_data}.py "$ROOT/openiti_catalog.tsv" "$P/"
cp "$ROOT"/brand/arabiyya-icon.svg "$ROOT"/brand/arabiyya-icon-small.svg "$ROOT"/brand/arabiyya-mark.svg "$P/brand/"
cp "$HERE/install_wizard.sh" "$P/"; chmod +x "$P/install_wizard.sh"
# أيقونة
if [ -f "$ROOT/brand/arabiyya-icon-512.png" ]; then
  IS="$OUT/a.iconset"; rm -rf "$IS"; mkdir "$IS"
  for s in 16 32 64 128 256 512; do sips -z $s $s "$ROOT/brand/arabiyya-icon-512.png" --out "$IS/icon_${s}x${s}.png" >/dev/null; done
  cp "$IS/icon_32x32.png" "$IS/icon_16x16@2x.png"; cp "$IS/icon_64x64.png" "$IS/icon_32x32@2x.png"
  cp "$IS/icon_256x256.png" "$IS/icon_128x128@2x.png"; cp "$IS/icon_512x512.png" "$IS/icon_256x256@2x.png"
  rm "$IS/icon_64x64.png"
  iconutil -c icns "$IS" -o "$APP/Contents/Resources/applet.icns"; rm -rf "$IS"
fi
codesign --force --deep -s - "$APP"
cd "$OUT" && rm -f arabiyya-setup-mac.zip && ditto -c -k --keepParent "العربية.app" arabiyya-setup-mac.zip
ls -la arabiyya-setup-mac.zip
