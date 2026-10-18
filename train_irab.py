#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تدريب محلّل الوظائف الإعرابية: يسِم كل كلمة بوظيفتها (فاعل، مفعول به، مبتدأ، خبر …).

النموذج: CAMeLBERT-CA (رخصة Apache-2.0) + طبقة وسم متعددة التسميات. التدريب على جهاز المستخدم.

المدوّنات (تُنزَّل من مصادرها ولا تُضمّ إلى المستودع):
  • MASAQ، جامعة الأردن (Mendeley Data، doi:10.17632/9yvrzxktmr.2)، رخصة CC BY 3.0 — يجب ذكر المصدر.
  • الشجرة القرآنية الموسّعة (Nashir وآخرون، Data in Brief 2025، doi:10.1016/j.dib.2025.111940؛
    github.com/NoorBayan/Quranic) — للتدريب الخاص؛ انظر DATA_LICENSES.md.
لكل مدوّنة نظام وسمها؛ فوسوم الشجرة تحمل البادئة «ق:» ولا يُحاسَب النموذج على وسوم مدوّنةٍ في عيّنة مدوّنة أخرى.

التشغيل:  python train_irab.py            (التدريب الكامل)
          python train_irab.py --smoke    (اختبار سريع بلا تنزيل، لسلامة الشيفرة فقط)
          python train_irab.py --no-eqtb  (MASAQ وحدها)
