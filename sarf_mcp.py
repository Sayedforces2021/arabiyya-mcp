"""arabiyya (العربية): خادم MCP لعلوم العربية بلا إنترنت — الصرف والنحو والمعجم والعروض والأصوات والدلالة والمدوّنات.

الأدوات:
- analyze_word: كل التحليلات المحتملة لكلمة مفردة (بلا سياق).
- analyze_text: تحليل جملة كلمةً كلمة مع ترجيح سياقي (BERT).
- diacritize: تشكيل النص آليًّا بحسب السياق.
- scan_verse: التقطيع العروضي (PyArud).
- lexicon_lookup: المعاجم التراثية من The Arabic Lexicon.
- conjugate: تصريف الفعل في الأزمنة والضمائر (قطرب).
- root_family: أسرة الجذر من أفعال وأسماء وصفات.
- search_poetry: شواهد الشعر من مدوّنة «أشعار» بلا إنترنت.
- quran_word / quran_root: التحليل الصرفي لكلمات القرآن ومواضع الجذور (المدوّنة القرآنية).
- maajim: مادة الجذر من 15 معجمًا تراثيًّا بلا إنترنت (OpenITI).
- word_similarity / substitutes_in_context / semantic_neighbors: الدلالة بنموذج CAMeLBERT الكلاسيكي.
- corpus_concordance / corpus_usage / corpus_collocates: المدوّنة التراثية (57 كتابًا) للتحليل الحاسوبي.
- scan_poem / text_profile: تقطيع القصيدة كاملة، والتحليل المعجمي لنص أو ديوان.
- compare_texts: الموازنة الأسلوبية بين نصّين أو شاعرين أو كتابين (الألفاظ والجذور والأوزان المميِّزة والمعجم المشترك).
- corpus_find_book / corpus_add_book / corpus_remove_book: توسيع المدوّنة بأي كتاب من OpenITI.
- phonetics / huruf: الكتابة الصوتية (IPA) والمقاطع والنبر، ومخارج الحروف وصفاتها.
"""

import os
from functools import lru_cache

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.tokenizers.word import simple_word_tokenize

INSTRUCTIONS = """أداة «العربية»: عُدّة باحث في علوم العربية تعمل على الجهاز بلا إنترنت.
- الصرف: analyze_word (تحليلات الكلمة كلها)، analyze_text (تحليل الجملة بالسياق)، root_family (أسرة الجذر)، conjugate (تصريف الفعل).
- الضبط والعروض: diacritize (التشكيل)، scan_verse (تقطيع البيت)، scan_poem (تقطيع القصيدة والتنبيه على المختل).
- الأصوات: phonetics (الكتابة الصوتية IPA والمقاطع والنبر)، huruf (المخارج والصفات والموازنة بين حرفين).
- المعجم: maajim (15 معجمًا تراثيًّا معزوّة بالجزء والصفحة)، lexicon_lookup (The Arabic Lexicon عبر الإنترنت).
- القرآن: quran_word (صرف كلمات الآية وإعرابها)، quran_root (مواضع الجذر وصيغه).
- الشعر: search_poetry (شواهد من أكثر من 3.8 مليون بيت).
- الدلالة: semantic_neighbors وword_similarity وsubstitutes_in_context (نموذج CAMeLBERT الكلاسيكي).
- المدوّنة التراثية: corpus_concordance (السياقات)، corpus_usage (التطوّر عبر القرون)، corpus_collocates (المتلازمات)، corpus_find_book / corpus_add_book / corpus_remove_book (توسيعها من OpenITI).
- الأسلوب: text_profile (التحليل المعجمي لنص أو ديوان)، compare_texts (الموازنة بين نصّين أو شاعرين أو كتابين).
تنبيهات: التحليل الآلي يقارب ولا يقطع، فما خالف المقرر عند أهل الفن يُنبَّه عليه ولا يُسلَّم به؛ والشعر القديم يُعطى مشكولًا ما أمكن لأن التشكيل الآلي مبني على الفصحى المعاصرة؛ ويُذكر المصدر بالجزء والصفحة كما تُرجعه الأدوات."""

try:  # mcp 2.x
    mcp = FastMCP("arabiyya", title="العربية", description="عُدّة باحث في علوم العربية بلا إنترنت: الصرف والعروض والأصوات والمعاجم والقرآن والشعر والدلالة والمدوّنات.",
                  instructions=INSTRUCTIONS)
except TypeError:  # mcp 1.x
    mcp = FastMCP("arabiyya", instructions=INSTRUCTIONS)

POS = {
    "noun": "اسم", "noun_prop": "علم", "noun_num": "اسم عدد", "noun_quant": "اسم كمية",
    "adj": "صفة", "adj_comp": "اسم تفضيل", "adj_num": "صفة عددية",
    "verb": "فعل", "verb_pseudo": "شبه فعل (إنّ وأخواتها)",
    "pron": "ضمير", "pron_dem": "اسم إشارة", "pron_rel": "اسم موصول", "pron_interrog": "اسم استفهام",
    "adv": "ظرف", "adv_interrog": "ظرف استفهام", "adv_rel": "ظرف موصول",
    "prep": "حرف جر", "conj": "حرف عطف", "conj_sub": "حرف مصدري/ربط", "part": "حرف",
    "part_neg": "حرف نفي", "part_det": "أداة تعريف", "part_focus": "حرف توكيد/حصر",
    "part_fut": "حرف استقبال", "part_interrog": "حرف استفهام", "part_voc": "حرف نداء",
    "part_verb": "حرف (قد)", "part_restrict": "حرف حصر",
    "interj": "اسم فعل/تعجب", "abbrev": "مختصر", "punc": "علامة ترقيم", "digit": "رقم",
    "foreign": "أعجمي",
}
ASP = {"p": "ماض", "i": "مضارع", "c": "أمر"}
VOX = {"a": "مبني للمعلوم", "p": "مبني للمجهول"}
CAS = {"n": "مرفوع", "a": "منصوب", "g": "مجرور"}
MOD = {"i": "مرفوع", "s": "منصوب", "j": "مجزوم"}
GEN = {"m": "مذكر", "f": "مؤنث"}
NUM = {"s": "مفرد", "d": "مثنى", "p": "جمع"}
STT = {"d": "معرّف", "i": "نكرة", "c": "مضاف"}
PER = {"1": "متكلم", "2": "مخاطب", "3": "غائب"}


@lru_cache(maxsize=1)
def _analyzer():
    return Analyzer(MorphologyDB.builtin_db())


@lru_cache(maxsize=1)
def _bert():
    # يُحمَّل عند أول طلب فقط حتى يبدأ الخادم سريعًا
    from camel_tools.disambig.bert import BERTUnfactoredDisambiguator
    return BERTUnfactoredDisambiguator.pretrained("msa")


def _wazn(pattern: str) -> str:
    return (pattern or "").translate(str.maketrans({"1": "ف", "2": "ع", "3": "ل", "4": "ل"}))


def _stem_wazn(a: dict) -> str:
    """وزن الكلمة مجرّدة من السوابق واللواحق وعلامة الإعراب، مع ردّ حروف العلة المنقلبة إلى العين أو اللام (قال ← فَعَلَ، سيف ← فَعْل)."""
    import re
    pat, diac, stem, bw = a.get("pattern") or "", a.get("diac") or "", a.get("stem") or "", a.get("bw") or ""
    w = pat
    if pat and stem and len(pat) == len(diac) and diac.find(stem) >= 0:
        i = diac.find(stem)
        segs = [x.rpartition("/") for x in bw.split("+")]
        k = next((j for j, (t, _, _g) in enumerate(segs) if stem in t), None)
        start, end = i, i + len(stem)
        if k is not None:
            j = k - 1
            while j >= 0 and segs[j][2].startswith("IV") and "SUFF" not in segs[j][2]:
                start -= len(segs[j][0]); j -= 1
            j = k + 1
            while j < len(segs) and (segs[j][2].startswith("NSUFF") or "SUBJ" in segs[j][2]):
                end += len(segs[j][0]); j += 1
        w = pat[max(0, start):end]
    root = (a.get("root") or "").split(".")
    if len(root) == 3 and "1" in w:
        if "2" not in w and root[1] in "وي#":
            if re.search("1ائ", w):  # فاعل من الأجوف: قائل
                w = w.replace("1ائ", "1اع", 1)
            elif re.search("1ْتا", w):  # افتعل من الأجوف: اختار
                w = w.replace("1ْتا", "1ْتَعَ", 1)
            elif re.search("1ا", w):  # قال، مقال
                w = re.sub("(م[َُ])1ا", r"\g<1>1ْعَ", w, count=1) if re.search("م[َُ]1ا", w) else w.replace("1ا", "1َعَ", 1)
            else:  # يقول، يبيع، بيت، نور
                def _hollow(m):
                    h, suk, nxt = m.group(1), m.group(3), m.group(4)
                    if not h or suk or nxt == "ا":  # بيت، صيام: الواو والياء حرف صحيح هنا
                        return "1" + h + "ع" + suk + nxt
                    if m.start() == 0:  # نور، سور: فُعْل
                        return "1" + h + "عْ" + nxt
                    return "1ْع" + h + nxt  # يقول ← يَفْعُل
                w = re.sub("1([ًٌٍَُِ]?)([وي])(ْ?)(.?)", _hollow, w, count=1)
        if "3" not in w and root[1] == root[2] and "2ّ" in w:  # المضعّف: مُدَّة ← فُعْلَة
            w = w.replace("ا2ّ", "ا2ِ3", 1) if "ا2ّ" in w else re.sub("2ّ([ًٌٍَُِ]?)", lambda m: "2ْ3" + m.group(1), w, count=1)
        if "3" not in w and root[2] in "وي#" and "2" in w:
            w = re.sub("(2)([ًٌٍَُِّ]*)([اوىي])", lambda m: m.group(1) + (m.group(2) or ("َ" if m.group(3) == "ا" else "")) + "ل", w, count=1)
    while w and w[-1] in "ًٌٍَُِْ":
        w = w[:-1]
    return _wazn(w)


def _fmt(a: dict) -> dict:
    out = {
        "المشكول": a.get("diac"),
        "الجذر": (a.get("root") or "").replace(".", " "),
        "الوزن": _wazn(a.get("pattern")),
        "المدخل المعجمي": a.get("lex"),
        "الجذع": a.get("stem"),
        "النوع": POS.get(a.get("pos"), a.get("pos")),
    }
    pos = a.get("pos", "")
    if pos == "verb":
        out["الزمن"] = ASP.get(a.get("asp"))
        out["البناء"] = VOX.get(a.get("vox"))
        out["الشخص"] = PER.get(a.get("per"))
        if a.get("asp") == "i":
            out["الحالة"] = MOD.get(a.get("mod"))
    else:
        out["الحالة"] = CAS.get(a.get("cas"))
        out["التعريف"] = STT.get(a.get("stt"))
    out["الجنس"] = GEN.get(a.get("gen"))
    out["العدد"] = NUM.get(a.get("num"))
    clitics = [a.get(k) for k in ("prc3", "prc2", "prc1", "prc0", "enc0")]
    clitics = [c for c in clitics if c and c not in ("0", "na")]
    if clitics:
        out["اللواصق"] = clitics
    out["المعنى (إنجليزي)"] = a.get("gloss")
    return {k: v for k, v in out.items() if v not in (None, "", "na")}


@mcp.tool()
def analyze_word(word: str, max_results: int = 10) -> list[dict]:
    """كل التحليلات الصرفية المحتملة لكلمة عربية مفردة (الجذر، الوزن، النوع، الحالة، اللواصق)، بلا ترجيح سياقي."""
    seen, results = set(), []
    for a in _analyzer().analyze(word.strip()):
        f = _fmt(a)
        key = (f.get("المشكول"), f.get("النوع"), f.get("الجذر"))
        if key not in seen:
            seen.add(key)
            results.append(f)
        if len(results) >= max_results:
            break
    return results or [{"تنبيه": "لم يُعثر على تحليل لهذه الكلمة"}]


@mcp.tool()
def analyze_text(text: str, alternatives: int = 1) -> list[dict]:
    """تحليل جملة أو نص قصير كلمةً كلمة مع اختيار التحليل الأرجح بحسب السياق (BERT). alternatives: عدد التحليلات المعروضة لكل كلمة."""
    tokens = simple_word_tokenize(text)
    out = []
    for dw in _bert().disambiguate(tokens):
        items = []
        for sa in dw.analyses[: max(1, alternatives)]:
            f = _fmt(sa.analysis)
            f["الدرجة"] = round(float(sa.score), 3)
            items.append(f)
        out.append({"الكلمة": dw.word, "التحليل": items})
    return out


def _diacritize(text: str) -> str:
    tokens = simple_word_tokenize(text)
    words = []
    for dw in _bert().disambiguate(tokens):
        words.append(dw.analyses[0].analysis.get("diac", dw.word) if dw.analyses else dw.word)
    return " ".join(words)


@mcp.tool()
def diacritize(text: str) -> str:
    """تشكيل نص عربي آليًّا بحسب السياق."""
    return _diacritize(text)


HARAKAT = set("ًٌٍَُِّْ")
BAHR_TYPE = {"tam": "تام", "majzoo": "مجزوء", "mashtoor": "مشطور", "manhook": "منهوك", "mukhalla": "مخلّع"}
HARAKA = {"fatha": "فتحة", "damma": "ضمة", "kasra": "كسرة", "sukun": "سكون"}


def _is_diacritized(text: str) -> bool:
    letters = sum(1 for c in text if "ء" <= c <= "ي")
    marks = sum(1 for c in text if c in HARAKAT)
    return letters > 0 and marks / letters >= 0.3


def _shatr(s) -> dict:
    return {
        "النص": s.text,
        "الكتابة العروضية": s.arudi_text,
        "الرموز": s.pattern,
        "التفعيلات": [
            {"التفعيلة": f.base_tafeela, "الحال": f.zihaf_name_ar, "سليمة": f.status == "ok"}
            for f in s.feet
        ],
        "موزون": s.is_valid,
    }


