"""بناء المدوّنة التراثية للتحليل الحاسوبي (57 كتابًا من OpenITI في النحو واللغة والبلاغة والشعر والأدب).
ينزّل النصوص من GitHub ويبني ~/.sarf/corpus.db: فقرات بفهرس نصي، وجدول تكرار الألفاظ، وبيانات الكتب.
"""
import os, re, sys, sqlite3, urllib.request
from collections import Counter

RAW = "https://raw.githubusercontent.com/OpenITI/{repo}/master/{path}"
CORPUS = [
    ("نحو", "0200AH", "data/0180Sibawayhi/0180Sibawayhi.KitabSibawayhi/0180Sibawayhi.KitabSibawayhi.Shamela0023018-ara1.mARkdown"),
    ("نحو", "0300AH", "data/0285IbnYazidMubarrad/0285IbnYazidMubarrad.Muqtadab/0285IbnYazidMubarrad.Muqtadab.Shamela0006965-ara1.mARkdown"),
    ("نحو", "0325AH", "data/0316IbnSarrajNahwi/0316IbnSarrajNahwi.UsulFiNahw/0316IbnSarrajNahwi.UsulFiNahw.Shamela0007365-ara1"),
    ("نحو", "0350AH", "data/0337IbnIshaqZajjaji/0337IbnIshaqZajjaji.IdahCilalNahw/0337IbnIshaqZajjaji.IdahCilalNahw.Sham19Y0143170-ara1"),
    ("نحو", "0400AH", "data/0392IbnJinniMawsili/0392IbnJinniMawsili.Khasais/0392IbnJinniMawsili.Khasais.Shamela0009986-ara1"),
    ("نحو", "0400AH", "data/0392IbnJinniMawsili/0392IbnJinniMawsili.LumacFiCarabiyya/0392IbnJinniMawsili.LumacFiCarabiyya.Shamela0006987-ara1"),
    ("نحو", "0550AH", "data/0538JarAllahZamakhshari/0538JarAllahZamakhshari.MufassalFiSuncatIcrab/0538JarAllahZamakhshari.MufassalFiSuncatIcrab.Shamela0000759-ara1"),
    ("نحو", "0600AH", "data/0577AbuBarakatAnbari/0577AbuBarakatAnbari.AsrarCarabiyya/0577AbuBarakatAnbari.AsrarCarabiyya.Shamela0007502-ara1"),
    ("نحو", "0600AH", "data/0577AbuBarakatAnbari/0577AbuBarakatAnbari.InsafFiMasail/0577AbuBarakatAnbari.InsafFiMasail.Shamela0007362-ara1"),
    ("نحو", "0650AH", "data/0643IbnYacish/0643IbnYacish.SharhMufassal/0643IbnYacish.SharhMufassal.Sham19Y0013301-ara1"),
    ("نحو", "0675AH", "data/0672IbnMalik/0672IbnMalik.SharhTashilFawaid/0672IbnMalik.SharhTashilFawaid.Sham19Y0013257-ara1"),
    ("نحو", "0700AH", "data/0686RadiDinAstarabadhi/0686RadiDinAstarabadhi.SharhRadiCalaKafiya/0686RadiDinAstarabadhi.SharhRadiCalaKafiya.ShamAY0034696-ara3"),
    ("نحو", "0700AH", "data/0686RadiDinAstarabadhi/0686RadiDinAstarabadhi.SharhShafiyaIbnHajib/0686RadiDinAstarabadhi.SharhShafiyaIbnHajib.Shamela0021567-ara1"),
    ("نحو", "0775AH", "data/0761JamalDinIbnHisham/0761JamalDinIbnHisham.AwdahMasalik/0761JamalDinIbnHisham.AwdahMasalik.Shamela0011825-ara1"),
    ("نحو", "0775AH", "data/0761JamalDinIbnHisham/0761JamalDinIbnHisham.MughniLabib/0761JamalDinIbnHisham.MughniLabib.Shamela0006972-ara1"),
    ("نحو", "0775AH", "data/0761JamalDinIbnHisham/0761JamalDinIbnHisham.SharhQatrNada/0761JamalDinIbnHisham.SharhQatrNada.Shamela0006970-ara1"),
    ("نحو", "0775AH", "data/0761JamalDinIbnHisham/0761JamalDinIbnHisham.SharhShudhurDhahab/0761JamalDinIbnHisham.SharhShudhurDhahab.Shamela0006969-ara1"),
    ("نحو", "0775AH", "data/0769IbnCaqilBahaDinMisri/0769IbnCaqilBahaDinMisri.SharhCalaAlfiyya/0769IbnCaqilBahaDinMisri.SharhCalaAlfiyya.Shamela0009904-ara1"),
    ("نحو", "0900AH", "data/0900IbnMuhammadNurDinAshmuni/0900IbnMuhammadNurDinAshmuni.SharhCalaAlfiyyatMalik/0900IbnMuhammadNurDinAshmuni.SharhCalaAlfiyyatMalik.Shamela0011742-ara1"),
    ("نحو", "0925AH", "data/0911Suyuti/0911Suyuti.HamcHawamic/0911Suyuti.HamcHawamic.Shamela0006975-ara1"),
    ("لغة", "0250AH", "data/0244IbnSikkit/0244IbnSikkit.IslahMantiq/0244IbnSikkit.IslahMantiq.Shamela0007508-ara1.completed"),
    ("لغة", "0300AH", "data/0291IbnYahyaThaclab/0291IbnYahyaThaclab.Fasih/0291IbnYahyaThaclab.Fasih.Shamela0096608-ara1"),
    ("لغة", "0450AH", "data/0429AbuMansurThacalibi/0429AbuMansurThacalibi.FiqhLugha/0429AbuMansurThacalibi.FiqhLugha.Shamela0011235-ara1.mARkdown"),
    ("لغة", "0925AH", "data/0911Suyuti/0911Suyuti.MuzhirFiCulumLugha/0911Suyuti.MuzhirFiCulumLugha.Shamela0006936-ara1"),
    ("بلاغة", "0400AH", "data/0395AbuHilalCaskari/0395AbuHilalCaskari.Sinacatayn/0395AbuHilalCaskari.Sinacatayn.Shamela0023787-ara1.inProgress"),
    ("بلاغة", "0475AH", "data/0471CabdQahirJurjani/0471CabdQahirJurjani.AsrarBalagha/0471CabdQahirJurjani.AsrarBalagha.Shamela0008187-ara1"),
    ("بلاغة", "0475AH", "data/0471CabdQahirJurjani/0471CabdQahirJurjani.DalailIcjaz/0471CabdQahirJurjani.DalailIcjaz.Shamela0012055-ara1"),
    ("بلاغة", "0650AH", "data/0626IbnMuhammadKhwarazmiSakkaki/0626IbnMuhammadKhwarazmiSakkaki.MiftahCulum/0626IbnMuhammadKhwarazmiSakkaki.MiftahCulum.Shamela0026581-ara1"),
    ("بلاغة", "0750AH", "data/0739JalalDinQazwini/0739JalalDinQazwini.IdahFiCulumBalagha/0739JalalDinQazwini.IdahFiCulumBalagha.JK001001-ara1"),
    ("بلاغة", "0750AH", "data/0739JalalDinQazwini/0739JalalDinQazwini.TalkhisMiftah/0739JalalDinQazwini.TalkhisMiftah.Kraken220201000819-ara1"),
    ("بلاغة", "0800AH", "data/0792IbnCumarTaftazani/0792IbnCumarTaftazani.MukhtasarMacani/0792IbnCumarTaftazani.MukhtasarMacani.ShamAY0033799-ara1"),
    ("شعر", "0175AH", "data/0168MufaddalDabbi/0168MufaddalDabbi.Mufaddaliyyat/0168MufaddalDabbi.Mufaddaliyyat.Shamela0006904-ara1.completed"),
    ("شعر", "0175AH", "data/0170AbuZaydQurashi/0170AbuZaydQurashi.JamharatAshcarCarab/0170AbuZaydQurashi.JamharatAshcarCarab.Shamela0001487-ara1"),
    ("شعر", "0225AH", "data/0216IbnQuraybAsmaci/0216IbnQuraybAsmaci.Asmaciyyat/0216IbnQuraybAsmaci.Asmaciyyat.Shamela0006905-ara1.mARkdown"),
    ("شعر", "0300AH", "data/0284Buhturi/0284Buhturi.Hamasa/0284Buhturi.Hamasa.Sham19Y0148535-ara1"),
    ("أدب", "0250AH", "data/0231IbnSallamJumahi/0231IbnSallamJumahi.TabaqatFuhulShucara/0231IbnSallamJumahi.TabaqatFuhulShucara.Shamela0006738-ara1"),
    ("أدب", "0275AH", "data/0255Jahiz/0255Jahiz.BayanWaTabyin/0255Jahiz.BayanWaTabyin.Shamela0010614-ara1.completed"),
    ("أدب", "0275AH", "data/0255Jahiz/0255Jahiz.Hayawan/0255Jahiz.Hayawan.Shamela0023775-ara1.completed"),
    ("أدب", "0300AH", "data/0276IbnQutaybaDinawari/0276IbnQutaybaDinawari.AdabKatib/0276IbnQutaybaDinawari.AdabKatib.Shamela0026349-ara1.mARkdown"),
    ("أدب", "0300AH", "data/0276IbnQutaybaDinawari/0276IbnQutaybaDinawari.CuyunAkhbar/0276IbnQutaybaDinawari.CuyunAkhbar.Shamela0023790-ara1.completed"),
    ("أدب", "0300AH", "data/0276IbnQutaybaDinawari/0276IbnQutaybaDinawari.ShicrWaShucara/0276IbnQutaybaDinawari.ShicrWaShucara.Shamela0023785-ara1.mARkdown"),
    ("أدب", "0300AH", "data/0285IbnYazidMubarrad/0285IbnYazidMubarrad.KamilFiLugha/0285IbnYazidMubarrad.KamilFiLugha.Shamela0008505-ara1.mARkdown"),
    ("أدب", "0350AH", "data/0328IbnCabdRabbih/0328IbnCabdRabbih.CiqdFarid/0328IbnCabdRabbih.CiqdFarid.Shamela0023789-ara1.completed"),
    ("أدب", "0375AH", "data/0356AbuCaliQali/0356AbuCaliQali.AmaliFiLugha/0356AbuCaliQali.AmaliFiLugha.Shamela0009160-ara1"),
    ("أدب", "0375AH", "data/0362AbuFarajIsbahani/0362AbuFarajIsbahani.Aghani/0362AbuFarajIsbahani.Aghani.JK000927-ara1.completed"),
    ("أدب", "0400AH", "data/0384IbnCimranMarzubani/0384IbnCimranMarzubani.Muwashshah/0384IbnCimranMarzubani.Muwashshah.Shamela0009427-ara1.completed"),
    ("أدب", "0400AH", "data/0398BadicZamanHamadhani/0398BadicZamanHamadhani.Maqamat/0398BadicZamanHamadhani.Maqamat.Shamela0028113-ara1"),
    ("أدب", "0425AH", "data/0406SharifRadi/0406SharifRadi.NahjBalagha/0406SharifRadi.NahjBalagha.Shia20200618-ara1.mARkdown"),
    ("أدب", "0425AH", "data/0413AbuIshaqHusri/0413AbuIshaqHusri.ZahrAdab/0413AbuIshaqHusri.ZahrAdab.Shamela0010768-ara1"),
    ("أدب", "0425AH", "data/0421IbnMuhammadMarzuqi/0421IbnMuhammadMarzuqi.SharhDiwanHamasa/0421IbnMuhammadMarzuqi.SharhDiwanHamasa.Shamela0026536-ara1.completed"),
    ("أدب", "0450AH", "data/0429AbuMansurThacalibi/0429AbuMansurThacalibi.YatimatDahr/0429AbuMansurThacalibi.YatimatDahr.Shamela0006743-ara1.mARkdown"),
    ("أدب", "0450AH", "data/0436SharifMurtada/0436SharifMurtada.Amali/0436SharifMurtada.Amali.Masaha003390Vols-ara1"),
    ("أدب", "0525AH", "data/0516IbnCaliHariri/0516IbnCaliHariri.Maqamat/0516IbnCaliHariri.Maqamat.Shamela0026585-ara1"),
    ("أدب", "0675AH", "data/0656IbnAbiHadid/0656IbnAbiHadid.SharhNahjBalagha/0656IbnAbiHadid.SharhNahjBalagha.Shia002185Vols-ara1.completed"),
    ("أدب", "0850AH", "data/0837IbnHijjaHamawi/0837IbnHijjaHamawi.KhizanatAdab/0837IbnHijjaHamawi.KhizanatAdab.Shamela0008675-ara1"),
    ("أدب", "0850AH", "data/0850ShihabDinIbshihi/0850ShihabDinIbshihi.Mustatraf/0850ShihabDinIbshihi.Mustatraf.Shamela0023802-ara1"),
    ("أدب", "1100AH", "data/1093CabdQadirBaghdadi/1093CabdQadirBaghdadi.KhizanatAdab/1093CabdQadirBaghdadi.KhizanatAdab.Shamela0012732-ara1"),
]

