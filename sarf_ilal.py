"""محرّك الميزان الصرفي والإعلال والإبدال (للثلاثي ومزيده).

يبني «الأصل» بوضع حروف الجذر في الوزن، ثم يطبّق قواعد الإعلال والإبدال والإدغام بالترتيب،
مسجّلًا كل خطوة بعبارة الصرفيين، حتى يبلغ الصورة المنطوقة. وتُستعمل القواعد نفسها
في الاتجاهين: لبيان أصل الكلمة وخطوات إعلالها (الميزان)، ولتوليد المشتقات القياسية.
"""

FATHA, DAMMA, KASRA, SUKUN, SHADDA = "َ", "ُ", "ِ", "ْ", "ّ"
TAN = {"ً": "an", "ٌ": "un", "ٍ": "in"}
V2M = {"a": FATHA, "u": DAMMA, "i": KASRA, "0": SUKUN, "": "", "an": "ً", "un": "ٌ", "in": "ٍ"}
M2V = {FATHA: "a", DAMMA: "u", KASRA: "i", SUKUN: "0"}
MADD_OF = {"a": "ا", "u": "و", "i": "ي"}
WEAK = "وي"
NAME = {"و": "الواو", "ي": "الياء", "ا": "الألف", "ء": "الهمزة", "ت": "التاء", "ط": "الطاء", "د": "الدال"}


class T:
    """حرف بحركته: c الحرف، v الحركة (a u i 0 an un in أو فارغ للمدّ)، sh الشدة، rad رقم الأصل (1-4) أو None للزائد."""
    __slots__ = ("c", "v", "sh", "rad")

    def __init__(self, c, v="", sh=False, rad=None):
        self.c, self.v, self.sh, self.rad = c, v, sh, rad

    def copy(self):
        return T(self.c, self.v, self.sh, self.rad)


_HZ = str.maketrans({"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء"})


def parse_wazn(wazn: str):
    """يحوّل الوزن المشكول (فَعَل، مَفْعُول، اِسْتَفْعَل...) إلى قالب: حروف زائدة ومواضع أصول."""
    out, rads = [], {"ف": 1, "ع": 2, "ل": 3}
    seen_l = 0
    for ch in wazn.replace("ٱ", "ا").translate(_HZ):
        if ch in (FATHA, DAMMA, KASRA, SUKUN) and out:
            out[-1].v = M2V[ch]
        elif ch in TAN and out:
            out[-1].v = TAN[ch]
        elif ch == SHADDA and out:
            out[-1].sh = True
        elif "ء" <= ch <= "ي":
            if ch in rads:
                r = rads[ch]
                if ch == "ل":
                    seen_l += 1
                    r = 3 if seen_l == 1 else 4
                out.append(T(ch, "", False, r))
            else:
                out.append(T(ch))
    return out


def fill(template, root):
    """الأصل: وضع حروف الجذر في القالب."""
    out = []
    for t in template:
        t = t.copy()
        if t.rad:
            if t.rad - 1 >= len(root):
                return None
            t.c = root[t.rad - 1].translate(_HZ)
        out.append(t)
    return out


def expand(tokens):
    """يفكّ الشدة إلى حرفين: الأول ساكن، والثاني بحركة الحرف."""
    out = []
    for t in tokens:
        if t.sh:
            a = T(t.c, "0", False, t.rad)
            b = T(t.c, t.v, False, t.rad)
            out += [a, b]
        else:
            out.append(t.copy())
    return out


def _hamza_seat(tokens, i):
    t = tokens[i]
    v = t.v
    prev = tokens[i - 1].v if i > 0 else None
    if i == 0:
        return "إ" if v == "i" else "أ"
    if i == len(tokens) - 1 or (i == len(tokens) - 2 and tokens[-1].c == "ة"):
        if prev in ("0", ""):
            return "ء"
        return {"a": "أ", "u": "ؤ", "i": "ئ"}.get(prev, "ء")
    if v == "i" or prev == "i" or (tokens[i - 1].c == "ي" and prev in ("0", "")):
        return "ئ"
    if v == "u" or prev == "u":
        return "ؤ" if prev != "i" else "ئ"
    if prev in ("0", "") and v == "a" and tokens[i - 1].c == "ا":
        return "ء"
    return "أ"


def render(tokens, final_maqsura_rad=None):
    """من الحروف إلى الرسم المشكول، مع الإدغام (شدة) ومقاعد الهمزة والألف المقصورة."""
    out = []
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        c = t.c
        if c == "ء":
            c = _hamza_seat(tokens, i)
            if c == "أ" and t.v == "a" and i + 1 < n and tokens[i + 1].c == "ا" and tokens[i + 1].v == "":
                out.append("آ")
                i += 2
                continue
        if i + 1 < n and tokens[i + 1].c == t.c and t.v == "0" and t.c not in "اى":
            nx = tokens[i + 1]
            out.append(t.c + SHADDA + V2M.get(nx.v, ""))
            i += 2
            continue
        if c == "ا" and i == n - 1 and t.rad == 3 and (final_maqsura_rad == "ي" or n > 3):
            c = "ى"
        v = t.v
        if v == "0" and i > 0 and ((c == "ي" and tokens[i - 1].v == "i") or (c == "و" and tokens[i - 1].v == "u")):
            v = ""  # حرف مدّ
        out.append(c + V2M.get(v, ""))
        i += 1
    s = "".join(out)
    return s