@mcp.tool()
def scan_verse(verse: str, meter: str | None = None, auto_diacritize: bool = True) -> dict:
    """تقطيع بيت شعر عروضيًّا: البحر ونوعه، والتفعيلات وزحافاتها وعللها، والقافية والرويّ.
    verse: البيت بشطريه مفصولين بـ " * " (أو شطر واحد). يفضَّل أن يكون مشكولًا؛ فإن لم يكن شُكِّل آليًّا أولًا.
    meter: اسم بحر بالإنجليزية لفرضه (taweel, baseet, kamel, wafer, ...) عند الحاجة."""
    import pyarud

    parts = [p.strip() for p in verse.replace("...", "*").split("*", 1)]
    note = None
    if auto_diacritize:
        prepared = [_prepare_verse_text(p) for p in parts]
        parts = [p for p, _ in prepared]
        notes = {n for _, n in prepared if n}
        if notes:
            note = " ".join(sorted(notes)) + " راجع الضبط إن بدت النتيجة غريبة."
    r = pyarud.analyze_verse(parts[0], parts[1] if len(parts) > 1 else "", forced_meter=meter)
    out = {
        "البحر": r.meter_name_ar,
        "نوعه": BAHR_TYPE.get(str(r.bahr_type), r.bahr_type),
        "نسبة المطابقة": r.score,
        "موزون": r.is_valid,
        "الصدر": _shatr(r.sadr) if r.sadr else None,
        "العجز": _shatr(r.ajuz) if r.ajuz else None,
    }
    q = r.qafiyah
    if q:
        out["القافية"] = {
            "نصها": q.qafiyah_text,
            "الروي": q.rawi,
            "حركة الروي": HARAKA.get(str(q.rawi_haraka), q.rawi_haraka),
            "نوعها": q.qafiyah_type_ar,
        }
    if r.errors:
        out["ملاحظات المحلل"] = [str(e) for e in r.errors]
    if note:
        out["تنبيه"] = note
    return {k: v for k, v in out.items() if v is not None}


# ───────────── المعاجم التراثية (The Arabic Lexicon — arabiclexicon.hawramani.com) ─────────────

LEXICON_BASE = "https://arabiclexicon.hawramani.com/"
HAMZA_FORMS = str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ؤ": "ء", "ئ": "ء"})


def _strip_tashkeel(s: str) -> str:
    return "".join(c for c in s if c not in HARAKAT and c != "ـ")


@lru_cache(maxsize=256)
def _lexicon_page(word: str):
    import urllib.request, urllib.parse, urllib.error
    url = LEXICON_BASE + urllib.parse.quote(word) + "/"
    req = urllib.request.Request(url, headers={"User-Agent": "sarf-mcp/1.0 (personal research tool)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return url, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return url, None
        raise


def _candidates(word: str) -> list[str]:
    w = word.strip()
    bare = _strip_tashkeel(w)
    cands = [w, bare, bare.translate(HAMZA_FORMS)]
    if bare.startswith("ء") or bare[:1] in "أإآ":
        cands.append("ا" + bare[1:])
    seen, out = set(), []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _parse_lexicon(html: str) -> tuple[list[dict], list[str]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for c in soup.select(".definition-container"):
        ar = c.select_one(".credits .ar")
        credit = c.select_one(".credits")
        name = (ar.get_text(" ", strip=True) if ar else "") or (credit.get_text(" ", strip=True) if credit else "")
        d = c.select_one(".definition")
        if not d:
            continue
        for br in d.find_all("br"):
            br.replace_with("\n")
        text = "\n".join(line.strip() for line in d.get_text().splitlines() if line.strip())
        perma = c.select_one(".sectionperma")
        entries.append({"المعجم": name, "النص": text, "الرابط": perma.get_text(strip=True) if perma else None})
    for s in soup.select(".reelcontainer .reel-list-ordinal, .reelcontainer .entry-count"):
        s.decompose()
    nearby = [a.get_text(" ", strip=True) for a in soup.select(".reelcontainer a:not(.meta)")]
    return entries, nearby


@mcp.tool()
def lexicon_lookup(word: str, dictionaries: list[str] | None = None, max_chars_per_entry: int = 4000) -> dict:
    """البحث عن جذر أو كلمة في نحو 47 معجمًا تراثيًّا معًا (العين، الصحاح، المحكم، مقاييس اللغة، لسان العرب، تاج العروس،
    القاموس المحيط، أساس البلاغة، المفردات، المصباح المنير، مختار الصحاح، المغرب، معجم لين، تكملة دوزي...) من موقع The Arabic Lexicon.
    word: يفضَّل الجذر مجرّدًا (مثل: كتب، ءمن).
    dictionaries: لتقييد النتائج بمعاجم معيّنة بجزء من اسمها العربي، مثل ["لسان", "مقاييس", "تاج"].
    max_chars_per_entry: الحد الأقصى لطول نص كل مادة (المواد الطويلة كاللسان والتاج قد تتجاوز عشرة آلاف حرف)."""
    tried = []
    for cand in _candidates(word):
        url, html = _lexicon_page(cand)
        tried.append(cand)
        if html is None:
            continue
        entries, nearby = _parse_lexicon(html)
        if dictionaries:
            entries = [e for e in entries if any(k in e["المعجم"] for k in dictionaries)]
        for e in entries:
            if len(e["النص"]) > max_chars_per_entry:
                e["النص"] = e["النص"][:max_chars_per_entry] + " …[مقطوع؛ ارفع max_chars_per_entry أو قيّد المعجم]"
        return {
            "المادة": cand,
            "المصدر": url,
            "عدد المعاجم": len(entries),
            "المواد": entries,
            "مداخل مجاورة": nearby,
        }
    return {"تنبيه": "لم توجد المادة", "جُرِّب": tried, "اقتراح": "جرّب الجذر المجرد بلا زوائد، وبالهمزة على صورة ء"}


# ───────────── التصريف (قطرب) وأسرة الجذر (CAMeL) ─────────────

FUTURE_HARAKA = {"َ": "فتحة", "ُ": "ضمة", "ِ": "كسرة"}
HOLLOW_HARAKA = {"و": "ضمة", "ي": "كسرة", "ا": "فتحة"}


@lru_cache(maxsize=1)
def _gen_db():
    return MorphologyDB.builtin_db(flags="g")


@lru_cache(maxsize=1)
def _root_index():
    idx = {}
    for lemma, entries in _gen_db().lemma_hash.items():
        for e in entries:
            r = e.get("root")
            if r:
                idx.setdefault(r, []).append((lemma, e))
    return idx


def _ain_haraka(lemma: str):
    """حركة عين المضارع من نمط المضارع في قاعدة CAMeL."""
    for e in _gen_db().lemma_hash.get(lemma, []):
        if e.get("pos") == "verb" and e.get("asp") == "i" and e.get("vox") == "a":
            pat = e.get("pattern") or ""
            i = pat.find("2")
            if i != -1 and i + 1 < len(pat) and pat[i + 1] in FUTURE_HARAKA:
                return FUTURE_HARAKA[pat[i + 1]]
            j = pat.find("1")
            if i == -1 and j != -1:
                rest = pat[j + 1:]
                # الناقص واللفيف المقرون: يَرْوِي (1ْوِي) — العين حرف ظاهر بعد فاء ساكنة
                if len(rest) >= 3 and rest[0] == "\u0652" and rest[1] not in HARAKAT and rest[2] in FUTURE_HARAKA:
                    return FUTURE_HARAKA[rest[2]]
                # الأجوف: يَقُول (1ُو3) — حركة الفاء هي حركة العين المنقولة
                if len(rest) >= 2 and rest[0] in FUTURE_HARAKA and rest[1] in "اوي":
                    return FUTURE_HARAKA[rest[0]]
            for ch in pat:  # الأجوف: يَقُول، يَبِيع، يَخاف
                if ch in HOLLOW_HARAKA:
                    return HOLLOW_HARAKA[ch]
    return None


def _verb_candidates(word: str) -> list:
    """الأفعال الماضية المشكولة المحتملة للكلمة، مع حركة عين مضارعها، مرتبةً بالأقرب إلى ما كُتب."""
    FATHA, SHADDA = "\u064e", "\u0651"
    typed = _strip_tashkeel(word.strip()).replace(SHADDA, "")
    out, seen = [], set()
    for a in _analyzer().analyze(word.strip()):
        if a.get("pos") != "verb":
            continue
        lex = (a.get("lex") or "").split("-")[0].split("_")[0]
        if not lex or lex in seen:
            continue
        seen.add(lex)
        past = lex.replace("\u0671", "\u0627")  # همزة الوصل ٱ ← ا (قطرب لا يقبلها)
        if past[-1] in "\u0627\u0649":  # الناقص: دَعَا، رَمَى
            if len(past) > 1 and past[-2] not in HARAKAT:
                past = past[:-1] + FATHA + past[-1]
        elif past[-1] not in HARAKAT:
            past += FATHA
        bare = _strip_tashkeel(past).replace(SHADDA, "")
        rank = 0 if bare == typed else (1 if _norm(bare) == _norm(typed) else 2)
        rank = rank * 2 + (1 if SHADDA in past and SHADDA not in word else 0)  # المجرد قبل المضعّف عند غياب الشدة
        out.append((rank, {"الفعل": past, "حركة عين المضارع": _ain_haraka(lex),
                           "المعنى (إنجليزي)": a.get("gloss")}))
    out.sort(key=lambda x: x[0])
    best = [c for r, c in out if r < 4]
    return best or [c for r, c in out]


def _same_verb(cand: str, typed: str) -> bool:
    """يطابق الفعل المرشح ما كتبه المستخدم: الحروف نفسها، والتشديد نفسه، والحركات حيث وُجدت في الاثنين."""
    def seq(w):
        out = []
        for ch in w.replace("\u0671", "\u0627"):
            if ch in HARAKAT and out:
                out[-1][1] += ch
            elif ch not in HARAKAT:
                out.append([ch, ""])
        return out
    a, b = seq(cand), seq(typed)
    if [x for x, _ in a] != [x for x, _ in b]:
        return False
    for i, ((_, ma), (_, mb)) in enumerate(zip(a, b)):
        if ("\u0651" in ma) != ("\u0651" in mb):
            return False
        va, vb = ma.replace("\u0651", ""), mb.replace("\u0651", "")
        if va and vb and va != vb and i != len(a) - 1:
            return False
    return True


def _ain_by_analogy(word: str, transitive: bool):
    """حركة عين المضارع بالقياس الغالب حين يغيب الفعل عن المعجم الصرفي."""
    b = _strip_tashkeel(word)
    if len(b) == 2 and "\u0651" in word or (len(b) == 3 and b[1] == b[2]):
        return ("ضمة", "بقياس المضعّف المتعدي (مدّ يمُدّ، أمّ يؤُمّ)") if transitive else \
               ("كسرة", "بقياس المضعّف اللازم (فرّ يفِرّ)")
    if b.endswith("ى"):
        return "كسرة", "بقياس الناقص اليائي (رمى يرمي)"
    if b.endswith("ا"):
        return "ضمة", "بقياس الناقص الواوي (دعا يدعو)"
    if b.startswith("و"):
        return "كسرة", "بقياس المثال الواوي (وعد يعِد)"
    return "فتحة", "افتراضًا"


@mcp.tool()
def conjugate(verb: str, ain_haraka: str | None = None, transitive: bool = True,
              tenses: list[str] | None = None) -> dict:
    """تصريف فعل عربي في الأزمنة كلها مع الضمائر: الماضي والمضارع (مرفوعًا ومنصوبًا ومجزومًا ومؤكدًا) والأمر، معلومًا ومجهولًا. يعمل للثلاثي والمزيد والمعتل.
    verb: الفعل الماضي، ويفضَّل مشكولًا (كَتَبَ، اسْتَغْفَرَ، قَالَ). إن كان غير مشكول اختيرت قراءته من المعجم الصرفي، وذُكرت القراءات الأخرى.
    ain_haraka: حركة عين المضارع للثلاثي: «فتحة» أو «ضمة» أو «كسرة» (كتب يكتُب = ضمة). تُستنتج تلقائيًّا إن أمكن.
    transitive: للمتعدي يُضاف المجهول.
    tenses: لتقييد الجداول بأسماء أزمنة بعينها، مثل ["المضارع المجزوم", "الأمر"]."""
    from libqutrub import mosaref_main

    word = verb.strip().replace("\u0671", "\u0627")
    notes, others = [], []
    vocalized = any(c in HARAKAT for c in word)
    if not vocalized or ain_haraka is None:
        cands = _verb_candidates(_strip_tashkeel(word) if not vocalized else word)
        if cands:
            if not vocalized:
                word = cands[0]["الفعل"]
                others = cands[1:]
            if ain_haraka is None:
                match = next((c for c in cands if _same_verb(c["الفعل"], word)), None)
                if match is None and not vocalized:
                    match = cands[0]
                if match is not None:
                    ain_haraka = match["حركة عين المضارع"]
    if ain_haraka is None:
        ain_haraka, why = _ain_by_analogy(word, transitive)
        notes.append(f"لم أجد الفعل في المعجم الصرفي، فجعلت عين المضارع {ain_haraka} {why}؛ فحدّدها إن كانت غيرها.")
    res = mosaref_main.do_sarf(word, ain_haraka, alltense=True, transitive=transitive, display_format="DICT")
    if not res:
        return {"تنبيه": f"لم يُقبل «{word}» فعلًا صالحًا للتصريف؛ اكتبه ماضيًا مشكولًا (مثل: كَتَبَ)."}
    tables = {k.strip(): {p: f for p, f in v.items() if f} for k, v in res.items()}
    if tenses:
        tables = {k: v for k, v in tables.items() if any(t in k for t in tenses)}
    out = {"الفعل": word, "حركة عين المضارع": ain_haraka, "الجداول": tables}
    if others:
        out["قراءات أخرى محتملة"] = others
    if notes:
        out["ملاحظات"] = notes
    return out


@mcp.tool()
def root_family(word: str) -> dict:
    """أسرة الجذر: كل ما في المعجم الصرفي من أفعال وأسماء وصفات ترجع إلى جذر الكلمة، مع أوزانها ومعانيها.
    word: الجذر (كتب، أو ك ت ب) أو أي كلمة منه (مكتوب، استكتاب)."""
    w = _strip_tashkeel(word.strip())
    letters = [c for c in w if c != " " and c != "."]
    roots = []
    if 3 <= len(letters) <= 4:
        roots.append(".".join(letters))
    for a in _analyzer().analyze(w):
        r = a.get("root")
        if r and r not in roots and "#" not in r:
            roots.append(r)
    idx = _root_index()
    roots = [r for r in roots if r in idx]
    if not roots:
        return {"تنبيه": "لم أجد جذرًا لهذه الكلمة في المعجم الصرفي."}
    result = {}
    for r in roots[:3]:
        groups = {}
        seen = set()
        for lemma, e in idx[r]:
            pos = POS.get(e.get("pos"), e.get("pos"))
            key = (lemma, pos)
            if key in seen:
                continue
            seen.add(key)
            pats = sorted({_wazn(x.get("pattern")) for l2, x in idx[r] if l2 == lemma and POS.get(x.get("pos"), x.get("pos")) == pos and x.get("pattern")})
            groups.setdefault(pos, []).append({
                "الكلمة": lemma.split("-")[0].split("_")[0],
                "الأوزان في القاعدة": pats,
                "المعنى (إنجليزي)": e.get("gloss"),
            })
        result[r.replace(".", " ")] = groups
    return {"الجذور": result,
            "ملاحظة": "الأوزان كما ترد في قاعدة CAMeL: قد تكون لصيغ الجمع أو المضارع أو المجهول لا للمفرد وحده."}


# ───────────── شواهد الشعر (مدوّنة أشعار) ─────────────

POETRY_DB = os.path.join(os.path.expanduser("~"), ".sarf", "ashaar.db")


def _norm(s: str) -> str:
    s = _strip_tashkeel(s or "")
    return s.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "ء", "ئ": "ء"}))


