"""تجهيز بيانات خادم sarf (يُشغَّل من سكربت التثبيت، ويتخطى ما سبق تجهيزه).
1) المدوّنة القرآنية  2) فهرس المعاجم التراثية  3) فهرس شواهد الشعر  4) المدوّنة التراثية  5) نموذج العربية الكلاسيكية ومتجهات مفرداته  6) كتب الفروق والأضداد  7) المحلل النحوي
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


LUGHAWIYYAT = ["0395AbuHilalCaskari.FuruqLughawiyya", "0328AbuBakrIbnAnbari.Addad", "0244IbnSikkit.QalbWaIbdal",
               "0351AbuTayyibLughawi.Ibdal", "0351AbuTayyibLughawi.Ittibac", "0582IbnBarri.FiTacrib",
               "0911Suyuti.MuhadhdhabFimaWaqaca", "0685SadidDinMuhallabi.MuthallathatLughawiyya"]


def lughawiyyat():
    """إضافة كتب الفروق والأضداد والإبدال والمعرّب والمثلثات إلى المدوّنة (يتخطى ما أضيف)."""
    import sqlite3
    import build_corpus_index as bci
    cat = {}
    for p in (os.path.join(HERE, "openiti_catalog.tsv"),):
        with open(p, encoding="utf-8") as f:
            for line in f:
                c = line.rstrip("\n").split("\t")
                if len(c) >= 7:
                    cat[c[0]] = c
    con = sqlite3.connect(os.path.join(HOME, "corpus.db"), timeout=60)
    have = {u for (u,) in con.execute("SELECT uri FROM books")}
    for uri in LUGHAWIYYAT:
        if uri in have or uri not in cat:
            continue
        c = cat[uri]
        t, n, k = bci.add_book(con, c[5], c[6], uri, "لغة", c[3], c[2].split("(")[0].strip())
        print(f"{t}: {n:,} كلمة", flush=True)
    con.close()
    open(os.path.join(HOME, "lughawiyyat.done"), "w").close()


def stanza_models():
    """نموذج المحلل النحوي Stanza للعربية (AraELECTRA على شجرة PADT)، مع النموذج الافتراضي احتياطًا."""
    import stanza
    stanza.download("ar", package="default_accurate", processors="tokenize,mwt,pos,lemma,depparse", verbose=False)
    stanza.download("ar", package="default", processors="tokenize,mwt,pos,lemma,depparse", verbose=False)
    from transformers import AutoModel, AutoTokenizer  # يعتمد عليه النموذج الأدق، ولا يُنزّله Stanza وحده
    AutoTokenizer.from_pretrained("aubmindlab/araelectra-base-discriminator")
    AutoModel.from_pretrained("aubmindlab/araelectra-base-discriminator")
    nlp = stanza.Pipeline("ar", processors="tokenize,mwt,pos,lemma,depparse", package="default_accurate",
                          download_method=None, verbose=False, use_gpu=False)
    nlp("ذهب الطالب إلى المدرسة")  # يُنزّل نموذج المحوّل عند أول تشغيل
    open(os.path.join(HOME, "stanza.done"), "w").close()
    print("تم.")


def catt_models():
    """نموذج CATT للتشكيل (محوِّل على مستوى الحروف مدرَّب على النصوص التراثية)."""
    from catt_tashkeel import CATTEncoderDecoder
    ed = CATTEncoderDecoder()
    print(ed.do_tashkeel("ذهب الطالب إلى المدرسة", verbose=False))
    open(os.path.join(HOME, "catt.done"), "w").close()


ok = [
    step("المدوّنة القرآنية", os.path.join(HOME, "morphology-terms-ar.json"), quran),
    step("المعاجم التراثية (تنزيل نحو 135 م.ب)", os.path.join(HOME, "maajim.db"), maajim),
    step("شواهد الشعر (تنزيل نحو 280 م.ب)", os.path.join(HOME, "ashaar.db"), poetry),
    step("المدوّنة التراثية: 57 كتابًا (تنزيل نحو 105 م.ب)", os.path.join(HOME, "corpus.db"), corpus),
    step("نموذج العربية الكلاسيكية ومتجهات المفردات (تنزيل نحو 440 م.ب، وحساب دقائق)",
         os.path.join(HOME, "ca_vocab_emb_v2.npz"), semantic),
    step("كتب الفروق والأضداد والإبدال والمعرّب (تنزيل نحو 15 م.ب)", os.path.join(HOME, "lughawiyyat.done"), lughawiyyat),
    step("مشكِّل النصوص التراثية CATT (تنزيل نحو 200 م.ب)", os.path.join(HOME, "catt.done"), catt_models),
    step("المحلل النحوي للإعراب: Stanza مع AraELECTRA (تنزيل نحو 700 م.ب)", os.path.join(HOME, "stanza.done"), stanza_models),
]
print("\nتجهيز البيانات:", "اكتمل." if all(ok) else "اكتمل مع خطوات متعذّرة (انظر أعلاه).")