def bare(s: str) -> str:
    """للموازنة: حذف الحركات والشدة، وتوحيد الهمزات والألف المقصورة."""
    tr = str.maketrans({"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ءا", "ى": "ا", "ٱ": "ا"})
    return "".join(c for c in s if not ("ً" <= c <= "ْ") and c != "ٰ").translate(tr)


def shadda_profile(s: str) -> str:
    return "".join("1" if SHADDA in s[i:i + 3] else "" for i in range(0, 0))


# ───────────── القواعد ─────────────
# كل قاعدة: (tokens, ctx) ← (tokens الجديدة، العبارة) أو None

def r_hamzatan(tk, ctx):
    for i in range(len(tk) - 1):
        a, b = tk[i], tk[i + 1]
        if a.c == "ء" and b.c == "ء" and b.v == "0" and a.v in MADD_OF:
            nt = [x.copy() for x in tk]
            nt[i + 1] = T(MADD_OF[a.v], "", False, b.rad)
            return nt, f"اجتمعت همزتان في كلمة واحدة، الثانية ساكنة، فقُلبت الثانية حرف مدّ من جنس حركة الأولى ({MADD_OF[a.v]})"
    return None


def r_iftial(tk, ctx):
    """إبدال تاء الافتعال، وقلب فاء المثال تاءً فيه."""
    if ctx.get("form") != "VIII":
        return None
    for i in range(len(tk) - 1):
        f, t = tk[i], tk[i + 1]
        if f.rad == 1 and t.rad is None and t.c == "ت" and f.v == "0":
            nt = [x.copy() for x in tk]
            if f.c in WEAK:
                nt[i].c = "ت"
                return nt, f"وقعت فاء الافتعال {NAME[f.c]} ساكنة قبل تائه، فقُلبت تاءً وأُدغمت في تاء الافتعال"
            if f.c in "صضطظ":
                nt[i + 1].c = "ط"
                if f.c == "ط":
                    return nt, "قُلبت تاء الافتعال طاءً لمجاورتها الطاء، ثم أُدغمت الطاء في الطاء"
                return nt, f"قُلبت تاء الافتعال طاءً لمجاورتها حرف الإطباق ({f.c})"
            if f.c in "دذز":
                nt[i + 1].c = "د"
                if f.c == "د":
                    return nt, "قُلبت تاء الافتعال دالًا لمجاورتها الدال، ثم أُدغمت الدال في الدال"
                return nt, f"قُلبت تاء الافتعال دالًا لمجاورتها الحرف المجهور ({f.c})"
    return None


def r_mithal_mudari(tk, ctx):
    if ctx.get("pos") != "verb":
        return None
    if len(tk) > 2 and tk[0].rad is None and tk[0].c in "يتنأء" and tk[0].v == "a" and tk[1].rad == 1 and tk[1].c == "و" \
            and tk[1].v == "0" and tk[2].v == "i":
        nt = [tk[0].copy()] + [x.copy() for x in tk[2:]]
        return nt, "حُذفت فاء المثال (الواو) في المضارع لوقوعها بين حرف المضارعة المفتوح وكسرة العين"
    return None


def r_mithal_masdar(tk, ctx):
    """مصدر المثال الواوي على «فِعْلة»: تُحذف الفاء وتُنقل كسرتها إلى العين، وتُعوَّض عنها التاء (عِدَة، صِلَة، زِنَة، جِهَة).
    لا تعمل إلا حيث طُلبت (ctx «mithal_masdar»)، لأن من هذه المصادر ما جاء تامًّا أيضًا (وِجْهة)."""
    if not ctx.get("mithal_masdar"):
        return None
    if len(tk) == 4 and tk[0].rad == 1 and tk[0].c == "و" and tk[0].v == "i" and tk[1].rad == 2 and tk[1].v == "0" \
            and tk[2].rad == 3 and tk[3].c == "ة":
        nt = [x.copy() for x in tk[1:]]
        nt[0].v = "i"
        return nt, ("حُذفت فاء المثال (الواو) من المصدر على «فِعْلة» ونُقلت كسرتها إلى العين، "
                    "وعُوِّض عنها تاءُ التأنيث في آخره (كعِدَة وصِلَة وزِنَة)")
    return None


