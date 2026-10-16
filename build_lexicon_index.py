"""بناء فهرس المعاجم التراثية بلا إنترنت من نصوص مشروع OpenITI (نسخ الشاملة).
يُنزّل نصوص المعاجم من GitHub ويبني ~/.sarf/maajim.db مفهرسًا بالجذر.
"""
import os, re, sys, sqlite3, urllib.request

RAW = "https://raw.githubusercontent.com/OpenITI/{repo}/master/data/{path}"
# (المعرّف، الاسم، سنة الوفاة، المستودع، المسار)
BOOKS = [
    ("cayn", "العين للخليل بن أحمد", 170, "0175AH", "0170KhalilFarahidi/0170KhalilFarahidi.Cayn/0170KhalilFarahidi.Cayn.Shamela0001682-ara1"),
    ("jamhara", "جمهرة اللغة لابن دريد", 321, "0325AH", "0321IbnDuraydAzdi/0321IbnDuraydAzdi.JamharatLugha/0321IbnDuraydAzdi.JamharatLugha.Shamela0007032-ara1"),
    ("tahdhib", "تهذيب اللغة للأزهري", 370, "0375AH", "0370AbuMansurAzhari/0370AbuMansurAzhari.TahdhibLugha/0370AbuMansurAzhari.TahdhibLugha.Shamela0007031-ara1"),
    ("sihah", "الصحاح للجوهري", 393, "0400AH", "0393IbnHammadJawhari/0393IbnHammadJawhari.SihahTajLugha/0393IbnHammadJawhari.SihahTajLugha.Shamela0023235-ara1"),
    ("maqayis", "مقاييس اللغة لابن فارس", 395, "0400AH", "0395IbnFarisQazwini/0395IbnFarisQazwini.MucjamMaqayis/0395IbnFarisQazwini.MucjamMaqayis.Shamela0021710-ara1"),
    ("mujmal", "مجمل اللغة لابن فارس", 395, "0400AH", "0395IbnFarisQazwini/0395IbnFarisQazwini.MujmalLugha/0395IbnFarisQazwini.MujmalLugha.Shamela0009252-ara1"),
    ("muhkam", "المحكم والمحيط الأعظم لابن سيده", 458, "0475AH", "0458IbnSidaMursi/0458IbnSidaMursi.MuhkamWaMuhit/0458IbnSidaMursi.MuhkamWaMuhit.Shamela0009757-ara1"),
    ("mufradat", "المفردات للراغب الأصفهاني", 502, "0525AH", "0502RaghibIsbahani/0502RaghibIsbahani.Mufradat/0502RaghibIsbahani.Mufradat.Shamela0023636-ara1"),
    ("asas", "أساس البلاغة للزمخشري", 538, "0550AH", "0538JarAllahZamakhshari/0538JarAllahZamakhshari.AsasBalagha/0538JarAllahZamakhshari.AsasBalagha.Shamela0021568-ara1"),
    ("nihaya", "النهاية في غريب الحديث لابن الأثير", 606, "0625AH", "0606IbnAthirMajdDin/0606IbnAthirMajdDin.NihayaFiGharib/0606IbnAthirMajdDin.NihayaFiGharib.Shamela0023691-ara1"),
    ("mukhtar", "مختار الصحاح للرازي", 666, "0675AH", "0666IbnAbiBakrZaynDinRazi/0666IbnAbiBakrZaynDinRazi.MukhtarSihah/0666IbnAbiBakrZaynDinRazi.MukhtarSihah.Shamela0023193-ara1"),
    ("lisan", "لسان العرب لابن منظور", 711, "0725AH", "0711IbnManzurIfriqi/0711IbnManzurIfriqi.LisanCarab/0711IbnManzurIfriqi.LisanCarab.Shamela0001687-ara1.mARkdown"),
    ("misbah", "المصباح المنير للفيومي", 770, "0775AH", "0770IbnMuhammadFayyumiHamawi/0770IbnMuhammadFayyumiHamawi.MisbahMunir/0770IbnMuhammadFayyumiHamawi.MisbahMunir.Shamela0012145-ara1"),
    ("qamus", "القاموس المحيط للفيروزآبادي", 817, "0825AH", "0817MajdDinFiruzabadi/0817MajdDinFiruzabadi.QamusMuhit/0817MajdDinFiruzabadi.QamusMuhit.Shamela0007283-ara1"),
    ("taj", "تاج العروس للزبيدي", 1205, "1225AH", "1205MurtadaZabidi/1205MurtadaZabidi.TajCarus/1205MurtadaZabidi.TajCarus.Shamela0007030-ara1"),
]