@mcp.tool()
def search_poetry(query: str = "", meter: str | None = None, era: str | None = None,
                  poet: str | None = None, ending: str | None = None,
                  exact_phrase: bool = True, limit: int = 20) -> dict:
    """البحث عن شواهد في مدوّنة «أشعار» (نحو 3.8 ملايين بيت لـ7 آلاف شاعر من الجاهلية إلى اليوم)، بلا إنترنت.
    query: كلمة أو تركيب يُبحث عنه في الأبيات (يتجاهل التشكيل وصور الهمزة). المطابقة بالكلمة كاملة، فـ«العزم» لا تطابق «بالعزم»؛
           وإضافة * في آخر الكلمة تطابق ما يبدأ بها («عزم*» = عزمه، عزمات...). يجوز ترك البحث فارغًا مع المرشِّحات.
    exact_phrase: صحيح = التركيب متتاليًا كما هو؛ خطأ = الكلمات كلها في البيت بأي ترتيب.
    meter: جزء من اسم البحر، مثل «الطويل» أو «مجزوء الرمل».
    era: جزء من اسم العصر، مثل «الجاهلي»، «الإسلامي»، «الأموي»، «العباسي»، «الأندلسي».
    poet: جزء من اسم الشاعر، مثل «المتنبي» أو «الكميت».
    ending: آخر العجز (حروف القافية)، مثل «مِ» أو «ـلِ» تُكتب حروفًا: «م»، «يم»، «ول».
    limit: عدد النتائج (الحد 100).
    المدوّنة للبحث العلمي غير التجاري؛ ونسبة الأبيات وضبطها كما في مصادرها الإلكترونية، فتُوثَّق من الدواوين."""
    import sqlite3
    if not os.path.exists(POETRY_DB):
        return {"تنبيه": "فهرس الشعر لم يُبنَ بعد. شغّل سكربت التثبيت مرة أخرى ليبنيه (تنزيل نحو 280 م.ب)."}
    limit = max(1, min(int(limit), 100))
    con = sqlite3.connect(f"file:{POETRY_DB}?mode=ro", uri=True)
    where, args = [], []
    q = _norm(query).strip()
    if q:
        words = [w for w in q.split() if w]
        if exact_phrase and not any(w.endswith("*") for w in words):
            fts = '"' + " ".join(words) + '"'
        else:  # «كتب*» = كل كلمة تبدأ بهذه الحروف (كتبه، كتبوا...)
            fts = " AND ".join(f'"{w[:-1]}"*' if w.endswith("*") else f'"{w}"' for w in words)
        where.append("v.rowid IN (SELECT rowid FROM verses_fts WHERE verses_fts MATCH ?)")
        args.append(fts)
    for col, val in (("p.meter", meter), ("p.era", era), ("p.poet", poet)):
        if val:
            where.append(f"{col}_n LIKE ?")
            args.append(f"%{_norm(val)}%")
    if ending:
        where.append("v.ajuz_end LIKE ?")
        args.append(f"%{_norm(ending).replace(' ', '')}")
    if not where:
        return {"تنبيه": "أعطِ كلمة للبحث أو مرشِّحًا واحدًا على الأقل."}
    sql = (f"SELECT v.sadr, v.ajuz, p.poet, p.era, p.meter, p.title, p.theme FROM verses v "
           f"JOIN poems p ON p.id = v.poem_id WHERE {' AND '.join(where)} LIMIT ?")
    rows = con.execute(sql, args + [limit]).fetchall()
    con.close()
    return {
        "عدد النتائج المعروضة": len(rows),
        "الأبيات": [
            {"البيت": f"{s} * {a}" if a else s, "الشاعر": po, "العصر": er, "البحر": me,
             "القصيدة": ti, "الغرض": th}
            for s, a, po, er, me, ti, th in rows
        ],
    }


# ───────────── المدوّنة القرآنية (Quranic Arabic Corpus v0.4، برخصة GPL) ─────────────

SARF_HOME = os.path.join(os.path.expanduser("~"), ".sarf")
QURAN_FILE = os.path.join(SARF_HOME, "quran-morphology.txt")
QURAN_TERMS_FILE = os.path.join(SARF_HOME, "morphology-terms-ar.json")