def r_naql(tk, ctx):
    """نقل حركة العين المعتلة إلى الساكن الصحيح قبلها؛ إلا أن تكون اللام معتلة أيضًا (اللفيف المقرون)،
    فإذا اجتمع حرفا علة عينًا ولامًا أُعلّت اللام وصحّت العين («مَأْوَى»، «طَوَى»)."""
    # اللام معتلة في أصلها، ولو قُلبت ألفًا قبل هذه القاعدة («مَأْوَيٌ» ← «مَأْوَى»)
    if ctx.get("no_naql") or any(t.rad == 3 and t.c in WEAK + "اى" for t in tk):
        return None
    for i in range(1, len(tk)):
        w, p = tk[i], tk[i - 1]
        if w.rad == 2 and w.c in WEAK and w.v in ("a", "u", "i") and p.v == "0" and p.c not in "اوي" and p.rad is not None:
            nxt = tk[i + 1] if i + 1 < len(tk) else None
            if nxt is not None and nxt.c == "ا" and nxt.rad is None and ctx.get("pos") != "verb" and ctx.get("pattern_kind") == "ala":
                return None
            nt = [x.copy() for x in tk]
            nt[i - 1].v = w.v
            expl = f"نُقلت حركة {NAME[w.c]} (عين الكلمة) إلى الساكن الصحيح قبلها ({p.c})"
            if w.v == "a":
                nt[i] = T("ا", "", False, w.rad)
                expl += f"، ثم قُلبت {NAME[w.c]} ألفًا لتحركها في الأصل وانفتاح ما قبلها الآن"
            elif (w.v == "u" and w.c == "و") or (w.v == "i" and w.c == "ي"):
                nt[i].v = ""
                expl += f"، فسكنت {NAME[w.c]} وصارت حرف مدّ"
            else:
                nt[i].v = "0"
            return nt, expl
    return None


def r_qalb_alif(tk, ctx):
    """تحركت الواو أو الياء وانفتح ما قبلها فقُلبت ألفًا."""
    idx = [i for i, t in enumerate(tk) if t.rad in (2, 3) and t.c in WEAK]
    both_weak = len([i for i in idx if tk[i].rad == 2]) and len([i for i in idx if tk[i].rad == 3])
    for i in sorted(idx, reverse=True):
        w = tk[i]
        if i == 0 or w.v not in ("a", "u", "i", "an", "un", "in", "") or tk[i - 1].v != "a":
            continue
        if w.v == "" and i != len(tk) - 1:
            continue
        if both_weak and w.rad == 2:
            continue  # اللفيف المقرون: تُعلّ اللام وحدها
        nxt = tk[i + 1] if i + 1 < len(tk) else None
        if nxt is not None and (nxt.c == "ا" or (nxt.c == "ي" and nxt.sh)):
            continue
        if nxt is not None and nxt.c in "اوي" and nxt.v in ("", "0") and w.rad == 2:
            continue  # صحّت العين لسكون ما بعدها (طَوِيل، غَيُور، بَيان)
        if ctx.get("pos") != "verb" and w.rad == 2 and (ctx.get("no_naql") or w.v != "a"):
            continue
        nt = [x.copy() for x in tk]
        tan = w.v if w.v in ("an", "un", "in") else ""
        nt[i] = T("ا", "", False, w.rad)
        expl = f"تحركت {NAME[w.c]} وانفتح ما قبلها فقُلبت ألفًا"
        if tan:
            nt[i - 1].v = "an"
            expl += "، ثم حُذفت الألف لالتقاء الساكنين (هي والتنوين) وبقي التنوين على ما قبلها"
            nt = nt[:i] + nt[i + 1:] if False else nt
        return nt, expl
    return None


def r_hamz_fail(tk, ctx):
    """العين المعتلة بعد ألف فاعل الزائدة تُقلب همزة (قاوِل ← قائِل)."""
    for i in range(1, len(tk)):
        w, p = tk[i], tk[i - 1]
        if w.rad == 2 and w.c in WEAK and p.c == "ا" and p.rad is None and w.v in ("i", "a", "u"):
            if ctx.get("pos") == "verb":
                return None
            nt = [x.copy() for x in tk]
            nt[i].c = "ء"
            return nt, f"وقعت {NAME[w.c]} عينًا بعد ألف زائدة في اسم أُعلّت عينه في فعله، فقُلبت همزة"
    return None


def r_hamz_tatarruf(tk, ctx):
    """تطرفت الواو أو الياء بعد ألف زائدة فقُلبت همزة (دُعاو ← دُعاء)."""
    n = len(tk)
    for i in range(1, n):
        w, p = tk[i], tk[i - 1]
        last = i == n - 1 or (i == n - 2 and tk[-1].c == "ة" and False)
        if w.rad == 3 and w.c in WEAK and p.c == "ا" and p.rad is None and last:
            nt = [x.copy() for x in tk]
            nt[i].c = "ء"
            return nt, f"تطرفت {NAME[w.c]} بعد ألف زائدة فقُلبت همزة"
    return None


def r_sakinayn_mafool(tk, ctx):
    """اسم المفعول من الأجوف: بعد النقل يلتقي ساكنان (العين وواو مفعول)، فتُحذف الواو الزائدة."""
    for i in range(len(tk) - 1):
        w, m = tk[i], tk[i + 1]
        if w.rad == 2 and w.c in WEAK and w.v in ("0", "") and m.rad is None and m.c == "و" and m.v in ("", "0"):
            nt = [x.copy() for x in tk[:i + 1]] + [x.copy() for x in tk[i + 2:]]
            expl = "التقى ساكنان (العين وواو مفعول)، فحُذفت واو مفعول الزائدة (على مذهب سيبويه، وعند الأخفش المحذوفة العين)"
            if w.c == "ي" and i > 0 and nt[i - 1].v == "u":
                nt[i - 1].v = "i"
                expl += "، ثم كُسر ما قبل الياء لتصحّ"
            nt[i].v = ""
            return nt, expl
    return None