# عناوين وأسماء لما خلت بياناته في OpenITI
NAMES = {
    "0337IbnIshaqZajjaji.IdahCilalNahw": ("الإيضاح في علل النحو", "الزجاجي"),
    "0643IbnYacish.SharhMufassal": ("شرح المفصل", "ابن يعيش"),
    "0672IbnMalik.SharhTashilFawaid": ("شرح تسهيل الفوائد", "ابن مالك"),
    "0686RadiDinAstarabadhi.SharhRadiCalaKafiya": ("شرح الرضي على الكافية", "رضي الدين الأستراباذي"),
    "0739JalalDinQazwini.TalkhisMiftah": ("تلخيص المفتاح", "الخطيب القزويني"),
    "0792IbnCumarTaftazani.MukhtasarMacani": ("مختصر المعاني", "سعد الدين التفتازاني"),
    "0284Buhturi.Hamasa": ("الحماسة", "البحتري"),
    "0436SharifMurtada.Amali": ("أمالي المرتضى (غرر الفوائد ودرر القلائد)", "الشريف المرتضى"),
}

HARAKAT = re.compile("[ً-ْـٰ]")
TR = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "ء", "ئ": "ء"})
PAGE = re.compile(r"PageV(\d+)P(\d+)")
TOKEN = re.compile("[ء-ي]+")


