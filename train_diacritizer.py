"""تدريب مشكِّل العربية التراثية على جهازك (يعمل وحده دون Claude).

1) ينزّل مدوّنة Tashkeela المعيارية (Fadel et al., 2019: 50 ألف سطر للتدريب، و2500 للتحقق، و2500 للاختبار).
2) يضيف الأبيات المشكولة تشكيلًا تامًّا من «أشعار» (~/.sarf/ashaar.db)، ويعزل قصائد كاملة للاختبار.
3) يدرّب نموذج BiLSTM على مستوى الحرف بكرت الشاشة إن وُجد، ويحفظ أفضل نسخة بحسب خطأ التحقق.
4) يقيس على الاختبارين: نسبة خطأ الحركات (DER) ونسبة الكلمات الخاطئة (WER)، مع علامة الإعراب ودونها،
   ويوازن بالمشكِّل الحالي (CAMeL BERT للفصحى المعاصرة) على العينة نفسها.
5) يكتب التقرير في ~/.sarf/models/diac_ca/report.txt؛ ويستعمل الخادم النموذج تلقائيًّا بعد إعادة تشغيل Claude.

يُستأنف التدريب من آخر نقطة محفوظة إن انقطع.
"""
import os, sys, json, time, random, sqlite3, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diac_model as D