def r_wy(tk, ctx):
    """اجتمعت الواو والياء وسبقت إحداهما بالسكون، فقُلبت الواو ياءً وأُدغمت."""
    for i in range(len(tk) - 1):
        a, b = tk[i], tk[i + 1]
        if {a.c, b.c} == {"و", "ي"} and a.v in ("0", "") and (a.rad or b.rad):
            nt = [x.copy() for x in tk]
            nt[i] = T("ي", "0", False, a.rad)
            nt[i + 1] = T("ي", b.v if b.v else "", False, b.rad)
            expl = "اجتمعت الواو والياء وسبقت إحداهما بالسكون، فقُلبت الواو ياءً وأُدغمت الياء في الياء"
            if i > 0 and nt[i - 1].v == "u":
                nt[i - 1].v = "i"
                expl += "، وكُسر ما قبلها لمناسبة الياء"
            return nt, expl
        if a.c == b.c and a.c in WEAK and a.v == "" and a.rad is None and b.rad == 3:
            nt = [x.copy() for x in tk]
            nt[i].v = "0"
            return nt, f"اجتمع مثلان أولهما ساكن ({NAME[a.c]} الزائدة ولام الكلمة)، فأُدغم الأول في الثاني"
    return None


def r_madd(tk, ctx):
    """الواو الساكنة بعد كسر تُقلب ياءً، والياء الساكنة بعد ضم تُقلب واوًا."""
    for i in range(1, len(tk)):
        w, p = tk[i], tk[i - 1]
        if w.rad and w.c in WEAK and w.v in ("0", ""):
            if i + 1 < len(tk) and tk[i + 1].c == w.c:
                continue
            if w.c == "و" and p.v == "i":
                nt = [x.copy() for x in tk]
                nt[i] = T("ي", "", False, w.rad)
                return nt, "سكنت الواو بعد كسرة فقُلبت ياءً"
            if w.c == "ي" and p.v == "u":
                nt = [x.copy() for x in tk]
                nt[i] = T("و", "", False, w.rad)
                return nt, "سكنت الياء بعد ضمة فقُلبت واوًا"
    return None


def r_naqis_kasra(tk, ctx):
    """تطرفت الواو بعد كسرة فقُلبت ياءً (داعِو ← داعِي)."""
    for i in range(1, len(tk)):
        w, p = tk[i], tk[i - 1]
        last = i == len(tk) - 1
        if w.rad == 3 and w.c == "و" and p.v == "i" and (last or (i == len(tk) - 2 and tk[-1].c == "ة")):
            nt = [x.copy() for x in tk]
            nt[i].c = "ي"
            return nt, "تطرفت الواو بعد كسرة فقُلبت ياءً"
    return None


def r_manqus_tanween(tk, ctx):
    """المنقوص المنوّن في الرفع والجر: تُحذف ياؤه لالتقاء الساكنين ويبقى التنوين على ما قبلها."""
    if len(tk) >= 2 and tk[-1].c == "ي" and tk[-1].rad == 3 and tk[-1].v in ("un", "in") and tk[-2].v == "i":
        nt = [x.copy() for x in tk[:-1]]
        nt[-1].v = "in"
        return nt, "استُثقلت الضمة (أو الكسرة) على الياء فحُذفت، ثم حُذفت الياء لالتقاء الساكنين (هي والتنوين)، وعُوّض عنها تنوين"
    return None


def r_idgham(tk, ctx):
    """إدغام المثلين: عين الكلمة ولامها من جنس واحد."""
    for i in range(len(tk) - 1):
        a, b = tk[i], tk[i + 1]
        if a.rad == 2 and b.rad == 3 and a.c == b.c:
            if a.v == "0":
                return None  # مدغم أصلًا
            if a.v in ("a", "u", "i") and b.v not in ("0",):
                p = tk[i - 1] if i > 0 else None
                if ctx.get("pos") != "verb" and p is not None and p.v in ("a", "u", "i") and p.rad == 1:
                    return None  # فَعَل الاسمي لا يُدغم (طَلَل، سَبَب)
                nt = [x.copy() for x in tk]
                if p is not None and p.v == "0" and p.c not in "اوي":
                    nt[i - 1].v = a.v
                    nt[i].v = "0"
                    return nt, "نُقلت حركة العين إلى الساكن قبلها، ثم أُدغمت العين في اللام لأنهما من جنس واحد"
                nt[i].v = "0"
                return nt, "سُكّنت العين وأُدغمت في اللام لأنهما من جنس واحد"
    return None