def norm(s):
    return HARAKAT.sub("", s or "").translate(TR)


def clean(line):
    line = PAGE.sub("", line)
    line = re.sub(r"\bms\d+\b|@[A-Z0-9]+@|#~:\w+:|%~%", " ", line)
    line = line.replace("~~", " ").lstrip("#$| ").strip()
    return re.sub(r"\s+", " ", line)


def parse(path):
    meta, paras, pending, cur = {}, [], [], None
    with open(path, encoding="utf-8") as f:
        header = True
        for raw in f:
            line = raw.rstrip("\n")
            if header:
                m = re.match(r"#META# \d+\.(\w+)\s*::\s*(.*)", line)
                if m:
                    meta[m.group(1)] = m.group(2).strip()
                if line.startswith("#META#Header#End#"):
                    header = False
                continue
            for m in PAGE.finditer(line):
                for p in pending:
                    p[0], p[1] = int(m.group(1)), int(m.group(2))
                pending.clear()
            if line.startswith("~~") and cur is not None:
                t = clean(line)
                if t:
                    cur[2] += " " + t
                continue
            t = clean(line)
            if not t or not TOKEN.search(t):
                continue
            if re.fullmatch(r"[\d\s\-–.()]+", t):
                continue
            cur = [None, None, t]
            paras.append(cur)
            pending.append(cur)
    return meta, paras