النتائج:  ~/.sarf/models/irab_parser/{model.pt, labels.json, report.txt, report.json}
"""
import argparse
import collections
import csv
import json
import os
import random
import re
import sys
import time
import zipfile
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

HOME = Path.home()
OUT_DIR = HOME / ".sarf" / "models" / "irab_parser"
LOG_DIR = HOME / ".sarf" / "train_irab"
MODEL_NAME = "CAMeL-Lab/bert-base-arabic-camelbert-ca"
KEY_ROLES = {"M": ["فاعل", "مفعول به", "نائب فاعل", "مبتدأ", "خبر", "مضاف إليه", "نعت", "حال"],
             "E": ["ق:فاعل", "ق:مفعول به", "ق:نائب فاعل", "ق:خبر", "ق:مضاف إليه", "ق:صفة", "ق:حال"],
             "U": ["ن:nsubj", "ن:obj", "ن:csubj", "ن:obl", "ن:nmod", "ن:amod", "ن:advcl", "ن:acl"]}
PHRASE_PREFIX = "ش:"          # وظيفة الشبه جملة (MASAQ)
E_PREFIX = "ق:"               # وسوم الشجرة القرآنية الموسّعة
U_PREFIX = "ن:"               # علاقات UD (PADT وPUD): نثر صحفي معاصر
MIN_LABEL_COUNT = 30          # الوسوم الأقل شيوعًا في التدريب تُهمَل
MARKS = re.compile("[ً-ٰٟـ]")
SRC_ID = {"M": 0, "E": 1, "U": 2, "P": 3}      # P = PUD (للقياس فقط)
SRC_NS = {"M": "M", "E": "E", "U": "U", "P": "U"}   # أيّ نظام وسوم تتبعه كل مدوّنة
SRC_NAME = {"M": "MASAQ", "E": "الشجرة القرآنية الموسّعة", "U": "PADT", "P": "PUD"}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "train.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ns_of(label):
    return "E" if label.startswith(E_PREFIX) else "U" if label.startswith(U_PREFIX) else "M"


# ───────────────────────── البيانات ─────────────────────────
def project_dir():
    p = os.environ.get("ARABIYYA_PROJECT")        # مجلد «مشروع العربية» على سطح المكتب
    return Path(p) if p and Path(p).exists() else None


def find_masaq(arg):
    cands = [arg] if arg else []
    proj = project_dir()
    if proj:
        for nm in ("ماساق.csv", "MASAQ.csv"):
            cands += list(proj.rglob(nm))
    cands += [HOME / "claude" / "corpora" / "masaq" / "MASAQ.csv",
              HOME / ".sarf" / "corpora" / "masaq" / "MASAQ.csv",
              Path(__file__).resolve().parent / "MASAQ.csv"]
    for c in cands:
        if c and Path(c).exists():
            return Path(c)
    sys.exit("لم أجد ملف MASAQ. نزّله من https://data.mendeley.com/datasets/9yvrzxktmr/2 "
             "وضعه في مجلد المشروع أو مرّر المسار بـ --masaq")


def find_eqtb(arg):
    """يجد الشجرة القرآنية الموسّعة، ويفكّ المضغوط منها إلى ~/.sarf/corpora إن لزم."""
    if arg and Path(arg).exists():
        return Path(arg)
    proj = project_dir()
    if proj:
        for c in proj.rglob("الشجرة القرآنية الموسّعة.csv"):
            return c
        for z in proj.rglob("الشجرة القرآنية الموسّعة.zip"):
            dst = HOME / ".sarf" / "corpora"
            dst.mkdir(parents=True, exist_ok=True)
            out = dst / "eqtb.csv"
            if not out.exists():
                with zipfile.ZipFile(z) as zf:
                    name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
                    out.write_bytes(zf.read(name))
            return out
    for c in (HOME / ".sarf" / "corpora" / "eqtb.csv", HOME / "claude" / "corpora" / "Quranic.csv"):
        if c.exists():
            return c
    return None


def load_masaq(path):
    """يجمّع أسطر MASAQ (مقطع في كل سطر) في كلمات، والكلمات في آيات."""
    csv.field_size_limit(10 ** 9)
    words = collections.OrderedDict()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            key = (int(r["Sura_No"]), int(r["Verse_No"]), int(r["Column5"]))
            words.setdefault(key, []).append(r)
    verses = collections.OrderedDict()
    for (s, v, _), rs in words.items():
        labs = {r["Syntactic_Role"].strip() for r in rs if r["Syntactic_Role"].strip()}
        labs |= {PHRASE_PREFIX + r["Phrasal_Function"].strip() for r in rs if r["Phrasal_Function"].strip()}
        plain = rs[0]["Without_Diacritics"].strip() or rs[0]["Word"].strip()
        verses.setdefault((s, v), []).append((plain, rs[0]["Word"].strip(), sorted(labs)))
    return [{"src": "M", "sura": s, "verse": v,
             "plain": [w[0] for w in ws], "diac": [w[1] for w in ws], "labels": [w[2] for w in ws]}
            for (s, v), ws in verses.items()]


def load_eqtb(path):
    """الشجرة القرآنية الموسّعة: رمزٌ في كل سطر (UTF-16، مفصول بجداول). نجمع الرموز في كلمات.
    السطر المضمَر (موضعه «_») يُهمَل. وسوم «NonRel» و«root» لا تُعدّ وظيفة."""
    csv.field_size_limit(10 ** 9)
    skip = {"NonRel", "root", "-", "_", ""}
    words = collections.OrderedDict()
    with open(path, encoding="utf-16", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["location"].strip() == "_":
                continue
            try:
                key = (int(r["chapter_id"]), int(r["verse_id"]), int(r["word_id"]))
                tid = int(r["tok_id"])
            except ValueError:
                continue
            r["_t"] = tid
            words.setdefault(key, []).append(r)
    verses = collections.OrderedDict()
    for (s, v, _), rs in words.items():
        rs.sort(key=lambda r: r["_t"])
        diac = "".join(r["uthmani_token"] for r in rs)
        plain = MARKS.sub("", "".join(r["imlaai_token"] for r in rs))
        labs = sorted({E_PREFIX + r["rel_label_ar"].strip() for r in rs if r["rel_label_ar"].strip() not in skip})
        verses.setdefault((s, v), []).append((plain, diac, labs))
    return [{"src": "E", "sura": s, "verse": v,
             "plain": [w[0] for w in ws], "diac": [w[1] for w in ws], "labels": [w[2] for w in ws]}
            for (s, v), ws in verses.items()]


def find_ud(arg):
    """مجلدا UD_Arabic-PADT وUD_Arabic-PUD (ملفات conllu)؛ يبحث في مجلد المشروع ثم في ~/.sarf/corpora."""
    roots = ([Path(arg)] if arg else []) + ([project_dir()] if project_dir() else []) + [HOME / ".sarf" / "corpora"]
    got = {}
    for r in roots:
        if r and Path(r).exists():
            for f in Path(r).rglob("*.conllu"):
                got.setdefault(f.name, f)
            for z in Path(r).rglob("*PADT*PUD*.zip"):          # الحزمة المضغوطة: تُفكّ مرة واحدة
                dst = HOME / ".sarf" / "corpora" / "ud"
                dst.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(z) as zf:
                    for n in zf.namelist():
                        if n.endswith(".conllu") and not (dst / Path(n).name).exists():
                            (dst / Path(n).name).write_bytes(zf.read(n))
                for f in dst.glob("*.conllu"):
                    got.setdefault(f.name, f)
    return got


def load_conllu(path, src, split):
    """كل رمز UD (والسوابق واللواحق منفصلة فيه) كلمةٌ بوسم علاقته؛ التفرّعات الفرعية (nsubj:pass) تُحفظ."""
    out, cur = [], []
    def flush():
        if cur:
            out.append({"src": src, "split": split, "sura": 0, "verse": len(out),
                        "plain": [c[0] for c in cur], "diac": [c[1] for c in cur], "labels": [[c[2]] for c in cur]})
            cur.clear()
    for l in open(path, encoding="utf-8"):
        l = l.rstrip("\n")
        if not l:
            flush(); continue
        p = l.split("\t")
        if len(p) != 10 or not p[0].isdigit() or p[7] in ("punct", "root"):
            if len(p) == 10 and p[0].isdigit():
                cur.append((p[1], p[1], U_PREFIX + p[7]))
            continue
        vf = re.search(r"Vform=([^|]+)", p[9])
        cur.append((p[1], vf.group(1) if vf else p[1], U_PREFIX + p[7].split(":")[0]))
    flush()
    return out


def split_of(sura):
    """التقسيم بحسب السورة لا بحسب الآية، كي لا يتسرّب شيء من آيات السورة نفسها."""
    return "test" if sura % 10 == 7 else "dev" if sura % 10 == 3 else "train"


def chunk(verses, maxw=60):
    out = []
    for v in verses:
        for i in range(0, len(v["plain"]), maxw):
            out.append({k: (v[k][i:i + maxw] if isinstance(v[k], list) else v[k]) for k in v})
    return out


def encode(batch, tok, lab2i, field, maxlen=320):
    enc = tok([b[field] for b in batch], is_split_into_words=True, truncation=True,
              max_length=maxlen, padding=True, return_tensors="pt")
    B, T = enc["input_ids"].shape
    y = torch.zeros(B, T, len(lab2i))
    m = torch.zeros(B, T, dtype=torch.bool)
    for bi, b in enumerate(batch):
        prev = None
        for ti, wid in enumerate(enc.word_ids(bi)):
            if wid is None or wid == prev:
                prev = wid
                continue
            prev = wid
            m[bi, ti] = True
            for l in b["labels"][wid]:
                if l in lab2i:
                    y[bi, ti, lab2i[l]] = 1
    return enc, y, m


# ───────────────────────── النموذج ─────────────────────────
class Tagger(nn.Module):
    def __init__(self, base, n_labels):
        super().__init__()
        self.enc = base
        self.drop = nn.Dropout(0.1)
        self.out = nn.Linear(base.config.hidden_size, n_labels)

    def forward(self, **kw):
        return self.out(self.drop(self.enc(**kw).last_hidden_state))


def make_smoke(data):
    """نموذج صغير عشوائي ومعجم من كلمات البيانات: لاختبار سلامة الشيفرة بلا تنزيل."""
    from transformers import BertConfig, BertModel, BertTokenizerFast
    import tempfile
    cnt = collections.Counter(w for v in data for w in v["plain"])
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + [w for w, _ in cnt.most_common(3000)]
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "vocab.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(vocab))
    tok = BertTokenizerFast(os.path.join(d, "vocab.txt"), do_lower_case=False)
    base = BertModel(BertConfig(vocab_size=len(vocab), hidden_size=64, num_hidden_layers=2,
                                num_attention_heads=2, intermediate_size=128, max_position_embeddings=512))
    return tok, base


# ───────────────────────── القياس ─────────────────────────
@torch.no_grad()
def predict(model, data, tok, lab2i, field, dev, bs=32):
    model.eval()
    P, Y, S = [], [], []
    for i in range(0, len(data), bs):
        batch = data[i:i + bs]
        enc, y, m = encode(batch, tok, lab2i, field)
        enc = {k: v.to(dev) for k, v in enc.items()}
        p = torch.sigmoid(model(**enc).float()).cpu()
        P.append(p[m])
        Y.append(y[m])
        for b, n in zip(batch, m.sum(1).tolist()):
            S.append(torch.full((n,), SRC_ID[b["src"]]))
    return torch.cat(P), torch.cat(Y), torch.cat(S)


def prf(P, Y, thr, idx):
    pred = P[:, idx] >= thr
    gold = Y[:, idx] > 0.5
    return ((pred & gold).sum(0).float(), (pred & ~gold).sum(0).float(), (~pred & gold).sum(0).float())


def f1_of(tp, fp, fn):
    p = tp / (tp + fp).clamp(min=1)
    r = tp / (tp + fn).clamp(min=1)
    return p, r, 2 * p * r / (p + r).clamp(min=1e-9)


def key_micro_f1(P, Y, thr, key_idx):
    if not key_idx:
        return 0.0
    tp, fp, fn = prf(P, Y, thr, key_idx)
    return float(f1_of(tp.sum(), fp.sum(), fn.sum())[2])


def mean_key_f1(P, Y, S, thr, key_by_ns):
    vals = []
    for ns, sid in SRC_ID.items():
        sel = S == sid
        if sel.any() and key_by_ns[SRC_NS[ns]] and ns != "P":      # PUD لا يدخل في اختيار أفضل نقطة
            vals.append(key_micro_f1(P[sel], Y[sel], thr, key_by_ns[SRC_NS[ns]]))
    return sum(vals) / max(1, len(vals))


def best_threshold(P, Y, S, key_by_ns):
    best = (0.5, -1.0)
    for t in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
        f = mean_key_f1(P, Y, S, t, key_by_ns)
        if f > best[1]:
            best = (t, f)
    return best


def lookup_baseline(train, test, lab2i):
    """خط أساس: لكل كلمة أكثر مجموعة وظائف وقعت لها في التدريب (في المدوّنة نفسها)."""
    cnt = collections.defaultdict(collections.Counter)
    for v in train:
        for w, labs in zip(v["plain"], v["labels"]):
            cnt[(SRC_NS[v["src"]], w)][tuple(l for l in labs if l in lab2i)] += 1
    rows = []
    for v in test:
        for w in v["plain"]:
            p = torch.zeros(len(lab2i))
            if (SRC_NS[v["src"]], w) in cnt:
                for l in cnt[(SRC_NS[v["src"]], w)].most_common(1)[0][0]:
                    p[lab2i[l]] = 1
            rows.append(p)
    return torch.stack(rows)


# ───────────────────────── التدريب ─────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masaq")
    ap.add_argument("--eqtb")
    ap.add_argument("--no-eqtb", action="store_true", help="ادرّب على MASAQ وحدها")
    ap.add_argument("--no-ud", action="store_true", help="بلا PADT وPUD")
    ap.add_argument("--ud")
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--diac", action="store_true", help="أدخل الكلمات مشكولة بدل المجرّدة")
    ap.add_argument("--smoke", action="store_true", help="اختبار سريع لسلامة الشيفرة (نموذج صغير عشوائي)")
    ap.add_argument("--max-verses", type=int, default=0)
    ap.add_argument("--out", default=str(OUT_DIR))
    a = ap.parse_args()

    random.seed(7)
    torch.manual_seed(7)
    out = Path(a.out) if not a.smoke else OUT_DIR.parent / "irab_parser_smoke"
    out.mkdir(parents=True, exist_ok=True)
    dev = torch.device("cuda" if torch.cuda.is_available() else
                       "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
    log(f"الجهاز: {dev}" + (f" ({torch.cuda.get_device_name(0)})" if dev.type == "cuda" else ""))

    verses = load_masaq(find_masaq(a.masaq))
    log(f"MASAQ: {len(verses)} آية")
    if not a.no_eqtb:
        ep = find_eqtb(a.eqtb)
        if ep:
            ev = load_eqtb(ep)
            log(f"الشجرة القرآنية الموسّعة: {len(ev)} آية (من {ep.name})")
            verses += ev
        else:
            log("تنبيه: لم أجد الشجرة القرآنية الموسّعة؛ سيجري التدريب على MASAQ وحدها")
    if not a.no_ud:
        ud = find_ud(a.ud)
        for nm, src, sp in (("ar_padt-ud-train.conllu", "U", "train"), ("ar_padt-ud-dev.conllu", "U", "dev"),
                            ("ar_padt-ud-test.conllu", "U", "test"), ("ar_pud-ud-test.conllu", "P", "test")):
            if nm in ud:
                d = load_conllu(ud[nm], src, sp)
                log(f"{SRC_NAME[src]} ({sp}): {len(d)} جملة")
                verses += d
            else:
                log(f"تنبيه: لم أجد {nm}")
    if a.max_verses:
        step = max(1, len(verses) // a.max_verses)        # عيّنة موزّعة على السور كلها
        verses = verses[::step]
    parts = {k: chunk([v for v in verses if v.get("split", split_of(v["sura"])) == k]) for k in ("train", "dev", "test")}
    log("مقاطع: " + "، ".join(f"{k}={len(parts[k])}" for k in parts))

    cnt = collections.Counter((v["src"], l) for v in parts["train"] for labs in v["labels"] for l in labs)
    labels = sorted({l for (s, l), c in cnt.items() if c >= MIN_LABEL_COUNT and ns_of(l) == SRC_NS[s]})
    lab2i = {l: i for i, l in enumerate(labels)}
    key_by_ns = {ns: [lab2i[k] for k in KEY_ROLES[ns] if k in lab2i] for ns in KEY_ROLES}
    nsmask = {ns: torch.tensor([1.0 if ns_of(l) == ns else 0.0 for l in labels]) for ns in ("M", "E", "U")}
    log(f"عدد الوسوم المعتمدة: {len(labels)} (MASAQ {int(nsmask['M'].sum())}، الشجرة {int(nsmask['E'].sum())}، UD {int(nsmask['U'].sum())})")
    (out / "labels.json").write_text(json.dumps(labels, ensure_ascii=False), encoding="utf-8")

    field = "diac" if a.diac else "plain"
    if a.smoke:
        tok, base = make_smoke(parts["train"])
    else:
        from transformers import AutoModel, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(a.model)
        base = AutoModel.from_pretrained(a.model)
    model = Tagger(base, len(labels)).to(dev)

    steps = a.epochs * ((len(parts["train"]) + a.batch - 1) // a.batch)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=steps, pct_start=0.1,
                                                anneal_strategy="linear")
    scaler = torch.amp.GradScaler("cuda", enabled=dev.type == "cuda")

    ck, best_path = out / "ckpt.pt", out / "model.pt"
    ep0, best_f, bad = 0, -1.0, 0
    if ck.exists():
        st = torch.load(ck, map_location="cpu")
        if st.get("labels") == labels:
            model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); sched.load_state_dict(st["sched"])
            ep0, best_f, bad = st["epoch"], st["best"], st["bad"]
            log(f"استئناف من الدورة {ep0} (أفضل متوسط F1 {best_f:.4f})")
        else:
            log("تغيّرت الوسوم عن التدريب السابق؛ أبدأ من جديد")

    for ep in range(ep0, a.epochs):
        model.train()
        order = list(range(len(parts["train"])))
        random.Random(ep).shuffle(order)
        t0, tot, nb = time.time(), 0.0, 0
        for i in range(0, len(order), a.batch):
            batch = [parts["train"][j] for j in order[i:i + a.batch]]
            enc, y, m = encode(batch, tok, lab2i, field)
            W = torch.stack([nsmask[SRC_NS[b["src"]]] for b in batch]).to(dev)   # لا يُحاسَب النموذج إلا على وسوم مدوّنة العيّنة
            enc = {k: v.to(dev) for k, v in enc.items()}
            y, m = y.to(dev), m.to(dev)
            with torch.autocast(dev.type, dtype=torch.float16, enabled=dev.type == "cuda"):
                logits = model(**enc)
            lm = F.binary_cross_entropy_with_logits(logits.float(), y, reduction="none") * W[:, None, :]
            loss = lm[m].sum() / m.sum().clamp(min=1)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); sched.step()
            tot += float(loss.detach()); nb += 1
        P, Y, S = predict(model, parts["dev"], tok, lab2i, field, dev)
        thr, f = best_threshold(P, Y, S, key_by_ns)
        log(f"دورة {ep + 1}/{a.epochs}: خسارة {tot / max(1, nb):.4f}، "
            f"متوسط F1 للوظائف الرئيسة على التطوير {f:.4f} (عتبة {thr})، {time.time() - t0:.0f} ث")
        if f > best_f:
            best_f, bad = f, 0
            torch.save({"model": model.state_dict(), "labels": labels, "thr": thr, "field": field,
                        "base": a.model}, best_path)
        else:
            bad += 1
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                    "epoch": ep + 1, "best": best_f, "bad": bad, "labels": labels}, ck)
        if bad >= a.patience:
            log("توقّف مبكر: لا تحسّن على التطوير")
            break

    # ── التقرير على الاختبار ──
    st = torch.load(best_path, map_location="cpu")
    model.load_state_dict(st["model"]); thr = st["thr"]
    P, Y, S = predict(model, parts["test"], tok, lab2i, field, dev)
    B = lookup_baseline(parts["train"], parts["test"], lab2i)
    rep = {"input": field, "threshold": thr, "n_test_words": int(len(Y)),
           "split": "بحسب السورة: الاختبار = السور التي رقمها يُختم بـ7، التطوير = بـ3",
           "sources": ["MASAQ (جامعة الأردن) CC BY 3.0, doi:10.17632/9yvrzxktmr.2",
                       "الشجرة القرآنية الموسّعة (Nashir وآخرون 2025, doi:10.1016/j.dib.2025.111940)",
                       "UD Arabic PADT (Hajič وآخرون؛ CC BY-NC-SA 3.0) وUD Arabic PUD (CC BY-SA 3.0)"],
           "per_corpus": {}}
    lines = [f"محلّل الوظائف الإعرابية — المدخل: {field} — كلمات الاختبار: {rep['n_test_words']}"]
    for src, sid in SRC_ID.items():
        sel = S == sid
        if not sel.any():
            continue
        ns = SRC_NS[src]
        idx = [i for i, l in enumerate(labels) if ns_of(l) == ns]
        Pn, Yn, Bn = P[sel], Y[sel], B[sel]
        kk = key_by_ns[ns]
        d = {"n_words": int(sel.sum()),
             "model_key_micro_f1": round(key_micro_f1(Pn, Yn, thr, kk), 4),
             "lookup_baseline_key_micro_f1": round(key_micro_f1(Bn, Yn, 0.5, kk), 4), "labels": {}}
        tp, fp, fn = prf(Pn, Yn, thr, idx); p, r, f = f1_of(tp, fp, fn)
        tpb, fpb, fnb = prf(Bn, Yn, 0.5, idx); fb = f1_of(tpb, fpb, fnb)[2]
        for j, i in enumerate(idx):
            d["labels"][labels[i]] = {"support": int((Yn[:, i] > 0.5).sum()), "P": round(float(p[j]), 3),
                                      "R": round(float(r[j]), 3), "F1": round(float(f[j]), 3),
                                      "baseline_F1": round(float(fb[j]), 3)}
        fl, ml = {"M": ("فاعل", "مفعول به"), "E": (E_PREFIX + "فاعل", E_PREFIX + "مفعول به"), "U": ("ن:nsubj", "ن:obj")}[ns]
        if fl in lab2i and ml in lab2i:
            gf, gm = Yn[:, lab2i[fl]] > .5, Yn[:, lab2i[ml]] > .5
            pf, pm = Pn[:, lab2i[fl]] >= thr, Pn[:, lab2i[ml]] >= thr
            d["agent_object_confusion"] = {"فاعل→مفعول به": int((gf & ~gm & pm & ~pf).sum()),
                                           "مفعول به→فاعل": int((gm & ~gf & pf & ~pm).sum()),
                                           "فاعل (الكل)": int(gf.sum()), "مفعول به (الكل)": int(gm.sum())}
        rep["per_corpus"][src] = d
        name = SRC_NAME[src]
        lines += ["", f"== {name} — كلمات: {d['n_words']} ==",
                  f"F1 المجمَّع للوظائف الرئيسة: النموذج {d['model_key_micro_f1']} | خط الأساس (الحفظ) {d['lookup_baseline_key_micro_f1']}",
                  f"الخلط بين الفاعل والمفعول: {d.get('agent_object_confusion')}",
                  "الوسم | العدد | الدقة | الاستدعاء | F1 | F1 للحفظ"]
        for l in sorted(d["labels"], key=lambda x: -d["labels"][x]["support"])[:30]:
            e = d["labels"][l]
            lines.append(f"{l} | {e['support']} | {e['P']} | {e['R']} | {e['F1']} | {e['baseline_F1']}")
    lines += ["", "التقسيم بحسب السورة. تنبيه: في القرآن عبارات مكرّرة بين السور فقد تتسرّب بعض الأحكام.",
              "المدوّنات: MASAQ (جامعة الأردن) CC BY 3.0, doi:10.17632/9yvrzxktmr.2 ؛ الشجرة القرآنية الموسّعة (Nashir وآخرون 2025) ؛ UD Arabic PADT وPUD (Universal Dependencies)."]
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "report.txt").write_text("\n".join(lines), encoding="utf-8")
    log("\n".join(lines[:12]))
    log(f"التقرير: {out / 'report.txt'}")


if __name__ == "__main__":
    main()
