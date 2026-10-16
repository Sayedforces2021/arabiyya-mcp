"""تجهيز بيانات خادم sarf (يُشغَّل من سكربت التثبيت، ويتخطى ما سبق تجهيزه).
1) المدوّنة القرآنية  2) فهرس المعاجم التراثية  3) فهرس شواهد الشعر  4) نموذج العربية الكلاسيكية ومتجهات مفرداته
"""
import os, sys, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.join(os.path.expanduser("~"), ".sarf")
os.makedirs(HOME, exist_ok=True)
sys.path.insert(0, HERE)
QAC = "https://raw.githubusercontent.com/mustafa0x/quran-morphology/master/"


def step(title, done_file, fn):
    print(f"\n== {title} ==", flush=True)
    if os.path.exists(done_file):
        print("موجود.")
        return True
    try:
        fn()
        return True
    except Exception as e:  # خطوة واحدة لا تُفسد البقية
        print(f"تعذّرت هذه الخطوة: {e!r}\nبقية الأدوات تعمل؛ أرسل هذه الرسالة إلى Claude.", flush=True)
        return False


def quran():
    for f in ("quran-morphology.txt", "morphology-terms-ar.json"):
        urllib.request.urlretrieve(QAC + f, os.path.join(HOME, f + ".part"))
        os.replace(os.path.join(HOME, f + ".part"), os.path.join(HOME, f))
    print("تم.")


def maajim():
    import build_lexicon_index
    build_lexicon_index.main()


def poetry():
    import build_poetry_index
    build_poetry_index.main()


def corpus():
    import build_corpus_index
    build_corpus_index.main()


def semantic():
    # في عملية مستقلة حتى لا يبقى النموذج في الذاكرة
    subprocess.run([sys.executable, os.path.join(HERE, "sarf_mcp.py"), "--build-semantic"], check=True)


ok = [
    step("المدوّنة القرآنية", os.path.join(HOME, "morphology-terms-ar.json"), quran),
    step("المعاجم التراثية (تنزيل نحو 135 م.ب)", os.path.join(HOME, "maajim.db"), maajim),
    step("شواهد الشعر (تنزيل نحو 280 م.ب)", os.path.join(HOME, "ashaar.db"), poetry),
    step("المدوّنة التراثية: 57 كتابًا (تنزيل نحو 105 م.ب)", os.path.join(HOME, "corpus.db"), corpus),
    step("نموذج العربية الكلاسيكية ومتجهات المفردات (تنزيل نحو 440 م.ب، وحساب دقائق)",
         os.path.join(HOME, "ca_vocab_emb_v2.npz"), semantic),
]
print("\nتجهيز البيانات:", "اكتمل." if all(ok) else "اكتمل مع خطوات متعذّرة (انظر أعلاه).")