@lru_cache(maxsize=1)
def _quran():
    """{(سورة، آية، كلمة): [(الصورة، النوع، [السمات])...]} + فهرس الجذور."""
    import json
    words, roots = {}, {}
    with open(QURAN_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            s, a, w, _seg = (int(x) for x in parts[0].split(":"))
            feats = parts[3].split("|")
            words.setdefault((s, a, w), []).append((parts[1], parts[2], feats))
            for ft in feats:
                if ft.startswith("ROOT:"):
                    roots.setdefault(ft[5:], []).append((s, a, w))
    with open(QURAN_TERMS_FILE, encoding="utf-8") as f:
        terms = json.load(f)
    return words, roots, terms


def _q_person(code: str, t: dict) -> str:
    pa = t["pronoun_attrs"]
    return " ".join(pa.get(c, c) for c in code)


def _q_segment(form: str, coarse: str, feats: list, t: dict) -> dict:
    d = {"الصورة": form}
    kinds = []
    for ft in feats:
        key, _, val = ft.partition(":")
        if key == "ROOT":
            d["الجذر"] = " ".join(val)
        elif key == "LEM":
            d["الصيغة"] = val
        elif key == "VF":
            forms = t["verb_forms_tri"]
            d["باب الفعل"] = forms[int(val) - 1] if val.isdigit() and 0 < int(val) <= len(forms) else val
        elif key == "MOOD":
            d["الإعراب"] = t["verb_grammar"].get(val, val)
        elif key == "FAM":
            d["العائلة"] = t["FAM"].get(val, val)
        elif ft in ("PREF", "SUFF"):
            d["الموقع"] = "سابقة" if ft == "PREF" else "لاحقة"
        elif coarse == "P" and ft in t["particles"]:
            kinds.append(t["particles"][ft])
        elif ft == "DET":
            kinds.append("أداة التعريف")
        elif ft in t["types"]:
            kinds.append(t["types"][ft])
        elif ft in t["noun_forms"]:
            kinds.append(t["noun_forms"][ft])
        elif ft in t["verb_tenses"]:
            kinds.append("فعل " + t["verb_tenses"][ft])
        elif ft in t["noun_grammar"]:
            d["الإعراب"] = t["noun_grammar"][ft]
        elif ft in t["attrs"]:
            d.setdefault("سمات", []).append(t["attrs"][ft])
        elif ft and all(c in "123MFSDP" for c in ft):
            d["الشخص والعدد"] = _q_person(ft, t)
    if not kinds:
        kinds.append({"N": "اسم", "V": "فعل", "P": "حرف"}.get(coarse, coarse))
    d["النوع"] = "، ".join(kinds)
    return d


def _q_ref(ref: str):
    nums = [int(x) for x in ref.replace("：", ":").replace(" ", "").split(":") if x.strip().isdigit()]
    return nums


@mcp.tool()
def quran_word(ref: str) -> dict:
    """التحليل الصرفي لكلمات آية أو كلمة في القرآن من «المدوّنة القرآنية»: لكل جزء من الكلمة نوعه وجذره وصيغته ووزن بابه وإعرابه وسماته، بلا إنترنت.
    ref: «سورة:آية» مثل «2:255»، أو «سورة:آية:كلمة» مثل «1:5:2» لكلمة واحدة."""
    if not os.path.exists(QURAN_FILE):
        return {"تنبيه": "بيانات المدوّنة القرآنية غير منزّلة؛ شغّل سكربت التثبيت مرة أخرى."}
    words, _, t = _quran()
    nums = _q_ref(ref)
    if len(nums) < 2:
        return {"تنبيه": "اكتب المرجع بصورة سورة:آية، مثل 2:255."}
    s, a = nums[0], nums[1]
    keys = sorted(k for k in words if k[0] == s and k[1] == a and (len(nums) < 3 or k[2] == nums[2]))
    if not keys:
        return {"تنبيه": "لم أجد هذا الموضع."}
    out = []
    for k in keys:
        segs = words[k]
        out.append({
            "الموضع": f"{k[0]}:{k[1]}:{k[2]}",
            "الكلمة": "".join(f for f, _, _ in segs),
            "الأجزاء": [_q_segment(f, c, ft, t) for f, c, ft in segs],
        })
    return {"الآية": f"{s}:{a}", "النص": " ".join(w["الكلمة"] for w in out), "الكلمات": out,
            "المصدر": "Quranic Arabic Corpus 0.4 بتصحيحات mustafa0x/quran-morphology (GPL)"}


@mcp.tool()
def quran_root(root: str, lemma: str | None = None, limit: int = 30) -> dict:
    """مواضع جذر في القرآن من «المدوّنة القرآنية»: عدد ورود الجذر، وصيغه (المداخل) بعدد كل منها، ومواضع وروده بالكلمة، بلا إنترنت.
    root: الجذر بحروفه، مثل «كتب» أو «ك ت ب» (المهموز بالهمزة: «أمن»، والمعتل بحرفه الأصلي: «قول»، «هدي»).
    lemma: لتقييد المواضع بصيغة بعينها من صيغ الجذر، مثل «كِتاب».
    limit: عدد المواضع المعروضة (الحد 300)."""
    if not os.path.exists(QURAN_FILE):
        return {"تنبيه": "بيانات المدوّنة القرآنية غير منزّلة؛ شغّل سكربت التثبيت مرة أخرى."}
    words, roots, t = _quran()
    r = _strip_tashkeel(root).replace(" ", "").replace(".", "")
    cands = [r, r.replace("ا", "أ"), r.replace("أ", "ا"), r.replace("ى", "ي"), r.replace("ء", "أ")]
    key = next((c for c in cands if c in roots), None)
    if not key:
        return {"تنبيه": f"لم يرد الجذر «{root}» في المدوّنة القرآنية.", "جُرِّب": sorted(set(cands))}
    locs = roots[key]

    def lem_of(k):
        for f, c, ft in words[k]:
            if any(x == "ROOT:" + key for x in ft):
                return next((x[4:] for x in ft if x.startswith("LEM:")), None)

    counts = {}
    for k in locs:
        counts[lem_of(k)] = counts.get(lem_of(k), 0) + 1
    if lemma:
        lm = _strip_tashkeel(lemma)
        locs = [k for k in locs if _strip_tashkeel(lem_of(k) or "") == lm]
    limit = max(1, min(int(limit), 300))
    return {
        "الجذر": " ".join(key),
        "عدد الورود": len(roots[key]),
        "الصيغ": sorted(({"الصيغة": l, "العدد": n} for l, n in counts.items()), key=lambda x: -x["العدد"]),
        "المواضع": [{"الموضع": f"{k[0]}:{k[1]}:{k[2]}", "الكلمة": "".join(f for f, _, _ in words[k])}
                    for k in locs[:limit]],
        "المعروض": f"{min(limit, len(locs))} من {len(locs)}",
    }


# ───────────── المعاجم التراثية بلا إنترنت (نصوص OpenITI) ─────────────

MAAJIM_DB = os.path.join(os.path.expanduser("~"), ".sarf", "maajim.db")


def _mk(s: str) -> str:
    """تطبيع مفتاح الجذر كما في فهرس المعاجم."""
    import re
    s = _strip_tashkeel(s or "").replace("ٰ", "")
    s = re.sub("[أإآؤئ]", "ء", s).replace("ى", "ي").replace("ة", "ه")
    return re.sub("[^ء-ي]", "", s)


def _root_variants(root: str) -> list:
    k = _mk(root)
    out = [k]
    if k.startswith("ا"):
        out.append("ء" + k[1:])
    if k.startswith("ء"):
        out.append("ا" + k[1:])
    if len(k) == 3:
        last = k[-1]
        alts = {"ا": "وي", "ي": "اوء", "و": "ايء", "ء": "اوي"}.get(last, "")
        out += [k[:-1] + a for a in alts]
        mid = k[1]
        if mid in "اوي":
            out += [k[0] + m + k[2] for m in "اوي" if m != mid]
    seen, res = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            res.append(v)
    return res


def _excerpt_from(text: str, variants: list, max_chars: int):
    """يبدأ النص من أول سطر تُذكر المادة في أوله؛ ويعيد None إن لم تُذكر."""
    import re
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        for w in re.findall("[\u0621-\u064a\u064b-\u0652]+", ln)[:3]:
            if _mk(w) in variants or _mk(w).removeprefix("ال") in variants:
                return "\n".join(lines[i:])[:max_chars]
    return None


@mcp.tool()
def maajim(root: str, books: list[str] | None = None, max_chars_per_entry: int = 3000) -> dict:
    """مادة الجذر من 15 معجمًا تراثيًّا بلا إنترنت، مرتبةً زمنيًّا مع الجزء والصفحة (ترقيم المطبوع كما في الشاملة):
    العين، الجمهرة، التهذيب، الصحاح، مقاييس اللغة، مجمل اللغة، المحكم، المفردات، أساس البلاغة، النهاية، مختار الصحاح، لسان العرب، المصباح المنير، القاموس المحيط، تاج العروس.
    root: الجذر (كتب، أمن، قول، دعو) أو بحروف مفرّقة (ك ت ب).
    books: لتقييد المعاجم بجزء من أسمائها، مثل ["لسان", "مقاييس", "العين"].
    max_chars_per_entry: الحد الأقصى لنص كل مادة (مواد اللسان والتاج قد تتجاوز عشرين ألف حرف).
    النصوص من مشروع OpenITI بلا تشكيل في الغالب؛ وفي أبواب التقاليب (العين والجمهرة والمحكم) يبدأ النص من موضع المادة داخل الباب."""
    import sqlite3
    if not os.path.exists(MAAJIM_DB):
        return {"تنبيه": "فهرس المعاجم لم يُبنَ بعد؛ شغّل سكربت التثبيت مرة أخرى."}
    variants = _root_variants(root)
    sorted_key = "~" + "".join(sorted(variants[0]))
    con = sqlite3.connect(f"file:{MAAJIM_DB}?mode=ro", uri=True)
    book_rows = con.execute("SELECT id, name, died FROM books ORDER BY died").fetchall()
    if books:
        book_rows = [b for b in book_rows if any(x in b[1] or x == b[0] for x in books)]
    entries, missing = [], []
    ph = ",".join("?" * len(variants))
    for bid, name, died in book_rows:
        rows = con.execute(
            f"SELECT DISTINCT u.id, u.title, u.kind, u.vol, u.page, u.text FROM keys k JOIN units u ON u.id = k.unit "
            f"WHERE u.book = ? AND k.key IN ({ph}) ORDER BY u.id LIMIT 2", [bid] + variants).fetchall()
        match = "مباشرة"
        picked = []
        for r in rows:
            body = _excerpt_from(r[5], variants, max_chars_per_entry) if r[2] == "taqalib" else r[5][:max_chars_per_entry]
            if body:
                picked.append((r, body))
        if not picked:
            match = "باب التقاليب"
            cands = con.execute(
                "SELECT DISTINCT u.id, u.title, u.kind, u.vol, u.page, u.text FROM keys k JOIN units u ON u.id = k.unit "
                "WHERE u.book = ? AND k.key = ? ORDER BY u.id LIMIT 12", (bid, sorted_key)).fetchall()
            for r in cands:
                body = _excerpt_from(r[5], variants, max_chars_per_entry)
                if body:
                    picked.append((r, body))
                    break
        if not picked:
            missing.append(name)
            continue
        for (_id, title, kind, vol, page, text), body in picked:
            if len(text) > max_chars_per_entry and len(body) >= max_chars_per_entry:
                body += " …[مقطوع]"
            entries.append({
                "المعجم": f"{name} (ت {died}هـ)",
                "الموضع": f"ج{vol} ص{page}" if vol else None,
                "العنوان": title,
                "المطابقة": match,
                "النص": body,
            })
    con.close()
    return {"المادة": " ".join(variants[0]), "المواد": entries,
            "لم توجد في": missing,
            "المصدر": "نصوص OpenITI المأخوذة من الشاملة؛ الموضع بترقيم المطبوع كما ورد فيها."}


# ───────────── الدلالة: نموذج CAMeLBERT للعربية الكلاسيكية ─────────────

CA_MODEL = "CAMeL-Lab/bert-base-arabic-camelbert-ca"
VOCAB_EMB = os.path.join(os.path.expanduser("~"), ".sarf", "ca_vocab_emb_v2.npz")


@lru_cache(maxsize=1)
def _ca():
    import torch
    from transformers import AutoTokenizer, AutoModelForMaskedLM
    tok = AutoTokenizer.from_pretrained(CA_MODEL)
    model = AutoModelForMaskedLM.from_pretrained(CA_MODEL, output_hidden_states=True)
    model.eval()
    torch.set_grad_enabled(False)
    return tok, model


def _embed(texts: list, targets: list | None = None):
    """متجه لكل نص (أو للكلمة المستهدفة داخله): متوسط آخر أربع طبقات لأجزاء الكلمة."""
    import torch
    tok, model = _ca()
    enc = tok([_strip_tashkeel(t) for t in texts], return_tensors="pt", padding=True, truncation=True, max_length=128)
    out = model(**enc).hidden_states
    h = torch.stack(out[-4:]).mean(0)  # [batch, seq, 768]
    vecs = []
    for i in range(len(texts)):
        ids = enc["input_ids"][i].tolist()
        mask = [j for j, t in enumerate(ids) if t not in (tok.cls_token_id, tok.sep_token_id, tok.pad_token_id)]
        if targets and targets[i]:
            sub = tok(_strip_tashkeel(targets[i]), add_special_tokens=False)["input_ids"]
            for s in range(len(ids) - len(sub) + 1):
                if ids[s:s + len(sub)] == sub:
                    mask = list(range(s, s + len(sub)))
                    break
        v = h[i, mask].mean(0)
        vecs.append(v / v.norm())
    return torch.stack(vecs)


@mcp.tool()
def word_similarity(word1: str, word2: str, sentence1: str | None = None, sentence2: str | None = None) -> dict:
    """مقدار التقارب الدلالي بين كلمتين (من -1 إلى 1) بنموذج CAMeLBERT المدرَّب على العربية الكلاسيكية.
    إن أُعطيت جملتان قِيس معنى كل كلمة في سياق جملتها (مفيد للتمييز بين معاني المشترك اللفظي، كـ«العين» الباصرة والجارية)."""
    t1, t2 = sentence1 or word1, sentence2 or word2
    v = _embed([t1, t2], [word1 if sentence1 else None, word2 if sentence2 else None])
    score = float(v[0] @ v[1])
    return {"الكلمتان": [word1, word2], "التقارب": round(score, 3),
            "بالسياق": bool(sentence1 or sentence2),
            "ملاحظة": "القيمة نسبية: تُقارن بقيم أزواج أخرى من الحقل نفسه لا تُقرأ وحدها."}


@mcp.tool()
def substitutes_in_context(sentence: str, word: str, k: int = 15) -> dict:
    """ما يصلح أن يحلّ محلّ الكلمة في سياق جملتها بحسب نموذج العربية الكلاسيكية: يكشف الحقل الدلالي والمترادفات السياقية والمتقابلات.
    sentence: الجملة أو البيت. word: الكلمة المراد استبدالها كما وردت فيه. k: عدد الاقتراحات (الحد 50)."""
    import torch
    tok, model = _ca()
    s, w = _strip_tashkeel(sentence), _strip_tashkeel(word)
    words = s.split()
    if w not in words:
        return {"تنبيه": "لم أجد الكلمة في الجملة بعد تجريدها من التشكيل؛ انسخها كما وردت."}
    idx = words.index(w)
    masked = " ".join(words[:idx] + [tok.mask_token] + words[idx + 1:])
    enc = tok(masked, return_tensors="pt", truncation=True, max_length=128)
    logits = model(**enc).logits[0]
    pos = (enc["input_ids"][0] == tok.mask_token_id).nonzero()[0].item()
    probs = torch.softmax(logits[pos], -1)
    top = torch.topk(probs, min(int(k), 50) * 3)
    out = []
    for p, i in zip(top.values.tolist(), top.indices.tolist()):
        t = tok.convert_ids_to_tokens(i)
        if t.startswith("##") or not any("ء" <= c <= "ي" for c in t) or len(t) < 2:
            continue
        out.append({"الكلمة": t, "الاحتمال": round(p, 4)})
        if len(out) >= int(k):
            break
    return {"الجملة": sentence, "الكلمة": word, "البدائل": out}


def build_vocab_embeddings(batch: int = 256):
    """يحسب متجهات مفردات النموذج مرة واحدة (بضع دقائق) لأداة semantic_neighbors."""
    import numpy as np
    tok, _ = _ca()
    vocab = [t for t in tok.get_vocab() if not t.startswith("##") and len(t) >= 2
             and all("ء" <= c <= "ي" for c in t)]
    vecs = []
    for i in range(0, len(vocab), batch):
        vecs.append(_embed(vocab[i:i + batch]).numpy().astype("float16"))
        print(f"\r{min(i + batch, len(vocab)):,}/{len(vocab):,}", end="", flush=True)
    M = np.concatenate(vecs).astype("float32")
    # إزالة الاتجاه المشترك بين المتجهات (متجهات BERT متقاربة كلها بلا ذلك)
    mean = M.mean(0)
    M = M - mean
    M /= np.linalg.norm(M, axis=1, keepdims=True)
    os.makedirs(os.path.dirname(VOCAB_EMB), exist_ok=True)
    np.savez_compressed(VOCAB_EMB, words=np.array(vocab), vecs=M.astype("float16"), mean=mean)
    print("\nتم:", VOCAB_EMB)


@lru_cache(maxsize=1)
def _vocab_matrix():
    import numpy as np
    d = np.load(VOCAB_EMB)
    return list(d["words"]), d["vecs"].astype("float32"), d["mean"].astype("float32")


@mcp.tool()
def semantic_neighbors(word: str, k: int = 20) -> dict:
    """أقرب الكلمات دلاليًّا إلى كلمة (خارج السياق) من مفردات نموذج العربية الكلاسيكية: لاستكشاف الحقل الدلالي.
    word: الكلمة. k: عدد الجيران (الحد 100). النتائج تقريبية تجمع المرادف والمقابل وما يشاركه السياق."""
    if not os.path.exists(VOCAB_EMB):
        return {"تنبيه": "متجهات المفردات لم تُحسب بعد؛ شغّل سكربت التثبيت مرة أخرى."}
    import numpy as np
    words, M, mean = _vocab_matrix()
    q = _embed([word]).numpy()[0].astype("float32") - mean
    q /= np.linalg.norm(q)
    sims = M @ q
    w = _strip_tashkeel(word)
    order = np.argsort(-sims)
    out = []
    for i in order:
        if words[i] == w:
            continue
        out.append({"الكلمة": str(words[i]), "التقارب": round(float(sims[i]), 3)})
        if len(out) >= min(int(k), 100):
            break
    return {"الكلمة": word, "الجيران": out}


# ───────────── المدوّنة التراثية للتحليل الحاسوبي ─────────────

CORPUS_DB = os.path.join(os.path.expanduser("~"), ".sarf", "corpus.db")
_PROCLITICS = ["", "و", "ف", "ب", "ك", "ل"]
_AL_PROCLITICS = ["وال", "فال", "بال", "كال"]
STOPWORDS = set("""في من على الى إلى عن ان أن إن ما لا لم لن قد ثم او أو و ف ب ك ل هو هي هم هما هن انت أنت انا أنا نحن
كان كانت يكون قال قالت يقال قيل اي أي ذلك ذلك هذا هذه هؤلاء الذي التي الذين اللذين ما من مع بين حتى اذا إذا لو لولا
كل بعض غير عند منه منها فيه فيها عليه عليها اليه إليه له لها به بها عنه انه أنه انها أنها ولا وما ومن وفي وهو وهي فقال
وقال ابن ابو أبو بن بنت عبد الله يا وقد فلما لما كما الا إلا وان وإن فان فإن فما ولو فلا ليس لكن بل اذ إذ ولم فلم فقد
وذلك وهذا وهذه فهذا فذلك هذان هاتان ذا تلك وكذلك كذلك ايضا أيضا نحو قوله قول وكان فكان فيكون يكون وكل وليس او""".split())
STOPWORDS = {_norm(w) for w in STOPWORDS}


def _cn(s: str) -> str:
    return _norm(s)


def _variants(word: str, clitics: bool) -> list:
    w = _cn(word).strip()
    if not clitics:
        return [w]
    vs = {p + w for p in _PROCLITICS if not (p == "ل" and w.startswith("ال"))}
    if w.startswith("ال"):
        vs |= {p + w[2:] for p in _AL_PROCLITICS} | {"لل" + w[2:]}
    return sorted(vs)


def _corpus_filter(genre, century_from, century_to, book):
    where, args = [], []
    if genre:
        where.append("b.genre = ?")
        args.append(genre)
    if century_from:
        where.append("b.died > ?")
        args.append((int(century_from) - 1) * 100)
    if century_to:
        where.append("b.died <= ?")
        args.append(int(century_to) * 100)
    if book:
        where.append("(b.title LIKE ? OR b.author LIKE ?)")
        args += [f"%{book}%", f"%{book}%"]
    return where, args


def _corpus_rows(word, clitics, genre, century_from, century_to, book, cap):
    import sqlite3
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    vs = _variants(word, clitics)
    match = " OR ".join(f'"{v}"' for v in vs)
    where, args = _corpus_filter(genre, century_from, century_to, book)
    sql = ("SELECT p.id, p.text, p.vol, p.page, b.title, b.died, b.genre, b.id FROM paras p JOIN books b ON b.id = p.book "
           "WHERE p.id IN (SELECT rowid FROM paras_fts WHERE paras_fts MATCH ?)"
           + (" AND " + " AND ".join(where) if where else "") + " ORDER BY b.died, p.id LIMIT ?")
    rows = con.execute(sql, [match] + args + [cap]).fetchall()
    return con, set(vs), rows


@mcp.tool()
def corpus_concordance(word: str, genre: str | None = None, century_from: int | None = None,
                       century_to: int | None = None, book: str | None = None, clitics: bool = True,
                       window: int = 8, limit: int = 30) -> dict:
    """سياقات الكلمة في المدوّنة التراثية (57 كتابًا، نحو 12 مليون كلمة، من سيبويه إلى البغدادي) بطريقة KWIC: ما قبلها وما بعدها، مع الكتاب والجزء والصفحة.
    genre: «نحو» أو «لغة» أو «بلاغة» أو «شعر» أو «أدب». century_from / century_to: القرن الهجري (مثل 2 إلى 5).
    book: جزء من عنوان الكتاب أو اسم مؤلفه («المغني»، «الجاحظ»). clitics: يشمل الكلمة بسوابقها (و، ف، ب، ك، ل، وال...).
    window: عدد الكلمات في كل جانب. limit: عدد السياقات (الحد 200)."""
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد؛ شغّل سكربت التثبيت مرة أخرى."}
    limit = max(1, min(int(limit), 200))
    con, vs, rows = _corpus_rows(word, clitics, genre, century_from, century_to, book, limit * 3)
    con.close()
    out = []
    for _pid, text, vol, page, title, died, g, _bid in rows:
        toks = text.split()
        for i, t in enumerate(toks):
            if _cn(t).strip(".,،؛:!?()[]«»\"'") in vs:
                out.append({
                    "قبل": " ".join(toks[max(0, i - window):i]),
                    "الكلمة": t,
                    "بعد": " ".join(toks[i + 1:i + 1 + window]),
                    "المصدر": f"{title} (ت {died}هـ)" + (f"، ج{vol} ص{page}" if vol else ""),
                    "الفن": g,
                })
                break
        if len(out) >= limit:
            break
    return {"الكلمة": word, "الصيغ المبحوث عنها": sorted(vs), "السياقات": out,
            "ملاحظة": "مرتبة بوفاة المؤلف؛ سياق واحد من كل فقرة. النصوص من OpenITI بلا تشكيل في الغالب."}


@mcp.tool()
def corpus_usage(word: str, genre: str | None = None, clitics: bool = True) -> dict:
    """تطوّر استعمال اللفظ عبر القرون في المدوّنة التراثية: عدد وروده في كل قرن هجري، ونسبته إلى كل مليون كلمة من نصوص ذلك القرن، وتوزّعه على الفنون والكتب الأكثر استعمالًا له."""
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد؛ شغّل سكربت التثبيت مرة أخرى."}
    con, vs, rows = _corpus_rows(word, clitics, genre, None, None, None, 200000)
    totals = {}
    for died, g, n in con.execute("SELECT died, genre, tokens FROM books" + (" WHERE genre = ?" if genre else ""),
                                  [genre] if genre else []):
        c = (died - 1) // 100 + 1
        totals[c] = totals.get(c, 0) + n
    by_c, by_g, by_b = {}, {}, {}
    for _pid, text, _v, _p, title, died, g, _bid in rows:
        n = sum(1 for t in text.split() if _cn(t).strip(".,،؛:!?()[]«»\"'") in vs)
        c = (died - 1) // 100 + 1
        by_c[c] = by_c.get(c, 0) + n
        by_g[g] = by_g.get(g, 0) + n
        by_b[f"{title} (ت {died}هـ)"] = by_b.get(f"{title} (ت {died}هـ)", 0) + n
    con.close()
    return {
        "الكلمة": word,
        "مجموع الورود": sum(by_c.values()),
        "بحسب القرن": [{"القرن": c, "الورود": by_c.get(c, 0), "لكل مليون كلمة": round(by_c.get(c, 0) * 1e6 / totals[c], 1),
                        "حجم نصوص القرن": totals[c]} for c in sorted(totals)],
        "بحسب الفن": by_g,
        "أكثر الكتب استعمالًا": sorted(({"الكتاب": k, "الورود": v} for k, v in by_b.items()), key=lambda x: -x["الورود"])[:10],
        "تنبيه": "المدوّنة مختارة لا شاملة، وتفاوت أحجام القرون فيها يجعل النسبة لكل مليون أدقّ من العدد المجرد.",
    }


@mcp.tool()
def corpus_collocates(word: str, window: int = 4, genre: str | None = None, top: int = 30,
                      min_count: int = 3, clitics: bool = True) -> dict:
    """المتلازمات اللفظية: الألفاظ التي تكثر مجاورتها للكلمة في المدوّنة التراثية أكثر مما يُتوقّع من شيوعها العام، مرتبة بمقياس الاقتران (Log-likelihood) مع عدد مرات المجاورة ومقياس PMI.
    window: مدى المجاورة بالكلمات في كل جانب. genre: لتقييدها بفن. min_count: أقل عدد للمجاورة."""
    import math
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد؛ شغّل سكربت التثبيت مرة أخرى."}
    con, vs, rows = _corpus_rows(word, clitics, genre, None, None, None, 30000)
    co, node = {}, 0
    for _pid, text, *_ in rows:
        toks = [_cn(t).strip(".,،؛:!?()[]«»\"'") for t in text.split()]
        for i, t in enumerate(toks):
            if t in vs:
                node += 1
                for j in range(max(0, i - window), min(len(toks), i + window + 1)):
                    if j != i and toks[j] and toks[j] not in vs and toks[j] not in STOPWORDS and len(toks[j]) > 1:
                        co[toks[j]] = co.get(toks[j], 0) + 1
    N = con.execute("SELECT SUM(tokens) FROM books").fetchone()[0]
    cands = [(w, n) for w, n in co.items() if n >= min_count]
    freqs = {}
    for i in range(0, len(cands), 500):
        chunk = [w for w, _ in cands[i:i + 500]]
        q = ",".join("?" * len(chunk))
        freqs.update(dict(con.execute(f"SELECT token, n FROM freq WHERE token IN ({q})", chunk).fetchall()))
    con.close()
    span = max(1, node * 2 * window)
    res = []
    for w, a in cands:
        f = freqs.get(w, a)
        e = span * f / N  # المتوقع
        b, c = span - a, f - a
        d = max(N - span - c, 1)
        ll = 2 * sum(o * math.log(o / ex) for o, ex in
                     ((a, e), (b, span - e), (c, f - e), (d, N - span - f + e)) if o > 0 and ex > 0)
        if a > e:
            res.append({"اللفظ": w, "المجاورة": a, "شيوعه العام": f, "LL": round(ll, 1), "PMI": round(math.log2(a / e), 2)})
    res.sort(key=lambda x: -x["LL"])
    return {"الكلمة": word, "مرات ورودها": node, "المتلازمات": res[:max(1, min(int(top), 100))],
            "ملاحظة": "حُذفت حروف المعاني والألفاظ الشائعة؛ واللفظ يُعدّ بصورته (دون تجريد السوابق)."}


# ───────────── تقطيع القصيدة وتحليل النص ─────────────

def _merge_tashkeel(orig: str, auto: str) -> str:
    """يُبقي تشكيل الأصل، ويملأ الحروف غير المشكولة من التشكيل الآلي (كلمةً كلمة)."""
    def split(w):
        out = []
        for ch in w:
            if ch in HARAKAT and out:
                out[-1][1] += ch
            elif ch not in HARAKAT:
                out.append([ch, ""])
        return out
    ow, aw = orig.split(), auto.split()
    if len(ow) != len(aw):
        return orig
    res = []
    for o, a in zip(ow, aw):
        so, sa = split(o), split(a)
        if [c for c, _ in so] != [c for c, _ in sa]:
            res.append(o)
            continue
        res.append("".join(c + (m or am) for (c, m), (_, am) in zip(so, sa)))
    return " ".join(res)


def _prepare_verse_text(text: str):
    """يعيد (النص المهيأ، ملاحظة) بحسب نسبة التشكيل: آليّ كامل، أو ملء الناقص، أو كما هو."""
    letters = sum(1 for c in text if "ء" <= c <= "ي")
    marks = sum(1 for c in text if c in HARAKAT)
    ratio = marks / letters if letters else 0
    if ratio < 0.3:
        return _diacritize(text), "البيت غير مشكول فشُكِّل آليًّا."
    if ratio < 0.85:
        try:
            return _merge_tashkeel(text, _diacritize(_strip_tashkeel(text))), "التشكيل ناقص فأُكمل آليًّا مع إبقاء ضبط الأصل."
        except Exception:
            return text, None
    return text, None


@mcp.tool()
def scan_poem(poem: str, meter: str | None = None, auto_diacritize: bool = True) -> dict:
    """تقطيع قصيدة كاملة: البحر الغالب، والرويّ الغالب، وحال كل بيت (موزون أو مختل، ونسبة مطابقته)، مع التنبيه على الأبيات التي خرجت عن البحر أو الروي.
    poem: الأبيات سطرًا سطرًا، وكل بيت «الصدر * العجز»؛ أو الصدر والعجز في سطرين متتاليين.
    meter: لفرض بحر بعينه بالإنجليزية (taweel, kamel...) عند الحاجة."""
    import pyarud
    lines = [l.strip() for l in poem.strip().splitlines() if l.strip()]
    verses = []
    if all(("*" in l or "..." in l) for l in lines):
        for l in lines:
            s, _, a = l.replace("...", "*").partition("*")
            verses.append((s.strip(), a.strip()))
    else:
        for i in range(0, len(lines), 2):
            verses.append((lines[i], lines[i + 1] if i + 1 < len(lines) else ""))
    notes = set()
    prepared = []
    for s, a in verses:
        if auto_diacritize:
            s2, n1 = _prepare_verse_text(s)
            a2, n2 = _prepare_verse_text(a) if a else (a, None)
            notes |= {n for n in (n1, n2) if n}
            prepared.append((s2, a2))
        else:
            prepared.append((s, a))
    r = pyarud.analyze_poem(prepared, forced_meter=meter) if meter else pyarud.analyze_poem(prepared)
    rows, odd = [], []
    for i, (v, (s, a)) in enumerate(zip(r.verses, verses), 1):
        rawi = v.qafiyah.rawi if v.qafiyah else None
        row = {"البيت": i, "النص": f"{s} * {a}" if a else s, "البحر": v.meter_name_ar,
               "موزون": v.is_valid, "المطابقة": round(v.score, 2), "الروي": rawi}
        if not v.is_valid:
            row["الخلل"] = [str(e) for e in v.errors][:2]
        rows.append(row)
        if v.meter_name_ar != r.meter_name_ar or not v.is_valid or (rawi and r.dominant_rawi and rawi != r.dominant_rawi):
            odd.append(i)
    out = {"البحر الغالب": r.meter_name_ar, "الروي الغالب": r.dominant_rawi, "عدد الأبيات": r.total_verses,
           "الموزون منها": r.valid_verses_count, "متجانسة البحر": r.is_homogeneous,
           "أبيات تستحق المراجعة": odd, "الأبيات": rows}
    if notes:
        out["تنبيه"] = " ".join(sorted(notes)) + " راجع الضبط في الأبيات المختلة قبل الحكم عليها."
    return out


@mcp.tool()
def text_profile(text: str | None = None, poet: str | None = None, top: int = 25, max_verses: int = 20000) -> dict:
    """تحليل معجمي لنص أو لشعر شاعر كامل من مدوّنة «أشعار»: عدد الكلمات وأنواعها وثراء المعجم (نسبة الأنواع إلى الرموز والكلمات المفردة الورود)، والجذور والمداخل والأوزان الأكثر ورودًا، وتوزّع أقسام الكلم.
    text: النص المراد تحليله. أو poet: اسم الشاعر (جزء منه) لتحليل ما في المدوّنة من شعره.
    top: عدد العناصر في كل قائمة. max_verses: الحد الأعلى للأبيات المأخوذة من شعر الشاعر."""
    import re, sqlite3
    from collections import Counter
    source = None
    if poet:
        if not os.path.exists(POETRY_DB):
            return {"تنبيه": "فهرس الشعر لم يُبنَ بعد."}
        con = sqlite3.connect(f"file:{POETRY_DB}?mode=ro", uri=True)
        poets = con.execute("SELECT poet, COUNT(*) FROM poems WHERE poet_n LIKE ? GROUP BY poet ORDER BY 2 DESC",
                            (f"%{_norm(poet)}%",)).fetchall()
        if not poets:
            return {"تنبيه": f"لم أجد شاعرًا باسم «{poet}» في المدوّنة."}
        name = poets[0][0]
        rows = con.execute("SELECT v.sadr, v.ajuz FROM verses v JOIN poems p ON p.id = v.poem_id WHERE p.poet = ? LIMIT ?",
                           (name, int(max_verses))).fetchall()
        con.close()
        text = "\n".join(f"{s} {a}" for s, a in rows)
        source = {"الشاعر": name, "عدد الأبيات المحللة": len(rows),
                  "شعراء آخرون بالاسم نفسه": [p for p, _ in poets[1:6]]}
    if not text:
        return {"تنبيه": "أعطِ نصًّا أو اسم شاعر."}
    toks = re.findall("[ء-يً-ْ]+", text)
    bare = [_strip_tashkeel(t) for t in toks]
    counts = Counter(bare)
    an = _analyzer()
    roots, lemmas, patterns, pos = Counter(), Counter(), Counter(), Counter()
    for w, n in counts.items():
        anal = an.analyze(w)
        if not anal:
            continue
        a = max(anal, key=lambda x: float(x.get("pos_lex_logprob", -99) or -99))
        p = POS.get(a.get("pos"), a.get("pos"))
        pos[p] += n
        r = a.get("root") or ""
        if r and "#" not in r and a.get("pos") in ("noun", "adj", "verb", "adj_comp", "noun_num"):
            roots[r.replace(".", " ")] += n
            lemmas[(a.get("lex") or "").split("-")[0].split("_")[0]] += n
            patterns[_stem_wazn(a)] += n
    content = Counter({w: n for w, n in counts.items() if _norm(w) not in STOPWORDS and len(w) > 2})
    N, V = len(bare), len(counts)
    hapax = sum(1 for n in counts.values() if n == 1)
    k = max(1, min(int(top), 100))
    out = {
        "الكلمات": N, "الأنواع (الكلمات المختلفة)": V,
        "نسبة الأنواع إلى الكلمات": round(V / N, 3) if N else 0,
        "المفردة الورود (hapax)": hapax,
        "أكثر الألفاظ": [{"اللفظ": w, "العدد": n} for w, n in content.most_common(k)],
        "أكثر الجذور": [{"الجذر": r, "العدد": n} for r, n in roots.most_common(k)],
        "أكثر المداخل": [{"المدخل": l, "العدد": n} for l, n in lemmas.most_common(k)],
        "أكثر الأوزان": [{"الوزن": p, "العدد": n} for p, n in patterns.most_common(k)],
        "أقسام الكلم": dict(pos.most_common()),
        "ملاحظة": "التحليل الصرفي بلا سياق (أرجح تحليل لكل كلمة منفردة)، فالأرقام تقريبية؛ ونسبة الأنواع تتأثر بطول النص فلا تُقارن إلا بين نصوص متقاربة الطول.",
    }
    if source:
        out = {**source, **out}
    return out



# ───────────── الموازنة بين نصّين أو شاعرين أو كتابين ─────────────

def _load_poet(poet: str, max_verses: int):
    import sqlite3
    if not os.path.exists(POETRY_DB):
        return None, {"تنبيه": "فهرس الشعر لم يُبنَ بعد."}
    con = sqlite3.connect(f"file:{POETRY_DB}?mode=ro", uri=True)
    poets = con.execute("SELECT poet, COUNT(*) FROM poems WHERE poet_n LIKE ? GROUP BY poet ORDER BY 2 DESC",
                        (f"%{_norm(poet)}%",)).fetchall()
    if not poets:
        con.close()
        return None, {"تنبيه": f"لم أجد شاعرًا باسم «{poet}» في مدوّنة الشعر."}
    name = poets[0][0]
    rows = con.execute("SELECT v.sadr, v.ajuz FROM verses v JOIN poems p ON p.id = v.poem_id WHERE p.poet = ? LIMIT ?",
                       (name, int(max_verses))).fetchall()
    con.close()
    return "\n".join(f"{s} {a}" for s, a in rows), {"الشاعر": name, "الأبيات": len(rows)}


def _load_corpus_book(book: str, max_words: int):
    import sqlite3
    if not os.path.exists(CORPUS_DB):
        return None, {"تنبيه": "المدوّنة لم تُبنَ بعد."}
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    b = con.execute("SELECT id, title, author, died, tokens FROM books WHERE uri = ? OR title LIKE ? OR author LIKE ? "
                    "ORDER BY (uri = ?) DESC, tokens DESC LIMIT 1", (book, f"%{book}%", f"%{book}%", book)).fetchone()
    if not b:
        con.close()
        return None, {"تنبيه": f"لم أجد في المدوّنة كتابًا يطابق «{book}». استعمل corpus_find_book ثم corpus_add_book لإضافته."}
    parts, n = [], 0
    for (t,) in con.execute("SELECT text FROM paras WHERE book = ? ORDER BY id", (b[0],)):
        parts.append(t)
        n += len(t.split())
        if n >= max_words:
            break
    con.close()
    return "\n".join(parts), {"الكتاب": f"{b[1]} لـ{_short_author(b[2])} (ت {b[3]}هـ)", "الكلمات المأخوذة": min(n, b[4] or n),
                              "حجم الكتاب": b[4]}


def _ll(a, b, c, d):
    """Log-likelihood (Rayson) ونسبة اللوغاريتم (Hardie) لكلمة وردت a مرة في نص حجمه c، وb مرة في نص حجمه d."""
    import math
    e1 = c * (a + b) / (c + d)
    e2 = d * (a + b) / (c + d)
    ll = 2 * ((a * math.log(a / e1) if a else 0) + (b * math.log(b / e2) if b else 0))
    lr = math.log2(((a + 0.5) / c) / ((b + 0.5) / d))
    return ll, lr


def _sttr(tokens, chunk=1000):
    """نسبة الأنواع المعيارية: متوسط نسبة الأنواع في كل ألف كلمة، فتصلح للموازنة بين نصّين مختلفي الطول."""
    vals = [len(set(tokens[i:i + chunk])) / chunk for i in range(0, len(tokens) - chunk + 1, chunk)]
    if not vals:
        return round(len(set(tokens)) / len(tokens), 3) if tokens else 0
    return round(sum(vals) / len(vals), 3)


def _side_stats(text: str, max_types: int = 30000):
    import re
    from collections import Counter
    toks = [_norm(_strip_tashkeel(t)) for t in re.findall("[ء-يً-ْٰ]+", text)]
    toks = [t for t in toks if t]
    counts = Counter(toks)
    an = _analyzer()
    roots, pats, lemmas = Counter(), Counter(), Counter()
    for w, n in counts.most_common(max_types):
        anal = an.analyze(w)
        if not anal:
            continue
        a = max(anal, key=lambda x: float(x.get("pos_lex_logprob", -99) or -99))
        r = a.get("root") or ""
        if r and "#" not in r and a.get("pos") in ("noun", "adj", "verb", "adj_comp", "noun_num"):
            roots[r.replace(".", " ")] += n
            pats[_stem_wazn(a)] += n
            lemmas[(a.get("lex") or "").split("-")[0].split("_")[0]] += n
    return toks, counts, roots, pats, lemmas


def _keyness(ca, cb, na, nb, min_freq, top, label, filt=None):
    res_a, res_b = [], []
    for w in set(ca) | set(cb):
        if filt and not filt(w):
            continue
        a, b = ca.get(w, 0), cb.get(w, 0)
        if a + b < min_freq:
            continue
        ll, lr = _ll(a, b, na, nb)
        if ll < 10.83:  # دلالة إحصائية p < 0.001
            continue
        row = {label: w, "في الأول": a, "في الثاني": b,
               "لكل عشرة آلاف (الأول/الثاني)": f"{a * 1e4 / na:.1f} / {b * 1e4 / nb:.1f}",
               "LL": round(ll, 1), "Log ratio": round(lr, 2)}
        (res_a if lr > 0 else res_b).append(row)
    res_a.sort(key=lambda x: -x["LL"])
    res_b.sort(key=lambda x: -x["LL"])
    return res_a[:top], res_b[:top]


@mcp.tool()
def compare_texts(text_a: str | None = None, text_b: str | None = None,
                  poet_a: str | None = None, poet_b: str | None = None,
                  book_a: str | None = None, book_b: str | None = None,
                  top: int = 25, min_freq: int = 5, max_words: int = 300000) -> dict:
    """الموازنة الأسلوبية بين نصّين: كل جانب نصٌّ مُعطى (text_a / text_b)، أو شعرُ شاعر من مدوّنة «أشعار» (poet_a / poet_b)، أو كتابٌ من المدوّنة التراثية (book_a / book_b: جزء من العنوان أو اسم المؤلف)؛ ويجوز الخلط (شاعر مقابل كتاب، ونحوه).
    تُخرج: الألفاظ التي يختص بها كل جانب بمقياس الإبانة الإحصائية (Log-likelihood مع نسبة اللوغاريتم)، والجذور والأوزان المميِّزة لكل منهما، والمعجم المشترك الأكثر دورانًا فيهما، ونسبة التداخل بين المعجمين، وثراء المعجم بمقياس معياري لا يتأثر بطول النص.
    min_freq: أقل مجموع ورود في النصّين لاعتبار اللفظ. max_words: حدّ ما يؤخذ من الكتاب؛ max_verses للشاعر عشرون ألف بيت."""
    sides = []
    for t, p, b in ((text_a, poet_a, book_a), (text_b, poet_b, book_b)):
        if p:
            txt, info = _load_poet(p, 20000)
        elif b:
            txt, info = _load_corpus_book(b, int(max_words))
        elif t:
            txt, info = t, {"نص": f"{len(t.split())} كلمة"}
        else:
            return {"تنبيه": "أعطِ لكل جانب نصًّا أو شاعرًا أو كتابًا."}
        if txt is None:
            return info
        sides.append((txt, info))
    (ta, ia), (tb, ib) = sides
    toks_a, ca, ra, pa, la = _side_stats(ta)
    toks_b, cb, rb, pb, lb = _side_stats(tb)
    na, nb = len(toks_a), len(toks_b)
    if not na or not nb:
        return {"تنبيه": "أحد النصّين خالٍ من الكلمات العربية."}
    k = max(1, min(int(top), 100))
    mf = max(1, int(min_freq))
    if min(na, nb) < 3000:
        mf = min(mf, 3)
    content = lambda w: w not in STOPWORDS and len(w) > 2
    wa, wb = _keyness(ca, cb, na, nb, mf, k, "اللفظ", content)
    ra_k, rb_k = _keyness(ra, rb, sum(ra.values()) or 1, sum(rb.values()) or 1, mf, k, "الجذر")
    pa_k, pb_k = _keyness(pa, pb, sum(pa.values()) or 1, sum(pb.values()) or 1, mf, min(k, 15), "الوزن")
    shared = [w for w in set(ca) & set(cb) if content(w)]
    shared.sort(key=lambda w: -min(ca[w] / na, cb[w] / nb))
    types_a, types_b = {w for w in ca if content(w)}, {w for w in cb if content(w)}
    inter = len(types_a & types_b)
    roots_inter = len(set(ra) & set(rb))
    return {
        "الأول": ia, "الثاني": ib,
        "الحجم": {"كلمات الأول": na, "كلمات الثاني": nb},
        "ثراء المعجم (نسبة الأنواع المعيارية لكل ألف كلمة)": {"الأول": _sttr(toks_a), "الثاني": _sttr(toks_b)},
        "التداخل المعجمي": {
            "ألفاظ مشتركة": inter, "يختص بها الأول": len(types_a - types_b), "يختص بها الثاني": len(types_b - types_a),
            "معامل جاكار للألفاظ": round(inter / len(types_a | types_b), 3) if types_a | types_b else 0,
            "جذور مشتركة": roots_inter,
            "معامل جاكار للجذور": round(roots_inter / len(set(ra) | set(rb)), 3) if ra or rb else 0,
        },
        "ألفاظ يختص بها الأول": wa, "ألفاظ يختص بها الثاني": wb,
        "جذور يختص بها الأول": ra_k, "جذور يختص بها الثاني": rb_k,
        "أوزان يكثر منها الأول": pa_k, "أوزان يكثر منها الثاني": pb_k,
        "المعجم المشترك الأكثر دورانًا": [{"اللفظ": w, "في الأول": ca[w], "في الثاني": cb[w]} for w in shared[:k]],
        "منهج": "اللفظ يُوحَّد رسمه (الهمزات والتاء المربوطة والألف المقصورة) دون تجريد سوابقه؛ والجذر والوزن بأرجح تحليل صرفي بلا سياق. "
                "LL ≥ 10.83 دالّ عند 0.001، وكلما عظم كان الاختصاص أبين؛ وLog ratio موجبه للأول وسالبه للثاني، وكل وحدة فيه مضاعفة للنسبة. "
                "وأرقام الكتب الطويلة من أوائلها إلى حدّ max_words.",
    }


# ───────────── إضافة كتب OpenITI إلى المدوّنة ─────────────

_GENRE_TAGS = [("_NAHW", "نحو"), ("_SARF", "نحو"), ("_BALAGHA", "بلاغة"), ("_SHICR", "شعر"), ("_GHARIB", "لغة"),
               ("_LUGHA", "لغة"), ("_MACAJIM", "لغة"), ("_ADAB", "أدب"), ("_TAFSIR", "تفسير"), ("_QURAN", "علوم القرآن"),
               ("_HADITH", "حديث"), ("_FIQH", "فقه"), ("_USUL", "أصول"), ("_TARIKH", "تاريخ"), ("_TARAJIM", "تراجم"),
               ("_TABAQAT", "تراجم"), ("_SIRA", "سيرة"), ("_CAQAID", "عقائد"), ("_BULDAN", "بلدان")]


@lru_cache(maxsize=1)
def _openiti_catalog():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, "openiti_catalog.tsv"), os.path.join(SARF_HOME, "openiti_catalog.tsv")):
        if os.path.exists(p):
            rows = []
            with open(p, encoding="utf-8") as f:
                for line in f:
                    c = line.rstrip("\n").split("\t")
                    if len(c) >= 7:
                        rows.append({"uri": c[0], "died": c[1], "author": c[2], "title": c[3], "tokens": c[4],
                                     "repo": c[5], "path": c[6], "tags": c[7] if len(c) > 7 else "",
                                     "_s": _norm(f"{c[3]} {c[2]}") + " " + c[0].lower()})
            return rows
    return []