HARAKAT = re.compile("[ً-ْـٰ]")
LETTER_NAMES = {
    "الهمزة": "ء", "الألف": "ا", "الالف": "ا", "الباء": "ب", "التاء": "ت", "الثاء": "ث", "الجيم": "ج",
    "الحاء": "ح", "الخاء": "خ", "الدال": "د", "الذال": "ذ", "الراء": "ر", "الزاي": "ز", "الزاء": "ز",
    "السين": "س", "الشين": "ش", "الصاد": "ص", "الضاد": "ض", "الطاء": "ط", "الظاء": "ظ", "العين": "ع",
    "الغين": "غ", "الفاء": "ف", "القاف": "ق", "الكاف": "ك", "اللام": "ل", "الميم": "م", "النون": "ن",
    "الهاء": "ه", "الواو": "و", "الياء": "ي",
}
PAGE = re.compile(r"PageV(\d+)P(\d+)")
AR = "ء-ي"


def norm_key(s):
    s = HARAKAT.sub("", s or "")
    s = re.sub("[أإآؤئ]", "ء", s)
    s = s.replace("ى", "ي").replace("ة", "ه")
    return re.sub(f"[^{AR}]", "", s)


def title_keys(title):
    """مفاتيح الجذر من عنوان الباب. يعيد (المفاتيح، نوعها)."""
    t = HARAKAT.sub("", title)
    t = re.sub(r"[\[\]\(\)«»\"'.,:؛،\-–]", " ", t).strip()
    names = re.findall("|".join(LETTER_NAMES), t)
    if len(names) >= 2 and len(re.findall(f"[{AR}]+", t)) <= len(names) * 2 + 4:
        groups = re.findall(f"(?:(?<![{AR}])[{AR}] ){{1,3}}[{AR}](?![{AR}])", t)
        keys = {norm_key(g) for g in groups}
        letters = "".join(LETTER_NAMES[n] for n in names)
        keys.add("~" + "".join(sorted(norm_key(letters))))  # باب تقاليب: مفتاح بالحروف مرتبة
        return keys, "taqalib"
    groups = re.findall(f"(?:(?<![{AR}])[{AR}]{{1,2}} ){{1,3}}[{AR}]{{1,2}}(?![{AR}])", t)
    if groups:
        ks = {norm_key(g) for g in groups if 2 <= len(norm_key(g)) <= 5}
        if ks:
            # الجمهرة ترتّب التقاليب تحت حروفها مرتبةً؛ فمفتاح إضافي بالحروف مرتبة
            ks |= {"~" + "".join(sorted(k)) for k in ks}
            return ks, "exact"
    words = re.findall(f"[{AR}]+", t)
    if len(words) == 1 and 2 <= len(words[0]) <= 5:
        return {norm_key(words[0])}, "exact"
    return set(), None


HEADWORD = re.compile(rf"^(?:### \$ |# |~~)?\s*([{AR}ً-ْ]{{2,7}})\s*:")
STOP_HEADWORDS = {norm_key(w) for w in (
    "قال قالت وقال يقال ويقال قلت وقلت قالوا انشد وانشد أنشد وأنشد قيل وقيل قوله ومنه يريد يعني "
    "روي وروي حكى وحكى حكي والجمع والواحد وهو وهي واحدها تقول ويقولون وانشدنا وانشدني اي أي ثعلب الليث "
    "الاصمعي الأصمعي الفراء شمر الجوهري ابن الاعرابي التهذيب المحكم الصحاح").split()}
BRACKET_HW = re.compile(rf"^#\s*\[([{AR}\u064b-\u0652]{{2,6}})\]")
BULLET = re.compile(rf"^#\s*•\s*([{AR}ً-ْ]+)")


def strip_al(w):
    w = norm_key(w)
    for p in ("وال", "ال"):
        if w.startswith(p) and len(w) - len(p) >= 2:
            w = w[len(p):]
            break
    return w


def bullet_keys(word, bab, fasl):
    """مفاتيح محتملة لمدخل القاموس: يُحذف «ال» والتاء/الهاء الأخيرة وحروف المد الداخلة، ويُقيَّد بالباب والفصل."""
    w = strip_al(word)
    cands = {w}
    if w.endswith("ه") and len(w) > 3:
        cands.add(w[:-1])
    for c in list(cands):
        inner = c[0] + re.sub("[اوي]", "", c[1:-1]) + c[-1] if len(c) > 3 else c
        cands.add(inner)
    ok = {c for c in cands if 2 <= len(c) <= 5
          and (not fasl or c[0] == fasl or (fasl in "ءا" and c[0] in "ءا"))
          and (not bab or c[-1] == bab or (bab in "وي" and c[-1] in "اويهء"))}
    return ok or {w}


TAQALIB_BOOKS = {"cayn", "jamhara", "tahdhib", "muhkam"}