def download(repo, path, local, timeout=180):
    req = urllib.request.urlopen(RAW.format(repo=repo, path=path), timeout=timeout)
    with open(local + ".part", "wb") as f:
        while True:
            b = req.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(local + ".part", local)


def book_names(uri, meta, title_hint=None, author_hint=None):
    title = meta.get("BookTITLE", "NODATA")
    author = meta.get("AuthorNAME", "NODATA")
    if uri in NAMES:
        title, author = NAMES[uri]
    if title in ("NODATA", "") and title_hint:
        title = title_hint
    if author in ("NODATA", "") and author_hint:
        author = author_hint
    title = uri.split(".")[1] if title in ("NODATA", "") else title
    author = re.sub(r"\s*\(المتوفى.*?\)", "", author) if author not in ("NODATA", "") else uri.split(".")[0][4:]
    return title.strip(), author.strip()


def insert_book(con, bid, pid, genre, uri, meta, paras, title_hint=None, author_hint=None):
    """يُدرج كتابًا في المدوّنة ويعيد (العنوان، عدد الكلمات، عدّاد الألفاظ، آخر رقم فقرة)."""
    died = int(uri[:4])
    title, author = book_names(uri, meta, title_hint, author_hint)
    ntok, rows, frows, counts = 0, [], [], Counter()
    for vol, page, text in paras:
        pid += 1
        n = norm(text)
        toks = TOKEN.findall(n)
        ntok += len(toks)
        counts.update(toks)
        rows.append((pid, bid, vol, page, text))
        frows.append((pid, n))
    con.execute("INSERT INTO books VALUES (?,?,?,?,?,?,?)", (bid, uri, title, author, died, genre, ntok))
    con.executemany("INSERT INTO paras VALUES (?,?,?,?,?)", rows)
    con.executemany("INSERT INTO paras_fts(rowid, body) VALUES (?,?)", frows)
    return title, ntok, counts, pid


