"""يبني ورقة مراجعة الإعراب (HTML ثم PDF) من items_with_tool_output.json.
الاستعمال: python build_sheet.py   (يلزم playwright لإخراج PDF)."""
import json, html, os
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "items_with_tool_output.json"), encoding="utf-8"))
e = html.escape
parts = []
for i, o in enumerate(d, 1):
    rows = "".join(f'<tr><td class="w">{e(w)}</td><td>{e(t)}</td><td class="c"></td><td class="c"></td><td class="n"></td></tr>' for w, t in o["rows"])
    parts.append(f'<section><h3><span>{i}</span> {e(o["text"])}</h3><p class="d">الضبط المقترح: {e(o["dabt"])}</p>'
                 f'<table><thead><tr><th>الكلمة</th><th>إعراب الأداة</th><th>صح</th><th>خطأ</th><th>الصواب عندك</th></tr></thead><tbody>{rows}</tbody></table></section>')
CSS = """@page{size:A4;margin:16mm 14mm}body{font-family:"Amiri","Noto Naskh Arabic",serif;font-size:13.5pt;line-height:1.6}
h1{font-size:21pt;margin:0 0 4pt}.sub{color:#444;margin:0 0 10pt}.box{border:1px solid #999;padding:8pt 12pt;margin:8pt 0 14pt;font-size:12pt}
section{break-inside:avoid;margin:0 0 14pt}h3{font-size:15pt;margin:0 0 2pt}h3 span{display:inline-block;min-width:22pt;border:1px solid #555;border-radius:4pt;text-align:center;font-size:11pt;margin-inline-end:6pt}
.d{margin:0 0 4pt;color:#555;font-size:11pt}table{border-collapse:collapse;width:100%;font-size:11.5pt}th,td{border:1px solid #999;padding:3pt 6pt;vertical-align:top}
th{background:#eee}td.w{white-space:nowrap;font-weight:600}td.c{width:34pt}td.n{width:120pt}"""
page = f'''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><title>ورقة مراجعة الإعراب الآلي</title><style>{CSS}</style>
<h1>ورقة مراجعة الإعراب الآلي</h1><p class="sub">أداة «العربية» — {len(d)} جملة، بإعراب الأداة لكل كلمة</p>
<div class="box"><p><b>المطلوب:</b> علامة «صح» أو «خطأ» أمام كل كلمة، والصواب في الخانة الأخيرة إن رأيتَ خطأً.</p>
<p><b>تنبيه:</b> الإعراب آلي (Stanza ثم قواعد نقل إلى أبواب النحو العربي). فيها جمل من القرآن والشعر والأمثلة النحوية، وبعضها مما اختلف فيه النحويون. المقصود قياس دقة الأداة لا الحكم في الخلاف.</p>
<p><b>المراجع:</b> ______________ &nbsp; <b>التاريخ:</b> ________</p></div>{"".join(parts)}</html>'''
out = os.path.join(HERE, "sheet.html")
open(out, "w", encoding="utf-8").write(page)
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); pg.goto("file://" + out)
        pg.pdf(path=os.path.join(HERE, "irab_review_sheet.pdf"), format="A4")
except Exception as ex:
    print("تعذّر إخراج PDF:", ex)