def r_ifala(tk, ctx):
    """مصدر أَفْعَل واسْتَفْعَل من الأجوف: إِقْوام ← إِقامَة."""
    if ctx.get("masdar_ifala") is None:
        return None
    for i in range(1, len(tk) - 1):
        w = tk[i]
        if w.rad == 2 and w.c in WEAK and tk[i + 1].c == "ا" and tk[i + 1].rad is None and tk[i - 1].v == "0":
            nt = [x.copy() for x in tk]
            nt[i - 1].v = "a"
            del nt[i]
            nt.append(T("ة", ""))
            if nt[-2].v in ("", "0"):
                nt[-2].v = "a"
            return nt, ("نُقلت حركة العين إلى الساكن قبلها، وقُلبت العين ألفًا، فالتقت ألفان فحُذفت إحداهما (العين عند الخليل وسيبويه، وألف المصدر عند الأخفش والفراء)"
                        "، وعُوّض عنها بتاء التأنيث في آخره")
    return None


KIND = {"r_hamzatan": "إبدال (الهمزة مدًّا)", "r_iftial": "إبدال", "r_mithal_mudari": "إعلال بالحذف", "r_ifala": "إعلال بالنقل والقلب والحذف مع التعويض",
        "r_mithal_masdar": "إعلال بالحذف مع التعويض",
        "r_naql": "إعلال بالنقل", "r_sakinayn_mafool": "إعلال بالحذف", "r_hamz_fail": "إبدال (همزة)", "r_hamz_tatarruf": "إبدال (همزة)",
        "r_wy": "إعلال بالقلب مع الإدغام", "r_qalb_alif": "إعلال بالقلب", "r_naqis_kasra": "إعلال بالقلب", "r_madd": "إعلال بالقلب",
        "r_manqus_tanween": "إعلال بالحذف", "r_idgham": "إدغام"}

RULES = [r_hamzatan, r_iftial, r_mithal_mudari, r_mithal_masdar, r_ifala, r_naql, r_sakinayn_mafool, r_hamz_fail, r_hamz_tatarruf,
         r_wy, r_qalb_alif, r_naqis_kasra, r_madd, r_manqus_tanween, r_idgham]


def derive(template, root, ctx, max_steps=8):
    """يطبّق القواعد على الأصل حتى لا يتغير شيء. يعيد (الأصل المرسوم، الصورة، الخطوات)."""
    tk = fill(template, root)
    if tk is None:
        return None
    tk = expand(tk)
    maq = root[2] if len(root) > 2 else None
    asl = render(tk)
    steps = []
    for _ in range(max_steps):
        for rule in RULES:
            r = rule(tk, ctx)
            if r:
                tk, expl = r
                steps.append({"الخطوة": expl, "الصورة": render(tk, maq), "النوع": KIND.get(rule.__name__, "")})
                break
        else:
            break
    return asl, render(tk, maq), steps


def surface_wazn(template, root, ctx):
    """الوزن على لفظ الكلمة بعد الإعلال: الأصول الباقية فاءً وعينًا ولامًا، وما تغير منها يُذكر بلفظه (قال ← فال، اتّصل ← اِتَّعَل)."""
    tk = fill(template, root)
    if tk is None:
        return None
    tk = expand(tk)
    for _ in range(8):
        for rule in RULES:
            r = rule(tk, ctx)
            if r:
                tk = r[0]
                break
        else:
            break
    names = {1: "ف", 2: "ع", 3: "ل", 4: "ل"}
    out = []
    for i, t in enumerate(tk):
        t = t.copy()
        madd = t.v == "" and t.c in "اوي"
        merged = i > 0 and tk[i - 1].c == t.c and tk[i - 1].v == "0" and tk[i - 1].rad is None
        if t.rad and t.rad <= len(root) and t.c == root[t.rad - 1].translate(_HZ) and not madd and not merged:
            t.c = names[t.rad]
        out.append(t)
    return render(out, root[2] if len(root) > 2 else None)


def root_type(root: str) -> str:
    r = root.translate(_HZ)
    if len(r) == 4:
        return "رباعي"
    w = [c in WEAK for c in r]
    if w[0] and w[2]:
        return "لفيف مفروق"
    if w[1] and w[2]:
        return "لفيف مقرون"
    if w[0]:
        return "مثال " + ("واوي" if r[0] == "و" else "يائي")
    if w[1]:
        return "أجوف " + ("واوي" if r[1] == "و" else "يائي")
    if w[2]:
        return "ناقص " + ("واوي" if r[2] == "و" else "يائي")
    if r[1] == r[2]:
        return "مضعّف"
    if "ء" in r:
        return "مهموز " + ("الفاء" if r[0] == "ء" else "العين" if r[1] == "ء" else "اللام")
    return "صحيح سالم"