def _corpus_uris():
    import sqlite3
    if not os.path.exists(CORPUS_DB):
        return {}
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    d = {u: (t, n, g) for u, t, n, g in con.execute("SELECT uri, title, tokens, genre FROM books")}
    con.close()
    return d


def _short_author(a: str) -> str:
    import re
    return re.sub(r"\s*\(المتوفى.*?(\)|$)", "", a).strip()


@mcp.tool()
def corpus_find_book(query: str | None = None, limit: int = 15) -> dict:
    """البحث في فهرس OpenITI (نحو 8800 كتاب عربي تراثي) بعنوان الكتاب أو اسم مؤلفه أو بعضهما، قبل إضافته إلى المدوّنة بأداة corpus_add_book.
    يُظهر لكل كتاب: معرّفه (URI)، والمؤلف ووفاته، وحجمه بالكلمات، وفنّه، وهل هو في المدوّنة الآن.
    إن تُرك query فارغًا عرضت الأداة كتب المدوّنة الحالية وأحجامها."""
    have = _corpus_uris()
    if not query:
        return {"كتب المدوّنة": [{"المعرّف": u, "العنوان": t, "الكلمات": n, "الفن": g} for u, (t, n, g) in sorted(have.items())],
                "العدد": len(have), "مجموع الكلمات": sum(n for _t, n, _g in have.values())}
    cat = _openiti_catalog()
    if not cat:
        return {"تنبيه": "فهرس OpenITI (openiti_catalog.tsv) غير موجود بجانب الخادم؛ أعد تشغيل سكربت التثبيت."}
    words = [_norm(w) for w in query.split()]
    words = [w[2:] if w.startswith("ال") and len(w) > 4 else w for w in words]
    hits = [r for r in cat if all(w.lower() in r["_s"] for w in words)]
    hits.sort(key=lambda r: (not any(_norm(query) in _norm(r["title"]) for _ in [0]), r["died"]))
    out = [{"المعرّف": r["uri"], "العنوان": r["title"], "المؤلف": _short_author(r["author"]), "الوفاة": int(r["died"]),
            "الكلمات": int(r["tokens"] or 0), "الفن": next((g for t, g in _GENRE_TAGS if t in r["tags"]), None),
            "في المدوّنة": r["uri"] in have} for r in hits[:max(1, min(int(limit), 50))]]
    return {"النتائج": out, "عدد المطابقات": len(hits),
            "ملاحظة": "أضف ما تريد بـ corpus_add_book ممرّرًا المعرّف. العناوين من بيانات OpenITI وقد تختلف عن المشهور."}


