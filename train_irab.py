#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تدريب محلّل الوظائف الإعرابية: يسِم كل كلمة بوظيفتها (فاعل، مفعول به، مبتدأ، خبر …).

النموذج: CAMeLBERT-CA (رخصة Apache-2.0) + طبقة وسم متعددة التسميات. التدريب على جهاز المستخدم.

المدوّنة: MASAQ، جامعة الأردن (Mendeley Data، doi:10.17632/9yvrzxktmr.2)، رخصة CC BY 3.0.
يجب ذكر مصدرها في كل عمل يستعملها.

التشغيل:  python train_irab.py            (التدريب الكامل)
          python train_irab.py --smoke    (اختبار سريع بلا تنزيل، لسلامة الشيفرة فقط)
النتائج:  ~/.sarf/models/irab_parser/{model.pt, labels.json, report.txt, report.json}
"""
import argparse
import collections
import csv
import json
import os
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

HOME = Path.home()
OUT_DIR = HOME / ".sarf" / "models" / "irab_parser"
LOG_DIR = HOME / ".sarf" / "train_irab"
MODEL_NAME = "CAMeL-Lab/bert-base-arabic-camelbert-ca"
KEY_ROLES = ["فاعل", "مفعول به", "نائب فاعل", "مبتدأ", "خبر", "مضاف إليه", "نعت", "حال"]
PHRASE_PREFIX = "ش:"          # وظيفة الشبه جملة (كالخبر الذي هو جار ومجرور)
MIN_LABEL_COUNT = 30          # الوسوم الأقل شيوعًا في التدريب تُهمَل


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "train.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ───────────────────────── البيانات ─────────────────────────
def find_masaq(arg):
    cands = [arg] if arg else []
    cands += [HOME / "claude" / "corpora" / "masaq" / "MASAQ.csv",
              HOME / ".sarf" / "corpora" / "masaq" / "MASAQ.csv",
              Path(__file__).resolve().parent / "MASAQ.csv"]
    for c in cands:
        if c and Path(c).exists():
            return Path(c)
    sys.exit("لم أجد MASAQ.csv. نزّلها من https://data.mendeley.com/datasets/9yvrzxktmr/2 "
             "وضعها في claude\\corpora\\masaq أو مرّر المسار بـ --masaq")


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
    return [{"sura": s, "verse": v,
             "plain": [w[0] for w in ws], "diac": [w[1] for w in ws], "labels": [w[2] for w in ws]}
            for (s, v), ws in verses.items()]


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
    P, Y = [], []
    for i in range(0, len(data), bs):
        enc, y, m = encode(data[i:i + bs], tok, lab2i, field)
        enc = {k: v.to(dev) for k, v in enc.items()}
        p = torch.sigmoid(model(**enc).float()).cpu()
        P.append(p[m])
        Y.append(y[m])
    return torch.cat(P), torch.cat(Y)


def prf(P, Y, thr, idx):
    pred = P[:, idx] >= thr
    gold = Y[:, idx] > 0.5
    tp = (pred & gold).sum(0).float()
    fp = (pred & ~gold).sum(0).float()
    fn = (~pred & gold).sum(0).float()
    return tp, fp, fn


def f1_of(tp, fp, fn):
    p = tp / (tp + fp).clamp(min=1)
    r = tp / (tp + fn).clamp(min=1)
    return p, r, 2 * p * r / (p + r).clamp(min=1e-9)


def key_micro_f1(P, Y, thr, key_idx):
    tp, fp, fn = prf(P, Y, thr, key_idx)
    return float(f1_of(tp.sum(), fp.sum(), fn.sum())[2])


def best_threshold(P, Y, key_idx):
    best = (0.5, -1.0)
    for t in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
        f = key_micro_f1(P, Y, t, key_idx)
        if f > best[1]:
            best = (t, f)
    return best


def lookup_baseline(train, test, lab2i):
    """خط أساس: لكل كلمة أكثر مجموعة وظائف وقعت لها في التدريب. إن لم يفُق نموذجُنا هذا الخط فلا قيمة له."""
    cnt = collections.defaultdict(collections.Counter)
    for v in train:
        for w, labs in zip(v["plain"], v["labels"]):
            cnt[w][tuple(l for l in labs if l in lab2i)] += 1
    rows = []
    for v in test:
        for w in v["plain"]:
            p = torch.zeros(len(lab2i))
            if w in cnt:
                for l in cnt[w].most_common(1)[0][0]:
                    p[lab2i[l]] = 1
            rows.append(p)
    return torch.stack(rows)


# ───────────────────────── التدريب ─────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masaq")
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
    out = Path(a.out if not a.smoke else OUT_DIR.parent / "irab_parser_smoke")
    out.mkdir(parents=True, exist_ok=True)
    dev = torch.device("cuda" if torch.cuda.is_available() else
                       "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
    log(f"الجهاز: {dev}" + (f" ({torch.cuda.get_device_name(0)})" if dev.type == "cuda" else ""))

    verses = load_masaq(find_masaq(a.masaq))
    if a.max_verses:
        verses = verses[:a.max_verses]
    parts = {k: chunk([v for v in verses if split_of(v["sura"]) == k]) for k in ("train", "dev", "test")}
    log("آيات: " + "، ".join(f"{k}={len(parts[k])} مقطعًا" for k in parts))

    cnt = collections.Counter(l for v in parts["train"] for labs in v["labels"] for l in labs)
    labels = sorted(l for l, c in cnt.items() if c >= MIN_LABEL_COUNT)
    lab2i = {l: i for i, l in enumerate(labels)}
    key_idx = [lab2i[k] for k in KEY_ROLES if k in lab2i]
    log(f"عدد الوسوم المعتمدة: {len(labels)}")
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
        model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); sched.load_state_dict(st["sched"])
        ep0, best_f, bad = st["epoch"], st["best"], st["bad"]
        log(f"استئناف من الدورة {ep0} (أفضل F1 للوظائف الرئيسة {best_f:.4f})")

    for ep in range(ep0, a.epochs):
        model.train()
        order = list(range(len(parts["train"])))
        random.Random(ep).shuffle(order)
        t0, tot = time.time(), 0.0
        for i in range(0, len(order), a.batch):
            batch = [parts["train"][j] for j in order[i:i + a.batch]]
            enc, y, m = encode(batch, tok, lab2i, field)
            enc = {k: v.to(dev) for k, v in enc.items()}
            y, m = y.to(dev), m.to(dev)
            with torch.autocast(dev.type, dtype=torch.float16, enabled=dev.type == "cuda"):
                logits = model(**enc)
            loss = F.binary_cross_entropy_with_logits(logits.float()[m], y[m], reduction="sum") / m.sum().clamp(min=1)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); sched.step()
            tot += float(loss.detach())
        P, Y = predict(model, parts["dev"], tok, lab2i, field, dev)
        thr, f = best_threshold(P, Y, key_idx)
        log(f"دورة {ep + 1}/{a.epochs}: خسارة {tot / max(1, len(order) / a.batch):.4f}، "
            f"F1 للوظائف الرئيسة على التطوير {f:.4f} (عتبة {thr})، {time.time() - t0:.0f} ث")
        if f > best_f:
            best_f, bad = f, 0
            torch.save({"model": model.state_dict(), "labels": labels, "thr": thr, "field": field,
                        "base": a.model}, best_path)
        else:
            bad += 1
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                    "epoch": ep + 1, "best": best_f, "bad": bad}, ck)
        if bad >= a.patience:
            log("توقّف مبكر: لا تحسّن على التطوير")
            break

    # ── التقرير على الاختبار ──
    st = torch.load(best_path, map_location="cpu")
    model.load_state_dict(st["model"]); thr = st["thr"]
    P, Y = predict(model, parts["test"], tok, lab2i, field, dev)
    B = lookup_baseline(parts["train"], parts["test"], lab2i)
    all_idx = list(range(len(labels)))
    rep = {"input": field, "threshold": thr, "n_test_words": int(len(Y)),
           "split": "بحسب السورة: الاختبار = السور التي رقمها يُختم بـ7، التطوير = بـ3",
           "source": "MASAQ (جامعة الأردن) CC BY 3.0, doi:10.17632/9yvrzxktmr.2", "labels": {}}
    for name, PP in (("model", P), ("lookup_baseline", B)):
        t = thr if name == "model" else 0.5
        tp, fp, fn = prf(PP, Y, t, key_idx)
        rep[name + "_key_micro_f1"] = round(float(f1_of(tp.sum(), fp.sum(), fn.sum())[2]), 4)
    tp, fp, fn = prf(P, Y, thr, all_idx)
    p, r, f = f1_of(tp, fp, fn)
    tpb, fpb, fnb = prf(B, Y, 0.5, all_idx)
    fb = f1_of(tpb, fpb, fnb)[2]
    for i, l in enumerate(labels):
        rep["labels"][l] = {"support": int((Y[:, i] > 0.5).sum()), "P": round(float(p[i]), 3),
                            "R": round(float(r[i]), 3), "F1": round(float(f[i]), 3), "baseline_F1": round(float(fb[i]), 3)}
    fi, mi = lab2i.get("فاعل"), lab2i.get("مفعول به")
    if fi is not None and mi is not None:
        gf, gm, pf, pm = Y[:, fi] > .5, Y[:, mi] > .5, P[:, fi] >= thr, P[:, mi] >= thr
        rep["agent_object_confusion"] = {
            "فاعل→مفعول به": int((gf & ~gm & pm & ~pf).sum()), "مفعول به→فاعل": int((gm & ~gf & pf & ~pm).sum()),
            "فاعل (الكل)": int(gf.sum()), "مفعول به (الكل)": int(gm.sum())}
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"محلّل الوظائف الإعرابية — المدخل: {field} — كلمات الاختبار: {rep['n_test_words']}",
             f"F1 المجمَّع للوظائف الرئيسة: النموذج {rep['model_key_micro_f1']} | خط الأساس (الحفظ) {rep['lookup_baseline_key_micro_f1']}",
             f"الخلط بين الفاعل والمفعول: {rep.get('agent_object_confusion')}", "",
             "الوسم | العدد | الدقة | الاستدعاء | F1 | F1 للحفظ"]
    for l in sorted(labels, key=lambda x: -rep["labels"][x]["support"])[:40]:
        d = rep["labels"][l]
        lines.append(f"{l} | {d['support']} | {d['P']} | {d['R']} | {d['F1']} | {d['baseline_F1']}")
    lines += ["", "التقسيم بحسب السورة. تنبيه: في القرآن عبارات مكرّرة بين السور فقد تتسرّب بعض الأحكام.",
              "المدوّنة: MASAQ (جامعة الأردن) CC BY 3.0, doi:10.17632/9yvrzxktmr.2"]
    (out / "report.txt").write_text("\n".join(lines), encoding="utf-8")
    log("\n".join(lines[:4]))
    log(f"التقرير: {out / 'report.txt'}")


if __name__ == "__main__":
    main()