def main(src_dir=None):
    home = os.path.join(os.path.expanduser("~"), ".sarf")
    src_dir = src_dir or os.path.join(home, "corpus_src")
    os.makedirs(src_dir, exist_ok=True)
    out = os.path.join(home, "corpus.db")
    tmp = out + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE books(id INTEGER PRIMARY KEY, uri TEXT, title TEXT, author TEXT, died INTEGER, genre TEXT, tokens INTEGER);
        CREATE TABLE paras(id INTEGER PRIMARY KEY, book INTEGER, vol INTEGER, page INTEGER, text TEXT);
        CREATE VIRTUAL TABLE paras_fts USING fts5(body, content='', tokenize='unicode61 remove_diacritics 0');
        CREATE TABLE freq(token TEXT PRIMARY KEY, n INTEGER) WITHOUT ROWID;
    """)
    total = Counter()
    pid = 0
    for bid, (genre, repo, path) in enumerate(CORPUS, 1):
        local = os.path.join(src_dir, os.path.basename(path))
        if not os.path.exists(local):
            print("تنزيل", os.path.basename(path).split(".")[1], "...", flush=True)
            download(repo, path, local)
        meta, paras = parse(local)
        uri = ".".join(os.path.basename(path).split(".")[:2])
        title, ntok, counts, pid = insert_book(con, bid, pid, genre, uri, meta, paras)
        total.update(counts)
        con.commit()
        print(f"{title}: {ntok:,} كلمة", flush=True)
    con.executemany("INSERT INTO freq VALUES (?,?)", ((t, n) for t, n in total.items() if n >= 2))
    con.execute("CREATE INDEX idx_paras_book ON paras(book)")
    con.execute("INSERT INTO paras_fts(paras_fts) VALUES('optimize')")
    con.commit()
    con.close()
    os.replace(tmp, out)
    if src_dir == os.path.join(home, "corpus_src"):
        for _g, _r, path in CORPUS:
            try:
                os.remove(os.path.join(src_dir, os.path.basename(path)))
            except OSError:
                pass
    print("تم:", out, f"({sum(total.values()):,} كلمة)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
