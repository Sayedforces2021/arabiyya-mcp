"""مشكِّل العربية التراثية: نموذج على مستوى الحرف (BiLSTM) يتنبأ لكل حرف بحركته، مع مرشحات مرتبة لكل كلمة.

يُدرَّب بـ train_diacritizer.py على مدوّنة Tashkeela المعيارية (Fadel et al., 2019) وعلى الأبيات المشكولة من «أشعار»،
ويُحفظ في ~/.sarf/models/diac_ca/. ويستعمله الخادم في التشكيل وفي التشكيل الموجَّه بالعروض.
"""
import os, json, math

HOME = os.path.join(os.path.expanduser("~"), ".sarf")
MODEL_DIR = os.path.join(HOME, "models", "diac_ca")

FATHA, DAMMA, KASRA, SUKUN, SHADDA = "َ", "ُ", "ِ", "ْ", "ّ"
FATHATAN, DAMMATAN, KASRATAN = "ً", "ٌ", "ٍ"
VOWELS = [FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN]
# الأصناف: بلا حركة، والحركات السبع، والشدة وحدها، والشدة مع كل حركة غير السكون
CLASSES = [""] + VOWELS + [SHADDA] + [SHADDA + v for v in (FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN)]
CLS_ID = {c: i for i, c in enumerate(CLASSES)}
DIACS = set(VOWELS) | {SHADDA}
ARABIC = set("ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوىي")


def split_diac(text: str):
    """نص مشكول ← (الحروف، صنف حركة كل حرف)."""
    chars, labels = [], []
    for ch in text:
        if ch in DIACS:
            if not chars:
                continue
            cur = labels[-1]
            marks = set(cur) | {ch}
            sh = SHADDA in marks
            vs = [v for v in VOWELS if v in marks]
            lab = (SHADDA if sh else "") + (vs[-1] if vs else "")
            if sh and vs and vs[-1] == SUKUN:
                lab = SHADDA
            labels[-1] = lab if lab in CLS_ID else cur
        elif ch in ("ـ", "ٰ"):  # التطويل والألف الخنجرية
            continue
        else:
            chars.append(ch)
            labels.append("")
    return "".join(chars), [CLS_ID.get(l, 0) for l in labels]


def strip_diac(text: str) -> str:
    return "".join(c for c in text if c not in DIACS and c not in ("ـ", "ٰ"))


def join_diac(chars: str, labels) -> str:
    return "".join(c + (CLASSES[l] if c in ARABIC else "") for c, l in zip(chars, labels))


def build_vocab(texts):
    vocab = {"<pad>": 0, "<unk>": 1}
    for t in texts:
        for ch in t:
            if ch not in vocab:
                vocab[ch] = len(vocab)
    return vocab


def make_model(n_vocab: int, emb: int = 128, hidden: int = 256, layers: int = 4, dropout: float = 0.25):
    import torch.nn as nn

    class Diac(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(n_vocab, emb, padding_idx=0)
            self.lstm = nn.LSTM(emb, hidden, num_layers=layers, bidirectional=True, batch_first=True, dropout=dropout)
            self.drop = nn.Dropout(dropout)
            self.out = nn.Linear(hidden * 2, len(CLASSES))

        def forward(self, x):
            h, _ = self.lstm(self.drop(self.emb(x)))
            return self.out(self.drop(h))
    return Diac()


class Diacritizer:
    """للاستعمال في الخادم: تشكيل نص، ومرشحات مرتبة لكل كلمة."""

    def __init__(self, model_dir: str = MODEL_DIR, device: str | None = None):
        import torch
        with open(os.path.join(model_dir, "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.vocab = cfg["vocab"]
        self.cfg = cfg
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = make_model(len(self.vocab), cfg["emb"], cfg["hidden"], cfg["layers"], 0.0)
        state = torch.load(os.path.join(model_dir, "model.pt"), map_location=self.device)
        self.model.load_state_dict(state)
        self.model.to(self.device).eval()

    def _probs(self, chars: str):
        import torch
        out = []
        for i in range(0, len(chars), 500):  # مقاطع طويلة على حدود الكلمات تقريبًا
            seg = chars[i:i + 500]
            ids = torch.tensor([[self.vocab.get(c, 1) for c in seg]], device=self.device)
            with torch.no_grad():
                p = torch.softmax(self.model(ids)[0].float(), -1).cpu()
            out.append(p)
        return torch.cat(out, 0) if out else None

    def diacritize(self, text: str, keep_marks: bool = True) -> str:
        """يُبقي ما ضبطه صاحب النص، ويملأ الباقي."""
        chars, given = split_diac(text)
        if not chars:
            return text
        p = self._probs(chars)
        labels = p.argmax(-1).tolist()
        if keep_marks:
            labels = [g if g else l for g, l in zip(given, labels)]
        labels = [l if c in ARABIC else 0 for c, l in zip(chars, labels)]
        return join_diac(chars, labels)

    def word_candidates(self, text: str, k: int = 8):
        """لكل كلمة أرجح k ضبطًا مع احتمالاتها (بحث شعاعي داخل الكلمة)، مقيدة بما ضبطه صاحب النص."""
        chars, given = split_diac(text)
        p = self._probs(chars)
        words, i = [], 0
        while i < len(chars):
            if chars[i] == " ":
                i += 1
                continue
            j = i
            while j < len(chars) and chars[j] != " ":
                j += 1
            beams = [(0.0, [])]
            for t in range(i, j):
                c = chars[t]
                if c not in ARABIC:
                    beams = [(s, l + [0]) for s, l in beams]
                    continue
                pr = p[t]
                if given[t]:
                    opts = [(given[t], 1.0)]
                else:
                    top = pr.topk(4)
                    opts = [(int(ix), float(v)) for v, ix in zip(top.values, top.indices)]
                beams = sorted(((s + math.log(max(v, 1e-9)), l + [ix]) for s, l in beams for ix, v in opts), key=lambda x: -x[0])[:k * 3]
            seen, cands = set(), []
            for s, l in beams:
                w = join_diac(chars[i:j], l)
                if w not in seen:
                    seen.add(w)
                    cands.append((w, math.exp(s)))
                if len(cands) >= k:
                    break
            words.append(cands)
            i = j
        return words


_INSTANCE = None


def get(device=None):
    global _INSTANCE
    if _INSTANCE is None and os.path.exists(os.path.join(MODEL_DIR, "model.pt")):
        _INSTANCE = Diacritizer(device=device)
    return _INSTANCE