@mcp.tool()
def corpus_add_book(book: str, genre: str | None = None) -> dict:
    """إضافة كتاب من OpenITI إلى المدوّنة التراثية (فيصبح متاحًا لأدوات corpus_concordance وcorpus_usage وcorpus_collocates وcompare_texts).
    book: معرّف الكتاب (مثل 0354Mutanabbi.Diwan) أو عنوانه إن كان لا يطابق إلا كتابًا واحدًا؛ ابحث أولًا بـ corpus_find_book.
    genre: الفن الذي يُنسب إليه في المدوّنة (نحو، لغة، بلاغة، شعر، أدب، تفسير، حديث...)؛ إن تُرك استُنتج من وسوم OpenITI.
    يُنزَّل النص من GitHub (يلزم الإنترنت مرة واحدة)، ويُفهرس على الجهاز."""
    import sqlite3, sys, tempfile
    from collections import Counter
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد؛ شغّل سكربت التثبيت مرة أخرى."}
    cat = _openiti_catalog()
    if not cat:
        return {"تنبيه": "فهرس OpenITI غير موجود بجانب الخادم؛ أعد تشغيل سكربت التثبيت."}
    cands = [r for r in cat if r["uri"].lower() == book.strip().lower()]
    if not cands:
        q = _norm(book)
        cands = [r for r in cat if _norm(r["title"]) == q] or [r for r in cat if q in _norm(r["title"])]
    if not cands:
        return {"تنبيه": f"لم أجد «{book}» في فهرس OpenITI.", "اقتراح": "ابحث بكلمة من العنوان أو اسم المؤلف عبر corpus_find_book."}
    if len(cands) > 1:
        return {"تنبيه": "الاسم يطابق أكثر من كتاب؛ أعد الطلب بالمعرّف.",
                "المرشحات": [{"المعرّف": r["uri"], "العنوان": r["title"], "المؤلف": _short_author(r["author"])} for r in cands[:15]]}
    r = cands[0]
    if r["uri"] in _corpus_uris():
        return {"تنبيه": f"«{r['title']}» في المدوّنة من قبل."}
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import build_corpus_index as bci
    g = genre or next((gg for t, gg in _GENRE_TAGS if t in r["tags"]), "أخرى")
    tmpdir = tempfile.mkdtemp(prefix="sarf_")
    local = os.path.join(tmpdir, os.path.basename(r["path"]))
    try:
        bci.download(r["repo"], r["path"], local)
        meta, paras = bci.parse(local)
    except Exception as e:
        return {"تنبيه": f"تعذّر تنزيل الكتاب: {e!r}. تحقق من الاتصال بالإنترنت."}
    finally:
        try:
            os.remove(local)
            os.rmdir(tmpdir)
        except OSError:
            pass
    if not paras:
        return {"تنبيه": "الملف المنزّل خالٍ من النص."}
    con = sqlite3.connect(CORPUS_DB, timeout=30)
    try:
        bid = (con.execute("SELECT MAX(id) FROM books").fetchone()[0] or 0) + 1
        pid = con.execute("SELECT MAX(id) FROM paras").fetchone()[0] or 0
        title, ntok, counts, _ = bci.insert_book(con, bid, pid, g, r["uri"], meta, paras,
                                                 title_hint=r["title"], author_hint=_short_author(r["author"]))
        con.executemany("INSERT INTO freq(token, n) VALUES (?, ?) ON CONFLICT(token) DO UPDATE SET n = n + excluded.n",
                        counts.items())
        con.commit()
    except Exception as e:
        con.rollback()
        return {"تنبيه": f"تعذّرت الفهرسة: {e!r}"}
    finally:
        con.close()
    total = sum(n for _t, n, _g in _corpus_uris().values())
    return {"أُضيف": title, "المؤلف": _short_author(r["author"]), "الوفاة": int(r["died"]), "الفن": g,
            "الكلمات": ntok, "الفقرات": len(paras), "حجم المدوّنة الآن": total}