# القوالب القياسية للثلاثي ومزيده: (الوزن، الوصف، النوع، سياق القواعد)
VERB_TEMPLATES = [
    ("فَعَلَ", "فعل ماضٍ ثلاثي مجرد (باب فَعَلَ)", "I"), ("فَعِلَ", "فعل ماضٍ ثلاثي مجرد (باب فَعِلَ)", "I"),
    ("فَعُلَ", "فعل ماضٍ ثلاثي مجرد (باب فَعُلَ)", "I"),
    ("أَفْعَلَ", "فعل ماضٍ مزيد بحرف (الهمزة)", "IV"), ("فَعَّلَ", "فعل ماضٍ مزيد بحرف (التضعيف)", "II"),
    ("فاعَلَ", "فعل ماضٍ مزيد بحرف (الألف)", "III"), ("اِنْفَعَلَ", "فعل ماضٍ مزيد بحرفين (الهمزة والنون)", "VII"),
    ("اِفْتَعَلَ", "فعل ماضٍ مزيد بحرفين (الهمزة والتاء)", "VIII"), ("اِفْعَلَّ", "فعل ماضٍ مزيد بحرفين (الهمزة والتضعيف)", "IX"),
    ("تَفَعَّلَ", "فعل ماضٍ مزيد بحرفين (التاء والتضعيف)", "V"), ("تَفاعَلَ", "فعل ماضٍ مزيد بحرفين (التاء والألف)", "VI"),
    ("اِسْتَفْعَلَ", "فعل ماضٍ مزيد بثلاثة أحرف (الهمزة والسين والتاء)", "X"),
    ("يَفْعُلُ", "فعل مضارع من الثلاثي (عينه مضمومة)", "I"), ("يَفْعِلُ", "فعل مضارع من الثلاثي (عينه مكسورة)", "I"),
    ("يَفْعَلُ", "فعل مضارع من الثلاثي (عينه مفتوحة)", "I"), ("يُفْعِلُ", "فعل مضارع من أَفْعَلَ", "IV"),
    ("يُفَعِّلُ", "فعل مضارع من فَعَّلَ", "II"), ("يُفاعِلُ", "فعل مضارع من فاعَلَ", "III"), ("يَنْفَعِلُ", "فعل مضارع من اِنْفَعَلَ", "VII"),
    ("يَفْتَعِلُ", "فعل مضارع من اِفْتَعَلَ", "VIII"), ("يَتَفَعَّلُ", "فعل مضارع من تَفَعَّلَ", "V"), ("يَتَفاعَلُ", "فعل مضارع من تَفاعَلَ", "VI"),
    ("يَسْتَفْعِلُ", "فعل مضارع من اِسْتَفْعَلَ", "X"),
]
NOUN_TEMPLATES = [
    ("فاعِل", "اسم فاعل من الثلاثي", "I"), ("مَفْعُول", "اسم مفعول من الثلاثي", "I"),
    ("مَفْعَل", "مصدر ميمي أو اسم زمان أو مكان", "I"), ("مَفْعِل", "اسم زمان أو مكان (أو مصدر ميمي من المثال)", "I"),
    ("مِفْعَل", "اسم آلة", "I"), ("مِفْعال", "اسم آلة أو صيغة مبالغة", "I"), ("مِفْعَلَة", "اسم آلة", "I"),
    ("فَعّال", "صيغة مبالغة أو اسم حرفة", "I"), ("فَعُول", "صيغة مبالغة", "I"), ("فَعِيل", "صفة مشبهة أو صيغة مبالغة أو بمعنى مفعول", "I"),
    ("فَعِل", "صفة مشبهة أو صيغة مبالغة", "I"), ("أَفْعَل", "اسم تفضيل أو صفة مشبهة", "I"), ("فَعْلان", "صفة مشبهة", "I"),
    ("فَعْل", "مصدر ثلاثي أو اسم", "I"), ("فِعْل", "مصدر ثلاثي أو اسم", "I"), ("فُعْل", "مصدر ثلاثي أو اسم أو جمع", "I"),
    ("فَعَل", "مصدر ثلاثي أو اسم", "I"), ("فُعُول", "مصدر ثلاثي أو جمع تكسير", "I"), ("فِعالَة", "مصدر ثلاثي (للحرفة غالبًا)", "I"),
    ("فَعالَة", "مصدر ثلاثي", "I"), ("فِعال", "مصدر ثلاثي أو جمع تكسير", "I"), ("فُعال", "مصدر ثلاثي (للداء والصوت غالبًا)", "I"),
    ("فَعال", "مصدر ثلاثي أو اسم", "I"), ("فَعْلَة", "اسم مرة أو مصدر", "I"), ("فِعْلَة", "اسم هيئة أو مصدر", "I"),
    ("فُعْلَة", "اسم", "I"), ("فَعَلَة", "جمع تكسير أو اسم", "I"), ("فَيْعِل", "صفة مشبهة", "I"), ("فُعْلَى", "اسم أو صفة مؤنثة", "I"),
    ("فَعْلَى", "صفة مؤنثة أو جمع", "I"), ("فَعْلاء", "صفة مشبهة مؤنثة (مؤنث أَفْعَل) أو اسم", "I"),
    ("أَفْعال", "جمع تكسير (جمع قلة)", "I"), ("فُعَلاء", "جمع تكسير", "I"),
    ("أَفْعِلاء", "جمع تكسير", "I"), ("فَواعِل", "جمع تكسير (صيغة منتهى الجموع)", "I"), ("مَفاعِل", "جمع تكسير (صيغة منتهى الجموع)", "I"),
    ("مَفاعِيل", "جمع تكسير (صيغة منتهى الجموع)", "I"), ("فَعائِل", "جمع تكسير (صيغة منتهى الجموع)", "I"),
    ("إِفْعال", "مصدر أَفْعَلَ", "IV"), ("تَفْعِيل", "مصدر فَعَّلَ", "II"), ("تَفْعِلَة", "مصدر فَعَّلَ (للناقص غالبًا)", "II"),
    ("مُفاعَلَة", "مصدر فاعَلَ", "III"), ("فِعال", "مصدر فاعَلَ أو مصدر ثلاثي", "III"), ("اِنْفِعال", "مصدر اِنْفَعَلَ", "VII"),
    ("اِفْتِعال", "مصدر اِفْتَعَلَ", "VIII"), ("اِفْعِلال", "مصدر اِفْعَلَّ", "IX"), ("تَفَعُّل", "مصدر تَفَعَّلَ", "V"),
    ("تَفاعُل", "مصدر تَفاعَلَ", "VI"), ("اِسْتِفْعال", "مصدر اِسْتَفْعَلَ", "X"),
    ("مُفْعِل", "اسم فاعل من أَفْعَلَ", "IV"), ("مُفْعَل", "اسم مفعول (أو زمان أو مكان أو مصدر ميمي) من أَفْعَلَ", "IV"),
    ("مُفَعِّل", "اسم فاعل من فَعَّلَ", "II"), ("مُفَعَّل", "اسم مفعول من فَعَّلَ", "II"), ("مُفاعِل", "اسم فاعل من فاعَلَ", "III"),
    ("مُفاعَل", "اسم مفعول من فاعَلَ", "III"), ("مُنْفَعِل", "اسم فاعل من اِنْفَعَلَ", "VII"), ("مُفْتَعِل", "اسم فاعل من اِفْتَعَلَ", "VIII"),
    ("مُفْتَعَل", "اسم مفعول من اِفْتَعَلَ", "VIII"), ("مُتَفَعِّل", "اسم فاعل من تَفَعَّلَ", "V"), ("مُتَفاعِل", "اسم فاعل من تَفاعَلَ", "VI"),
    ("مُسْتَفْعِل", "اسم فاعل من اِسْتَفْعَلَ", "X"), ("مُسْتَفْعَل", "اسم مفعول من اِسْتَفْعَلَ", "X"),
]