def parse_book(path, bid=""):
    units, cur = [], None
    pending = []
    bab = fasl = None

    def new_unit(title, keys, kind):
        nonlocal cur
        cur = {"title": title, "keys": keys, "kind": kind, "lines": [], "page": None}
        units.append(cur)
        pending.append(cur)

    with open(path, encoding="utf-8") as f:
        in_header = True
        for raw in f:
            line = raw.rstrip("\n")
            if in_header:
                if line.startswith("#META#Header#End#"):
                    in_header = False
                continue
            for m in PAGE.finditer(line):
                for u in pending:
                    u["page"] = (int(m.group(1)), int(m.group(2)))
                pending.clear()
            clean = PAGE.sub("", line)
            clean = re.sub(r"\bms\d+\b", "", clean)
            if clean.startswith("### $"):
                m = HEADWORD.match(clean)
                key = norm_key(m.group(1)) if m else None
                new_unit(m.group(1) if m else clean[5:40].strip(), {key} if key else set(), "exact")
                cur["lines"].append(clean[5:].strip())
                continue
            if clean.startswith("### "):
                title = clean.lstrip("#").lstrip(" |").strip()
                mb = re.match(r"(باب|فصل)\s+(\S+)", HARAKAT.sub("", title))
                if mb and mb.group(2) in LETTER_NAMES:
                    if mb.group(1) == "باب":
                        bab, fasl = LETTER_NAMES[mb.group(2)], None
                    else:
                        fasl = LETTER_NAMES[mb.group(2)]
                keys, kind = title_keys(title)
                if kind == "exact" and bid in TAQALIB_BOOKS:
                    kind = "taqalib"  # أبواب هذه المعاجم تجمع تقاليب الجذر
                new_unit(title, keys, kind)
                continue
            m = HEADWORD.match(clean)
            br = BRACKET_HW.match(clean)
            hk = norm_key(m.group(1)) if m else ""
            if br and cur is not None and cur["kind"] in ("taqalib", None, "sub"):
                new_unit(br.group(1), {norm_key(br.group(1))}, "sub")
            elif (m and cur is not None and cur["kind"] in ("taqalib", None, "sub") and clean.startswith("# ")
                    and hk not in STOP_HEADWORDS and len(hk) <= 5 and not hk.startswith(("ال", "وال"))):
                new_unit(m.group(1), {hk}, "sub")
            else:
                b = BULLET.match(clean)
                if b and cur is not None and cur["kind"] in (None, "bullet"):
                    new_unit(b.group(1), bullet_keys(b.group(1), bab, fasl), "bullet")
            if cur is not None:
                txt = clean
                if txt.startswith("~~"):
                    if cur["lines"]:
                        cur["lines"][-1] += " " + txt[2:].strip()
                        continue
                    txt = txt[2:]
                txt = txt.lstrip("#").strip()
                if txt:
                    cur["lines"].append(txt)
    return [u for u in units if u["keys"] and u["lines"]]


def main(src_dir=None):
    home = os.path.join(os.path.expanduser("~"), ".sarf")
    os.makedirs(home, exist_ok=True)
    src_dir = src_dir or os.path.join(home, "openiti")
    os.makedirs(src_dir, exist_ok=True)
    out = os.path.join(home, "maajim.db")
    tmp = out + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE books(id TEXT PRIMARY KEY, name TEXT, died INTEGER);
        CREATE TABLE units(id INTEGER PRIMARY KEY, book TEXT, title TEXT, kind TEXT, vol INTEGER, page INTEGER, text TEXT);
        CREATE TABLE keys(key TEXT, unit INTEGER);
    """)
    uid = 0
    for bid, name, died, repo, path in BOOKS:
        local = os.path.join(src_dir, os.path.basename(path))
        if not os.path.exists(local):
            print("تنزيل", name, "...", flush=True)
            urllib.request.urlretrieve(RAW.format(repo=repo, path=path), local + ".part")
            os.replace(local + ".part", local)
        units = parse_book(local, bid)
        con.execute("INSERT INTO books VALUES (?,?,?)", (bid, name, died))
        rows, krows = [], []
        for u in units:
            uid += 1
            vol, page = u["page"] or (None, None)
            rows.append((uid, bid, u["title"], u["kind"], vol, page, "\n".join(u["lines"])))
            krows.extend((k, uid) for k in u["keys"])
        con.executemany("INSERT INTO units VALUES (?,?,?,?,?,?,?)", rows)
        con.executemany("INSERT INTO keys VALUES (?,?)", krows)
        con.commit()
        print(f"{name}: {len(units):,} مادة", flush=True)
    con.execute("CREATE INDEX idx_keys ON keys(key)")
    con.commit()
    con.close()
    os.replace(tmp, out)
    if src_dir == os.path.join(home, "openiti"):  # حذف النصوص المصدرية بعد البناء توفيرًا للمساحة
        for _bid, _n, _d, _r, path in BOOKS:
            try:
                os.remove(os.path.join(src_dir, os.path.basename(path)))
            except OSError:
                pass
    print("تم:", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