@mcp.tool()
def corpus_remove_book(book: str) -> dict:
    """حذف كتاب من المدوّنة التراثية بمعرّفه (URI) كما يظهر في corpus_find_book بلا مُدخل. لا يمسّ ملفات أخرى."""
    import sqlite3, re
    from collections import Counter
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد."}
    con = sqlite3.connect(CORPUS_DB, timeout=30)
    row = con.execute("SELECT id, title FROM books WHERE uri = ?", (book.strip(),)).fetchone()
    if not row:
        con.close()
        return {"تنبيه": f"لا يوجد في المدوّنة كتاب بالمعرّف «{book}». اعرض الكتب بـ corpus_find_book بلا مُدخل."}
    bid, title = row
    counts = Counter()
    tr = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "ء", "ئ": "ء"})
    har = re.compile("[ً-ْـٰ]")
    for pid, text in con.execute("SELECT id, text FROM paras WHERE book = ?", (bid,)).fetchall():
        n = har.sub("", text).translate(tr)
        con.execute("INSERT INTO paras_fts(paras_fts, rowid, body) VALUES('delete', ?, ?)", (pid, n))
        counts.update(re.findall("[ء-ي]+", n))
    con.executemany("UPDATE freq SET n = n - ? WHERE token = ?", ((c, t) for t, c in counts.items()))
    con.execute("DELETE FROM freq WHERE n < 2")
    con.execute("DELETE FROM paras WHERE book = ?", (bid,))
    con.execute("DELETE FROM books WHERE id = ?", (bid,))
    con.commit()
    con.close()
    return {"حُذف": title, "الكلمات": sum(counts.values())}


# ───────────── الأصوات: المخارج والصفات والكتابة الصوتية والمقاطع ─────────────

# المخارج على مذهب ابن الجزري (17 مخرجًا في خمسة مواضع)، مع الوصف الصوتي الحديث
_MAKHRAJ = {
    "ء": ("الحلق", "أقصى الحلق", "حنجري (glottal)", "ʔ", "انفجاري"),
    "ه": ("الحلق", "أقصى الحلق", "حنجري (glottal)", "h", "احتكاكي"),
    "ع": ("الحلق", "وسط الحلق", "حلقي (pharyngeal)", "ʕ", "احتكاكي/تقريبي"),
    "ح": ("الحلق", "وسط الحلق", "حلقي (pharyngeal)", "ħ", "احتكاكي"),
    "غ": ("الحلق", "أدنى الحلق (مما يلي الفم)", "لهوي (uvular) أو طبقي خلفي", "ɣ", "احتكاكي"),
    "خ": ("الحلق", "أدنى الحلق (مما يلي الفم)", "لهوي (uvular) أو طبقي خلفي", "x", "احتكاكي"),
    "ق": ("اللسان", "أقصى اللسان مما يلي الحلق مع ما يحاذيه من الحنك الأعلى", "لهوي (uvular)", "q", "انفجاري"),
    "ك": ("اللسان", "أقصى اللسان أسفل من مخرج القاف قليلًا مع ما يحاذيه من الحنك الأعلى", "طبقي (velar)", "k", "انفجاري"),
    "ج": ("اللسان", "وسط اللسان مع ما يحاذيه من الحنك الأعلى", "غاري (palatal)/لثوي غاري", "d͡ʒ", "مركّب (انفجاري احتكاكي)"),
    "ش": ("اللسان", "وسط اللسان مع ما يحاذيه من الحنك الأعلى", "لثوي غاري (postalveolar)", "ʃ", "احتكاكي"),
    "ي": ("اللسان", "وسط اللسان مع ما يحاذيه من الحنك الأعلى (غير المدية)", "غاري (palatal)", "j", "تقريبي (شبه صائت)"),
    "ض": ("اللسان", "إحدى حافتي اللسان أو كلتاهما مع ما يحاذيها من الأضراس العليا", "أسناني لثوي مفخّم", "dˤ", "انفجاري (والقديم جانبي احتكاكي)"),
    "ل": ("اللسان", "أدنى حافتي اللسان إلى منتهى طرفه مع ما يحاذيها من لثة الأسنان العليا", "لثوي (alveolar)", "l", "جانبي"),
    "ن": ("اللسان", "طرف اللسان تحت مخرج اللام قليلًا", "لثوي (alveolar)", "n", "أنفي"),
    "ر": ("اللسان", "طرف اللسان مع ظهره قريبًا من مخرج النون", "لثوي (alveolar)", "r", "تكراري (مكرّر)"),
    "ط": ("اللسان", "طرف اللسان مع أصول الثنايا العليا (نِطْعية)", "أسناني لثوي مفخّم", "tˤ", "انفجاري"),
    "د": ("اللسان", "طرف اللسان مع أصول الثنايا العليا (نِطْعية)", "أسناني لثوي", "d", "انفجاري"),
    "ت": ("اللسان", "طرف اللسان مع أصول الثنايا العليا (نِطْعية)", "أسناني لثوي", "t", "انفجاري"),
    "ص": ("اللسان", "طرف اللسان مع ما فوق الثنايا السفلى (أَسَلية)", "لثوي مفخّم", "sˤ", "احتكاكي (صفيري)"),
    "ز": ("اللسان", "طرف اللسان مع ما فوق الثنايا السفلى (أَسَلية)", "لثوي", "z", "احتكاكي (صفيري)"),
    "س": ("اللسان", "طرف اللسان مع ما فوق الثنايا السفلى (أَسَلية)", "لثوي", "s", "احتكاكي (صفيري)"),
    "ظ": ("اللسان", "طرف اللسان مع أطراف الثنايا العليا (لِثَوية)", "بين أسناني مفخّم", "ðˤ", "احتكاكي"),
    "ذ": ("اللسان", "طرف اللسان مع أطراف الثنايا العليا (لِثَوية)", "بين أسناني (interdental)", "ð", "احتكاكي"),
    "ث": ("اللسان", "طرف اللسان مع أطراف الثنايا العليا (لِثَوية)", "بين أسناني (interdental)", "θ", "احتكاكي"),
    "ف": ("الشفتان", "باطن الشفة السفلى مع أطراف الثنايا العليا", "شفوي أسناني (labiodental)", "f", "احتكاكي"),
    "ب": ("الشفتان", "الشفتان معًا بانطباقهما", "شفوي (bilabial)", "b", "انفجاري"),
    "م": ("الشفتان", "الشفتان معًا بانطباقهما، والغنة من الخيشوم", "شفوي (bilabial)", "m", "أنفي"),
    "و": ("الشفتان", "الشفتان معًا بانفتاحهما (غير المدية)", "شفوي طبقي (labio-velar)", "w", "تقريبي (شبه صائت)"),
    "ا": ("الجوف", "الجوف (هوائي، ينتهي بانتهاء الهواء)", "صائت طويل مفتوح", "aː", "صائت"),
}
_SIFAT_GROUPS = [
    # (الصفة، ضدها، حروفها)
    ("الهمس", "الجهر", set("فحثهشخصسكت")),
    ("الشدة", None, set("ءأجدقطبكت")),
    ("التوسط (البينية)", None, set("لنعمر")),
    ("الاستعلاء", "الاستفال", set("خصضغطقظ")),
    ("الإطباق", "الانفتاح", set("صضطظ")),
    ("الإذلاق", "الإصمات", set("فرمنلب")),
]
_SIFAT_SINGLE = [
    ("الصفير", set("صزس")), ("القلقلة", set("قطبجد")), ("الانحراف", set("لر")), ("التكرير", set("ر")),
    ("التفشي", set("ش")), ("الاستطالة", set("ض")), ("الغنة", set("نم")),
    ("اللين (إذا سكنت بعد فتح)", set("وي")), ("المدّ (إذا سكنت بعد حركة تجانسها)", set("اوي")),
]


def _letter_sifat(ch):
    ch = "ء" if ch in "أإؤئآ" else ("ا" if ch in "ىٱ" else ("ت" if ch == "ة" else ch))
    out = []
    for name, opp, letters in _SIFAT_GROUPS:
        if ch in letters:
            out.append(name)
        elif opp:
            out.append(opp)
    if ch not in _SIFAT_GROUPS[1][2] and ch not in _SIFAT_GROUPS[2][2]:
        out.insert(1, "الرخاوة")
    out += [n for n, letters in _SIFAT_SINGLE if ch in letters]
    return ch, out


def _letter_info(ch):
    base, sifat = _letter_sifat(ch)
    if base not in _MAKHRAJ:
        return None
    area, mk, modern, ipa, manner = _MAKHRAJ[base]
    strong = sum(s in ("الجهر", "الشدة", "الاستعلاء", "الإطباق", "الصفير", "القلقلة", "الانحراف", "التكرير",
                       "التفشي", "الاستطالة", "الغنة") for s in sifat)
    return {"الحرف": base, "الموضع العام": area, "المخرج (ابن الجزري)": mk, "الوصف الحديث": modern,
            "IPA": ipa, "طريقة النطق": manner, "الصفات": sifat,
            "قوة الحرف (عدد صفات القوة)": strong}


@mcp.tool()
def huruf(letters: str) -> dict:
    """مخارج الحروف وصفاتها على مذهب علماء التجويد (ابن الجزري: سبعة عشر مخرجًا)، مع الوصف الصوتي الحديث ورمزها الصوتي الدولي (IPA).
    letters: حرف أو أكثر (مثل «ض» أو «ص س ز» أو كلمة). وإذا أُعطي حرفان بُيّن ما اتفقا فيه وما افترقا من المخرج والصفات (نافع في الإبدال والإدغام وتعليل التقارب الصوتي)."""
    seen, infos = set(), []
    for ch in letters:
        if ch in HARAKAT or ch.isspace():
            continue
        info = _letter_info(ch)
        if info and info["الحرف"] not in seen:
            seen.add(info["الحرف"])
            infos.append(info)
    if not infos:
        return {"تنبيه": "لم أجد حروفًا عربية في المُدخل."}
    out = {"الحروف": infos}
    if len(infos) == 2:
        a, b = infos
        sa, sb = set(a["الصفات"]), set(b["الصفات"])
        order = list(dict.fromkeys(v[1] for v in _MAKHRAJ.values()))
        ia, ib = order.index(a["المخرج (ابن الجزري)"]), order.index(b["المخرج (ابن الجزري)"])
        rel = ("متجانسان (اتحدا مخرجًا واختلفا صفة)" if ia == ib else
               "متقاربان مخرجًا" if abs(ia - ib) == 1 and a["الموضع العام"] == b["الموضع العام"] else
               "متقاربان صفةً (تباعد مخرجاهما)" if len(sa ^ sb) <= 2 else "متباعدان")
        out["الموازنة"] = {"العلاقة": rel, "صفات مشتركة": sorted(sa & sb),
                           f"ينفرد بها {a['الحرف']}": sorted(sa - sb), f"ينفرد بها {b['الحرف']}": sorted(sb - sa)}
    out["ملاحظة"] = ("الصفات بحسب كتب التجويد؛ وبعضها يخالف الوصف الحديث: فالطاء والقاف عند سيبويه مجهورتان وهما في النطق المعاصر مهموستان، "
                     "والضاد القديمة جانبية رخوة تخرج من حافة اللسان، والجيم عند القدماء شديدة.")
    return out