def ctx_for(wazn: str, pos: str, form: str):
    ctx = {"pos": pos}
    if form == "VIII":
        ctx["form"] = "VIII"
    if wazn in ("إِفْعال", "اِسْتِفْعال"):
        ctx["masdar_ifala"] = True
    if pos != "verb" and (wazn.startswith("أَفْعَل") or wazn.startswith("مِفْعَل") or wazn == "مِفْعال" or wazn.startswith("أَفْعال")
                          or wazn in ("فَعّال", "فَعْلان")):
        ctx["no_naql"] = True
    if wazn.startswith("مِفْعَل") or wazn == "مِفْعال":
        ctx["pattern_kind"] = "ala"
    return ctx


def match_word(word_diac: str, roots: list, pos_hint: str | None):
    """يجرّب القوالب القياسية مع الجذور المرشحة، ويعيد ما يطابق الكلمة بعد الإعلال."""
    target = bare(strip_case(word_diac))
    has_sh = SHADDA in word_diac
    templates = []
    if pos_hint in (None, "verb"):
        templates += [(w, d, f, "verb") for w, d, f in VERB_TEMPLATES]
    if pos_hint in (None, "noun"):
        templates += [(w, d, f, "noun") for w, d, f in NOUN_TEMPLATES]
        templates += [(w + "َة", d + " مؤنث بالتاء", f, "noun") for w, d, f in NOUN_TEMPLATES if not w.endswith("َة") and not w.endswith("ء") and not w.endswith("ى")]
        if any(r[2:3] in ("و", "ي") for r in roots) and not target.endswith(("ي", "ا")):
            templates += [(w + "ٌ", d + " (منقوص منوّن)", f, "noun") for w, d, f in NOUN_TEMPLATES if w.endswith("ِل")]
    order = {t[0]: i for i, t in enumerate(templates)}
    out = []
    for root in roots:
        for wazn, desc, form, pos in templates:
            tpl = parse_wazn(wazn)
            if sum(1 for t in tpl if t.rad) != len(root):
                continue
            ctx = ctx_for(wazn.replace("َة", "") if wazn.endswith("َة") and wazn not in ("مِفْعَلَة", "فِعالَة", "فَعالَة", "فَعْلَة", "فِعْلَة", "فُعْلَة", "فَعَلَة", "تَفْعِلَة", "مُفاعَلَة") else wazn, pos, form)
            tries = [(ctx, desc)]
            if wazn == "فِعْلَة" and pos == "noun" and root[:1] == "و":  # عِدَة، صِلَة، زِنَة، جِهَة، ثِقَة، صِفَة
                tries.append((dict(ctx, mithal_masdar=True), "مصدر المثال الواوي على «فِعْلة» (حُذفت فاؤه وعُوّض عنها التاء)"))
            for ctx, desc_ in tries:
                r = derive(tpl, root, ctx)
                if r is None:
                    continue
                asl, surf, steps = r
                pref_variants = [bare(surf)]
                if pos == "verb" and wazn.startswith("يَ") or wazn.startswith("يُ"):
                    pref_variants += [c + bare(surf)[1:] for c in "تنء"]
                if target in pref_variants and (SHADDA in surf) == has_sh and vowels_agree(word_diac, surf):
                    out.append({"order": order.get(wazn, 99), "wazn": wazn, "desc": desc_, "form": form, "pos": pos, "root": root, "asl": asl, "surf": surf,
                                "steps": steps, "swazn": surface_wazn(tpl, root, ctx)})
    return out


