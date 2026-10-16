"""بناء فهرس مدوّنة «أشعار» للبحث بلا إنترنت (يُشغَّل مرة واحدة).
يُنزّل ملفات المدوّنة من Hugging Face ويبني قاعدة SQLite بفهرس نصي كامل في ~/.sarf/ashaar.db
"""
import os, sys, sqlite3, urllib.request

HARAKAT = set("ًٌٍَُِّْـ")
TR = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "ء", "ئ": "ء"})
BASE = "https://huggingface.co/datasets/arbml/ashaar/resolve/main/data/"
FILES = ["train-00000-of-00002.parquet", "train-00001-of-00002.parquet"]
COLS = ["poem title", "poem meter", "poem verses", "poem theme", "poet name", "poet era"]


def norm(s):
    return "".join(c for c in (s or "") if c not in HARAKAT).translate(TR)


def letters_end(s, n=4):
    t = [c for c in norm(s) if "ء" <= c <= "ي"]
    return "".join(t[-n:])


def main(src_dir=None):
    import pyarrow.parquet as pq
    home = os.path.join(os.path.expanduser("~"), ".sarf")
    os.makedirs(home, exist_ok=True)
    src_dir = src_dir or home
    paths = []
    for f in FILES:
        p = os.path.join(src_dir, f)
        if not os.path.exists(p):
            print("تنزيل", f, "...", flush=True)
            urllib.request.urlretrieve(BASE + f, p + ".part")
            os.replace(p + ".part", p)
        paths.append(p)

    out = os.path.join(home, "ashaar.db")
    tmp = out + ".building"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE poems(id INTEGER PRIMARY KEY, title TEXT, meter TEXT, theme TEXT, poet TEXT, era TEXT,
                           meter_n TEXT, era_n TEXT, poet_n TEXT);
        CREATE TABLE verses(rowid INTEGER PRIMARY KEY, poem_id INTEGER, n INTEGER, sadr TEXT, ajuz TEXT, ajuz_end TEXT);
        CREATE VIRTUAL TABLE verses_fts USING fts5(bayt, content='', tokenize='unicode61 remove_diacritics 0');
    """)
    pid, vid = 0, 0
    for p in paths:
        pf = pq.ParquetFile(p)
        for batch in pf.iter_batches(batch_size=2000, columns=COLS):
            d = batch.to_pydict()
            poems, verses, fts = [], [], []
            for i in range(batch.num_rows):
                pid += 1
                title, meter, theme = d["poem title"][i], d["poem meter"][i], d["poem theme"][i]
                poet, era = d["poet name"][i], d["poet era"][i]
                poems.append((pid, title, meter, theme, poet, era, norm(meter), norm(era), norm(poet)))
                vs = [v for v in (d["poem verses"][i] or []) if v and v.strip()]
                for k in range(0, len(vs), 2):
                    sadr = vs[k].strip()
                    ajuz = vs[k + 1].strip() if k + 1 < len(vs) else ""
                    vid += 1
                    verses.append((vid, pid, k // 2 + 1, sadr, ajuz, letters_end(ajuz or sadr)))
                    fts.append((vid, norm(sadr + " " + ajuz)))
            con.executemany("INSERT INTO poems VALUES (?,?,?,?,?,?,?,?,?)", poems)
            con.executemany("INSERT INTO verses VALUES (?,?,?,?,?,?)", verses)
            con.executemany("INSERT INTO verses_fts(rowid, bayt) VALUES (?,?)", fts)
            con.commit()
            print(f"\r{pid:,} قصيدة، {vid:,} بيتًا", end="", flush=True)
    print("\nفهرسة...", flush=True)
    con.executescript("""
        CREATE INDEX idx_verses_poem ON verses(poem_id);
        INSERT INTO verses_fts(verses_fts) VALUES('optimize');
    """)
    con.commit()
    con.close()
    os.replace(tmp, out)
    if src_dir == home:  # حذف ملفات المصدر بعد البناء توفيرًا للمساحة
        for p in paths:
            try:
                os.remove(p)
            except OSError:
                pass
    print("تم:", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