HOME = D.HOME
OUT = D.MODEL_DIR
WORK = os.path.join(HOME, "train_diac")
os.makedirs(OUT, exist_ok=True)
os.makedirs(WORK, exist_ok=True)
LOG = open(os.path.join(WORK, "train.log"), "a", encoding="utf-8")
RAW = "https://raw.githubusercontent.com/AliOsm/arabic-text-diacritization/master/dataset/{}.txt"


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(name):
    p = os.path.join(WORK, name + ".txt")
    if not os.path.exists(p):
        log("تنزيل", name)
        urllib.request.urlretrieve(RAW.format(name), p + ".part")
        os.replace(p + ".part", p)
    with open(p, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def ratio(t):
    letters = sum(1 for c in t if c in D.ARABIC)
    marks = sum(1 for c in t if c in D.DIACS)
    return marks / letters if letters else 0


def poetry(max_verses=400000, test_poems=400, seed=7):
    db = os.path.join(HOME, "ashaar.db")
    if not os.path.exists(db):
        return [], []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("SELECT poem_id, sadr, ajuz FROM verses").fetchall()
    con.close()
    good = {}
    for pid, s, a in rows:
        t = (s + " * " + a).replace("ـ", "").strip()
        if ratio(t) >= 0.9 and len(t) > 20:
            good.setdefault(pid, []).append(t)
    pids = sorted(good)
    rnd = random.Random(seed)
    rnd.shuffle(pids)
    test_ids = set(pids[:test_poems])
    test = [v for p in test_ids for v in good[p]]
    seen = {D.strip_diac(v) for v in test}  # «أشعار» فيها قصائد مكررة: لا يدخل التدريبَ بيتٌ من الاختبار
    train = [v for p in pids[test_poems:] for v in good[p] if D.strip_diac(v) not in seen]
    rnd.shuffle(train)
    return train[:max_verses], test[:6000]


def segments(lines, maxlen=300):
    """تقطيع السطور الطويلة على حدود الكلمات."""
    out = []
    for l in lines:
        words, cur = l.split(), ""
        for w in words:
            if len(cur) + len(w) + 1 > maxlen and cur:
                out.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            out.append(cur)
    return out


def encode(lines, vocab):
    data = []
    for l in lines:
        chars, labels = D.split_diac(l)
        if chars:
            data.append(([vocab.get(c, 1) for c in chars], labels))
    return data


def batches(data, bs, shuffle, rnd):
    idx = list(range(len(data)))
    if shuffle:
        rnd.shuffle(idx)
    # ترتيب تقريبي بالطول داخل كتل لتقليل الحشو
    for k in range(0, len(idx), bs * 50):
        block = sorted(idx[k:k + bs * 50], key=lambda i: len(data[i][0]))
        bl = [block[i:i + bs] for i in range(0, len(block), bs)]
        if shuffle:
            rnd.shuffle(bl)
        for b in bl:
            yield b


def to_tensor(data, b, device):
    import torch
    L = max(len(data[i][0]) for i in b)
    x = torch.zeros(len(b), L, dtype=torch.long)
    y = torch.full((len(b), L), -100, dtype=torch.long)
    for r, i in enumerate(b):
        ids, lab = data[i]
        x[r, :len(ids)] = torch.tensor(ids)
        y[r, :len(lab)] = torch.tensor(lab)
    return x.to(device), y.to(device)


def der_wer(pred_lines, gold_lines):
    """DER وWER على الحروف العربية (باستثناء ما لا حركة له في المرجع)، مع علامة الإعراب ودونها."""
    e = n = e_nc = n_nc = 0
    we = wn = we_nc = 0
    for pl, gl in zip(pred_lines, gold_lines):
        def keep(t):  # الحروف العربية والمسافات وحدها، فلا يفسد المقارنةَ حذفُ علامة ترقيم
            c, l = D.split_diac(t)
            out_c, out_l = [], []
            for ch, lb in zip(c, l):
                if ch in D.ARABIC or (ch == " " and out_c and out_c[-1] != " "):
                    out_c.append(ch); out_l.append(lb)
            return "".join(out_c).strip(), out_l
        pc, pll = keep(pl)
        gc, gll = keep(gl)
        if pc != gc:
            continue
        # حدود الكلمات لتمييز الحرف الأخير
        last = set()
        for i, c in enumerate(gc):
            if c in D.ARABIC and (i + 1 == len(gc) or gc[i + 1] not in D.ARABIC):
                last.add(i)
        word_err, word_err_nc, in_word = False, False, False
        for i, c in enumerate(gc):
            if c in D.ARABIC:
                in_word = True
                if gll[i] != 0:
                    bad = pll[i] != gll[i]
                    n += 1
                    e += bad
                    word_err |= bad
                    if i not in last:
                        n_nc += 1
                        e_nc += bad
                        word_err_nc |= bad
            if in_word and (i + 1 == len(gc) or gc[i + 1] not in D.ARABIC):
                wn += 1
                we += word_err
                we_nc += word_err_nc
                word_err = word_err_nc = in_word = False
    return {"DER مع علامة الإعراب": round(100 * e / max(n, 1), 2), "DER دون علامة الإعراب": round(100 * e_nc / max(n_nc, 1), 2),
            "WER مع علامة الإعراب": round(100 * we / max(wn, 1), 2), "WER دون علامة الإعراب": round(100 * we_nc / max(wn, 1), 2)}


def predict(model, vocab, lines, device, bs=64):
    import torch
    out = []
    model.eval()
    data = [(D.strip_diac(l)) for l in lines]
    for k in range(0, len(data), bs):
        chunk = data[k:k + bs]
        L = max(len(c) for c in chunk)
        x = torch.zeros(len(chunk), L, dtype=torch.long)
        for r, c in enumerate(chunk):
            x[r, :len(c)] = torch.tensor([vocab.get(ch, 1) for ch in c])
        with torch.no_grad():
            p = model(x.to(device)).argmax(-1).cpu().tolist()
        for c, lab in zip(chunk, p):
            out.append(D.join_diac(c, [l if ch in D.ARABIC else 0 for ch, l in zip(c, lab)]))
    return out


def main():
    import torch
    quick = "--quick" in sys.argv
    epochs = 1 if quick else int(os.environ.get("DIAC_EPOCHS", "25"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log("الجهاز:", device, torch.cuda.get_device_name(0) if device == "cuda" else "(بلا كرت شاشة: التدريب سيكون بطيئًا جدًّا)")
    rnd = random.Random(1)
    tr, va, te = fetch("train"), fetch("val"), fetch("test")
    ptr, pte = poetry(max_verses=300 if quick else 400000)
    if quick:
        pte = pte[:50]
    log(f"Tashkeela: {len(tr)} سطرًا للتدريب؛ والشعر: {len(ptr)} بيتًا للتدريب و{len(pte)} للاختبار")
    if quick:
        tr, va, te = tr[:150], va[:30], te[:30]
    train_lines = segments(tr) + ptr
    val_lines = segments(va) + pte[:1000]
    vocab = D.build_vocab(D.strip_diac(l) for l in train_lines + val_lines)
    cfg = {"vocab": vocab, "emb": 128, "hidden": 256, "layers": 4}
    train = encode(train_lines, vocab)
    val = encode(val_lines, vocab)
    model = D.make_model(len(vocab), cfg["emb"], cfg["hidden"], cfg["layers"], 0.25).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=epochs * (len(train) // 128 + 1), pct_start=0.1)
    scaler = torch.amp.GradScaler("cuda", enabled=(device == "cuda"))
    lossf = torch.nn.CrossEntropyLoss(ignore_index=-100)
    ck = os.path.join(WORK, "checkpoint.pt")
    start, best = 0, 1e9
    if os.path.exists(ck) and not quick:
        st = torch.load(ck, map_location=device)
        if st.get("vocab") == vocab:
            model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); sched.load_state_dict(st["sched"])
            start, best = st["epoch"] + 1, st["best"]
            log("استئناف من الدورة", start)
    patience = 0
    for ep in range(start, epochs):
        model.train()
        t0, tot, nb = time.time(), 0.0, 0
        for b in batches(train, 128, True, rnd):
            x, y = to_tensor(train, b, device)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device, dtype=torch.float16, enabled=(device == "cuda")):
                loss = lossf(model(x).float().reshape(-1, len(D.CLASSES)), y.reshape(-1))
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt); scaler.update(); sched.step()
            tot += loss.item(); nb += 1
            if nb % 500 == 0:
                log(f"  الدورة {ep + 1}: {nb} دفعة، الخسارة {tot / nb:.4f}")
        pv = predict(model, vocab, val_lines, device)
        m = der_wer(pv, val_lines)
        log(f"الدورة {ep + 1}/{epochs}: الخسارة {tot / max(nb, 1):.4f}، التحقق {m}، {int(time.time() - t0)} ثانية")
        score = m["DER مع علامة الإعراب"]
        if score < best:
            best, patience = score, 0
            torch.save(model.state_dict(), os.path.join(OUT, "model.pt"))
            with open(os.path.join(OUT, "config.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False)
            log("  حُفظ أفضل نموذج حتى الآن")
        else:
            patience += 1
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "epoch": ep, "best": best,
                    "vocab": vocab}, ck)
        if patience >= 4:
            log("توقف مبكر: لم يتحسن التحقق أربع دورات")
            break
    # التقويم النهائي
    model.load_state_dict(torch.load(os.path.join(OUT, "model.pt"), map_location=device))
    report = {"Tashkeela (اختبار Fadel)": der_wer(predict(model, vocab, te, device), te)}
    if pte:
        report["الشعر (قصائد معزولة من «أشعار»)"] = der_wer(predict(model, vocab, pte, device), pte)
    # الموازنة بالمشكِّل الحالي
    try:
        from camel_tools.disambig.bert import BERTUnfactoredDisambiguator
        from camel_tools.tokenizers.word import simple_word_tokenize
        bert = BERTUnfactoredDisambiguator.pretrained("msa", use_gpu=(device == "cuda"))
        def camel(line):
            toks = simple_word_tokenize(D.strip_diac(line))
            return " ".join(d.analyses[0].analysis.get("diac", d.word) if d.analyses else d.word for d in bert.disambiguate(toks))
        sample_t = [l for l in te[:(10 if quick else 300)]]
        report["الموازنة: CAMeL BERT (الحالي) على 300 سطر من Tashkeela"] = der_wer([camel(l) for l in sample_t], sample_t)
        report["الموازنة: النموذج الجديد على السطور نفسها"] = der_wer(predict(model, vocab, sample_t, device), sample_t)
        if pte:
            sp = pte[:(10 if quick else 300)]
            report["الموازنة: CAMeL BERT على 300 بيت"] = der_wer([camel(l) for l in sp], sp)
            report["الموازنة: النموذج الجديد على الأبيات نفسها"] = der_wer(predict(model, vocab, sp, device), sp)
    except Exception as e:
        report["الموازنة"] = f"تعذّرت: {e!r}"
    try:
        from catt_tashkeel import CATTEncoderDecoder
        ed = CATTEncoderDecoder()
        st = te[:(10 if quick else 300)]
        report["الموازنة: CATT على 300 سطر من Tashkeela"] = der_wer([ed.do_tashkeel(D.strip_diac(l), verbose=False) for l in st], st)
        if pte:
            sp = pte[:(10 if quick else 300)]
            report["الموازنة: CATT على الأبيات نفسها"] = der_wer([ed.do_tashkeel(D.strip_diac(l), verbose=False) for l in sp], sp)
            report["الموازنة: النموذج الجديد على الأبيات نفسها"] = der_wer(predict(model, vocab, sp, device), sp)
    except Exception as e:
        report["الموازنة بـ CATT"] = f"تعذّرت: {e!r}"
    report["التاريخ"] = time.strftime("%Y-%m-%d %H:%M")
    report["الجهاز"] = device
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8") as f:
        for k, v in report.items():
            f.write(f"{k}: {v}\n")
    log("التقرير:", json.dumps(report, ensure_ascii=False, indent=1))
    log("تم. أغلق Claude وافتحه ليستعمل الأداة المشكِّل الجديد.")


if __name__ == "__main__":
    main()