def skeleton_roots(word: str, pos_hint: str | None = None, min_fixed: int = 0) -> list:
    """جذور مرشحة بمطابقة حروف الكلمة على القوالب القياسية حرفًا بحرف: الزوائد تطابق زوائد القالب،
    وما وقع موقع الأصل يؤخذ أصلًا، وحرف العلة أو الهمزة في موضع الأصل يُردّ إلى الواو والياء والهمزة جميعًا.
    مرشحات فحسب، لمن لم يعرف المحلّلُ الكلمةَ: لا يُقبل منها إلا ما يعيد به الاشتقاقُ الكلمةَ نفسها (match_word).
    min_fixed: أقل عدد من الزوائد (سوى تاء التأنيث) في القالب؛ فالكلمة غير المشكولة لا تُطابَق على قالب
    كـ«فَعِلَة» تحتمله كل كلمة من أربعة أحرف."""
    import itertools
    target = bare(strip_case(word))
    templates = []
    if pos_hint in (None, "verb"):
        templates += [w for w, _, _ in VERB_TEMPLATES]
    if pos_hint in (None, "noun"):
        templates += [w for w, _, _ in NOUN_TEMPLATES]
        templates += [w + "َة" for w, _, _ in NOUN_TEMPLATES if not w.endswith(("َة", "ء", "ى"))]
    out = []
    for wazn in templates:
        toks = expand(parse_wazn(wazn))
        if len(toks) != len(target) or sum(1 for t in toks if t.rad) < 3 \
                or sum(1 for t in toks if not t.rad and t.c != "ة") < min_fixed:
            continue
        slots, ok = {}, True
        for t, ch in zip(toks, target):
            if t.rad:
                if slots.setdefault(t.rad, ch) != ch:
                    ok = False
                    break
            elif bare(t.c) != ch:
                ok = False
                break
        if not ok or sorted(slots) != list(range(1, len(slots) + 1)):
            continue
        opts = [["و", "ي", "ء"] if slots[k] in "اوىيء" else [slots[k]] for k in sorted(slots)]
        for r in itertools.product(*opts):
            r = "".join(r)
            if r not in out:
                out.append(r)
    # مصدر المثال المحذوف الفاء: حرفان وتاء («جِهَة» من «وجه»)، لا يطابق قالبًا بحروفه
    if pos_hint in (None, "noun") and len(target) == 3 and target.endswith("ة") and "و" + target[:2] not in out:
        out.append("و" + target[:2])
    return out


def strip_case(w: str) -> str:
    while w and w[-1] in "\u064b\u064c\u064d\u064e\u064f\u0650\u0652":
        w = w[:-1]
    return w


def _lm(w):
    out = []
    for ch in w.replace("\u0671", "ا"):
        if "\u064b" <= ch <= "\u0652" and out:
            out[-1][1] += ch
        elif not ("\u064b" <= ch <= "\u0652"):
            out.append([ch, ""])
    return out


def shadda_agrees(word: str, surf: str) -> bool:
    """حرفٌ ضبطه الكاتب بحركة ولم يشدّده لا يُقرأ مشددًا («عِدَة» غير «عِدَّة»)؛ وما لم يضبطه فلا حكم فيه."""
    a, b = _lm(strip_case(word)), _lm(strip_case(surf))
    if len(a) != len(b):
        return True
    return not any(ma and SHADDA not in ma and SHADDA in mb for (_, ma), (_, mb) in zip(a, b))


def vowels_agree(word: str, surf: str) -> bool:
    """الحركات المضبوطة في الكلمة توافق حركات الصورة المولّدة (ما عدا حركة الآخر)."""
    a, b = _lm(strip_case(word)), _lm(strip_case(surf))
    if len(a) != len(b):
        return True
    for i, ((ca, ma), (cb, mb)) in enumerate(zip(a, b)):
        if i == len(a) - 1:
            break
        va = [c for c in ma if c in "\u064e\u064f\u0650\u0652"]
        vb = [c for c in mb if c in "\u064e\u064f\u0650\u0652"]
        if va and vb and va[0] != vb[0]:
            return False
        if va and not vb and va[0] != "\u0652" and cb not in "اوي":
            return False
    return True