_SUN = set("تثدذرزسشصضطظلن")
_IPA = {"ء": "ʔ", "أ": "ʔ", "إ": "ʔ", "ؤ": "ʔ", "ئ": "ʔ", "ب": "b", "ت": "t", "ث": "θ", "ج": "d͡ʒ", "ح": "ħ",
        "خ": "x", "د": "d", "ذ": "ð", "ر": "r", "ز": "z", "س": "s", "ش": "ʃ", "ص": "sˤ", "ض": "dˤ", "ط": "tˤ",
        "ظ": "ðˤ", "ع": "ʕ", "غ": "ɣ", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h",
        "و": "w", "ي": "j", "ة": "t"}
_VOW = {"َ": "a", "ُ": "u", "ِ": "i"}
_TAN = {"ً": "a", "ٌ": "u", "ٍ": "i"}
_DAGGER = "ٰ"


def _hidden_alif(w: str) -> str:
    """يُثبت الألف المحذوفة رسمًا في ألفاظ مشهورة (هذا، ذلك، لكن، الله، إله، الرحمن...)."""
    import re
    if _DAGGER in w:
        return w
    b = _strip_tashkeel(w)
    if b in ("لله", "ولله", "فلله"):
        out, k = [], 0
        for i, ch in enumerate(w):
            out.append(ch)
            if ch not in HARAKAT:
                k += 1
            if k == len(b) - 1 and (i + 1 >= len(w) or w[i + 1] not in HARAKAT):
                out.append(_DAGGER); k += 1000
        return "".join(out)
    pre = re.match("^(?:[وف]?[بكل]?)", b).group(0)
    rest = b[len(pre):]
    # موضع الإدراج بعد الحرف رقم n من بقية الكلمة (بعد السوابق)
    rules = [("هذ", 1), ("هؤ", 1), ("ذلك", 1), ("لكن", 1), ("الله", 3), ("لله", 2), ("اله", 2), ("إله", 2),
             ("الرحمن", 5), ("رحمن", 4), ("السموات", 4), ("سموات", 3), ("أولئك", 0)]
    for start, n in rules:
        if rest.startswith(start) and n:
            if start in ("اله", "إله") and rest not in ("اله", "إله", "الها", "إلها", "الهكم", "إلهكم", "الهه", "إلهه", "الهي", "إلهي"):
                continue
            target = len(pre) + n  # عدد الحروف قبل موضع الإدراج
            out, k = [], 0
            for i, ch in enumerate(w):
                out.append(ch)
                if ch not in HARAKAT and ch != _DAGGER:
                    k += 1
                if k == target and (i + 1 >= len(w) or w[i + 1] not in HARAKAT):
                    out.append(_DAGGER)
                    k += 1000
            return "".join(out)
    return w


def _split_letters(w):
    out = []
    for ch in w:
        if (ch in HARAKAT or ch == _DAGGER) and out:
            out[-1][1] += ch
        elif ch not in HARAKAT and ch != _DAGGER and ch != "ـ":
            out.append([ch, ""])
    return out


def _word_phones(w: str, initial: bool, pausal: bool):
    """يحوّل كلمة مشكولة إلى قائمة أصوات: ('C', رمز) أو ('V', رمز، طويل؟)."""
    import re
    w = _hidden_alif(w)
    b = _strip_tashkeel(w).replace(_DAGGER, "")
    L = _split_letters(w)
    ph = []
    pre = re.match("^(?:[وف]?[بكل]?)", b).group(0)
    k0 = len(pre)
    novowel = lambda x: not any(c in _VOW for c in x[1])
    al_at = None
    if (k0 + 2 < len(L) and L[k0][0] in "اٱ" and not any(c in _VOW for c in L[k0][1])
            and L[k0 + 1][0] == "ل" and novowel(L[k0 + 1])):
        al_at = k0
    elif k0 and pre.endswith("ل") and k0 + 1 < len(L) and L[k0][0] == "ل" and novowel(L[k0]) and "ّ" not in L[k0][1]:
        al_at = k0 - 1  # لِلْ = لِ + الْ
    if b in ("أولئك", "اولئك", "أولو", "اولو", "أولي", "اولي", "أولات", "اولات"):
        L = [x for i, x in enumerate(L) if not (i == 1 and x[0] == "و")]
    if b.endswith("رو") and b in ("عمرو",):
        L = L[:-1]

    def vowel(v, long=False):
        ph.append(("V", v + ("ː" if long else ""), long))

    def last_v():
        return ph[-1] if ph and ph[-1][0] == "V" else None

    n = len(L)
    for i, (ch, m) in enumerate(L):
        final = i == n - 1
        v = next((_VOW[c] for c in m if c in _VOW), None)
        tan = next((_TAN[c] for c in m if c in _TAN), None)
        shadda = "ّ" in m
        sukun = "ْ" in m
        dag = _DAGGER in m
        if ch == "ا" and i == 0 and v and al_at != 0:  # همزة قطع لم تُرسم
            ph.append(("C", "ʔ")); vowel(v)
            continue
        if ch in "اٱ" and i == 0:  # همزة الوصل
            if initial:
                ph.append(("C", "ʔ"))
                if v:
                    vowel(v)
                elif al_at == 0 or (n > 1 and L[1][0] == "ل" and al_at is not None):
                    vowel("a")
                else:
                    third = L[2][1] if n > 2 else ""
                    vowel("u" if "ُ" in third else "i")
            continue
        if ch == "ا" and al_at is not None and i == al_at:  # ألف «ال» بعد حرف جر أو عطف
            if initial and i == 0:
                ph.append(("C", "ʔ")); vowel("a")
            continue
        if ch == "ل" and al_at is not None and i == al_at + 1 and i + 1 < n and L[i + 1][0] in _SUN and not v:
            continue  # اللام الشمسية
        if ch == "آ":
            ph.append(("C", "ʔ")); vowel("a", True)
            continue
        if ch in "اى" and not v and not tan:
            lv = last_v()
            if ch == "ا" and i > 0 and L[i - 1][0] == "و" and final and not L[i - 1][1].strip("ْ"):
                continue  # الألف الفارقة
            if ch == "ا" and i > 0 and any(c in "ً" for c in L[i - 1][1]):
                continue  # ألف تنوين النصب
            if lv and not lv[2]:
                ph[-1] = ("V", "aː", True)
            elif not lv:
                vowel("a", True)
            continue
        if ch in "وي" and not v and not shadda and not tan:
            lv = last_v()
            if lv and not lv[2] and lv[1] == ("u" if ch == "و" else "i"):
                ph[-1] = ("V", lv[1] + "ː", True)
                continue
        if ch == "ة" and final and pausal:
            ph.append(("C", "h"))
            continue
        c = _IPA.get(ch)
        if not c:
            continue
        ph.append(("C", c))
        sun_gem = (al_at is not None and i == al_at + 2 and ch in _SUN and not shadda)
        if shadda or sun_gem:
            ph.append(("C", c))
        if dag:
            vowel("a", True)
            continue
        if final and pausal:
            if tan == "a" and ch != "ة":
                vowel("a", True)
            continue
        if v:
            vowel(v)
        elif tan:
            if pausal and tan == "a" and i == n - 2 and L[-1][0] in "اى":
                vowel("a", True)  # الوقف على تنوين النصب ألفًا
                break
            vowel(tan)
            ph.append(("C", "n"))
    return ph


def _join_phrase(words_ph):
    """يصل أصوات الكلمات: يحذف همزة الوصل في الدرج، ويقصّر المدّ قبل الساكنين، ويحرّك الساكن قبل الوصل."""
    out = []
    for k, (ph, wasl) in enumerate(words_ph):
        if out and ph and ph[0][0] == "C" and (len(ph) < 2 or ph[1][0] == "C"):
            # تبدأ بساكن بعد حذف همزة الوصل: التقاء الساكنين
            if out[-1][0] == "V" and out[-1][2]:
                out[-1] = ("V", out[-1][1].rstrip("ː"), False)
            elif out[-1][0] == "C":
                out.append(("V", "i", False))
        out += ph
    return out


def _syllabify(ph):
    sylls, cur = [], []
    for i, p in enumerate(ph):
        if p[0] == "C" and i + 1 < len(ph) and ph[i + 1][0] == "V" and cur:
            if any(x[0] == "V" for x in cur):
                sylls.append(cur)
                cur = []
        cur.append(p)
    if cur:
        if sylls and not any(x[0] == "V" for x in cur):
            sylls[-1] += cur
        else:
            sylls.append(cur)
    res = []
    for s in sylls:
        shape = "".join("C" if p[0] == "C" else ("VV" if p[2] else "V") for p in s)
        res.append(("".join(p[1] for p in s), shape))
    return res


_SYL_NAME = {"CV": "قصير مفتوح", "CVV": "طويل مفتوح", "CVC": "طويل مغلق", "CVVC": "مديد (طويل مغلق بصائت طويل)",
             "CVCC": "مديد (مغلق بساكنين)", "CVVCC": "بالغ الطول"}
_ARUD = {"CV": "/", "CVV": "/0", "CVC": "/0", "CVVC": "/00", "CVCC": "/00"}


def _stress(sylls):
    """النبر التقريبي في الفصحى المعاصرة: على الأخير إن كان مديدًا، وإلا على ما قبل الأخير إن كان طويلًا، وإلا على الثالث من الآخر."""
    if not sylls:
        return None
    n = len(sylls)
    if n == 1:
        return 0
    if sylls[-1][1] in ("CVVC", "CVCC", "CVVCC"):
        return n - 1
    if sylls[-2][1] != "CV" or n == 2:
        return n - 2
    return n - 3


@mcp.tool()
def phonetics(text: str, auto_diacritize: bool = True, pausal: bool = True) -> dict:
    """التحليل الصوتي للكلمة أو العبارة: كتابتها بالرموز الصوتية الدولية (IPA)، وتقطيعها إلى مقاطع (CV قصير، CVV وCVC طويلان، CVVC وCVCC مديدان) مع رموزها العروضية (/ و/0)، ومقطع النبر التقريبي في كل كلمة، وإحصاء أنواع المقاطع؛ مع مراعاة همزة الوصل واللام الشمسية والتنوين والوقف والألف المحذوفة رسمًا.
    text: كلمة أو عبارة أو بيت (يُستحسن مشكولًا). auto_diacritize: يُكمل التشكيل الناقص آليًّا. pausal: يقف على آخر العبارة بالسكون (وعلى تنوين النصب ألفًا والتاء المربوطة هاءً).
    ولمخارج الحروف وصفاتها استعمل أداة huruf."""
    import re
    note = None
    src = text.strip()
    if auto_diacritize:
        try:
            src, note = _prepare_verse_text(src)
            note = note.replace("البيت", "النص") if note else note
        except Exception as e:
            note = f"تعذّر التشكيل الآلي ({type(e).__name__})، فحُلّل النص كما هو."
    words = re.findall("[ء-يٱ" + "".join(HARAKAT) + _DAGGER + "ـ]+|[.،؛:!?؟*]", src)
    items, words_ph = [], []
    for idx, w in enumerate(words):
        if not re.search("[ء-يٱ]", w):
            continue
        nxt = words[idx + 1] if idx + 1 < len(words) else None
        is_last = nxt is None or not re.search("[ء-يٱ]", nxt)
        first = not words_ph or (idx > 0 and not re.search("[ء-يٱ]", words[idx - 1]))
        ph_ctx = _word_phones(w, initial=first, pausal=pausal and is_last)
        ph_iso = _word_phones(w, initial=True, pausal=True)
        s_iso = _syllabify(ph_iso)
        st = _stress(s_iso)
        items.append({"الكلمة": w, "IPA (منفردة موقوفًا عليها)": "/" + ".".join(
            ("ˈ" if i == st and len(s_iso) > 1 else "") + s for i, (s, _) in enumerate(s_iso)) + "/",
            "المقاطع": [{"المقطع": s, "النوع": sh, "الوصف": _SYL_NAME.get(sh, sh)} for s, sh in s_iso],
            "النبر": f"المقطع {len(s_iso) - st} من الآخر" if st is not None else None})
        if first and words_ph:
            words_ph.append(([("C", "‖")], False))
        words_ph.append((ph_ctx, False))
    if not items:
        return {"تنبيه": "لم أجد كلمات عربية."}
    # العبارة متصلة (الدرج)
    chunks, cur = [], []
    for ph, _ in words_ph:
        if ph == [("C", "‖")]:
            chunks.append(cur); cur = []
        else:
            cur.append((ph, False))
    chunks.append(cur)
    phrase_sylls, phrase_ipa = [], []
    for ch in chunks:
        joined = _join_phrase(ch)
        s = _syllabify(joined)
        phrase_sylls += s
        phrase_ipa.append(".".join(x for x, _ in s))
    from collections import Counter
    cnt = Counter(sh for _, sh in phrase_sylls)
    out = {
        "النص المشكول": src,
        "IPA (موصولًا)": "/" + " ‖ ".join(phrase_ipa) + "/",
        "المقاطع": " ".join(f"{s}({sh})" for s, sh in phrase_sylls),
        "الرموز العروضية": "".join(_ARUD.get(sh, "/0") for _, sh in phrase_sylls),
        "عدد المقاطع": len(phrase_sylls),
        "أنواع المقاطع": {f"{k} {_SYL_NAME.get(k, '')}": v for k, v in cnt.most_common()},
        "الكلمات": items,
        "ملاحظة": "الكتابة صوتية وظيفية (phonemic) بنطق الفصحى؛ والنبر تقريبي إذ لم يصفه القدماء. "
                  "والرموز العروضية: / متحرك، و0 ساكن.",
    }
    if note:
        out["تنبيه"] = note
    return out


if __name__ == "__main__":
    import sys
    if "--build-semantic" in sys.argv:
        build_vocab_embeddings()
        raise SystemExit
    secret = os.environ.get("SARF_SECRET")
    if secret:  # وضع الاستضافة: يعمل عبر الإنترنت على مسار سري
        import threading
        # تحميل المحلل ونموذج BERT في الخلفية حتى لا يتأخر أول طلب
        threading.Thread(target=lambda: (_analyzer(), _bert()), daemon=True).start()
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(os.environ.get("PORT", "7860")),
            streamable_http_path=f"/{secret}/mcp",
            stateless_http=True,
            json_response=True,
        )
    else:  # الوضع المحلي (Claude Desktop)
        mcp.run()
