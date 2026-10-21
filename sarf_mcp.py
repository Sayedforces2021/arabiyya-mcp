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
- corpus_add_shamela_book: إضافة كتب من المكتبة الشاملة المثبّتة على الجهاز بصفحاتها المطبوعة.
- phonetics / huruf: الكتابة الصوتية (IPA) والمقاطع والنبر، ومخارج الحروف وصفاتها.
- mizan / mushtaqqat / taqalib: الميزان الصرفي وخطوات الإعلال، والمشتقات القياسية، وتقاليب الجذر.
- irab: الإعراب بمحلل نحوي حديث (Stanza/UD) منقولًا إلى أبواب النحو العربي.
- analyze_qafiya / detect_badi: علم القافية وعيوبها، والمحسنات البديعية.
- takhrij_shahid / usage_compare / attribute_author / semantic_change / lughawiyyat: تخريج الشاهد، وموازنة التعابير، ونسبة النص، والتطور الدلالي، وكتب اللغة المتخصصة.
- benchmark: قياس دقة الأدوات.
"""

import os
import re
from functools import lru_cache

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.tokenizers.word import simple_word_tokenize

INSTRUCTIONS = """أداة «العربية»: عُدّة باحث في علوم العربية تعمل على الجهاز (38 أداة).
- الصرف: analyze_word، analyze_text، root_family، conjugate، mizan (الميزان مع الأصل وخطوات الإعلال والإبدال)، mushtaqqat (المشتقات القياسية)، taqalib (تقاليب الجذر).
- النحو: irab (إعراب الجملة كلمةً كلمة بالأبواب والعلامات، مع ضبط الأواخر).
- الضبط والعروض والقافية: diacritize، scan_verse وscan_poem (مع الضبط الموجَّه بالوزن)، analyze_qafiya (عناصر القافية وعيوبها).
- الأصوات: phonetics (IPA والمقاطع والنبر)، huruf (المخارج والصفات).
- البلاغة: detect_badi (الجناس والطباق والمقابلة والتصريع وردّ العجز والسجع والاقتباس).
- المعجم: maajim (15 معجمًا تراثيًّا بالجزء والصفحة)، lughawiyyat (الفروق والأضداد والإبدال والمعرّب والمثلثات وفقه اللغة)، lexicon_lookup (عبر الإنترنت).
- القرآن: quran_word، quran_root.
- الشعر: search_poetry، takhrij_shahid (تخريج البيت ونسبته ورواياته ومواضع الاستشهاد به).
- الدلالة: semantic_neighbors، word_similarity، substitutes_in_context، semantic_change (التطور الدلالي عبر القرون).
- المدوّنة التراثية: corpus_concordance، corpus_usage، corpus_collocates، usage_compare (موازنة التعابير)، corpus_find_book / corpus_add_book / corpus_remove_book / corpus_add_shamela_book (من الشاملة المثبّتة).
- الأسلوب: text_profile، compare_texts، attribute_author (نسبة النص إلى قائله بمقياس Delta).
- benchmark: قياس دقة الأدوات على بيانات معيارية.
تنبيهات: التحليل الآلي يقارب ولا يقطع، فما خالف المقرر عند أهل الفن يُنبَّه عليه ولا يُسلَّم به؛ والشعر القديم يُعطى مشكولًا ما أمكن؛ ويُذكر المصدر بالجزء والصفحة كما تُرجعه الأدوات، ويُميَّز بين ما نقلته الأداة وما استنبطته."""

# أيقونة الأداة (ختم العين) تعرضها العملاء التي تدعم أيقونات الخوادم
ICON_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAABmJLR0QA/wD/AP+gvaeTAAARPElEQVR4nO2deXxUVZbHv/dVUkkqa2VPCLIkgSD7GkVkEUVBUEahHcFBQRScZmzb6W677XZQZnrsT9ujto4yoKiNDdICAoKiIIiNyBJigLBTJARMhZCkKnsqS9WbPyJ2QGpJ8ip5L7zvf6k697wD71fv3eWcewXtIC6uf1hTUN1YySWNBfrLyOkg4oEwILA9vnV+hAOoAIpkmSOSkA82OQ2fVBSfzmuPU9GWNubE1LuEJOYKuEeGoPYEoNNuDsuyWGp0hfy1uPhITWsbt0oA0d3SZiLzHDCwtRfS8TulAvGfZUkRS8nObvS1kU8CiEvpne50GZaCPLHt8el0ECeEy/Vw2cW8LF+MDd4MzElps2XEZiCj3aHpdARxCDE3ODy6wVFl+8absacngDB3S/u9kPmNgsHpdCACVpWZeBSLpd6DzbU/j0lKfVMWYqGfYtPpKGTxaURQ4/3nzp1zXOvrawrA3C3tv9vzy4+LMhIZFogpyIBBtGWgoXOZJpdMbb2TsvIGymt87ttdgYAtZVbLdMB5je+uxJyUNlsI/tqaC0SYAhiZYebm/maGpUcSEuS1a6HTBsoqG8g+VcFXR0rJOVOBLPveVoY37FbLoqs/v0IAzb196VuaJ3K8Em4y8MCEFO4ZnUBggMSl8nr2nygnv6gWW2U9DY2tiFDHLUFGicSYIPqmhDO8TxThJgPni+tY+vE5DlkqfPYjZOaUFVnev+Kzln9EJ6d/4etQb3JmPPOm3IDJaGDbwRK27CvmbGGr5yF0WkmAJBgzKJrZt3cnJS6YnTmlLN9SQEW1T6+HKqdTGtJy9vAHAUR3S5uBzFpvHgwGWDCtF9NuTiD7dDnLNhdw4VJd2/41Om3GaJCYMSGJf57QDVtVI79bcYLvSq7Zz7sSwVZboWXK5T8vv6xFSHj0GiDBU1uDARbPyWD8kFjW7irk1XX5VLSxY6LTPpyyTG5eFVkny7l9eCx3jkogN6+SssoGb03TQ8Ojc2qrbKcAJABzYupd+DC9u2BaL0b0jeLP6/N497MLuFrTC9HxCxZrDf++9Bg1dU3816MZJMUEe23jgiV8//SXAIQk5nprNDkzgWk3J7B2VyGfZ11qb9w6ClJUVs9v3j6B0wXPzUkn2Ch5azLY3C19CoAhNrZvOAZ5BRDgzjrcZOD5uX3Jzavk1XX56L979VHjcHK2sIb7bk0iKszI/hN2b01CHVW2NZIzoGmMtyXdByakYDIaWL6lQH/sq5gcSwXrdxdx56g4eiWGerQVcHdESv9oSZLEOE+GEaYA7hmdwPbsEs4X6719tfPhTivVdU7mTenuzTTA4HJMkoD+nqxGZpgJDJDYvLdYsSB1/Ee1o4kPvyxkRN8obkgI8WgrZMZLMvTxZDS6v5lL5fXkWfVJHq2wI7sUpxPGDorxbCjEQAlwayUEDE2PZP+J8lbNO+t0LuU1jeTmVzBmYLQ3094SEO7u29hIIyFBBvKLahUNUMf/5OZV0j0+hADJ/WqsALMEGN0ZRIY1J/baKt3mE+iolGJ7A5IQxEa5vb3IEORxxiDk+wmFugaXstHp+J3LU8IxEZ6Ttr1MGTU/PvT3v/ZwuppvmuTlDnudM9Tp2ugCuM7RBXCd43YBSMuEBBu5ZWRfBvZNoW9qMj1TYgk3hRAWGgRCUF3toMReyQlLIYeOFrBtdy72iutzoqtLCeCmYenMunc0Y0dlEBTkvjY12hxGtDmMvr2TmT5pJL998p/44uuj/HnFZxQUlnRgxJ1PlxDAqMG9eWr+FIb279mm9oEBBiaPH8zttw7k3TVf8vp7n9PkvD6GvpoWQHhoML9cMJUZd2ciFKg/CDRIPD57IiOHpPLk4pWU2ioViFLdaLYT2KdXEh8tf5qZU29S5Oa3ZGj/nqx+bRE3JMcq6leNaFIA42/qx+rXF5GS5HWxo810T47mvZcXkBAb6bdrqAHNCWBsZgavLXmEUJP/96VIijfzfy/Ox2jsupudaEoAwwf24vUXHiYwoONKzzJSk3hm4dQOu15HoxkBRJvD+J/nHuqUX+OD945mxKBeHX7djkATowAhBC89O0ux97HNXs2WHTkcPnme84WlNDU1ERIcRI9ucQwb0IMxozJIio+64vq/XDCNB376miLXVxOaEMC0O4YxerjHzDWfWbluNy+v+JT6+h9XNOUcO8fGbVlIkiBzaBpz7h/L+Jv6ATCo3w2MHt6Hb7JPKxKHWlD9KyA8NJhfLVDmHfzim5t48c1N17z5LXG5ZPZmn+GJZ1cw819f4/CJAgBm3J2pSBxqQvUCePDe0cSY3Wat+czaLftYuW53q9sdPXmeWf/2v7zwynpGDe6NwaD6/7JWoepXgNEYyJz7b223H3tFDX9ctqXN7V0umTWb93Lg8FlCQ4KorO469RGqFsDtYwYo8uvf8HkW1TU+lE57Ie9816uJVPXzbOptQxTxk3XorCJ+uiKqFUBIsJExo5TZmtBeoae1u0O1AhjUr4diM37mSJMifroiqhXA0P49lPM1oGvO4imBagWQ1jNRMV/T7xyBMVDV/d1OQ7UCSE6I8m7kI/ExESyYre9zfS1UK4D4GGXX4RfMnsjEMQMU9dkVUK0AvFW0tBaDQeKVxXOYde9oxTOItIxqBdC2w0w8E2iQeO5n9/Hunx7nxvQUxf1rEdUKoKLKf9OtmUPTWb/sKf7y8kJm3J1JYrxy/Q2todqu8cWScjJSk/x6jVFD0hg1JA2A4tIKzheWYi22U1lVh6Ohqc1+c47m8+Xe40qF6VdUK4ALhaUder2E2EjFEk4e+pk2bj6o+BWQc+xcZ4fQJo6fKSQ7N7+zw/AZ1Qog60g+sgY3Jli14evODqFVqFYApbZKDh0v6OwwWoW9ooYtOw91dhitQrUCANjw+cHODqFVfLhlLw0N2to9XdUC+HRnjmbKtpucLtZ8vLezw2g1qhZATW09S9/f3tlh+MT23blcLPH9+Ba1oGoBAKzZ9I0mUrFWb9RW5+8yqhdAo9PFz19432sqd2dy/EwhB49oZ+jXEtULAOB0fhF/ePPjzg7DLVob+rVEEwIAWLN5L8tWfdHZYfwILQ79WqIZAQC8uuIzPlBZT3vtJ/s0N/RriaYEAJAQ0/46AaVocrr4YJPXA7pVjaYEcMetA7ntFvVk9Wh16NcSzQgg1BTEs4umd3YYV6Dlzt9lNCOAuTPHkRinnv16tLbq5w5NCCA4yMis6bd0dhhX0BV+/aARAdx31wjMkZ6PQetItD70a4nqBSCE4F8UKBFXEq0P/Vqi2pSwy/Tvk0LPlDi/XuNiSQU7vzlG/vlLlNqqvNrvP2TxazwdieoFcPsYj8catouv9p/gnb99xcEjZ3G5tJd9pASqF0BbN4D2RHllLb996UN27jmquG+toWoBCCEUL+AoumRn3i+Wc+6762tbeHeouhMYHRVGWGiwYv6qahzMf+Yt/ea3QNUCSFK4YudPy7aQV6D+5JKORNUCiIkKU8zXpbJKPtp6QDF/XQVVC8BoVK6L8vlXR66bU0Bag6oFEKSgAHJPnlfMV1dC1QJoalLuF1tcUq6Yr66EqgVQ52hQzFdtfdurfbsyqhbApTLlki1Mwe5P0b6eUbUALhTZFCsQjVbRaqKaULUAqmscFCi0T0C/9G6K+OlqqFoAAAcP5yniJ3NoqiJ+uhqqF8DOb44p4mdwvx5+33JGi6heAF8fOEmJD2v0vrDo4TsV8dOVUL0AGp0uVm/co4iviWMGcP/kUYr46iqoXgAAK9f/nTK7Mk+BxT+/X98xtAWaEEBtXQO/f32jIr4CAwy8sngOj8wcp+8YikYEALB112E2bstSxFegQeKZJ6bxzkuPX/cdQ80IAGDxyx8pWoxx07B01i97mmUvzmfS2IGKn0fcq3scj8wcxx23DlTUr5KoOiXsahoaGnn812+x7MXHFDvKVZIEYzMzGJuZgdPp4uRZK9/m5pOdm09hsZ1LpRXYyqvdLiWHBBuJj4kkNjqM5AQzfXon0y8tmb69E4mNjuCjz7JYuf7visTqDzQlAGjuDzSL4FFGDlZ2csdgkOjfJ4X+fVKuqEVwuWRs5VXUOZoXlIKCAggKCsAYEECImzUGl0vm1RWfsXz1DlXvd6g5AUDzKuG8XyzjyXmTeezBCX6/niQJYqMjfLY/by3jdy99SNZh9Z9WpkkBQHNt/stvfcLJs1aWPD1D8fd3W7BX1LBs1Q4++Fg7+wVqVgCX+XRnDlmHLDw1fwrTJ41Akjp+aJd/oYRVG/awcVsWNbX1HX799qB5AQCU2Kr47R//xqoNe3h89m3cdssAAv18xm+ZvYptu4/yyY5v+fboOVW/5z3RJQRwmeNnvuOp51cSGx3BfXeNZNLYgfRL66bIU6GiupaDh/LYl2NhX46FswXFmr3pLelSArhMqa2S5at3sHz1DqIiTAy5sQd9UpNJ75lIUnwUcTERREaEYAoOAiGorXPgcDTS0OCkqqYWW3kNBYUlFHxXSkFhKQXflXGhqLRL1g92SQG0pLyyll37TrBr34nODkWVeHxRur6f+zB0QsdKp338Y5nD81PLowBsVc092pgIPaFSa5iMzecu19Z7Tq2XBLgdt5SWN+CSZeKjdAFojdjI5ntmr3KfWi+gXpLBbe51o1Pmu0sOBqb6Pgumow56JpuocTixV7mfkJKhSgI8Zl3uzi1jcO8IIsMClY5Rx08IAZkZZrJPl+NlpFoiAbmeLHYfsSFJgolDY5WMUcePpKeEERtpZP9xu0c7GU5LMmKXJ6OC4lqyT5fzkwndCA02KBmnjp+YenMCDY0uDpz0Ug8pOCY1IbYBHgvn3vn0POEmAz+ZoBdXqJ2eiSYmDo1l456LVNd5rocUstglVVlPlwrY6skwr6iWbVklzBibxJA09WzXqnMlkiRYMK0H1Q4na7+0ejOvDaZmjwTggre8WS/bfI7zl+r49ax04s2dv/Sq82Meuas7Q9IieXtLAdUOb9XQ8iar1VorAditli0gjngydzS4WLLyNAYD/OGxfiTF6CJQE5Mz45k5LplNX19ke7Yvm2CJ9wB+6NWZwszFCPGApybVdU0cOVvJpJHxTBoRx2FLJTYP40wd/yNJgnmTezB38g0cOFnOK+ss3oZ+CMixWS3PQAsB1FXbT4aER48GPCbalVU2sO+4jXFDYpk+JhFJEpwqqMbZBZZGtUbPRBPPPJjGbUNj2bTnIq+ss+B0em8nwcLaKtspgCtWeSK7p6UanOQAXs9liQoNZP7UHkwcFkthaR2rvyhk95EyGp26EPyJEJDWLYxpoxOYOCyW6jonb39SwPaDPu59KNhqK7RM+cefVxHTLXWOLIu/+BrQ4NRInri3Bz0STFQ7msg+Vc7pCzUU2epx1PsgRx2vGI0ScRFGeiWFMqpfFLGRRhoaXWzcc5G1X1p96PD9QIXTKQ2rKD79w+zvNdd5zclprwtY5KtXIWBIaiRjB8cwvE8UcfrikV+ocTj59kw5+47ZOXCy3Os4/2pkxGy79czqlp+5W+g3xCSnbZRhalsCjTAFEBdlxBQcQICeS9AunLJMbb0Te2UjZZXt2jRric1qWXz1h+7vTlpaUHSN+AghT3Fro6MJZHjDbrVc84nufnLfZnPWJUavNzXRExjkp9h0/M8Su9XyK3dfel7dsdmcdVW2DcHhMbUCxnu111ETFQjm2KyWNzwZ+fyCjk1KHe4SYiVwY7tD0/Evgq3OJsNPK4pPeS2lbl0PbfjwwJii8oUy4j8APUFAZQjIEfB8qdXi81HrbeqiJycnmxxyyENCiIUyDG2LDx3FqAN5I4j3bFbLdrylAV9Fu8dokQl9ewUYmu6WYbhADJaRE0GYAeWO+tABaACqgWIZTiM4JmSxK5iaPVartbatTv8f2LWfDO6/+RcAAAAASUVORK5CYII="

try:  # mcp 2.x
    from mcp.types import Icon
    mcp = FastMCP("arabiyya", title="العربية", description="عُدّة باحث في علوم العربية بلا إنترنت: الصرف والعروض والأصوات والمعاجم والقرآن والشعر والدلالة والمدوّنات.",
                  instructions=INSTRUCTIONS, website_url="https://ikagi07.github.io/arabiyya-mcp/",
                  icons=[Icon(src=ICON_PNG, mimeType="image/png", sizes=["128x128"])])
except (TypeError, ImportError):  # mcp 1.x
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


@lru_cache(maxsize=1)
def _catt():
    """CATT: مشكِّل محوِّلي على مستوى الحروف مدرَّب على نصوص تراثية (Tashkeela)، يضبط أواخر الكلم أيضًا."""
    import sys, contextlib
    from catt_tashkeel import CATTEncoderDecoder
    with contextlib.redirect_stdout(sys.stderr):  # المكتبة تطبع رسائل تفسد قناة MCP
        return CATTEncoderDecoder()


def _diacritize_camel(text: str) -> str:
    tokens = simple_word_tokenize(text)
    words = []
    for dw in _bert().disambiguate(tokens):
        words.append(dw.analyses[0].analysis.get("diac", dw.word) if dw.analyses else dw.word)
    return " ".join(words)


def _diacritize_catt(text: str) -> str:
    import re
    lines = text.split("\n")
    out = []
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        # قطع الأسطر الطويلة عند علامات الترقيم حتى لا تتجاوز طاقة النموذج
        parts = re.split(r"([.،؛!?؟:])", line)
        buf, chunks = "", []
        for p_ in parts:
            if len(buf) + len(p_) > 400 and buf:
                chunks.append(buf)
                buf = ""
            buf += p_
        if buf:
            chunks.append(buf)
        out.append("".join(_catt().do_tashkeel(_strip_tashkeel(c), verbose=False) if re.search("[ء-ي]", c) else c for c in chunks))
    return "\n".join(out)


@lru_cache(maxsize=1)
def _poetry_model():
    """مشكِّل الشعر المدرَّب على الجهاز (train_diacritizer.py) إن وُجد وكان أدق من CATT في اختبار الشعر."""
    try:
        import sys, json
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import diac_model
        rep = os.path.join(diac_model.MODEL_DIR, "report.json")
        if not os.path.exists(rep):
            return None
        with open(rep, encoding="utf-8") as f:
            r = json.load(f)
        mine = r.get("الموازنة: النموذج الجديد على الأبيات نفسها", {}).get("DER مع علامة الإعراب")
        catt = r.get("الموازنة: CATT على الأبيات نفسها", {}).get("DER مع علامة الإعراب")
        if mine is None or catt is None or mine >= catt:  # لا يُعتمد إلا إن ثبت تفوقه على CATT
            return None
        return diac_model.get()
    except Exception:
        return None


def _diacritize(text: str, engine: str = "auto") -> str:
    """التشكيل الآلي: CATT أولًا (أدق في النصوص التراثية وأواخر الكلم)، ثم CAMeL احتياطًا."""
    if engine in ("auto", "catt"):
        try:
            return _diacritize_catt(text)
        except Exception:
            if engine == "catt":
                raise
    return _diacritize_camel(text)


@mcp.tool()
def diacritize(text: str, engine: str = "auto") -> str:
    """تشكيل نص عربي آليًّا بحسب السياق، بأواخر الكلم.
    engine: «catt» (الافتراضي: مشكِّل محوِّلي على مستوى الحروف مدرَّب على النصوص التراثية) أو «camel» (CAMeL BERT المدرَّب على الفصحى المعاصرة)."""
    return _diacritize(text, engine)


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


_SHORT = "\u064e\u064f\u0650"  # فتحة ضمة كسرة


def _letters_marks(w: str):
    out = []
    for ch in w.replace("\u0671", "\u0627"):
        if ch in HARAKAT and out:
            out[-1][1] += ch
        elif ch not in HARAKAT and ch != "ـ":
            out.append([ch, ""])
    return out


def _agrees(cand: str, orig: str) -> bool:
    """المرشح يوافق ما ضبطه صاحب النص: الحروف نفسها، وكل حركة أو شدة في الأصل موجودة فيه."""
    a, b = _letters_marks(cand), _letters_marks(orig)
    if [x for x, _ in a] != [x for x, _ in b]:
        return False
    return all(all(c in ma for c in mb) for (_, ma), (_, mb) in zip(a, b))


def _poetic_variants(w: str) -> list:
    """بدائل الضرورة والإشباع: إشباع هاء الكناية، وصلة ميم الجمع."""
    out = []
    if len(w) > 2 and w[-1] in "\u064f\u0650" and w[-2] == "ه":
        out.append(w + ("و" if w[-1] == "\u064f" else "ي"))
    for suf in ("كُمْ", "هُمْ", "تُمْ", "كُمْ"):
        if w.endswith(suf):
            out.append(w[:-1] + "\u064f" + "و")
    if w.endswith("هُمْ") or w.endswith("هِمْ"):
        out.append(w[:-1] + "\u064f" + "و")
    return out


_END_VOWELS = ["\u064f", "\u064e", "\u0650", "\u064c", "\u064d", "\u0652"]


def _ending_variants(w: str, noun: bool = True) -> list:
    """بدائل حركة الآخر لكلمة خلا آخرها من الضبط أو احتمل غيره: الحركات الثلاث والتنوين والسكون."""
    if not w:
        return []
    lm = _letters_marks(w)
    last, marks = lm[-1]
    if last in "اىو" and len(lm) > 1 or last == "ي" and len(lm) > 1 and not marks:
        return []
    keep = marks.replace("\u064e", "").replace("\u064f", "").replace("\u0650", "").replace("\u064b", "") \
        .replace("\u064c", "").replace("\u064d", "").replace("\u0652", "")
    stem = "".join(c + m for c, m in lm[:-1])
    vs = [stem + last + keep + v for v in (_END_VOWELS if noun else ["\u064f", "\u064e", "\u0650", "\u0652"])]
    if last == "ة" or (noun and last not in "ء"):
        pass
    if noun and last != "ة":
        vs.append(stem + last + keep + "\u064b" + "ا")  # تنوين النصب بألفه
    return vs


_SUN_LETTERS = set("تثدذرزسشصضطظلن")


def _sun_shadda(w: str) -> str:
    """يُثبت شدة الحرف الشمسي بعد «ال» (يغفلها ضبط CAMeL، فيفسد بها التقطيع): السَيْف ← السَّيْف."""
    lm = _letters_marks(w)
    for i in range(len(lm) - 2):
        if lm[i][0] == "ا" and lm[i + 1][0] == "ل" and not any(c in lm[i + 1][1] for c in "\u064e\u064f\u0650") \
                and lm[i + 2][0] in _SUN_LETTERS and "\u0651" not in lm[i + 2][1] \
                and (i == 0 or (i <= 2 and all(x[0] in "وفبكل" for x in lm[:i]))):
            lm[i + 2][1] = "\u0651" + lm[i + 2][1]
            break
    else:
        # لِلشَّمْس: لام الجر ثم لام التعريف
        if len(lm) > 3 and lm[0][0] == "ل" and lm[1][0] == "ل" and lm[2][0] in _SUN_LETTERS and "\u0651" not in lm[2][1] \
                and not any(c in lm[1][1] for c in "\u064e\u064f\u0650\u0651"):
            lm[2][1] = "\u0651" + lm[2][1]
    return "".join(c + m for c, m in lm)


def _has_end_mark(w: str) -> bool:
    lm = _letters_marks(w)
    return bool(lm) and (any(c in lm[-1][1] for c in "\u064e\u064f\u0650\u064b\u064c\u064d\u0652")
                         or lm[-1][0] in "اىوي" and len(lm) > 1)


def _word_candidates(orig: str, base: str, limit: int = 24) -> list:
    """ضبوط ممكنة للكلمة، أولها ما اختاره المشكِّل، مقيدة بما ضبطه صاحب النص:
    تحليلات المحلل الصرفي، وبدائل حركة الآخر (الإعراب والتنوين والسكون)، وإشباع الهاء وصلة الميم."""
    seen, out = set(), []

    def add(c, check=True):
        if c and c not in seen and (not check or _agrees(c, orig)):
            seen.add(c)
            out.append(c)
    add(base, check=False)
    pm = _poetry_model()
    if pm is not None:  # مرشحات مشكِّل الشعر مرتبةً باحتمالها
        try:
            for c, _p in pm.word_candidates(orig, 8)[0]:
                add(c)
                _CAND_TRUST[c] = True
        except Exception:
            pass
    try:
        anal = _analyzer().analyze(_strip_tashkeel(orig))
    except Exception:
        anal = []
    anal = sorted(anal, key=lambda x: -float(x.get("pos_lex_logprob", -99) or -99))
    forms = []
    for a_ in anal:
        d = a_.get("diac") or ""
        if d and d not in [f for f, _ in forms]:
            forms.append((d, a_.get("pos") not in ("verb",)))
    marked = [d for d, _ in forms if _has_end_mark(d)]
    bare = [(d, n) for d, n in forms if not _has_end_mark(d)]
    trusted = {base} | {d for d, _ in forms}
    for v in _ending_variants(base, True) if not _has_end_mark(base) else []:
        add(v)
    for d in marked[:12]:
        add(d)
    for d, n in bare[:5]:
        for v in _ending_variants(d, n):
            add(v)
    for d, _ in bare[:5]:
        add(d)
    for d in list(out[:8]):
        for v in _poetic_variants(d):
            add(v, check=False)
            trusted.add(v)
    out = out[:limit] or [base]
    fixed = []
    for c in out:
        c2 = _sun_shadda(c)
        if c2 not in fixed:
            fixed.append(c2)
            _CAND_TRUST[c2] = c in trusted
    return fixed


_CAND_TRUST = {}


def _vowel_end(w: str) -> bool:
    lm = _letters_marks(w)
    return bool(lm) and (any(c in lm[-1][1] for c in "\u064e\u064f\u0650\u064b\u064c\u064d")
                         or (lm[-1][0] in "اىوي" and len(lm) > 1 and not lm[-1][1]))


def _verse_score(parts, meter):
    import pyarud
    _patch_pyarud()
    try:
        r = pyarud.analyze_verse(parts[0], parts[1] if len(parts) > 1 else "", forced_meter=meter)
    except Exception:
        return (False, 0.0), None
    return (bool(r.is_valid), float(r.score or 0)), r


@lru_cache(maxsize=1)
def _patch_pyarud():
    """تصحيح علّة في PyArud: قاعدة «يس ← ياسين» تُطبَّق على آخر «ليس» و«وليس» فتفسد وزنهما."""
    import gc
    from pyarud.core import phonetics as ph
    ph.DEFAULT_ARUDI_REPLACEMENTS.pop("يس", None)
    for o in gc.get_objects():
        if isinstance(o, ph.ArudiConverter):
            o.replacements.pop("يس", None)
    return True


@lru_cache(maxsize=1)
def _meter_grammars():
    """أنماط الأشطر الصحيحة لكل بحر وفروعه، وبادئاتها، من نحو PyArud."""
    from pyarud.meters.engine import ALL_GRAMMARS
    out = []
    for g in ALL_GRAMMARS:
        def prefixes(pats):
            ps = set()
            for p in pats:
                for i in range(len(p) + 1):
                    ps.add(p[:i])
            return ps
        out.append({"key": g.meter_key, "type": g.bahr_type, "name": g.name_ar,
                    "sadr": g.canonical_patterns_sadr, "ajuz": g.canonical_patterns_ajuz or g.canonical_patterns_sadr,
                    "sadr_pre": prefixes(g.canonical_patterns_sadr),
                    "ajuz_pre": prefixes(g.canonical_patterns_ajuz or g.canonical_patterns_sadr)})
    return out


@lru_cache(maxsize=1)
def _arudi():
    from pyarud.core.phonetics import ArudiConverter
    _patch_pyarud()
    return ArudiConverter()


def _fit_shatr(cands: list, full: set, pre: set, ajuz: bool, max_changes: int = 5, budget: int = 15000):
    """بحث بالعمق مع التقليم: أقل عدد من التغييرات عن ضبط المشكِّل يجعل نمط الشطر من أنماط البحر."""
    conv = _arudi()
    n = len(cands)
    best = [None]
    calls = [0]

    def pat(words, final):
        calls[0] += 1
        t = " ".join(words)
        if final:
            pats = {conv.prepare_text(t, saturate=True)[1], conv.prepare_text(t, saturate=False)[1]}
            if ajuz:
                pats.add(conv.prepare_text(t, saturate=False, muqayyad=True)[1])
            return pats
        return {conv.prepare_text(t, saturate=False)[1]}

    def dfs(i, chosen, changes):
        if calls[0] > budget or (best[0] and changes >= best[0][0]):
            return
        if i == n:
            if pat(chosen, True) & full:
                best[0] = (changes, list(chosen))
            return
        for j, c in enumerate(cands[i]):
            # التغيير عن ضبط المشكِّل بنقطة، وترك آخر الكلمة بلا حركة في حشو الشطر بنصف نقطة
            ch = changes + (j > 0) + (0.5 if i + 1 < n and not _vowel_end(c) and not _CAND_TRUST.get(c, True) else 0)
            if ch > max_changes or (best[0] and ch >= best[0][0]):
                continue
            chosen.append(c)
            ok = True
            if i + 1 < n:  # تقليم: نمط ما قبل الكلمة الأخيرة يجب أن يكون بادئة نمط صحيح
                p = next(iter(pat(chosen, False)))
                ok = p[:-2] in pre
            if ok:
                dfs(i + 1, chosen, ch)
            chosen.pop()
            if best[0] and best[0][0] == 0:
                return
    dfs(0, [], 0)
    return best[0]


def _fit_meter(orig_parts: list, base_parts: list, meter: str | None = None):
    """التشكيل الموجَّه بالعروض: يختار لكل كلمة من ضبوطها الممكنة ما يستقيم به البيت على بحره بأقل تغيير عن ضبط المشكِّل.
    يعيد (الأجزاء المضبوطة، التغييرات، نتيجة PyArud)."""
    ow = [p.split() for p in orig_parts]
    bw = [p.split() for p in base_parts]
    if any(len(o) != len(b) for o, b in zip(ow, bw)):
        return base_parts, [], None
    cands = [[_word_candidates(o, b) for o, b in zip(os_, bs)] for os_, bs in zip(ow, bw)]
    grams = [g for g in _meter_grammars() if not meter or g["key"] == meter]
    if len(grams) > 6:  # تقديم أقرب البحور إلى نمط الضبط الأولي
        import difflib
        bp = _arudi().prepare_text(base_parts[0], saturate=True)[1]
        def closeness(g):
            return max((difflib.SequenceMatcher(None, bp, x).ratio() for x in g["sadr"]), default=0)
        grams = sorted(grams, key=closeness, reverse=True)[:6]
    sols = []
    for g in grams:
        sol, total = [], 0
        for si, c in enumerate(cands):
            r = _fit_shatr(c, g["ajuz"] if si else g["sadr"], g["ajuz_pre"] if si else g["sadr_pre"], ajuz=bool(si))
            if r is None:
                sol = None
                break
            total += r[0]
            sol.append(r[1])
        if sol is not None:
            sols.append((total, g, sol))
    if not sols:
        return base_parts, [], None
    order = {g["key"] + g["type"]: i for i, g in enumerate(_meter_grammars())}
    sols.sort(key=lambda x: (x[0], order.get(x[1]["key"] + x[1]["type"], 99)))
    for total, g, sol in sols[:4]:
        parts = [" ".join(x) for x in sol]
        sc, r = _verse_score(parts, g["key"])
        if r is not None and r.is_valid:
            changes = [{"قبل": bw[si][wi], "بعد": sol[si][wi]} for si in range(len(sol)) for wi in range(len(sol[si]))
                       if sol[si][wi] != bw[si][wi]]
            return parts, changes, r
    return base_parts, [], None


@mcp.tool()
def scan_verse(verse: str, meter: str | None = None, auto_diacritize: bool = True) -> dict:
    """تقطيع بيت شعر عروضيًّا: البحر ونوعه، والتفعيلات وزحافاتها وعللها، والقافية والرويّ.
    verse: البيت بشطريه مفصولين بـ " * " (أو شطر واحد). يفضَّل أن يكون مشكولًا؛ فإن لم يكن شُكِّل آليًّا أولًا.
    meter: اسم بحر بالإنجليزية لفرضه (taweel, baseet, kamel, wafer, ...) عند الحاجة."""
    import pyarud
    _patch_pyarud()

    parts = [p.strip() for p in verse.replace("...", "*").split("*", 1)]
    orig_parts = list(parts)
    note, changes = None, []
    if auto_diacritize:
        prepared = [_prepare_verse_text(p) for p in parts]
        parts = [p for p, _ in prepared]
        notes = {n for _, n in prepared if n}
        if notes:
            note = " ".join(sorted(notes)) + " راجع الضبط إن بدت النتيجة غريبة."
    r = pyarud.analyze_verse(parts[0], parts[1] if len(parts) > 1 else "", forced_meter=meter)
    if auto_diacritize and not (r.is_valid and r.score >= 0.99):
        fitted, changes, r2 = _fit_meter(orig_parts, parts, meter)
        if r2 is not None and changes and (r2.is_valid, r2.score) > (r.is_valid, r.score):
            parts, r = fitted, r2
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
    out["النص المقطَّع"] = " * ".join(parts)
    if changes:
        out["ضبط موجَّه بالوزن"] = changes
        note = (note or "") + " وعُدّل ضبط بعض الكلمات ليستقيم الوزن (انظر «ضبط موجَّه بالوزن»)؛ فهو ضبطٌ يقتضيه العروض لا روايةٌ محققة."
    if note:
        out["تنبيه"] = note.strip()
    return {k: v for k, v in out.items() if v is not None}


# ───────────── المعاجم التراثية (The Arabic Lexicon — arabiclexicon.hawramani.com) ─────────────

LEXICON_BASE = "https://arabiclexicon.hawramani.com/"
HAMZA_FORMS = str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ؤ": "ء", "ئ": "ء"})


def _strip_tashkeel(s: str) -> str:
    return "".join(c for c in s if c not in HARAKAT and c not in "ـ\u0670")   # والألف الخنجرية كما في فهرس المدوّنة


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
    # تُجلب المرشحات كلها (إلى حدٍّ معقول) ثم تُرتَّب، لا أن يُقتطع أولها بترتيب التخزين: فالبيت الأصلي قد يكون الخامس
    # بعد أبيات تضمّنته أو عارضته، والأخذ بالأول يُخطئ النسبة (مثل «قفا نبك» يُنسب إلى من ضمّنه).
    rows = con.execute(sql, args + [3000 if q else limit]).fetchall()
    loose = False
    if q and not rows and exact_phrase and len(words) > 1:
        # لا مطابقة حرفية (لاختلاف الرسم مثل «أن ما» و«أنما»، أو رواية أخرى): يُعاد البحث بالكلمات مجتمعةً في البيت
        def _alts(w):   # الواو والفاء المتصلتان: «إنما» تطابق «وإنما»، و«ولو» تطابق «فلو»
            b = w[1:] if w[0] in "وف" and len(w) > 2 else w
            vs = {w, b, "و" + b, "ف" + b}
            return "(" + " OR ".join(f'"{x}"' for x in sorted(vs)) + ")"
        args[0] = " AND ".join(_alts(w) for w in words if len(w) > 2) or args[0]
        rows = con.execute(sql, args + [3000]).fetchall()
        loose = bool(rows)
    con.close()
    total = len(rows)
    if q:
        rows.sort(key=lambda r: _poetry_rank(q, *r))
    rows = rows[:limit]
    out = []
    for s, a, po, er, me, ti, th in rows:
        item = {"البيت": f"{s} * {a}" if a else s, "الشاعر": po, "العصر": er, "البحر": me, "القصيدة": ti, "الغرض": th}
        if q:
            item["موضع المطابقة"] = _poetry_where(q, s, a)
        out.append(item)
    res = {"عدد النتائج المعروضة": len(out), "الأبيات": out}
    if q:
        res["عدد المطابقات"] = total if total < 3000 else "3000 أو أكثر"
        if loose:
            res["تنبيه"] = "لم أجد العبارة بلفظها، فهذه أبيات فيها كلماتها كلها أو جلّها بغير ترتيبها؛ تحقق من الرواية."
        res["الترتيب"] = ("ما بدأ صدرُه بالمبحوث عنه أولًا، ثم ما وقع في صدره، ثم في عجزه (وهو غالبًا تضمين أو معارضة)، "
                          "والأقدم عصرًا قبل الأحدث، والبيت التام قبل الناقص. ولا يعني تقدّمُ بيتٍ أنه الأصل؛ "
                          "فللنسبة استعمل takhrij_shahid بالبيت كاملًا.")
    return res


_ERAS = [("الجاهلي", 0), ("قبل الإسلام", 0), ("المخضرم", 1), ("الإسلامي", 2), ("صدر الإسلام", 2), ("الراشدي", 2),
         ("الأموي", 3), ("بين الدولتين", 3.5), ("العباسي", 4), ("الأندلس", 5), ("الفاطمي", 6), ("الأيوبي", 6),
         ("المملوكي", 7), ("العثماني", 8), ("الحديث", 9)]


def _poet_key(name: str | None) -> str:
    return " ".join(_norm(name or "").split())


@lru_cache(maxsize=1)
def _poet_eras() -> dict:
    """عصر كل شاعر كما ورد في قصائده الأخرى: فنحو 40٪ من قصائد «أشعار» بلا عصر (ومنها نسخ من معلقات لبيد والأعشى
    وشعر جرير)، فيتأخر الشاعر القديم عن متأخر ضمّن بيته لأن المتأخر مؤرَّخ. يُؤخذ أكثر عصوره ورودًا."""
    import sqlite3, collections
    if not os.path.exists(POETRY_DB):
        return {}
    m = collections.defaultdict(collections.Counter)
    con = sqlite3.connect(f"file:{POETRY_DB}?mode=ro", uri=True)
    try:
        for poet, era in con.execute("SELECT poet, era FROM poems WHERE era IS NOT NULL AND era != ''"):
            m[_poet_key(poet)][era] += 1
    finally:
        con.close()
    return {k: c.most_common(1)[0][0] for k, c in m.items()}


# شعراء قدماء مشهورون لا عصر لهم في أيّ قصيدة من قصائدهم في «أشعار» (من أكثرهم قصائدَ بلا عصر)، فيُعامَلون
# معاملة المجهول ويتقدّم عليهم من ضمّن شعرهم. عصورهم معروفة لا خلاف فيها.
_KNOWN_ERAS = {
    "الأموي": ("الكميت بن زيد", "عمر بن أبي ربيعة", "قيس بن الملوح", "قيس بن الملوح (مجنون ليلى)", "نصيب بن رباح",
               "عدي بن الرقاع", "الطرماح", "جميل بن معمر", "يزيد بن الطثرية", "وضاح اليمن", "مسكين الدارمي",
               "مسكين الدرامي", "العجاج", "العرجي", "النابغة الشيباني"),
    "المخضرم": ("لبيد بن ربيعة", "عمرو بن معد يكرب", "العباس بن مرداس", "الشماخ الذبياني", "خفاف بن ندبة السلمي",
                "تميم بن أبي بن مقبل"),
    "صدر الإسلام": ("الإمام علي بن أبي طالب", "مالك الأشتر"),
    "العباسي": ("أبو الطيب المتنبي", "عبيد الله بن عبدالله بن طاهر", "يحيى بن المبارك اليزيدي", "أبو الفضل الميكالي",
                "علي بن محمد التهامي"),
    "الأيوبي": ("ابن الساعاتي", "جمال الدين بن مطروح"),
    "الأندلسي": ("ابن الزقاق البلنسي", "لسان الدين الخطيب", "ابن جبير الشاطبي"),
}


@lru_cache(maxsize=1)
def _known_eras() -> dict:
    return {_poet_key(n): e for e, names in _KNOWN_ERAS.items() for n in names}


def _era_rank(era: str | None, poet: str | None = None, eras: dict | None = None) -> float:
    """رتبة العصر (الأقدم أصغر)؛ وإن خلت القصيدة من العصر أُخذ عصر الشاعر من قصائده الأخرى، ثم من _KNOWN_ERAS،
    وإلا فـ10 (مجهول)."""
    if not era and poet:
        k = _poet_key(poet)
        era = (_poet_eras() if eras is None else eras).get(k) or _known_eras().get(k)
    return next((r for k, r in _ERAS if era and k in era), 10)


_QUOTE_TITLES = ("معارضه", "تخميس", "مخمس", "تشطير", "مشطر", "تضمين")


def _is_quotation(sadr: str, title: str | None) -> bool:
    """بيتٌ واقعٌ في قصيدة معارضة أو تخميس أو تشطير، أو منقول بين أقواس: ورودٌ للبيت لا نسبةٌ له."""
    t = _norm(title or "")
    return any(k in t for k in _QUOTE_TITLES) or (sadr or "").lstrip().startswith(("(", "«", "﴿", '"'))


def _poetry_where(q: str, sadr: str, ajuz: str) -> str:
    sn, an = _norm(sadr or ""), _norm(ajuz or "")
    if sn.startswith(q):
        return "أول الصدر"
    if q in sn:
        return "الصدر"
    if q in an:
        return "العجز"
    return "البيت"


def _poetry_rank(q, sadr, ajuz, poet, era, meter, title, theme):
    where = {"أول الصدر": 0, "الصدر": 1, "البيت": 2, "العجز": 3}[_poetry_where(q, sadr, ajuz)]
    a = (ajuz or "").strip()
    incomplete = 1 if (not a or a == "#") else 0
    era_rank = _era_rank(era, poet)
    title_match = 0 if title and _norm(title).startswith(q[:20]) else 1   # القصيدة التي مطلعها البيت نفسه
    return (where, incomplete, era_rank, title_match)


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


def _fix_corpus_names():
    """تعريب عناوين الكتب التي خلت بياناتها في OpenITI فبقيت بالحرف اللاتيني في فهارس قديمة."""
    try:
        if not os.path.exists(CORPUS_DB):
            return
        import sqlite3
        from build_corpus_index import NAMES
        con = sqlite3.connect(CORPUS_DB, timeout=5)
        for uri, (title, author) in NAMES.items():
            con.execute("UPDATE books SET title=?, author=? WHERE uri=? AND title GLOB '*[A-Za-z]*'", (title, author, uri))
        con.commit()
        con.close()
    except Exception:
        pass


_fix_corpus_names()
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
    rest = [_cn(w) for w in word.split()[1:]]            # بقية كلمات العبارة تُطابَق بلا سوابق
    firsts = {v.split()[0] for v in vs}
    punct = ".,،؛:!?()[]«»\"'"
    for _pid, text, vol, page, title, died, g, _bid in rows:
        toks = text.split()
        norm = [_cn(t).strip(punct) for t in toks]
        for i in range(len(toks)):
            if norm[i] in firsts and norm[i + 1:i + 1 + len(rest)] == rest:
                j = i + 1 + len(rest)
                out.append({
                    "قبل": " ".join(toks[max(0, i - window):i]),
                    "الكلمة": " ".join(toks[i:j]),
                    "بعد": " ".join(toks[j:j + window]),
                    "المصدر": f"{title} (ت {died}هـ)" + _cite(vol, page),
                    "الفن": g,
                })
                break
        if len(out) >= limit:
            break
    return {"الكلمة": word, "الصيغ المبحوث عنها": sorted(vs), "السياقات": out,
            "ملاحظة": "مرتبة بوفاة المؤلف؛ سياق واحد من كل فقرة. الجزء والصفحة كما في مصدر النص (الشاملة أو OpenITI)."}


def _cite(vol, page) -> str:
    """«، ج1 ص200» أو «، ص615» لكتاب بلا أجزاء؛ ولا شيء إن لم تُعرف الصفحة."""
    if page is None or page == 0:
        return ""
    return f"، ج{vol} ص{page}" if vol else f"، ص{page}"


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
    t, n = _prepare_verse_text0(text)
    return " ".join(_sun_shadda(w) for w in t.split()), n


def _diacritize_verse(text: str) -> str:
    m = _poetry_model()
    if m is not None:
        try:
            return m.diacritize(text)
        except Exception:
            pass
    return _diacritize(text)


def _prepare_verse_text0(text: str):
    letters = sum(1 for c in text if "ء" <= c <= "ي")
    marks = sum(1 for c in text if c in HARAKAT)
    ratio = marks / letters if letters else 0
    if ratio < 0.3:
        return _diacritize_verse(text), "البيت غير مشكول فشُكِّل آليًّا."
    if ratio < 0.85:
        try:
            return _merge_tashkeel(text, _diacritize_verse(_strip_tashkeel(text))), "التشكيل ناقص فأُكمل آليًّا مع إبقاء ضبط الأصل."
        except Exception:
            return text, None
    return text, None


def _split_poem(poem: str):
    lines = [l.strip() for l in poem.strip().splitlines() if l.strip()]
    verses = []
    if all(("*" in l or "..." in l or "\t" in l) for l in lines):
        for l in lines:
            s_, _, a_ = l.replace("...", "*").replace("\t", "*").partition("*")
            verses.append((s_.strip(), a_.strip()))
    else:
        for i in range(0, len(lines), 2):
            verses.append((lines[i], lines[i + 1] if i + 1 < len(lines) else ""))
    return verses


def _prepare_poem(poem: str, meter: str | None, auto_diacritize: bool):
    """تهيئة القصيدة: تقسيم الأبيات، والتشكيل، ثم التشكيل الموجَّه بالبحر الغالب للأبيات المختلة."""
    import pyarud
    _patch_pyarud()
    verses = _split_poem(poem)
    notes, prepared = set(), []
    for s_, a_ in verses:
        if auto_diacritize:
            s2, n1 = _prepare_verse_text(s_)
            a2, n2 = _prepare_verse_text(a_) if a_ else (a_, None)
            notes |= {n for n in (n1, n2) if n}
            prepared.append((s2, a2))
        else:
            prepared.append((s_, a_))
    r = pyarud.analyze_poem(prepared, forced_meter=meter) if meter else pyarud.analyze_poem(prepared)
    fixed = {}
    if auto_diacritize:
        dom = meter or r.meter
        for i, v in enumerate(r.verses):
            if not (v.is_valid and v.score >= 0.99):
                o = [verses[i][0], verses[i][1]] if verses[i][1] else [verses[i][0]]
                b_ = [prepared[i][0], prepared[i][1]] if verses[i][1] else [prepared[i][0]]
                f, ch, r2 = _fit_meter(o, b_, dom)
                if ch and r2 is not None and (r2.is_valid, r2.score) > (v.is_valid, v.score):
                    prepared[i] = (f[0], f[1] if len(f) > 1 else "")
                    fixed[i + 1] = ch
        if fixed:
            r = pyarud.analyze_poem(prepared, forced_meter=meter) if meter else pyarud.analyze_poem(prepared)
    if fixed:
        notes.add(f"وعُدّل ضبط كلمات في {len(fixed)} بيتًا ليستقيم على البحر الغالب (انظر «ضبط موجَّه بالوزن»)، وهو ضبطٌ يقتضيه العروض لا روايةٌ محققة.")
    return verses, prepared, r, fixed, notes


@mcp.tool()
def scan_poem(poem: str, meter: str | None = None, auto_diacritize: bool = True) -> dict:
    """تقطيع قصيدة كاملة: البحر الغالب، والرويّ الغالب، وحال كل بيت (موزون أو مختل، ونسبة مطابقته)، مع التنبيه على الأبيات التي خرجت عن البحر أو الروي.
    يُضبط البيت المختل ضبطًا موجَّهًا بالبحر الغالب: تُجرَّب الضبوط الممكنة لكلماته (الإعراب، والتنوين، وإشباع الهاء، وصلة الميم) فيُختار أقلها تغييرًا مما يستقيم به الوزن.
    poem: الأبيات سطرًا سطرًا، وكل بيت «الصدر * العجز»؛ أو الصدر والعجز في سطرين متتاليين.
    meter: لفرض بحر بعينه بالإنجليزية (taweel, kamel...) عند الحاجة."""
    verses, prepared, r, fixed, notes = _prepare_poem(poem, meter, auto_diacritize)
    rows, odd = [], []
    for i, (v, (s_, a_)) in enumerate(zip(r.verses, verses), 1):
        rawi = v.qafiyah.rawi if v.qafiyah else None
        row = {"البيت": i, "النص": f"{s_} * {a_}" if a_ else s_, "البحر": v.meter_name_ar,
               "موزون": v.is_valid, "المطابقة": round(v.score, 2), "الروي": rawi}
        if not v.is_valid:
            row["الخلل"] = [str(e) for e in v.errors][:2]
        if i in fixed:
            row["ضبط موجَّه بالوزن"] = fixed[i]
            row["النص المقطَّع"] = " * ".join(x for x in prepared[i - 1] if x)
        rows.append(row)
        if v.meter_name_ar != r.meter_name_ar or not v.is_valid or (rawi and r.dominant_rawi and rawi != r.dominant_rawi):
            odd.append(i)
    out = {"البحر الغالب": r.meter_name_ar, "الروي الغالب": r.dominant_rawi, "عدد الأبيات": r.total_verses,
           "الموزون منها": r.valid_verses_count, "متجانسة البحر": r.is_homogeneous,
           "أبيات تستحق المراجعة": odd, "الأبيات": rows}
    if notes:
        out["تنبيه"] = " ".join(sorted(notes)) + " راجع الضبط في الأبيات المختلة قبل الحكم عليها. ولتفصيل القافية وعيوبها استعمل analyze_qafiya."
    return out


# ───────────── علم القافية ─────────────

_VNAME = {"\u064e": "فتحة", "\u064f": "ضمة", "\u0650": "كسرة", "\u0652": "سكون", None: None}
_MADD_OF = {"\u064e": "ا", "\u064f": "و", "\u0650": "ي"}
_RAWI_NAME = {"ء": "همزية", "ا": "ألفية (مقصورة)", "ب": "بائية", "ت": "تائية", "ث": "ثائية", "ج": "جيمية", "ح": "حائية",
              "خ": "خائية", "د": "دالية", "ذ": "ذالية", "ر": "رائية", "ز": "زائية", "س": "سينية", "ش": "شينية",
              "ص": "صادية", "ض": "ضادية", "ط": "طائية", "ظ": "ظائية", "ع": "عينية", "غ": "غينية", "ف": "فائية",
              "ق": "قافية", "ك": "كافية", "ل": "لامية", "م": "ميمية", "ن": "نونية", "ه": "هائية", "و": "واوية",
              "ي": "يائية"}


def _units(text: str):
    """وحدات آخر العجز: (الحرف، حركته، رقم الكلمة)، مع ردّ الهمزات إلى ء والألف المقصورة إلى ا."""
    words = text.split()[-3:]
    out = []
    for wi, w in enumerate(words):
        for ch, m in _letters_marks(w):
            if ch in "أإؤئ":
                ch = "ء"
            elif ch in "ىٱآ":
                ch = "ا" if ch != "آ" else "ء"
            elif ch == "ة":
                ch = "ه" if wi == len(words) - 1 else "ت"
            if not ("ء" <= ch <= "ي"):
                continue
            v = next((c for c in m if c in "\u064e\u064f\u0650\u0652"), None)
            tan = next((c for c in m if c in "\u064b\u064c\u064d"), None)
            if tan:
                v = {"\u064b": "\u064e", "\u064c": "\u064f", "\u064d": "\u0650"}[tan]
            out.append([ch, v, wi])
    # ألف تنوين النصب في الآخر ليست حرفًا منطوقًا إلا إطلاقًا
    return out


def _is_madd(u, prev):
    return u[0] in "اوي" and u[1] in (None, "\u0652") and prev is not None and \
        (u[0] == "ا" and prev[1] in ("\u064e", None) or u[0] == "و" and prev[1] == "\u064f" or u[0] == "ي" and prev[1] == "\u0650")


def _qafiya_hypotheses(text: str):
    """الاحتمالات الممكنة للروي في آخر البيت: [(موضع الروي، الوحدات)]."""
    u = _units(text)
    if not u:
        return u, []
    n = len(u)
    hyps = []
    last = n - 1
    if n >= 2 and _is_madd(u[last], u[last - 1]):
        # ألف الإطلاق أو واوه أو ياؤه: الروي ما قبلها
        r = last - 1
        if u[r][0] == "ه" and r >= 1 and u[r - 1][1] in ("\u064e", "\u064f", "\u0650") and r - 1 >= 0:
            hyps.append(r - 1)  # هاء الوصل والخروج
        hyps.append(r)
        if u[last][0] in "اي":
            hyps.append(last)  # المقصورة أو الياء رويًّا
    elif u[last][0] == "ه" and n >= 2 and u[last - 1][1] in ("\u064e", "\u064f", "\u0650"):
        hyps += [last - 1, last]
    else:
        hyps.append(last)
    return u, hyps


def _qafiya_details(u, r):
    """عناصر القافية إذا كان الروي في الموضع r."""
    rawi = u[r]
    d = {"الروي": rawi[0]}
    after = u[r + 1:]
    majra = rawi[1] if rawi[1] in ("\u064e", "\u064f", "\u0650") else None
    if after:
        d["الوصل"] = after[0][0]
        if after[0][0] == "ه":
            d["النفاذ"] = _VNAME.get(after[0][1])
            if len(after) > 1:
                d["الخروج"] = after[1][0]
            elif after[0][1] in _MADD_OF:
                d["الخروج"] = _MADD_OF[after[0][1]] + " (إشباع)"
    elif majra:
        d["الوصل"] = _MADD_OF[majra] + " (إشباع)"
    d["المجرى"] = _VNAME.get(majra) if majra else None
    d["نوعها"] = "مطلقة" if majra or after else "مقيدة"
    if rawi[0] in "ا" and not after:
        d["نوعها"] = "مقيدة"
    if r >= 1 and (u[r - 1][0] == "ا" and u[r - 1][1] in (None, "\u0652") or
                   u[r - 1][0] in "وي" and u[r - 1][1] in (None, "\u0652")):
        d["الردف"] = u[r - 1][0]
        if r >= 2:
            d["الحذو"] = _VNAME.get(u[r - 2][1])
    elif r >= 2 and u[r - 2][0] == "ا" and u[r - 2][1] in (None, "\u0652") and u[r - 1][1] in ("\u064e", "\u064f", "\u0650") \
            and u[r - 2][2] == u[r][2]:
        d["التأسيس"] = "ا"
        d["الدخيل"] = u[r - 1][0]
        d["الإشباع"] = _VNAME.get(u[r - 1][1])
        if r >= 3:
            d["الرس"] = _VNAME.get(u[r - 3][1])
    if d["نوعها"] == "مقيدة" and r >= 1 and "الردف" not in d and "التأسيس" not in d:
        d["التوجيه"] = _VNAME.get(u[r - 1][1])
    return {k: v for k, v in d.items() if v}


def _letter_relation(a: str, b: str) -> str:
    ia, ib = _letter_info(a), _letter_info(b)
    if not ia or not ib:
        return "متباعدان"
    order = list(dict.fromkeys(v[1] for v in _MAKHRAJ.values()))
    x, y = order.index(ia["المخرج (ابن الجزري)"]), order.index(ib["المخرج (ابن الجزري)"])
    return "متقاربان" if abs(x - y) <= 1 and ia["الموضع العام"] == ib["الموضع العام"] else "متباعدان"


@mcp.tool()
def analyze_qafiya(poem: str, auto_diacritize: bool = True) -> dict:
    """علم القافية لقصيدة كاملة: الروي وتسمية القصيدة به، والمجرى، والقافية مطلقة أو مقيدة، وعناصرها في كل بيت (الوصل، والخروج، والردف، والتأسيس، والدخيل)، وحروفها وحركاتها (الرس، والإشباع، والحذو، والتوجيه، والنفاذ)،
    ونوعها بحسب عدد المتحركات بين ساكنيها (المتكاوس، المتراكب، المتدارك، المتواتر، المترادف)؛
    ثم عيوبها: الإقواء والإصراف، والإكفاء والإجازة، وسناد الردف والتأسيس والإشباع والحذو والتوجيه، والإيطاء.
    poem: الأبيات سطرًا سطرًا، وكل بيت «الصدر * العجز». ويُستحسن أن يكون مشكولًا، فإن لم يكن ضُبط آليًّا ضبطًا موجَّهًا بالوزن."""
    from collections import Counter
    verses, prepared, r, fixed, notes = _prepare_poem(poem, None, auto_diacritize)
    data = []
    for i, ((s_, a_), (ps, pa)) in enumerate(zip(verses, prepared)):
        end = pa or ps
        u, hyps = _qafiya_hypotheses(end)
        data.append((u, hyps))
    tally = Counter(u[h][0] for u, hyps in data for h in hyps[:2] if u)
    if not tally:
        return {"تنبيه": "لم أجد أبياتًا."}
    rawi_letter = tally.most_common(1)[0][0]
    rows = []
    for i, ((u, hyps), v) in enumerate(zip(data, r.verses), 1):
        if not u:
            continue
        pick = next((h for h in hyps if u[h][0] == rawi_letter), hyps[0])
        det = _qafiya_details(u, pick)
        q = v.qafiyah
        if q:
            det["القافية"] = q.qafiyah_text
            det["نوعها بحسب المتحركات"] = q.qafiyah_type_ar
        det["البيت"] = i
        det["آخر العجز"] = " ".join((prepared[i - 1][1] or prepared[i - 1][0]).split()[-2:])
        rows.append(det)
    # الحكم العام
    R = Counter(d["الروي"] for d in rows).most_common(1)[0][0]
    majras = Counter(d.get("المجرى") for d in rows if d.get("المجرى"))
    kind = Counter(d.get("نوعها") for d in rows).most_common(1)[0][0]
    summary = {"الروي": R, "تسميتها": _RAWI_NAME.get(R, R), "نوعها": kind}
    if majras:
        m = majras.most_common(1)[0][0]
        summary["المجرى"] = m
        summary["وصفها"] = f"{_RAWI_NAME.get(R, R)} {'مضمومة' if m == 'ضمة' else 'مكسورة' if m == 'كسرة' else 'مفتوحة'}"
    types = Counter(d.get("نوعها بحسب المتحركات") for d in rows if d.get("نوعها بحسب المتحركات"))
    if types:
        summary["نوع القافية بحسب المتحركات"] = types.most_common(1)[0][0]
    has_ridf = sum(1 for d in rows if "الردف" in d)
    has_tasis = sum(1 for d in rows if "التأسيس" in d)
    summary["مردفة"] = has_ridf > len(rows) / 2
    summary["مؤسسة"] = has_tasis > len(rows) / 2
    # العيوب
    uyub = []
    for d in rows:
        n = d["البيت"]
        if d["الروي"] != R:
            rel = _letter_relation(d["الروي"], R)
            uyub.append({"العيب": "الإكفاء" if rel == "متقاربان" else "الإجازة", "البيت": n,
                         "بيانه": f"الروي «{d['الروي']}» مكان «{R}» ({'حرفان متقاربا المخرج' if rel == 'متقاربان' else 'حرفان متباعدا المخرج'})"})
        mj = d.get("المجرى")
        if majras and mj and mj != summary["المجرى"]:
            pair = {mj, summary["المجرى"]}
            uyub.append({"العيب": "الإصراف" if "فتحة" in pair else "الإقواء", "البيت": n,
                         "بيانه": f"المجرى {mj} والغالب {summary['المجرى']}"})
        if summary["مردفة"] != ("الردف" in d):
            uyub.append({"العيب": "سناد الردف", "البيت": n, "بيانه": "أُردف هذا البيت والغالب غير مردف" if "الردف" in d else "لم يُردف والغالب مردف"})
        elif "الردف" in d:
            ridfs = Counter(x["الردف"] for x in rows if "الردف" in x)
            main = ridfs.most_common(1)[0][0]
            if (d["الردف"] == "ا") != (main == "ا"):
                uyub.append({"العيب": "سناد الردف", "البيت": n, "بيانه": f"الردف «{d['الردف']}» مع غلبة «{main}» (تتعاقب الواو والياء، ولا تعاقب الألف أحدهما)"})
        if summary["مؤسسة"] != ("التأسيس" in d):
            uyub.append({"العيب": "سناد التأسيس", "البيت": n, "بيانه": "أُسّس هذا البيت والغالب غير مؤسس" if "التأسيس" in d else "لم يؤسس والغالب مؤسس"})
    for key, name in (("الإشباع", "سناد الإشباع"), ("الحذو", "سناد الحذو"), ("التوجيه", "سناد التوجيه")):
        vals = Counter(d[key] for d in rows if key in d)
        if len(vals) > 1:
            main = vals.most_common(1)[0][0]
            for d in rows:
                if key in d and d[key] != main and not (key == "الحذو" and {d[key], main} == {"ضمة", "كسرة"}):
                    uyub.append({"العيب": name, "البيت": d["البيت"], "بيانه": f"{key} {d[key]} والغالب {main}"})
    words = {}
    for d in rows:
        w = _norm(_strip_tashkeel(d["آخر العجز"].split()[-1])) if d["آخر العجز"] else ""
        if w:
            words.setdefault(w, []).append(d["البيت"])
    for w, ns in words.items():
        if len(ns) > 1:
            gaps = [b - a for a, b in zip(ns, ns[1:])]
            uyub.append({"العيب": "الإيطاء (تكرار كلمة القافية)", "البيت": ns,
                         "بيانه": f"تكررت «{w}»؛ وأقرب ما بين تكرارين {min(gaps)} أبيات" + ("، وهو دون سبعة أبيات فيُعدّ عيبًا عند أكثرهم" if min(gaps) < 7 else "، فوق سبعة أبيات فيُتسامح فيه") +
                                  " — ولا يكون إيطاءً إذا اختلف المعنى (فهو حينئذ جناس)."})
    out = {"الحكم العام": summary, "عيوب القافية": uyub or "لم يظهر عيب.", "الأبيات": rows,
           "ملاحظة": "الحكم مبني على ضبط آخر العجز؛ فإن كان الضبط آليًّا فراجع الأبيات المعيبة قبل القطع، ولا سيما الإقواء. "
                     "وعيب التضمين (تعلّق القافية بما بعدها) لا يُكشف آليًّا."}
    if notes:
        out["تنبيه"] = " ".join(sorted(notes))
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
    import sqlite3, sys
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد."}
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import import_shamela
    con = sqlite3.connect(CORPUS_DB, timeout=30)
    try:
        row = con.execute("SELECT id, title, tokens FROM books WHERE uri = ?", (book.strip(),)).fetchone()
        if not row:
            return {"تنبيه": f"لا يوجد في المدوّنة كتاب بالمعرّف «{book}». اعرض الكتب بـ corpus_find_book بلا مُدخل."}
        bid, title, ntok = row
        import_shamela.remove_book(con, bid)
    finally:
        con.close()
    return {"حُذف": title, "الكلمات": ntok}


@mcp.tool()
def corpus_add_shamela_book(book_id: int | None = None, genre: str = "نحو", replace_openiti: bool = False,
                            category: str | None = None, limit: int = 40) -> dict:
    """إضافة كتاب من «المكتبة الشاملة» المثبّتة على جهاز الباحث (الإصدار الرابع) إلى المدوّنة التراثية، بنصّه المشكول
    وجزئه وصفحته كما يعرضها برنامج الشاملة. يُقرأ المتن وحده دون الحاشية. يعمل بلا إنترنت، ويقرأ ملفات الشاملة ولا يعدّلها.
    book_id: رقم الكتاب في الشاملة (يظهر في بطاقة الكتاب، مثل 6972 لمغني اللبيب).
    replace_openiti: إن كان true استُبدل بكل كتاب في المدوّنة أُخذ من الشاملة عبر OpenITI نسختُه من الشاملة المثبّتة (أدقّ ترقيمًا ومشكولة)، دون تكرار.
    category: لاستيراد فنٍّ كاملًا من الشاملة: «النحو والصرف»، «كتب اللغة»، «البلاغة»، «العروض والقوافي»، «الشعر ودواوينه»،
    «الغريب والمعاجم»، «الأدب»، أو «الكل» للفنون السبعة. يُستورد على دفعات (limit كتابًا في كل استدعاء، والافتراضي 40)
    بلا تكرار، فأعد الاستدعاء حتى يصير «الباقي» صفرًا. الفنون السبعة كاملةً نحو 860 كتابًا و155 مليون كلمة (نحو 3.3 غ.ب).
    يتطلب برنامج الشاملة 4 وحزمة JPype1؛ ويُحدَّد مجلد الشاملة تلقائيًّا أو بمتغير البيئة SHAMELA_ROOT."""
    import sqlite3, sys
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد؛ شغّل سكربت التثبيت مرة أخرى."}
    if book_id is None and not replace_openiti and not category:
        return {"تنبيه": "مرّر book_id (رقم الكتاب في الشاملة) أو category (فنًّا يُستورد كاملًا) أو replace_openiti=true."}
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import import_shamela as ISH
    try:
        import jpype  # noqa: F401
    except ImportError:
        return {"تنبيه": "حزمة JPype1 غير مثبّتة؛ ثبّتها بـ: pip install JPype1"}
    root = ISH.default_root()
    if not root:
        return {"تنبيه": "لم أجد برنامج الشاملة 4 على الجهاز. عيّن مجلده في متغير البيئة SHAMELA_ROOT."}
    sh = ISH.Shamela(root)
    con = sqlite3.connect(CORPUS_DB, timeout=60)
    try:
        out = {}
        if replace_openiti:
            out["الاستبدال"] = ISH.replace_openiti(sh, con, CORPUS_DB)
        if book_id is not None:
            out["الإضافة"] = ISH.import_book(sh, con, int(book_id), genre)
        if category:
            c = _norm(category).strip()
            cats = (list(ISH.LANG_CATEGORIES) if c in ("الكل", "كل", "الكل اللغوي")
                    else [k for k, n in ISH.CATEGORY_NAMES.items() if c and (c in _norm(n) or _norm(n) in c)])
            if not cats:
                out["تنبيه"] = "فنٌّ غير معروف؛ الفنون: " + "، ".join(ISH.CATEGORY_NAMES.values()) + "، أو «الكل»."
            else:
                out["الفنون"] = [ISH.CATEGORY_NAMES[k] for k in cats]
                out["الاستيراد"] = ISH.import_categories(sh, con, root, CORPUS_DB, cats, limit=max(1, min(int(limit), 300)))
    finally:
        con.close()
    return out


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



# ───────────── الميزان الصرفي والإعلال، والمشتقات، والتقاليب ─────────────

def _ilal():
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import sarf_ilal
    return sarf_ilal


@lru_cache(maxsize=4096)
def _root_books(root: str) -> int:
    """عدد المعاجم التي فيها هذا الجذر (لترجيح الواوي على اليائي ونحوه)."""
    import sqlite3
    if not os.path.exists(MAAJIM_DB):
        return 0
    con = sqlite3.connect(f"file:{MAAJIM_DB}?mode=ro", uri=True)
    n = con.execute("SELECT COUNT(DISTINCT u.book) FROM keys k JOIN units u ON u.id = k.unit WHERE k.key = ?", (_mk(root),)).fetchone()[0]
    con.close()
    return n


def _resolve_roots(camel_root: str, surface: str) -> list:
    """يردّ رمز «#» في جذر CAMeL (حرف علة أو همزة) إلى الحروف الممكنة، مرتبةً بشيوعها في المعاجم."""
    import itertools
    parts = (camel_root or "").split(".")
    if not parts or len(parts) < 3:
        return []
    opts = [["و", "ي", "ء"] if p == "#" else [p.translate(HAMZA_FORMS)] for p in parts]
    cands = ["".join(c) for c in itertools.product(*opts)]
    scored = [(c, _root_books(c)) for c in cands]
    if any(n for _, n in scored):
        scored = [x for x in scored if x[1]]
    scored.sort(key=lambda x: -x[1])
    return [c for c, _ in scored]


@lru_cache(maxsize=4096)
def _root_evidence(word: str, root: str) -> int:
    """عدد مواد الجذر في المعاجم التي تذكر الكلمة بلفظها (شاهد على نسبتها إلى هذا الجذر)."""
    import sqlite3
    if not os.path.exists(MAAJIM_DB):
        return 0
    con = sqlite3.connect(f"file:{MAAJIM_DB}?mode=ro", uri=True)
    rows = con.execute("SELECT u.text FROM keys k JOIN units u ON u.id = k.unit WHERE k.key = ? AND u.book IN ('lisan','taj','sihah','qamus','maqayis')",
                       (_mk(root),)).fetchall()
    con.close()
    w = _norm(word)
    return sum(1 for (t,) in rows if w in _norm(_strip_tashkeel(t or "")))


_BAB = {"ضمة": "فَعَلَ يَفْعُلُ (باب نَصَرَ)، أو فَعُلَ يَفْعُلُ (باب كَرُمَ)", "كسرة": "فَعَلَ يَفْعِلُ (باب ضَرَبَ)، أو فَعِلَ يَفْعِلُ (باب حَسِبَ)",
        "فتحة": "فَعِلَ يَفْعَلُ (باب فَرِحَ)، أو فَعَلَ يَفْعَلُ (باب فَتَحَ) إذا كانت عينه أو لامه حرف حلق"}


@mcp.tool()
def mizan(word: str, context: str | None = None) -> dict:
    """الميزان الصرفي مع بيان الأصل وخطوات الإعلال والإبدال والإدغام بعبارة الصرفيين:
    الجذر ونوعه (صحيح، مهموز، مضعّف، مثال، أجوف، ناقص، لفيف)، والوزن الأصلي، والأصل قبل الإعلال، ثم كل خطوة (إعلال بالقلب أو بالنقل أو بالحذف، أو إبدال، أو إدغام) حتى الصورة المنطوقة، والوزن على لفظ الكلمة، والصيغة (اسم فاعل، مصدر، اسم آلة...).
    مثل: قال، يقول، مقول، مبيع، قائل، ميزان، اتّصل، اصطبر، مرميّ، مدعوّ، داعٍ، دعاء، استقامة، آمن، إيمان، يعد، مدّ.
    word: الكلمة (يُستحسن مشكولة). context: جملة ترد فيها الكلمة لترجيح قراءتها.
    التحقق ذاتي: لا تُعرض الخطوات إلا إذا أعادت القواعدُ الأصلَ إلى الكلمة نفسها."""
    I = _ilal()
    w = word.strip()
    analyses = []
    if context:
        try:
            for dw in _bert().disambiguate(simple_word_tokenize(context)):
                if _strip_tashkeel(dw.word) == _strip_tashkeel(w) and dw.analyses:
                    analyses = [x.analysis for x in dw.analyses[:3]]
                    break
        except Exception:
            pass
    if not analyses:
        analyses = sorted(_analyzer().analyze(_strip_tashkeel(w)), key=lambda x: -float(x.get("pos_lex_logprob", -99) or -99))
    vocalized = any(c in HARAKAT for c in w)
    readings, seen = [], set()
    for a in analyses[:12]:
        diac = a.get("diac") or ""
        stem = a.get("stem") or diac
        # الكلمة مجردة من السوابق واللواحق: جذعها مع لاحقة التأنيث أو حرف المضارعة
        core = _stem_core(a)
        if vocalized and not _agrees(core, _core_of_typed(w, core)):
            pass
        pos = "verb" if a.get("pos") == "verb" else "noun"
        roots = _resolve_roots(a.get("root") or "", core)
        if not roots:
            continue
        key = (core, pos)
        if key in seen:
            continue
        seen.add(key)
        ms = I.match_word(core, roots[:3], pos)
        if not ms:
            continue
        if len({m["root"] for m in ms}) > 1:  # جذران محتملان: يُرجَّح ما تشهد له المعاجم بورود الكلمة في مادته
            ev = {rt: _root_evidence(_strip_tashkeel(core), rt) for rt in {m["root"] for m in ms}}
            roots = sorted(roots, key=lambda rt: -ev.get(rt, -1))
        ms.sort(key=lambda m: (roots.index(m["root"]), m["order"]))
        m = ms[0]
        r = {
            "الكلمة": diac, "الجذع المعتبر": core, "الجذر": " ".join(m["root"]), "نوع الجذر": I.root_type(m["root"]),
            "الصيغة": m["desc"], "الوزن": m["wazn"], "الأصل": m["asl"],
            "خطوات الإعلال": [{"النوع": s["النوع"], "الخطوة": s["الخطوة"], "فصار": s["الصورة"]} for s in m["steps"]] or "لا إعلال فيه",
            "الوزن على لفظه": m["swazn"] if m["steps"] and any(x["النوع"] != "إدغام" for x in m["steps"]) else m["wazn"],
        }
        if pos == "verb" and m["form"] == "I" and m["wazn"].startswith("فَعَ"):
            ah = _ain_haraka((a.get("lex") or "").split("_")[0].split("-")[0])
            if ah:
                r["باب الفعل"] = _BAB.get(ah, "")
                r["الوزن"] = {"ضمة": "فَعَلَ", "كسرة": "فَعَلَ", "فتحة": "فَعِلَ"}[ah] if m["steps"] else r["الوزن"]
        alts = list(dict.fromkeys(f"{x['wazn']} ({x['desc']})" for x in ms[1:6] if x["wazn"] != m["wazn"]))[:3]
        if alts:
            r["أوزان أخرى تحتملها"] = alts
        if len(roots) > 1 and roots[0] == m["root"]:
            others = [" ".join(x) for x in roots[1:] if any(y["root"] == x for y in ms)]
            if others:
                r["جذر محتمل آخر"] = others
        readings.append(r)
        if len(readings) >= 3:
            break
    if not readings:
        return {"تنبيه": "لم أستطع وزن هذه الكلمة بالقوالب القياسية؛ قد تكون جامدة أو رباعية أو أعجمية، أو على وزن غير مدرج.",
                "التحليل الصرفي": _fmt(analyses[0]) if analyses else None}
    return {"القراءات": readings,
            "ملاحظة": "الأصل والخطوات مولّدة بقواعد الإعلال والإبدال ومتحقَّق منها بإعادة الكلمة نفسها؛ وما فيه خلاف بين البصريين والكوفيين أو بين سيبويه والأخفش يُنبَّه عليه في الخطوة."}


def _stem_core(a: dict) -> str:
    """الجذع مع ما يدخل في الوزن (حرف المضارعة، ولاحقة التأنيث والجمع) دون السوابق والضمائر وعلامة الإعراب."""
    diac, stem, bw = a.get("diac") or "", a.get("stem") or "", a.get("bw") or ""
    if not stem or stem not in diac:
        return diac
    segs = [x.rpartition("/") for x in bw.split("+")]
    k = next((j for j, (t, _, _g) in enumerate(segs) if stem in t), None)
    core = stem
    if k is not None:
        j = k - 1
        while j >= 0 and segs[j][2].startswith("IV") and "SUFF" not in segs[j][2]:
            core = segs[j][0] + core
            j -= 1
        j = k + 1
        while j < len(segs) and segs[j][2].startswith("NSUFF") and "FEM_SG" in segs[j][2]:
            core = core + segs[j][0]
            j += 1
    return core.replace("ٱ", "ا")


def _core_of_typed(w, core):
    return w


_DERIV_I = [("فاعِل", "اسم الفاعل"), ("مَفْعُول", "اسم المفعول"), ("مَفْعَل", "المصدر الميمي"),
            ("مَفْعَل", "اسم الزمان والمكان"), ("مِفْعَل", "اسم الآلة"), ("مِفْعال", "اسم الآلة"), ("مِفْعَلَة", "اسم الآلة"),
            ("فَعّال", "صيغة المبالغة"), ("مِفْعال", "صيغة المبالغة"), ("فَعُول", "صيغة المبالغة"), ("فَعِيل", "صيغة المبالغة"),
            ("فَعِل", "صيغة المبالغة"), ("أَفْعَل", "اسم التفضيل"), ("فَعْلَة", "اسم المرة"), ("فِعْلَة", "اسم الهيئة")]
_DERIV_AUG = {
    "IV": ("إِفْعال", "مُفْعِل", "مُفْعَل"), "II": ("تَفْعِيل", "مُفَعِّل", "مُفَعَّل"), "III": ("مُفاعَلَة", "مُفاعِل", "مُفاعَل"),
    "VII": ("اِنْفِعال", "مُنْفَعِل", "مُنْفَعَل"), "VIII": ("اِفْتِعال", "مُفْتَعِل", "مُفْتَعَل"), "IX": ("اِفْعِلال", "مُفْعَلّ", None),
    "V": ("تَفَعُّل", "مُتَفَعِّل", "مُتَفَعَّل"), "VI": ("تَفاعُل", "مُتَفاعِل", "مُتَفاعَل"), "X": ("اِسْتِفْعال", "مُسْتَفْعِل", "مُسْتَفْعَل"),
}


def _attested(word: str, root: str) -> bool:
    """هل الصيغة المولّدة مستعملة في المعجم الصرفي بالجذر نفسه؟"""
    try:
        for a in _analyzer().analyze(_strip_tashkeel(word)):
            r = (a.get("root") or "").split(".")
            if len(r) == len(root) and all(x == "#" or x.translate(HAMZA_FORMS) == y for x, y in zip(r, root)) \
                    and a.get("pos") != "verb" and not (a.get("prc1") not in (None, "0", "") or a.get("prc0") not in (None, "0", "")):
                return True
    except Exception:
        pass
    return False


@mcp.tool()
def mushtaqqat(verb: str, ain_haraka: str | None = None) -> dict:
    """المشتقات القياسية من الفعل مع أوزانها وإعلالها: اسم الفاعل، واسم المفعول، والمصدر الميمي، واسما الزمان والمكان، واسم الآلة، وصيغ المبالغة، واسم التفضيل، واسما المرة والهيئة، ومصدر المزيد.
    يُبيَّن لكل صيغة: وزنها، وصورتها بعد الإعلال، وهل هي مستعملة في المعجم الصرفي أو قياسية لم تُسمع فيه.
    verb: الفعل الماضي (كتب، قال، رمى، وعد، استقام، اختار). ain_haraka: حركة عين المضارع للثلاثي إن أردت فرضها («ضمة» أو «كسرة» أو «فتحة»)."""
    I = _ilal()
    cands = [a for a in _analyzer().analyze(_strip_tashkeel(verb.strip())) if a.get("pos") == "verb" and a.get("asp") == "p"]
    if not cands:
        cands = [a for a in _analyzer().analyze(_strip_tashkeel(verb.strip())) if a.get("pos") == "verb"]
    if not cands:
        return {"تنبيه": "لم أجد هذا الفعل في المعجم الصرفي؛ اكتبه ماضيًا (مثل: كتب)."}
    a = max(cands, key=lambda x: float(x.get("pos_lex_logprob", -99) or -99))
    lex = (a.get("lex") or "").split("_")[0].split("-")[0]
    roots = _resolve_roots(a.get("root") or "", lex)
    if not roots:
        return {"تنبيه": "لم أستطع تحديد جذر الفعل."}
    # الباب: من قالب الماضي المطابق
    form, root = None, None
    for rt in roots[:3]:
        ms = I.match_word(lex if lex.endswith(("َ", "ا", "ى")) else lex + "َ", [rt], "verb")
        ms = [m for m in ms if not m["wazn"].startswith("يَ") and not m["wazn"].startswith("يُ")]
        if ms:
            form, root = ms[0]["form"], rt
            break
    if not form:
        form, root = "I", roots[0]
    if len(root) != 3:
        return {"تنبيه": "توليد المشتقات للثلاثي ومزيده فقط."}
    ah = ain_haraka or _ain_haraka(lex) or _ain_by_analogy(lex, True)[0]
    rows = []
    if form == "I":
        tmpl = list(_DERIV_I)
        # اسم الزمان والمكان: مَفْعِل من مكسور العين في المضارع ومن المثال، وإلا مَفْعَل
        if ah == "كسرة" and root[2] not in "وي" or root[0] == "و":
            tmpl[3] = ("مَفْعِل", "اسم الزمان والمكان")
    else:
        m, fa, mf = _DERIV_AUG[form]
        tmpl = [(m, "المصدر"), (fa, "اسم الفاعل")]
        if mf:
            tmpl += [(mf, "اسم المفعول"), (mf, "اسم الزمان والمكان والمصدر الميمي")]
        if form == "II" and root[2] in "وي":
            tmpl[0] = ("تَفْعِلَة", "المصدر")
    for wazn, name in tmpl:
        ctx = I.ctx_for(wazn, "noun", form)
        r = I.derive(I.parse_wazn(wazn), root, ctx)
        if not r:
            continue
        asl, surf, steps = r
        rows.append({"الصيغة": name, "الوزن": wazn, "الكلمة": surf,
                     "مستعملة في المعجم الصرفي": _attested(surf, root),
                     **({"الأصل": asl, "الإعلال": [s["الخطوة"] for s in steps]} if steps else {})})
    return {"الفعل": a.get("diac"), "الجذر": " ".join(root), "نوعه": I.root_type(root),
            "البناء": "ثلاثي مجرد" if form == "I" else f"مزيد (الباب {form})",
            "حركة عين المضارع": ah if form == "I" else None, "المشتقات": rows,
            "ملاحظة": "الصيغ قياسية؛ وما لم يُستعمل في المعجم الصرفي لا يعني أنه غير مسموع في المعاجم التراثية (فابحثه بـ maajim). "
                      "ومصادر الثلاثي سماعية فلا تُولَّد قياسًا؛ وتُرى في أسرة الجذر (root_family). وصيغ المبالغة والصفة المشبهة سماعية في أكثرها."}


@mcp.tool()
def taqalib(root: str) -> dict:
    """تقاليب الجذر على طريقة الخليل في العين وابن جني في الاشتقاق الكبير: التباديل الستة لحروف الثلاثي (أو الأربعة والعشرون للرباعي)،
    وما استُعمل منها وما أُهمل بحسب المعاجم الخمسة عشر، مع عدد المعاجم التي ذكرت كل تقليب وأسمائها.
    root: الجذر بحروفه (كتب، أو ك ت ب)."""
    import itertools, sqlite3
    letters = [c for c in _strip_tashkeel(root).translate(HAMZA_FORMS) if c not in " .،"]
    if len(letters) not in (3, 4):
        return {"تنبيه": "أعطِ جذرًا ثلاثيًّا أو رباعيًّا."}
    if not os.path.exists(MAAJIM_DB):
        return {"تنبيه": "فهرس المعاجم لم يُبنَ بعد."}
    con = sqlite3.connect(f"file:{MAAJIM_DB}?mode=ro", uri=True)
    names = dict(con.execute("SELECT id, name FROM books").fetchall())
    perms = sorted(set("".join(p) for p in itertools.permutations(letters)))
    rows = []
    for p in perms:
        books = [b for (b,) in con.execute("SELECT DISTINCT u.book FROM keys k JOIN units u ON u.id = k.unit WHERE k.key = ?", (_mk(p),))]
        nonq = [b for b in books if b not in ("cayn", "jamhara", "tahdhib", "muhkam")]
        status = "مستعمل" if len(nonq) >= 2 else ("نادر (في معجم واحد)" if len(nonq) == 1 else
                                                   ("في معاجم التقاليب وحدها" if books else "مهمل"))
        rows.append({"التقليب": " ".join(p), "الحال": status, "عدد المعاجم": len(books),
                     "المعاجم": [names.get(b, b) for b in books]})
    con.close()
    used = [r["التقليب"] for r in rows if r["الحال"] == "مستعمل"]
    return {"الجذر": " ".join(letters), "التقاليب": rows, "المستعمل": used,
            "المهمل": [r["التقليب"] for r in rows if r["الحال"] == "مهمل"],
            "ملاحظة": "الحكم بالاستعمال مبني على ورود المادة في المعاجم المرتبة على الحروف (لا يكفي ذكرها في أبواب التقاليب، فقد يُذكر فيها المهمل). "
                      "وللنظر في المعنى الجامع بين التقاليب (الاشتقاق الأكبر) اعرض موادّها بـ maajim."}



# ───────────── الإعراب: محلّل نحوي حديث (Stanza/UD) مع نقل علاقاته إلى أبواب النحو العربي ─────────────

@lru_cache(maxsize=1)
def _stanza():
    import stanza
    for pkg in ("default_accurate", "default"):
        try:
            return stanza.Pipeline("ar", processors="tokenize,mwt,pos,lemma,depparse", package=pkg,
                                   download_method=None, verbose=False, use_gpu=False), pkg
        except Exception:
            continue
    raise RuntimeError("نموذج المحلل النحوي (Stanza) غير منزّل؛ شغّل سكربت التثبيت مرة أخرى.")


_NASIKH_KANA = {"كان", "أصبح", "أضحى", "ظل", "أمسى", "بات", "صار", "ليس", "زال", "برح", "فتئ", "انفك", "دام"}
_NASIKH_INNA = {"إن": "إنّ", "أن": "أنّ", "كأن": "كأنّ", "لكن": "لكنّ", "ليت": "ليت", "لعل": "لعلّ"}
_ZARF = {"يوم", "ليلة", "صباح", "مساء", "عند", "قبل", "بعد", "فوق", "تحت", "أمام", "خلف", "وراء", "بين", "حين", "وقت",
         "ساعة", "دون", "لدى", "لدن", "حول", "يمين", "شمال", "شهر", "عام", "سنة", "أبد", "غدا", "أمس", "الآن", "ثم", "هنا", "حيث",
         "إذ", "إذا", "متى", "أين", "كلما", "لما", "مع", "نحو", "جانب", "قرب", "وسط"}
_PARTICLES = {
    "لم": "حرف نفي وجزم وقلب، مبني على السكون لا محل له من الإعراب",
    "لن": "حرف نفي ونصب واستقبال، مبني على السكون لا محل له من الإعراب",
    "لا": "حرف نفي مبني على السكون لا محل له من الإعراب",
    "ما": "حرف نفي مبني على السكون لا محل له من الإعراب",
    "قد": "حرف تحقيق (أو تقليل مع المضارع) مبني على السكون لا محل له من الإعراب",
    "سوف": "حرف استقبال مبني على الفتح لا محل له من الإعراب",
    "س": "حرف استقبال مبني على الفتح لا محل له من الإعراب",
    "هل": "حرف استفهام مبني على السكون لا محل له من الإعراب",
    "أ": "همزة الاستفهام، حرف مبني على الفتح لا محل له من الإعراب",
    "يا": "حرف نداء مبني على السكون لا محل له من الإعراب",
    "أن": "حرف مصدري ونصب مبني على السكون لا محل له من الإعراب",
    "كي": "حرف مصدري ونصب مبني على السكون لا محل له من الإعراب",
    "إذن": "حرف جواب وجزاء ونصب مبني على السكون لا محل له من الإعراب",
    "إن": "حرف شرط جازم مبني على السكون لا محل له من الإعراب",
    "لو": "حرف شرط غير جازم مبني على السكون لا محل له من الإعراب",
    "بل": "حرف إضراب مبني على السكون لا محل له من الإعراب",
    "إلا": "أداة استثناء (أو حصر) مبنية على السكون لا محل لها من الإعراب",
    "و": "حرف عطف مبني على الفتح لا محل له من الإعراب",
    "ف": "حرف عطف (أو استئناف أو جواب) مبني على الفتح لا محل له من الإعراب",
    "ثم": "حرف عطف مبني على الفتح لا محل له من الإعراب",
    "أو": "حرف عطف مبني على السكون لا محل له من الإعراب",
    "أم": "حرف عطف مبني على السكون لا محل له من الإعراب",
    "حتى": "حرف غاية (جر أو عطف أو ابتداء) مبني على السكون لا محل له من الإعراب",
}
_CASE_AR = {"Nom": "مرفوع", "Acc": "منصوب", "Gen": "مجرور"}
_CASE_MAHALL = {"Nom": "في محل رفع", "Acc": "في محل نصب", "Gen": "في محل جر"}
_MOOD_AR = {"Ind": "مرفوع", "Sub": "منصوب", "Jus": "مجزوم"}


def _feats(w) -> dict:
    return dict(x.split("=", 1) for x in (w.feats or "").split("|") if "=" in x)


def _bare_ar(s: str) -> str:
    return _norm(_strip_tashkeel(s or ""))


def _sign(w, f, case_or_mood: str) -> str:
    """علامة الإعراب الأصلية أو الفرعية بحسب نوع الكلمة."""
    t = _strip_tashkeel(w.text or "")
    num, gen = f.get("Number"), f.get("Gender")
    if w.upos == "VERB":
        five = t.endswith(("ون", "ين", "ان")) and f.get("Person") in ("2", "3") and num in ("Plur", "Dual") or \
            (t.endswith("ين") and gen == "Fem" and f.get("Person") == "2")
        if case_or_mood == "Ind":
            return "ثبوت النون لأنه من الأفعال الخمسة" if five else ("الضمة المقدرة على آخره للثقل" if t.endswith(("و", "ي")) else
                                                                     "الضمة المقدرة على آخره للتعذر" if t.endswith(("ا", "ى")) else "الضمة الظاهرة على آخره")
        if case_or_mood == "Sub":
            return "حذف النون لأنه من الأفعال الخمسة" if five else ("الفتحة المقدرة للتعذر" if t.endswith(("ا", "ى")) else "الفتحة الظاهرة على آخره")
        if case_or_mood == "Jus":
            return "حذف النون لأنه من الأفعال الخمسة" if five else ("حذف حرف العلة من آخره" if t.endswith(("و", "ي", "ا", "ى")) else "السكون الظاهر على آخره")
        return ""
    if num == "Dual":
        return "الألف لأنه مثنى" if case_or_mood == "Nom" else "الياء لأنه مثنى"
    if num == "Plur" and gen == "Masc" and t.endswith(("ون", "ين", "و", "ي")) and w.upos in ("NOUN", "ADJ", "PROPN"):
        return "الواو لأنه جمع مذكر سالم" if case_or_mood == "Nom" else "الياء لأنه جمع مذكر سالم"
    if num == "Plur" and gen == "Fem" and t.endswith("ات") and case_or_mood == "Acc":
        return "الكسرة نيابة عن الفتحة لأنه جمع مؤنث سالم"
    if _bare_ar(w.lemma) in ("اب", "اخ", "حم", "فو", "ذو") and t.endswith(("و", "ا", "ي")) and f.get("Definite") == "Cons":
        return {"Nom": "الواو", "Acc": "الألف", "Gen": "الياء"}[case_or_mood] + " لأنه من الأسماء الخمسة"
    if t.endswith(("ى", "ا")) and len(t) > 2 and not t.endswith("اء"):
        return {"Nom": "الضمة", "Acc": "الفتحة", "Gen": "الكسرة"}[case_or_mood] + " المقدرة على الألف للتعذر"
    if t.endswith("ي") and w.upos in ("NOUN", "ADJ") and f.get("Definite") in ("Def", "Cons") and case_or_mood != "Acc" and len(t) > 3:
        return {"Nom": "الضمة", "Gen": "الكسرة"}[case_or_mood] + " المقدرة على الياء للثقل"
    if case_or_mood == "Gen" and f.get("Definite") == "Ind" and f.get("Diptote") == "Yes":
        return "الفتحة نيابة عن الكسرة لأنه ممنوع من الصرف"
    return {"Nom": "الضمة الظاهرة", "Acc": "الفتحة الظاهرة", "Gen": "الكسرة الظاهرة"}[case_or_mood] + " على آخره" + \
        ("" if f.get("Definite") != "Ind" else " (منوّنًا)")


def _verb_desc(w, f) -> str:
    asp, mood, voice = f.get("Aspect"), f.get("Mood"), f.get("Voice")
    pas = " مبني للمجهول" if voice == "Pass" else ""
    lem = _bare_ar(w.lemma)
    naqis = " ناقص (ناسخ)" if lem in {_norm(x) for x in _NASIKH_KANA} else ""
    if asp == "Perf":
        return f"فعل ماضٍ{naqis}{pas} مبني"
    if mood == "Imp" or asp is None and w.xpos and w.xpos.startswith("VC"):
        return f"فعل أمر{pas} مبني"
    m = mood or "Ind"
    return f"فعل مضارع{naqis}{pas} {_MOOD_AR.get(m, 'مرفوع')} وعلامة {'رفعه' if m == 'Ind' else 'نصبه' if m == 'Sub' else 'جزمه'} {_sign(w, f, m)}"


def _role(w, sent, by_id, kids) -> tuple:
    """(الباب النحوي، الحالة المتوقعة) للكلمة بحسب علاقتها بعاملها."""
    rel = (w.deprel or "").split(":")[0]
    sub = w.deprel or ""
    head = by_id.get(w.head)
    f = _feats(w)
    hf = _feats(head) if head else {}
    lem = _bare_ar(w.lemma)
    hk = kids.get(w.head, [])
    if rel == "root":
        if w.upos == "VERB":
            return "", None
        cop = [k for k in kids.get(w.id, []) if k.deprel == "cop"]
        if cop:
            return f"خبر {_strip_tashkeel(cop[0].text)}", "Acc"
        inna = [k for k in kids.get(w.id, []) if _bare_ar(k.text) in {_norm(x) for x in _NASIKH_INNA} and k.id < w.id]
        if inna:
            return f"خبر {_NASIKH_INNA.get(_strip_tashkeel(inna[0].text), _strip_tashkeel(inna[0].text))}", "Nom"
        return "خبر", "Nom"
    if sub == "nsubj:pass":
        return "نائب فاعل", "Nom"
    if rel == "nsubj":
        if head is not None and head.upos == "VERB":
            if _bare_ar(head.lemma) in {_norm(x) for x in _NASIKH_KANA}:
                return f"اسم {_strip_tashkeel(head.text)}", "Nom"
            return "فاعل", "Nom"
        cop = [k for k in hk if k.deprel == "cop"]
        if cop:
            return f"اسم {_strip_tashkeel(cop[0].text)}", "Nom"
        inna = [k for k in hk if _bare_ar(k.text) in {_norm(x) for x in _NASIKH_INNA}]
        if inna or f.get("Case") == "Acc":
            n = _strip_tashkeel(inna[0].text) if inna else "إنّ"
            return f"اسم {_NASIKH_INNA.get(n, n)}", "Acc"
        return "مبتدأ", "Nom"
    if rel == "obj":
        return "مفعول به", "Acc"
    if rel == "iobj":
        return "مفعول به ثانٍ", "Acc"
    if rel == "amod":
        return f"نعت لـ«{_strip_tashkeel(head.text)}»" if head else "نعت", hf.get("Case")
    own_cop = [k for k in kids.get(w.id, []) if k.deprel == "cop" or (k.upos == "AUX" and _bare_ar(k.lemma) in {_norm(x) for x in _NASIKH_KANA})]
    if own_cop and w.upos != "VERB":
        n = _strip_tashkeel(own_cop[0].text)
        return f"خبر {n}" + ("، والجملة معطوفة على ما قبلها" if rel == "conj" else ""), "Acc"
    if rel == "conj":
        return f"معطوف على «{_strip_tashkeel(head.text)}»" if head else "معطوف", hf.get("Case") if head and head.upos != "VERB" else None
    if rel == "appos":
        return f"بدل من «{_strip_tashkeel(head.text)}»" if head else "بدل", hf.get("Case")
    if rel in ("nmod", "obl"):
        case_kids = [k for k in kids.get(w.id, []) if k.deprel == "case"]
        if case_kids:
            return f"اسم مجرور بـ«{_strip_tashkeel(case_kids[0].text)}»", "Gen"
        if rel == "nmod" and f.get("Case") == "Gen":
            return "مضاف إليه", "Gen"
        if f.get("Case") == "Acc" or rel == "obl":
            if lem in {_norm(x) for x in _ZARF} or w.upos == "ADV":
                return "ظرف (مفعول فيه)", "Acc"
            if head is not None and head.upos == "VERB" and _same_root(w.lemma, head.lemma):
                return "مفعول مطلق", "Acc"
            if w.upos in ("ADJ",) and f.get("Definite") == "Ind":
                return "حال", "Acc"
            if f.get("Definite") == "Ind" and w.upos == "NOUN":
                return "مفعول لأجله أو تمييز (بحسب المعنى)", "Acc"
            return "منصوب على الظرفية أو المفعولية (بحسب المعنى)", "Acc"
        return "مضاف إليه", "Gen"
    if rel == "xcomp" or rel == "advcl" and w.upos == "ADJ":
        if f.get("Case") == "Acc" and w.upos in ("ADJ", "NOUN"):
            return "حال" if f.get("Definite") == "Ind" else "خبر الفعل الناسخ أو مفعول به ثانٍ", "Acc"
    if rel == "nummod":
        return "عدد", f.get("Case")
    if rel == "vocative":
        return "منادى", "Acc"
    if rel == "advmod":
        return "ظرف أو حال (بحسب المعنى)", "Acc"
    if rel == "ccomp":
        return "جملة في محل نصب مفعول به", None
    if rel == "acl":
        if head is not None and (_bare_ar(head.lemma) in ("الذي", "التي", "الذين", "اللذان", "اللتان", "اللاتي", "اللواتي", "من", "ما") or (head.upos in ("PRON", "DET"))):
            return "جملة صلة الموصول لا محل لها من الإعراب", None
        if head is not None and hf.get("Definite") == "Ind":
            return f"جملة {_CASE_MAHALL.get(hf.get('Case'), 'في محل')} نعت لـ«{_strip_tashkeel(head.text)}»", None
        return f"جملة {_CASE_MAHALL.get(hf.get('Case'), 'في محل')} حال من «{_strip_tashkeel(head.text)}»" if head is not None else "جملة حالية أو نعت", None
    return "", f.get("Case")


def _same_root(a: str, b: str) -> bool:
    try:
        ra = {x.get("root") for x in _analyzer().analyze(_strip_tashkeel(a or "")) if x.get("root")}
        rb = {x.get("root") for x in _analyzer().analyze(_strip_tashkeel(b or "")) if x.get("root")}
        return bool(ra & rb)
    except Exception:
        return False


_ZURUF_MAKAN = {"بين", "عند", "فوق", "تحت", "امام", "خلف", "وراء", "دون", "حول", "لدي", "لدن", "تلقاء", "حيال", "ازاء", "مع"}
_ZURUF_ZAMAN = {"بعد", "قبل", "حين", "يوم", "ليله", "عشيه", "غدا", "صباح", "مساء", "ابدا", "قط", "عوض"}
_JAZM = {"لم", "لما", "إن"}  # بالهمزة كما تُكتب: «إن» الشرطية غير «أن» الناصبة
_NASB = {"لن", "أن", "كي", "لكي", "إذن", "لئلا"}


def _set_feat(w, key, val):
    fs = dict(x.split("=", 1) for x in (w.feats or "").split("|") if "=" in x)
    fs[key] = val
    w.feats = "|".join(f"{k}={v}" for k, v in sorted(fs.items()))


def kids_of(sent, w):
    return [x for x in sent.words if x.head == w.id]


def _irab_rules(doc):
    """قواعد من كتب النحو تُصحَّح بها شجرة المحلل قبل الإعراب:
    الظرف (بعد، قبل، بين، عند...) اسم منصوب على الظرفية، ومجرور إن سبقه حرف جر؛
    والمضارع بعد «لم» و«لمّا» مجزوم، وبعد «لن» و«أن» و«كي» منصوب، وبعد «لا» الناهية مجزوم إذا كان من الأفعال الخمسة محذوف النون."""
    PREP = {"من", "في", "ب", "ل", "ك", "الي", "علي", "عن", "حتي", "منذ", "مذ"}
    for s_ in doc.sentences:
        toks = s_.tokens
        last_jus = cond_k = talab_k = None
        for k, tok in enumerate(toks):
            if any(x.upos == "VERB" and _feats(x).get("Mood") == "Imp" for x in tok.words):
                talab_k = k  # فعل أمر: ما بعده من مضارع جواب للطلب
            prev = _norm(_strip_tashkeel(toks[k - 1].text)) if k else ""
            prev = prev[1:] if len(prev) > 2 and prev[0] in "وف" else prev
            praw = _strip_tashkeel(toks[k - 1].text).replace("ٱ", "ا") if k else ""
            praw = praw[1:] if len(praw) > 2 and praw[0] in "وف" else praw
            for j, w in enumerate(tok.words):
                t = _norm(_strip_tashkeel(w.text))
                t = t[1:] if len(t) > 3 and t[0] in "وف" and (t[1:] in _ZURUF_MAKAN or t[1:] in _ZURUF_ZAMAN) else t
                if t in _ZURUF_MAKAN or t in _ZURUF_ZAMAN:
                    before = [_norm(_strip_tashkeel(x.text)) for x in tok.words[:j]]
                    gen = (j > 0 and before and before[-1] in PREP | {"ب", "ل", "ك"}) or (j == 0 and prev in PREP)
                    if w.upos in ("ADP", "SCONJ", "X", "NOUN", "ADV") and not (w.upos == "NOUN" and _feats(w).get("Case")):
                        w.upos = "NOUN"
                        if (w.deprel or "").startswith("case") or not w.deprel:
                            w.deprel = "obl"
                        _set_feat(w, "Case", "Gen" if gen else "Acc")
                        w.lemma = w.lemma or w.text
                        w.zarf = "مكان" if t in _ZURUF_MAKAN else "زمان"
                bare = _strip_tashkeel(tok.text).replace("ٓ", "")
                core = bare[1:] if len(bare) > 3 and bare[0] in "وف" else bare
                lam_amr = len(core) > 3 and core[0] == "ل" and core[1] in "يتن" and len(bare) > len(core)  # فَلْيَفْعَلْ، وَلْيَفْعَلْ
                is_imp = (w.upos in ("VERB", "AUX") and _feats(w).get("Aspect") == "Imp") or \
                         (w.upos == "X" and (core[:1] in "يتنأ" or lam_amr))
                first = j == next((i_ for i_, x in enumerate(tok.words) if x.upos not in ("CCONJ", "PART") or x is w), 0)
                if is_imp and (first or lam_amr):
                    stem = core
                    for suf in ("هما", "كما", "هم", "هن", "كم", "كن", "نا", "ني", "ها", "ه", "ك"):
                        if stem.endswith(suf) and len(stem) - len(suf) >= 3:
                            stem = stem[: -len(suf)]
                            break
                    # ما ثبتت نونه (الأفعال الخمسة) أو أُكِّد بالنون بعد لام القسم أو ثبت حرف علته في آخره لا يكون مجزومًا
                    nun = stem.endswith(("ون", "ين", "ان"))
                    emph = stem.endswith("ن") and core[:1] == "ل" and len(stem) > 4
                    weak = stem.endswith(("ى", "و")) and not stem.endswith("وا")
                    no_jus = nun or emph or weak
                    lam_amr = lam_amr and core[1:2] in "يت" and not emph
                    pr = praw[1:] if praw[:1] == "أ" and praw[1:] in ("لم", "فلم", "ولم") else praw
                    pr = pr[1:] if len(pr) > 2 and pr[0] in "وف" else pr
                    mood = None
                    if pr in _JAZM or lam_amr:
                        mood = "Jus"
                    elif pr in _NASB:
                        mood = "Sub"
                    elif prev == "لا" and core.startswith("ت") and not nun:
                        mood = "Jus"  # «لا» الناهية مع المخاطَب
                    elif prev == "من" and not nun and (k == 1 or praw != _strip_tashkeel(toks[k - 1].text)):
                        mood = "Jus"  # «مَن» الشرطية في صدر الكلام أو بعد الواو والفاء، لا الموصولة
                    elif bare[:1] in "وف" and last_jus is not None and k - last_jus <= 4 and not nun:
                        mood = "Jus"  # المعطوف على مجزوم
                    elif bare[:1] not in "وف" and not nun and cond_k is not None and 0 < k - cond_k <= 8:
                        mood = "Jus"  # جواب الشرط
                        cond_k = None
                    elif bare[:1] not in "وف" and not nun and talab_k is not None and 0 < k - talab_k <= 4:
                        mood = "Jus"  # جواب الطلب
                        talab_k = None
                    if mood == "Jus" and no_jus:
                        mood = None
                    if mood == "Jus" and (pr in ("إن",) or (prev == "من" and mood == "Jus" and cond_k is None and pr not in _JAZM)):
                        cond_k = k  # فعل الشرط: يُنتظر جوابه
                    if mood:
                        w.mood_rule = "jazm" if (pr in _JAZM or lam_amr) else "nasb" if pr in _NASB else \
                            "la" if prev == "لا" else "man" if prev == "من" else "coord" if bare[:1] in "وف" else "jawab"
                        if w.upos == "X":
                            w.upos = "VERB"
                            _set_feat(w, "Aspect", "Imp")
                        _set_feat(w, "Mood", mood)
                    if _feats(w).get("Mood") == "Jus":
                        last_jus = k
        # ما لم يُعيّن المحلل حالته يُستعان فيه بمُزيل الالتباس الصرفي (CAMeL BERT) قراءةً ثانية
        try:
            need = [k for k, tok in enumerate(toks) if any(x.upos in ("X", "NOUN", "ADJ", "PROPN") and not _feats(x).get("Case") for x in tok.words)]
            dis = _bert().disambiguate([_strip_tashkeel(t.text) for t in toks])
            # إذا خالف مُزيلُ الالتباس المحللَ في نوع الكلمة المفردة (اسم أو فعل مضارع) قُدِّم حكمه في نوعها وحالتها
            for k, tok in enumerate(toks):
                an = dis[k].analyses[0].analysis if dis[k].analyses else {}
                pos = an.get("pos", "")
                core = [x for x in tok.words if x.upos not in ("CCONJ", "ADP", "PRON", "PART", "DET", "PUNCT")]
                if len(core) != 1:
                    continue
                x = core[0]
                if x.upos == "VERB" and pos.startswith(("noun", "adj")) and an.get("cas") in ("n", "a", "g") \
                        and not any(c.deprel in ("nsubj", "obj") for c in kids_of(s_, x)):
                    x.upos = "NOUN"
                    x.feats = ""
                    _set_feat(x, "Case", {"n": "Nom", "a": "Acc", "g": "Gen"}[an["cas"]])
                elif x.upos in ("NOUN", "X") and pos == "verb" and an.get("asp") == "i" and an.get("mod") in ("i", "s", "j"):
                    x.upos = "VERB"
                    x.feats = ""
                    _set_feat(x, "Aspect", "Imp")
                    _set_feat(x, "Mood", {"i": "Ind", "s": "Sub", "j": "Jus"}[an["mod"]])
                    x.mood_rule = "bert"
            if need:
                for k in need:
                    an = dis[k].analyses[0].analysis if dis[k].analyses else {}
                    cas = {"n": "Nom", "a": "Acc", "g": "Gen"}.get(an.get("cas"))
                    if cas and an.get("pos", "").startswith(("noun", "adj")):
                        for x in toks[k].words:
                            if x.upos in ("X", "NOUN", "ADJ", "PROPN") and not _feats(x).get("Case"):
                                if x.upos == "X":
                                    x.upos = "NOUN"
                                _set_feat(x, "Case", cas)
                                break
        except Exception:
            pass
        # حالة الاسم من عامله القريب: اسم إنّ وأخواتها منصوب، والمضاف إليه مجرور، والمنادى المضاف منصوب
        INNA = {"إن", "أن", "لكن", "كأن", "ليت", "لعل", "إنما", "أنما"}
        NOMINAL = ("NOUN", "ADJ", "PROPN", "NUM", "X")
        prev_nom = None
        for k, tok in enumerate(toks):
            praw = _strip_tashkeel(toks[k - 1].text).replace("ٱ", "ا") if k else ""
            praw = praw[1:] if len(praw) > 2 and praw[0] in "وف" else praw
            w0 = tok.words[0]
            if w0.upos in NOMINAL and not getattr(w0, "zarf", None):
                case = None
                if praw in INNA:
                    case = "Acc"
                elif praw in ("يا", "أيها"):
                    case = "Acc" if _feats(w0).get("Definite") == "Cons" else "Nom"
                elif prev_nom is not None and (getattr(prev_nom, "zarf", None) or
                        (_feats(prev_nom).get("Definite") == "Cons" and prev_nom.upos in ("NOUN", "NUM", "X"))):
                    case = "Gen"
                if case:
                    _set_feat(w0, "Case", case)
            nom = [x for x in tok.words if x.upos in NOMINAL]
            prev_nom = nom[-1] if nom and tok.words[-1].upos != "PRON" else None
    return doc


def _irab_word(w, sent, by_id, kids) -> str:
    f = _feats(w)
    t = _strip_tashkeel(w.text)
    rel = w.deprel or ""
    if w.upos == "PUNCT":
        return ""
    if w.upos == "ADP" or rel == "case":
        return "حرف جر مبني لا محل له من الإعراب"
    if w.upos in ("CCONJ",) or rel == "cc":
        return _PARTICLES.get(t, "حرف عطف مبني لا محل له من الإعراب")
    if t in _NASIKH_INNA and w.upos in ("SCONJ", "PART", "X"):
        return f"{_NASIKH_INNA[t]}: حرف ناسخ (توكيد ونصب أو ما في معناه) مبني على الفتح لا محل له من الإعراب"
    if w.upos in ("PART", "SCONJ", "AUX") and t in _PARTICLES:
        return _PARTICLES[t]
    if (w.upos == "AUX" or rel == "cop") and (_bare_ar(w.lemma) in {_norm(x) for x in _NASIKH_KANA} or _bare_ar(w.text) in {_norm(x) for x in _NASIKH_KANA}):
        return _verb_desc(w, f).replace("ناقص (ناسخ) ", "").replace("فعل ماضٍ", "فعل ماضٍ ناقص (ناسخ)").replace("فعل مضارع", "فعل مضارع ناقص (ناسخ)") \
            + "، يرفع الاسم وينصب الخبر"
    if w.upos == "VERB":
        d = _verb_desc(w, f)
        role, _ = _role(w, sent, by_id, kids)
        if role and "جملة" in role:
            d += f"، والجملة {role.replace('جملة ', '')}"
        return d
    role, case = _role(w, sent, by_id, kids)
    case = f.get("Case") or case
    if getattr(w, "zarf", None):
        if case == "Acc":
            return f"ظرف {w.zarf} منصوب وعلامة نصبه الفتحة الظاهرة" + ("، وهو مضاف" if kids.get(w.id) else "")
        if case == "Gen":
            return "اسم مجرور وعلامة جره الكسرة الظاهرة" + ("، وهو مضاف" if kids.get(w.id) else "")
    mabni = w.upos in ("PRON", "DET") or (w.xpos or "").startswith(("S", "D")) or _bare_ar(w.lemma) in ("الذي", "التي", "الذين", "هذا", "هذه", "ذلك", "تلك", "هؤلاء", "من", "ما")
    kind = {"PRON": "ضمير", "DET": "اسم إشارة"}.get(w.upos, "")
    if mabni and f.get("Number") != "Dual":
        if role:
            return f"{kind + ' ' if kind else ''}مبني {_CASE_MAHALL.get(case, '')} {role}".replace("  ", " ").strip()
        return f"{kind + ' ' if kind else ''}مبني".strip()
    if not role:
        role = {"Nom": "اسم مرفوع", "Acc": "اسم منصوب", "Gen": "اسم مجرور"}.get(case, "")
    if case in _CASE_AR:
        sign = _sign(w, f, case)
        verb = {"Nom": "رفعه", "Acc": "نصبه", "Gen": "جره"}[case]
        out = f"{role} وعلامة {verb} {sign}" if role.startswith("اسم مجرور") else f"{role} {_CASE_AR[case]} وعلامة {verb} {sign}"
        if f.get("Definite") == "Cons":
            out += "، وهو مضاف"
        return out
    return role


def _end_mark(w, case_or_mood) -> str:
    """حركة الآخر المقترحة: الضمة أو الفتحة أو الكسرة أو السكون، منوّنة للنكرة."""
    f = _feats(w)
    t = _strip_tashkeel(w.text)
    if t.endswith(("ا", "ى", "و", "ي", "ون", "ين", "ان")) or (t.endswith("ات") and w.upos == "VERB"):
        return ""
    ind = f.get("Definite") == "Ind"
    if w.upos == "VERB":
        return {"Ind": "ُ", "Sub": "َ", "Jus": "ْ"}.get(case_or_mood or "", "")
    if t.endswith("ات") and case_or_mood == "Acc":
        return "ٍ" if ind else "ِ"
    m = {"Nom": ("ُ", "ٌ"), "Acc": ("َ", "ً"), "Gen": ("ِ", "ٍ")}.get(case_or_mood or "")
    if not m:
        return ""
    return m[1] if ind else m[0]


@mcp.tool()
def irab(sentence: str, detail: bool = True) -> dict:
    """إعراب الجملة كلمةً كلمة: الباب النحوي (فاعل، نائب فاعل، مبتدأ، خبر، اسم كان وخبرها، اسم إنّ وخبرها، مفعول به، مفعول مطلق، ظرف، حال، تمييز، نعت، معطوف، بدل، مضاف إليه، اسم مجرور...)
    والحكم (مرفوع، منصوب، مجرور، مجزوم، مبني) وعلامة الإعراب الأصلية أو الفرعية (الألف للمثنى، والواو والياء لجمع المذكر، والكسرة نيابة عن الفتحة لجمع المؤنث، وثبوت النون وحذفها للأفعال الخمسة، والمقدّرة للتعذر والثقل...)،
    مع الضبط المقترح لأواخر الكلمات بحسب مواقعها.
    يعتمد على المحلل النحوي Stanza (نموذج AraELECTRA المدرَّب على شجرة PADT في Universal Dependencies)، ثم تُنقل علاقاته إلى أبواب النحو العربي بقواعد.
    sentence: جملة أو جمل قليلة. detail: يعرض علاقة كل كلمة بعاملها في الشجرة."""
    try:
        nlp, pkg = _stanza()
    except Exception as e:
        return {"تنبيه": str(e)}
    doc = _irab_rules(nlp(_strip_tashkeel(sentence)))
    out_sents = []
    for s_ in doc.sentences:
        by_id = {w.id: w for w in s_.words}
        kids = {}
        for w in s_.words:
            kids.setdefault(w.head, []).append(w)
        rows = []
        for tok in s_.tokens:
            parts = []
            for w in tok.words:
                i = _irab_word(w, s_, by_id, kids)
                if not i:
                    continue
                part = {"الجزء": w.text, "الإعراب": i}
                if detail:
                    head = by_id.get(w.head)
                    part["العامل في الشجرة"] = head.text if head else "—"
                    part["العلاقة (UD)"] = w.deprel
                parts.append(part)
            if parts:
                rows.append({"الكلمة": tok.text, "الأجزاء": parts} if len(parts) > 1 else {"الكلمة": tok.text, **parts[0]})
        # الضبط المقترح للأواخر
        voc = []
        for tok in s_.tokens:
            seg = []
            for w in tok.words:
                f = _feats(w)
                _, case = _role(w, s_, by_id, kids) if w.upos not in ("VERB",) else ("", f.get("Mood") or "Ind")
                cm = f.get("Case") or case if w.upos != "VERB" else (f.get("Mood") or "Ind")
                seg.append(w.text + (_end_mark(w, cm) if w.upos in ("NOUN", "ADJ", "PROPN", "VERB") and f.get("Aspect") != "Perf" else ""))
            voc.append("".join(seg) if len(tok.words) > 1 else seg[0])
        out_sents.append({"الجملة": s_.text, "الإعراب": rows, "ضبط الأواخر المقترح": " ".join(voc)})
    return {"الجمل": out_sents, "النموذج": f"Stanza ({pkg})",
            "تنبيه": "الإعراب آليّ: المحلل مدرَّب على نصوص صحفية معاصرة، فتقلّ دقته في الشعر والتقديم والتأخير؛ وما احتمل وجهين (كالحال والتمييز، والمفعول لأجله، والظرف) يُذكر بوجهيه. "
                      "فراجع الإعراب على قواعد النحو قبل اعتماده، ولا سيما في النصوص التراثية."}


# ───────────── أدوات البحث: تخريج الشاهد، وموازنة التعابير، ونسبة النص، والتطور الدلالي، وكتب اللغة، والبديع ─────────────

def _ntoks(text: str) -> list:
    import re
    return [_norm(t) for t in re.findall("[ء-ي]+", _strip_tashkeel(text or ""))]


def _sim(a: list, b: list) -> float:
    import difflib
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _word_diff(a: list, b: list) -> list:
    import difflib
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            out.append({"في المُدخل": " ".join(a[i1:i2]) or "—", "في الرواية": " ".join(b[j1:j2]) or "—"})
    return out


_ATTR_TRIGGER = re.compile(r"(?:^|\s)(?:و|ف)?(?:قال|قول|كقول|لقول|بقول|انشد|وانشد|ينشد|انشده|انشدنا|انشدني)\s+")
_ATTR_STOP = {"في", "يصف", "يمدح", "يرثي", "يذكر", "يهجو", "يفخر", "يخاطب", "من", "وهو", "حين", "لما", "وقد", "ابياتا",
              "بيتا", "قصيدته", "معلقته", "قصيدة", "شعرا", "رحمه", "رضي", "عليه", "الله", "تعالي"}
_ATTR_ANON = {"الشاعر", "الاخر", "اخر", "بعضهم", "الراجز", "رجل", "القاءل", "الشعراء", "بعض", "قاءل", "فيه", "فيها",
              "تعالي", "الله", "النبي", "رسول", "ايضا", "فيهم", "لهم", "له", "لي", "عنه", "المصنف", "الشيخ", "المصنف", "الشارح", "المؤلف", "ابن", "هذا", "ذلك"}
_ATTR_CASE = {"ابي": "ابو", "ابا": "ابو", "امريء": "امرء", "امري": "امرء", "امرا": "امرء", "ذا": "ذو", "ذي": "ذو"}
_ATTR_ALIAS = {"ابو الطيب": "المتنبي", "ابو العلاء": "المعري", "ابو فراس": "ابو فراس", "حبيب": "ابو تمام",
               "مجنون": "قيس", "الحطيءه": "الحطيءه"}
_ATTR_TWO = {"ابو", "ابن", "ام", "امرء", "عبد", "بنت", "ذو", "ذي", "ابي"}


def _attr_key(toks: list) -> str:
    """مفتاح جمع النسبة: الاسم الأول، أو الأولان إن بدأ بكنية أو نسبة مركّبة (أبو، ابن، امرؤ...)."""
    if not toks:
        return ""
    toks = [_ATTR_CASE.get(toks[0], toks[0])] + list(toks[1:])
    k = " ".join(toks[:2]) if toks[0] in _ATTR_TWO and len(toks) > 1 else toks[0]
    return _ATTR_ALIAS.get(k, k)


def _attribution_in_books(ref: list, hits: dict) -> list:
    """من نسب البيت إلى قائله في كتب المدوّنة: «قال فلان» أو «قول فلان» أو «أنشد لفلان» قبل البيت مباشرة.
    hits = {رقم الفقرة: (الوفاة، العنوان، المؤلف، الفن، الجزء، الصفحة، النص)}. يُحصى كل كتاب مرة واحدة،
    ولا يُحصى «قال الشاعر» و«قال الآخر» (بلا تسمية)."""
    if len(ref) < 2:
        return []
    pat = re.compile(r"\W+".join(re.escape(t) for t in ref[:2]))
    agg = {}
    for pid, (died, title, author, genre, vol, page, text) in hits.items():
        nt = _norm(_strip_tashkeel(text))
        m = pat.search(nt)
        if not m:
            continue
        before = nt[max(0, m.start() - 90):m.start()]
        trig = list(_ATTR_TRIGGER.finditer(before))
        if not trig:
            continue
        tail = before[trig[-1].end():]
        if len(re.findall(r"[ء-ي]+", tail)) > 8:     # بين «قال» والبيت كلام كثير: ليست نسبة
            continue
        name = []
        for w in re.findall(r"[ء-ي]+|[:\[(«]", tail):
            if w in ":[(«" or w in _ATTR_STOP or len(name) >= 5:
                break
            name.append(w)
        if name and name[0].startswith("ل") and trig[-1].group(0).strip().endswith(("انشد", "انشده", "انشدنا", "انشدني")):
            name[0] = name[0][1:]                          # «أنشد لعنترة» ← عنترة
        if not name or name[0] in _ATTR_ANON or len(name[0]) < 3:
            continue
        k = _attr_key(name)
        a = agg.setdefault(k, {"names": {}, "books": {}})
        a["names"][" ".join(name[:3])] = a["names"].get(" ".join(name[:3]), 0) + 1
        a["books"].setdefault(title, (died or 9999, f"«{title}» (ت {died}هـ){_cite(vol, page)}"))
    out = []
    for k, a in agg.items():
        first = min(a["books"].values())
        out.append({"الشاعر": max(a["names"].items(), key=lambda x: (x[1], -len(x[0])))[0], "عدد الكتب": len(a["books"]),
                    "أقدمها": first[1]})
    out.sort(key=lambda x: (-x["عدد الكتب"], x["أقدمها"]))
    strong = [a for a in out if a["عدد الكتب"] >= 2]
    return strong[:6] if strong else out[:3]      # ما ورد في كتاب واحد لا يُعرض إلا إذا لم يُوجد غيره


def _strip_conj(toks: list) -> list:
    """الواو والفاء في أول الشطر لا تُعدّ فرقًا في الرواية عند المطابقة: «إنما الأمم» = «وإنما الأمم»، «يا ليت» = «فيا ليت»."""
    if toks and len(toks[0]) > 2 and toks[0][0] in "وف":
        return [toks[0][1:]] + toks[1:]
    return toks


def _takhrij_key(q: list, sc: float, v, copies: dict | None = None) -> tuple:
    """ترتيب مرشحات النسبة عند تساوي التطابق: ما ليس تضمينًا ولا معارضة (بعنوانه أو بأقواسه) أولًا، ثم ما وقع فيه
    الشطر المبحوث عنه صدرًا لا عجزًا (فمن جعل صدر غيره عجزًا لبيته فقد ضمّنه)، ثم الأقدم عصرًا.
    v = (الصدر، العجز، الرقم، الشاعر، القصيدة، البحر، العصر، ...)."""
    pos = 0
    if len(q) <= len(_ntoks((v[0] or "") + " " + (v[1] or ""))) * 0.7 and _sim(q, _ntoks(v[1])) > _sim(q, _ntoks(v[0])):
        pos = 1
    # ثم عند تساوي العصر: من نسبته إليه نسخٌ أكثر في المدوّنة (كالمتنبي وأبي العتاهية في «ما كل ما يتمنى المرء يدركه»)
    return (-round(sc, 2), _is_quotation(v[0], v[4]), pos, _era_rank(v[6], v[3]), -(copies or {}).get(_poet_key(v[3]), 0))


@mcp.tool()
def takhrij_shahid(verse: str, limit: int = 8, citations: bool = True) -> dict:
    """تخريج بيت الشعر: نسبته إلى قائله وقصيدته وبحره وعصره من مدوّنة «أشعار»، واختلاف رواياته (الألفاظ التي تختلف بين المصادر، واختلاف النسبة إن نُسب إلى أكثر من شاعر)،
    ثم مواضع الاستشهاد به في كتب النحو واللغة والبلاغة والأدب في المدوّنة التراثية، بالكتاب والجزء والصفحة، مع موضع «الشاهد فيه» إن صرّح به المؤلف.
    verse: البيت أو شطره (مشكولًا أو غير مشكول). citations: البحث عن مواضع الاستشهاد به."""
    import sqlite3
    q = _ntoks(verse)
    if len(q) < 3:
        return {"تنبيه": "أعطِ شطرًا كاملًا على الأقل."}
    out = {"البيت": verse}
    if os.path.exists(POETRY_DB):
        con = sqlite3.connect(f"file:{POETRY_DB}?mode=ro", uri=True)
        rare = sorted(set(q), key=len, reverse=True)[:8]
        match = " OR ".join(f'"{t}"' for t in rare if len(t) > 1)
        rows = con.execute("SELECT rowid FROM verses_fts WHERE verses_fts MATCH ? ORDER BY rank LIMIT 400", (match,)).fetchall()
        cands = []
        for (rid,) in rows:
            v = con.execute("SELECT v.sadr, v.ajuz, v.n, p.poet, p.title, p.meter, p.era, p.id FROM verses v JOIN poems p ON p.id = v.poem_id WHERE v.rowid = ?",
                            (rid,)).fetchone()
            if not v:
                continue
            t = _ntoks(v[0] + " " + v[1])
            qc, half = _strip_conj(q), len(q) <= len(t) * 0.7
            sc = max(_sim(qc, _strip_conj(t)), _sim(qc, _strip_conj(_ntoks(v[0]))) if half else 0,
                     _sim(qc, _strip_conj(_ntoks(v[1]))) if half else 0)
            cands.append((sc, v, t))
        copies = {}
        for sc0, v0, _t in cands:
            if sc0 >= 0.85 and not _is_quotation(v0[0], v0[4]) and _takhrij_key(q, sc0, v0)[2] == 0:
                copies[_poet_key(v0[3])] = copies.get(_poet_key(v0[3]), 0) + 1
        cands.sort(key=lambda x: _takhrij_key(q, x[0], x[1], copies))
        allc = [c for c in cands if c[0] >= 0.55]
        cands = allc[:max(1, min(int(limit), 30))]
        con.close()
        if cands:
            best = cands[0]
            sc, v, t = best
            out["النسبة"] = {"الشاعر": v[3], "العصر": v[6], "القصيدة": v[4], "البحر": v[5], "رقم البيت": v[2],
                             "نص البيت": f"{v[0]} * {v[1]}", "نسبة التطابق": round(sc, 2)}
            if _era_rank(v[6], v[3]) >= 9:
                out["تنبيه النسبة"] = ("أقدم من وجدته يقول هذا في المدوّنة شاعرٌ حديث أو مجهول العصر؛ فإن كان البيت معروفًا لقديم "
                                       "فأصله ليس في المدوّنة، وما هنا تضمينٌ له أو نسخة بلا عصر. لا تعتمد هذه النسبة حتى توثّقها من ديوانه.")
            poets, names = {}, {}
            rw, near, seen_t = [], [], set()
            # اختلاف النسبة يُحصى من المرشحات كلها لا من المعروض وحده، وإلا سقط من القائلين من تأخر ترتيبه
            # (كالعرجي في «أضاعوني وأي فتى أضاعوا»)
            for sc2, v2, t2 in allc:
                if sc2 >= 0.85 and not _is_quotation(v2[0], v2[4]) and _takhrij_key(q, sc2, v2)[2] == 0:
                    pn = _norm(_strip_tashkeel(v2[3] or ""))
                    poets[pn] = poets.get(pn, 0) + 1
                    names.setdefault(pn, v2[3])
            for sc2, v2, t2 in cands:
                key = " ".join(t2)
                if key in seen_t:
                    continue
                seen_t.add(key)
                quoted = _is_quotation(v2[0], v2[4])
                d = _word_diff(q, t2) if sc2 < 0.999 else []
                if sc2 < 0.999 and d:
                    item = {"الشاعر": v2[3], "القصيدة": v2[4], "النص": f"{v2[0]} * {v2[1]}", "الفروق": d[:6], "التطابق": round(sc2, 2)}
                    (rw if sc2 >= 0.85 and not quoted else near).append(item)
                elif quoted and v2 is not v:
                    near.append({"الشاعر": v2[3], "القصيدة": v2[4], "النص": f"{v2[0]} * {v2[1]}", "التطابق": round(sc2, 2)})
            if rw:
                out["اختلاف الرواية"] = rw
            if near:
                out["أبيات قريبة (معارضة أو تضمين أو اقتباس)"] = near[:6]
            if len(poets) > 1:
                out["اختلاف النسبة"] = [{"الشاعر": names[p], "عدد المواضع": n} for p, n in sorted(poets.items(), key=lambda x: -x[1])]
        else:
            out["النسبة"] = "لم أجده في مدوّنة «أشعار»."
    else:
        out["النسبة"] = "فهرس الشعر لم يُبنَ بعد."
    if citations and os.path.exists(CORPUS_DB):
        ref = q if "النسبة" not in out or not isinstance(out["النسبة"], dict) else _ntoks(out["النسبة"]["نص البيت"])
        grams = []
        for start in (0, max(0, len(ref) // 2 - 1), max(0, len(ref) - 3)):
            g = ref[start:start + 3]
            if len(g) == 3 and " ".join(g) not in grams:
                grams.append(" ".join(g))
        con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
        hits = {}
        for g in grams:
            for pid, text, vol, page, title, died, genre, author in con.execute(
                    "SELECT p.id, p.text, p.vol, p.page, b.title, b.died, b.genre, b.author FROM paras p JOIN books b ON b.id = p.book "
                    "WHERE p.id IN (SELECT rowid FROM paras_fts WHERE paras_fts MATCH ?) LIMIT 300", (f'"{g}"',)):
                if pid in hits:
                    continue
                pt = _ntoks(text)
                covered = sum(1 for x in set(ref) if x in pt) / max(1, len(set(ref)))
                if covered >= 0.6:
                    hits[pid] = (died, title, author, genre, vol, page, text)
        con.close()
        books_attr = _attribution_in_books(ref, hits)
        if books_attr:
            out["قائله في كتب المدوّنة"] = books_attr
            top = books_attr[0]
            nis = out.get("النسبة")
            pk = _attr_key(_ntoks(nis["الشاعر"])) if isinstance(nis, dict) else None
            if top["عدد الكتب"] >= 2 and pk not in {_attr_key(_ntoks(a["الشاعر"])) for a in books_attr}:
                out["تنبيه النسبة"] = (f"نسبته كتب المدوّنة إلى «{top['الشاعر']}» في {top['عدد الكتب']} كتبٍ أقدمها {top['أقدمها']}، "
                                       f"وليس فيها من نسبه إلى «{nis['الشاعر'] if isinstance(nis, dict) else ''}» الذي في «أشعار»؛ "
                                       "فالأرجح أن ما في «أشعار» تضمينٌ أو نسخة بغير نسبتها، ونسبةُ الكتب أولى بالاعتماد.")
        cites = []
        for pid, (died, title, author, genre, vol, page, text) in sorted(hits.items(), key=lambda x: x[1][0]):
            item = {"الكتاب": f"{title} (ت {died}هـ)", "الفن": genre, "الموضع": _cite(vol, page).lstrip("، ")}
            import re
            m = re.search(r"(?:والشاهد|الشاهد|وشاهده|استشهد|والاستشهاد)[^.]{0,220}", _strip_tashkeel(text))
            if m:
                item["الشاهد فيه"] = m.group(0)[:220]
            else:
                item["السياق"] = _strip_tashkeel(text)[:260]
            cites.append(item)
        out["مواضع الاستشهاد في المدوّنة"] = cites[:40] if cites else "لم أجد موضعًا في كتب المدوّنة."
        if cites:
            from collections import Counter
            out["عدد مواضع الاستشهاد بحسب الفن"] = dict(Counter(c["الفن"] for c in cites))
    out["ملاحظة"] = "المطابقة تقريبية على الألفاظ بعد توحيد الرسم؛ وما في «أشعار» قد يقع فيه تصحيف أو اختلاف عن المطبوع، فتُراجَع الرواية في الدواوين المحققة."
    return out


def _phrase_variants(phrase: str) -> list:
    toks = [_norm(t) for t in _strip_tashkeel(phrase).split() if t]
    if not toks:
        return []
    out = []
    for v in _variants(toks[0], True):
        out.append(" ".join([v] + toks[1:]))
    return out


@mcp.tool()
def usage_compare(expressions: list[str], genre: str | None = None, examples: int = 2) -> dict:
    """موازنة استعمال تعبيرين أو أكثر في المدوّنة التراثية: كم ورد كل تعبير، ونسبته لكل مليون كلمة، وتوزّعه على الفنون والقرون، مع شواهد منه.
    ينفع في مسائل التعدية والاستعمال الفصيح: «رغب في» و«رغب عن»، «تأسّف على» و«تأسّف لـ»، «استقال من»، «لعب بـ»، وفي المفاضلة بين صيغتين («مِئذنة» و«مأذنة»).
    expressions: قائمة التعابير (كلمة أو أكثر). genre: لتقييد الموازنة بفن («نحو»، «لغة»، «بلاغة»، «شعر»، «أدب»)."""
    import sqlite3, re
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد."}
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    total = con.execute("SELECT SUM(tokens) FROM books" + (" WHERE genre = ?" if genre else ""), [genre] if genre else []).fetchone()[0] or 1
    res = []
    for e in expressions[:6]:
        vs = _phrase_variants(e)
        if not vs:
            continue
        match = " OR ".join(f'"{v}"' for v in vs)
        sql = ("SELECT p.text, p.vol, p.page, b.title, b.died, b.genre FROM paras p JOIN books b ON b.id = p.book "
               "WHERE p.id IN (SELECT rowid FROM paras_fts WHERE paras_fts MATCH ?)" + (" AND b.genre = ?" if genre else "") + " ORDER BY b.died LIMIT 20000")
        rows = con.execute(sql, [match] + ([genre] if genre else [])).fetchall()
        n, by_g, by_c, ex = 0, {}, {}, []
        pats = [re.compile(r"(?<![ء-ي])" + re.escape(v) + r"(?![ء-ي])") for v in vs]
        for text, vol, page, title, died, g in rows:
            nt = " ".join(_ntoks(text))
            k = sum(len(p.findall(nt)) for p in pats)
            if not k:
                continue
            n += k
            by_g[g] = by_g.get(g, 0) + k
            c = (died - 1) // 100 + 1
            by_c[c] = by_c.get(c, 0) + k
            if len(ex) < examples:
                i = next((m.start() for p in pats for m in [p.search(nt)] if m), 0)
                ex.append({"الشاهد": nt[max(0, i - 80):i + 100], "المصدر": f"{title} (ت {died}هـ)" + _cite(vol, page)})
        res.append({"التعبير": e, "الورود": n, "لكل مليون كلمة": round(n * 1e6 / total, 2),
                    "بحسب الفن": by_g, "بحسب القرن": dict(sorted(by_c.items())), "شواهد": ex})
    con.close()
    return {"الموازنة": res,
            "ملاحظة": "كثرة الورود في المدوّنة قرينة على الاستعمال لا حكمٌ بالصواب أو الخطأ؛ وقد يختلف المعنى بحرف الجر نفسه (رغب فيه: أراده، ورغب عنه: زهد فيه). "
                      "ويُبحث التعبير بالسوابق في كلمته الأولى (و، ف، ب، ك، ل، ال)."}


def _load_side(name: str, kind: str, max_words: int):
    if kind == "poet":
        return _load_poet(name, 20000)
    return _load_corpus_book(name, max_words)


@mcp.tool()
def attribute_author(text: str, candidates: list[str], kind: str = "poet", features: int = 150) -> dict:
    """نسبة النص إلى قائله بالأسلوبية الإحصائية: يوازن النصَّ المجهول بنصوص المرشحين بمقياس «دلتا» لبروز (Burrows's Delta) ومقياس «دلتا جيب التمام» (Cosine Delta)،
    على أكثر الألفاظ دورانًا (وجلّها حروف المعاني والضمائر التي يستعملها الكاتب بلا قصد)، ثم يرتّب المرشحين من الأقرب إلى الأبعد.
    text: النص المجهول النسبة (يُستحسن ألا يقل عن ألف كلمة). candidates: أسماء المرشحين.
    kind: «poet» للشعراء من مدوّنة «أشعار»، أو «book» لكتب المدوّنة التراثية (جزء من العنوان أو اسم المؤلف). features: عدد الألفاظ الأكثر دورانًا."""
    import math
    from collections import Counter
    tt = [t for t in _ntoks(text)]
    if len(tt) < 100:
        return {"تنبيه": "النص قصير جدًّا؛ لا يصح الحكم الإحصائي بأقل من مئات الكلمات (ويُستحسن ألف فأكثر)."}
    corpora, info = {}, {}
    for c in candidates[:12]:
        t, inf = _load_side(c, kind, 200000)
        if t is None:
            return inf
        corpora[c] = _ntoks(t)
        info[c] = inf
    if len(corpora) < 2:
        return {"تنبيه": "أعطِ مرشحَين على الأقل."}
    allc = Counter()
    for toks in corpora.values():
        allc.update(toks)
    mfw = [w for w, _ in allc.most_common(int(features))]
    chunk = max(500, min(2000, len(tt)))

    def rel(toks):
        c = Counter(toks)
        n = len(toks) or 1
        return [c[w] / n for w in mfw]
    # المتوسط والانحراف من مقاطع المرشحين جميعًا
    segs = []
    for toks in corpora.values():
        for i in range(0, max(1, len(toks) - chunk + 1), chunk):
            segs.append(rel(toks[i:i + chunk]))
    if len(segs) < 3:
        return {"تنبيه": "نصوص المرشحين قصيرة جدًّا للحساب."}
    mean = [sum(s[j] for s in segs) / len(segs) for j in range(len(mfw))]
    sd = [math.sqrt(sum((s[j] - mean[j]) ** 2 for s in segs) / (len(segs) - 1)) or 1e-9 for j in range(len(mfw))]

    def z(v):
        return [(v[j] - mean[j]) / sd[j] for j in range(len(mfw))]
    zt = z(rel(tt))
    rows = []
    for c, toks in corpora.items():
        zc = z(rel(toks))
        delta = sum(abs(a - b) for a, b in zip(zt, zc)) / len(mfw)
        dot = sum(a * b for a, b in zip(zt, zc))
        na, nb = math.sqrt(sum(a * a for a in zt)), math.sqrt(sum(b * b for b in zc))
        cosd = 1 - dot / (na * nb) if na and nb else 1
        rows.append({"المرشح": info[c].get("الشاعر") or info[c].get("الكتاب") or c, "Delta": round(delta, 3),
                     "Cosine Delta": round(cosd, 3), "حجم نصوصه": len(toks)})
    rows.sort(key=lambda r: r["Cosine Delta"])
    gap = rows[1]["Cosine Delta"] - rows[0]["Cosine Delta"] if len(rows) > 1 else 0
    verdict = ("فارق واضح يرجّح الأول" if gap > 0.15 else "فارق متوسط" if gap > 0.05 else "الفارق ضئيل فلا ترجيح")
    return {"الترتيب (الأقرب أولًا)": rows, "الحكم": verdict, "حجم النص": len(tt), "الألفاظ المعتمدة": mfw[:30],
            "منهج": "Burrows (2002) وSmith & Aldridge (2011): تُحسب نسب أكثر الألفاظ دورانًا في كل نص، وتُحوَّل إلى درجات معيارية بمتوسط مقاطع المرشحين وانحرافها، "
                    "ثم يُقاس البعد. وأصغر القيمة أقرب. والنتيجة قرينة إحصائية تُضمّ إلى أدلة النسبة الأخرى (الرواية والتاريخ والأسلوب)، لا حكمٌ قاطع؛ "
                    "وتضعف إذا قصر النص عن ألف كلمة أو كان المرشحون من غير عصره أو فنّه."}


def _collocates_core(word, window, genre, min_count, clitics, cf, ct, top):
    import math
    con, vs, rows = _corpus_rows(word, clitics, genre, cf, ct, None, 30000)
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
        e = span * f / N
        b, c = span - a, f - a
        d = max(N - span - c, 1)
        ll = 2 * sum(o * math.log(o / ex) for o, ex in ((a, e), (b, span - e), (c, f - e), (d, N - span - f + e)) if o > 0 and ex > 0)
        if a > e:
            res.append((w, a, round(ll, 1)))
    res.sort(key=lambda x: -x[2])
    return node, res[:top], rows


@mcp.tool()
def semantic_change(word: str, periods: list[str] | None = None, top: int = 20, genre: str | None = None) -> dict:
    """التطور الدلالي للفظ عبر العصور في المدوّنة التراثية: لكل حقبة متلازماته الأقوى، وتكراره لكل مليون كلمة، ومقدار التداخل بين متلازمات الحقب (معامل جاكار)،
    وما استجدّ من متلازماته وما غاب؛ ومقدار ابتعاد معناه بين الحقب بتمثيلاته السياقية في نموذج CAMeLBERT الكلاسيكي (متوسط تمثيل اللفظ في سياقاته في كل حقبة).
    ينفع في تتبع انتقال اللفظ من معناه اللغوي إلى الاصطلاحي (المجاز، الاستعارة، البديع، النظم، الإعراب...).
    periods: حقب بالقرون الهجرية مثل ["2-4", "5-7", "8-11"] (الافتراضي). genre: لتقييدها بفن."""
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد."}
    import sqlite3
    periods = periods or ["2-4", "5-7", "8-11"]
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    out, colls, contexts = [], [], []
    for p in periods:
        a_, _, b_ = p.partition("-")
        cf, ct = int(a_), int(b_ or a_)
        size = con.execute("SELECT SUM(tokens) FROM books WHERE died > ? AND died <= ?" + (" AND genre = ?" if genre else ""),
                           [(cf - 1) * 100, ct * 100] + ([genre] if genre else [])).fetchone()[0] or 1
        node, res, rows = _collocates_core(word, 4, genre, 3, True, cf, ct, top)
        colls.append({w for w, _, _ in res})
        out.append({"الحقبة": f"القرن {cf}–{ct}", "الورود": node, "لكل مليون كلمة": round(node * 1e6 / size, 1),
                    "حجم نصوص الحقبة": size, "المتلازمات": [{"اللفظ": w, "المجاورة": n, "LL": ll} for w, n, ll in res]})
        vs = set(_variants(word, True))
        ctx = []
        for _pid, text, *_ in rows[:400]:
            toks = text.split()
            for i, t in enumerate(toks):
                if _cn(t).strip(".,،؛:!?()[]«»\"'") in vs:
                    ctx.append((" ".join(toks[max(0, i - 20):i + 21]), t))
                    break
            if len(ctx) >= 40:
                break
        contexts.append(ctx)
    con.close()
    shifts = []
    for i in range(len(periods) - 1):
        a, b = colls[i], colls[i + 1]
        j = len(a & b) / len(a | b) if a | b else 0
        shifts.append({"بين": f"{out[i]['الحقبة']} و{out[i + 1]['الحقبة']}", "تداخل المتلازمات (جاكار)": round(j, 2),
                       "متلازمات استجدّت": sorted(b - a)[:12], "متلازمات غابت": sorted(a - b)[:12]})
    # الابتعاد الدلالي بالتمثيلات السياقية
    try:
        import numpy as np
        cents = []
        for ctx in contexts:
            if len(ctx) < 5:
                cents.append(None)
                continue
            v = _embed([c for c, _ in ctx], [t for _, t in ctx]).numpy()
            c = v.mean(0)
            cents.append(c / (np.linalg.norm(c) or 1))
        for i, s in enumerate(shifts):
            a, b = cents[i], cents[i + 1]
            if a is not None and b is not None:
                s["الابتعاد الدلالي السياقي (1 − جيب التمام)"] = round(float(1 - a @ b), 4)
    except Exception as e:
        for s in shifts:
            s["الابتعاد الدلالي السياقي"] = f"تعذّر حسابه ({type(e).__name__})"
    return {"اللفظ": word, "الحقب": out, "التحوّل بين الحقب": shifts,
            "منهج": "المتلازمات بنسبة الأرجحية في نافذة ±4 كلمات؛ والابتعاد السياقي على طريقة Giulianelli et al. (2020) مبسّطةً: متوسط تمثيل اللفظ في 40 سياقًا من كل حقبة. "
                    "والقيمة تُقرأ بالموازنة بين الحقب لا منفردة، وتتأثر بتفاوت الفنون في كل حقبة."}


LUGHAWIYYAT = [
    ("0395AbuHilalCaskari.FuruqLughawiyya", "الفروق اللغوية لأبي هلال العسكري"),
    ("0328AbuBakrIbnAnbari.Addad", "الأضداد لابن الأنباري"),
    ("0244IbnSikkit.QalbWaIbdal", "القلب والإبدال لابن السكيت"),
    ("0351AbuTayyibLughawi.Ibdal", "الإبدال لأبي الطيب اللغوي"),
    ("0351AbuTayyibLughawi.Ittibac", "الإتباع لأبي الطيب اللغوي"),
    ("0582IbnBarri.FiTacrib", "في التعريب والمعرّب لابن بري"),
    ("0911Suyuti.MuhadhdhabFimaWaqaca", "المهذب فيما وقع في القرآن من المعرّب للسيوطي"),
    ("0685SadidDinMuhallabi.MuthallathatLughawiyya", "المثلثات اللغوية للمهلبي"),
    ("0429AbuMansurThacalibi.FiqhLugha", "فقه اللغة وسر العربية للثعالبي"),
]


@mcp.tool()
def lughawiyyat(word: str, books: list[str] | None = None, limit: int = 12) -> dict:
    """البحث في كتب اللغة المتخصصة: الفروق اللغوية (العسكري)، والأضداد (ابن الأنباري)، والقلب والإبدال (ابن السكيت، وأبو الطيب)، والإتباع، والمعرّب (ابن بري، والسيوطي)، والمثلثات، وفقه اللغة للثعالبي (الحقول الدلالية).
    يُخرج المواضع التي تذكر اللفظ، بالكتاب والجزء والصفحة. ينفع في: الفرق بين لفظين متقاربين، وهل اللفظ من الأضداد، وهل هو معرّب، وما أُبدل من حروفه، وحقله الدلالي.
    word: اللفظ أو لفظان (مثل «الحمد المدح» للفرق بينهما). books: لتقييد الكتب بجزء من أسمائها («الفروق»، «الأضداد»)."""
    import sqlite3, re
    if not os.path.exists(CORPUS_DB):
        return {"تنبيه": "المدوّنة لم تُبنَ بعد."}
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    have = {u: (bid, t) for u, bid, t in con.execute("SELECT uri, id, title FROM books")}
    sel = [(u, n) for u, n in LUGHAWIYYAT if not books or any(b in n for b in books)]
    missing = [n for u, n in sel if u not in have]
    words = [w for w in _strip_tashkeel(word).split() if w]
    vs_all = [set(_variants(w, True)) | {_norm(w)} for w in words]
    res = []
    for u, n in sel:
        if u not in have:
            continue
        bid = have[u][0]
        match = " AND ".join("(" + " OR ".join(f'"{v}"' for v in vs) + ")" for vs in vs_all)
        rows = con.execute("SELECT p.text, p.vol, p.page FROM paras p WHERE p.book = ? AND p.id IN (SELECT rowid FROM paras_fts WHERE paras_fts MATCH ?) "
                           "ORDER BY p.id LIMIT ?", (bid, match, int(limit))).fetchall()
        for text, vol, page in rows:
            loc = (f"ج{vol} ص{page}" if vol and vol < 200 else f"ص{page}" if page else "")
            res.append({"الكتاب": n, "الموضع": loc, "النص": _strip_tashkeel(text).replace("AUTO", "").strip()[:900]})
    con.close()
    out = {"اللفظ": word, "المواضع": res or "لم يرد في الكتب المختارة."}
    if missing:
        out["كتب لم تُضف بعد"] = missing
        out["تنبيه"] = "بعض الكتب لم تُضف إلى المدوّنة؛ أضفها بـ corpus_add_book أو أعد تشغيل سكربت التثبيت."
    return out


# ── البديع ──

_ANTONYMS = [("حياة", "موت"), ("حي", "ميت"), ("ليل", "نهار"), ("نور", "ظلام"), ("ضياء", "ظلام"), ("ابيض", "اسود"), ("بياض", "سواد"),
             ("سماء", "ارض"), ("شمس", "قمر"), ("قريب", "بعيد"), ("قرب", "بعد"), ("كبير", "صغير"), ("عظيم", "حقير"), ("طويل", "قصير"),
             ("غني", "فقير"), ("غنى", "فقر"), ("عز", "ذل"), ("عزيز", "ذليل"), ("حق", "باطل"), ("خير", "شر"), ("صدق", "كذب"),
             ("حلو", "مر"), ("فرح", "حزن"), ("ضحك", "بكى"), ("ضحك", "بكاء"), ("سرور", "حزن"), ("اول", "اخر"), ("ظاهر", "باطن"),
             ("قديم", "حديث"), ("جديد", "قديم"), ("حر", "عبد"), ("حر", "برد"), ("حار", "بارد"), ("قوي", "ضعيف"), ("قوة", "ضعف"),
             ("علم", "جهل"), ("عالم", "جاهل"), ("نفع", "ضر"), ("سلم", "حرب"), ("امن", "خوف"), ("رجاء", "ياس"), ("وصل", "هجر"),
             ("وصال", "هجر"), ("لقاء", "فراق"), ("قرب", "نوى"), ("يمين", "شمال"), ("شرق", "غرب"), ("صباح", "مساء"), ("غداة", "عشي"),
             ("صيف", "شتاء"), ("ذكر", "انثى"), ("رجل", "امراه"), ("دنيا", "اخره"), ("جنه", "نار"), ("ثواب", "عقاب"), ("ايمان", "كفر"),
             ("هدى", "ضلال"), ("رشد", "غي"), ("صحه", "سقم"), ("سقم", "شفاء"), ("داء", "دواء"), ("جود", "بخل"), ("كريم", "لئيم"),
             ("كرم", "لؤم"), ("شجاع", "جبان"), ("شجاعه", "جبن"), ("عدل", "ظلم"), ("جمع", "فرق"), ("فتح", "غلق"), ("دخل", "خرج"),
             ("اقبل", "ادبر"), ("اقبال", "ادبار"), ("علا", "سفل"), ("علو", "سفل"), ("فوق", "تحت"), ("امام", "خلف"), ("سهل", "صعب"),
             ("لين", "شده"), ("رخاء", "شده"), ("يسر", "عسر"), ("ضيق", "سعه"), ("بخيل", "جواد"), ("صادق", "كاذب"), ("مؤمن", "كافر"),
             ("نوم", "يقظه"), ("نائم", "يقظان"), ("عطش", "ري"), ("جوع", "شبع"), ("بكاء", "ضحك"), ("يبكي", "يضحك"), ("احيا", "امات"),
             ("يحيي", "يميت"), ("رفع", "خفض"), ("رفع", "وضع"), ("اعطى", "منع"), ("عطاء", "منع"), ("حضر", "غاب"), ("حاضر", "غائب"),
             ("صحو", "سكر"), ("حب", "بغض"), ("حبيب", "عدو"), ("صديق", "عدو"), ("وفاء", "غدر"), ("نجاح", "فشل"), ("سعد", "شقاء"),
             ("سعيد", "شقي"), ("ربح", "خسر"), ("ربح", "خساره"), ("بدايه", "نهايه"), ("كثير", "قليل"), ("كثره", "قله"), ("ملك", "مملوك")]


@lru_cache(maxsize=1)
def _antonym_index():
    idx = {}
    for a, b in _ANTONYMS:
        idx.setdefault(_norm(a), set()).add(_norm(b))
        idx.setdefault(_norm(b), set()).add(_norm(a))
    return idx


def _lemma_bare(w: str) -> str:
    try:
        an = _analyzer().analyze(_strip_tashkeel(w))
        if an:
            a = max(an, key=lambda x: float(x.get("pos_lex_logprob", -99) or -99))
            return _norm(_strip_tashkeel((a.get("lex") or "").split("_")[0].split("-")[0]))
    except Exception:
        pass
    return _norm(_strip_tashkeel(w))


def _core_letters(w: str) -> str:
    """الكلمة مجردة من «ال» وأحرف العطف والجر في أولها."""
    b = _norm(_strip_tashkeel(w))
    for p in ("وال", "فال", "بال", "كال", "لل", "ال"):
        if b.startswith(p) and len(b) - len(p) >= 2:
            return b[len(p):]
    if len(b) > 3 and b[0] in "وف":
        return b[1:]
    return b


def _roots_of(w: str) -> set:
    try:
        return {a.get("root") for a in _analyzer().analyze(_strip_tashkeel(w)) if a.get("root") and "#" not in (a.get("root") or "")}
    except Exception:
        return set()


@mcp.tool()
def detect_badi(text: str) -> dict:
    """استخراج المحسنات البديعية من بيت أو قصيدة أو نثر: الجناس (التام، والناقص بزيادة حرف، والمضارع واللاحق باختلاف حرف متقارب المخرج أو متباعده، والمحرّف باختلاف الحركات، وجناس الاشتقاق)،
    والطباق (طباق الإيجاب بمعجم للأضداد، وطباق السلب بالنفي)، والمقابلة، والتصريع، وردّ العجز على الصدر، ولزوم ما لا يلزم، والسجع في النثر (المطرَّف والمتوازي)، والاقتباس من القرآن.
    text: النص؛ والشعر بيتًا في كل سطر بشطريه مفصولين بـ «*». النتائج مرشحات تُراجع: البديع حكم بلاغي يتوقف على المعنى."""
    import re
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    poetry = sum(1 for l in lines if "*" in l) >= max(1, len(lines) // 2)
    units = []
    for l in lines:
        if poetry and "*" in l:
            s_, _, a_ = l.partition("*")
            units.append((s_.strip(), a_.strip()))
        else:
            for seg in re.split(r"[.،؛!?؟\n]+", l):
                if seg.strip():
                    units.append((seg.strip(), ""))
    found = {"الجناس": [], "الطباق": [], "المقابلة": [], "التصريع": [], "ردّ العجز على الصدر": [], "السجع": [], "لزوم ما لا يلزم": [], "الاقتباس": []}
    ant = _antonym_index()
    neg = {"لا", "لم", "لن", "ما", "ليس", "غير"}
    for ui, (s_, a_) in enumerate(units, 1):
        words = re.findall("[ء-يً-ْ]+", s_ + " " + a_)
        bare = [_core_letters(w) for w in words]
        lemmas = [_lemma_bare(w) for w in words]
        where = f"البيت {ui}" if poetry else f"الجملة {ui}"
        # الجناس
        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                x, y = bare[i], bare[j]
                if len(x) < 3 or len(y) < 3 or x in STOPWORDS or y in STOPWORDS:
                    continue
                kind = None
                if x == y:
                    if lemmas[i] != lemmas[j]:
                        kind = "جناس تام (اتفقت الحروف واختلف المعنى)"
                    elif _strip_tashkeel(words[i]) != _strip_tashkeel(words[j]) and any(c in HARAKAT for c in words[i] + words[j]) \
                            and words[i].strip("ًٌٍَُِّْ") != words[j].strip("ًٌٍَُِّْ"):
                        kind = "جناس محرّف (اختلفت الحركات)"
                elif len(x) == len(y) and sum(1 for p, q in zip(x, y) if p != q) == 1:
                    p, q = next((p, q) for p, q in zip(x, y) if p != q)
                    rel = _letter_relation(p, q)
                    kind = f"جناس {'مضارع' if rel == 'متقاربان' else 'لاحق'} (اختلفا في «{p}» و«{q}»)"
                elif abs(len(x) - len(y)) == 1 and (x in y or y in x or x[1:] == y or y[1:] == x or x[:-1] == y or y[:-1] == x):
                    kind = "جناس ناقص (زاد أحدهما حرفًا)"
                elif lemmas[i] != lemmas[j] and _roots_of(words[i]) & _roots_of(words[j]):
                    kind = "جناس الاشتقاق (من جذر واحد)"
                if kind:
                    found["الجناس"].append({"الموضع": where, "اللفظان": [words[i], words[j]], "نوعه": kind})
        # الطباق
        pairs = []
        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                if lemmas[j] in ant.get(lemmas[i], set()) or bare[j] in ant.get(bare[i], set()):
                    pairs.append((i, j))
                    found["الطباق"].append({"الموضع": where, "اللفظان": [words[i], words[j]], "نوعه": "طباق إيجاب"})
                elif lemmas[i] == lemmas[j] and len(bare[i]) > 2 and lemmas[i] not in STOPWORDS and \
                        ((i > 0 and _norm(words[i - 1]) in neg) != (j > 0 and _norm(words[j - 1]) in neg)):
                    found["الطباق"].append({"الموضع": where, "اللفظان": [words[i], words[j]], "نوعه": "طباق سلب (إثبات ونفي)"})
        distinct = []
        for i, j in pairs:
            key = frozenset((lemmas[i], lemmas[j]))
            if key not in [frozenset((lemmas[a], lemmas[b])) for a, b in distinct] and all(i != a and j != b for a, b in distinct):
                distinct.append((i, j))
        if len(distinct) >= 2:
            found["المقابلة"].append({"الموضع": where, "الأزواج": [[words[i], words[j]] for i, j in distinct]})
        # ردّ العجز على الصدر
        if poetry and a_:
            last = _core_letters(a_.split()[-1])
            sw = [_core_letters(w) for w in s_.split()]
            r_last = _roots_of(a_.split()[-1])
            for k, w in enumerate(s_.split()):
                if len(last) > 2 and (sw[k] == last or (r_last & _roots_of(w))):
                    found["ردّ العجز على الصدر"].append({"الموضع": where, "اللفظان": [w, a_.split()[-1]],
                                                       "موضعه": "أول الصدر" if k == 0 else "حشو الصدر" if k < len(sw) - 1 else "آخر الصدر"})
                    break
        # التصريع (في المطلع غالبًا)
        if poetry and a_:
            us, hs = _qafiya_hypotheses(s_)
            ua, ha = _qafiya_hypotheses(a_)
            if us and ua and hs and ha and us[hs[0]][0] == ua[ha[0]][0] and (us[hs[0]][1] == ua[ha[0]][1] or not us[hs[0]][1] or not ua[ha[0]][1]):
                found["التصريع"].append({"الموضع": where, "آخر الصدر": s_.split()[-1], "آخر العجز": a_.split()[-1]})
    # لزوم ما لا يلزم: التزام حرف قبل الروي في القصيدة
    if poetry and len(units) >= 3:
        before = []
        for s_, a_ in units:
            u, h = _qafiya_hypotheses(a_ or s_)
            if u and h and h[0] >= 1:
                before.append(u[h[0] - 1][0])
        if before and len(set(before)) == 1 and before[0] not in "اوي":
            found["لزوم ما لا يلزم"].append({"الحرف الملتزم قبل الروي": before[0], "في الأبيات": len(before)})
    # السجع في النثر
    if not poetry and len(units) >= 2:
        ends = [(_core_letters(u.split()[-1]), u.split()[-1]) for u, _ in units if u.split()]
        for (b1, w1), (b2, w2) in zip(ends, ends[1:]):
            if b1 and b2 and b1[-1] == b2[-1] and b1 != b2:
                same_wazn = _wazn_of(w1) == _wazn_of(w2) and _wazn_of(w1)
                found["السجع"].append({"الفاصلتان": [w1, w2], "نوعه": "سجع متوازٍ (اتفقتا وزنًا ورويًّا)" if same_wazn else "سجع مطرَّف (اتفقتا رويًّا واختلفتا وزنًا)"})
    # الاقتباس من القرآن
    try:
        found["الاقتباس"] = _iqtibas(text)
    except Exception:
        pass
    found = {k: v for k, v in found.items() if v}
    return {"المحسنات": found or "لم يظهر محسّن بديعي من الأنواع المرصودة.",
            "ملاحظة": "الجناس يُرصد بالموازنة الحرفية والصرفية، والطباق بمعجم أضداد مختار وبالنفي؛ فهي مرشحات يُحكم فيها المعنى. "
                      "والتورية والاستخدام والتوجيه ونحوها مما يقوم على المعنى الخفي لا يُرصد آليًّا."}


def _wazn_of(w: str) -> str:
    try:
        an = _analyzer().analyze(_strip_tashkeel(w))
        if an:
            return _stem_wazn(max(an, key=lambda x: float(x.get("pos_lex_logprob", -99) or -99)))
    except Exception:
        pass
    return ""


@lru_cache(maxsize=1)
def _quran_words():
    """كلمات القرآن مرتبة: [(سورة، آية، الكلمة المجردة)]."""
    words, _r, _t = _quran()
    out = []
    for (s_, a_, w_) in sorted(words):
        form = "".join(seg[0] for seg in words[(s_, a_, w_)])
        import re
        form = re.sub("[\u06d6-\u06ed\u0670]", "", form).replace("ٱ", "ا")
        out.append((s_, a_, _norm(_strip_tashkeel(form))))
    return out


def _iqtibas(text: str, n: int = 4) -> list:
    """مواضع اتفاق النص مع القرآن في أربع كلمات متتالية فأكثر."""
    qw = _quran_words()
    idx = {}
    for i in range(len(qw) - n + 1):
        idx.setdefault(tuple(x[2] for x in qw[i:i + n]), []).append(i)
    toks = _ntoks(text)
    res, used = [], set()
    for i in range(len(toks) - n + 1):
        g = tuple(toks[i:i + n])
        if g in idx and i not in used:
            j = idx[g][0]
            k = n
            while i + k < len(toks) and j + k < len(qw) and toks[i + k] == qw[j + k][2]:
                k += 1
            used.update(range(i, i + k))
            res.append({"النص المقتبس": " ".join(toks[i:i + k]), "الموضع": f"سورة {qw[j][0]}، الآية {qw[j][1]}", "عدد الكلمات": k})
    return res



# ───────────── قياس دقة الأدوات على بيانات معيارية ─────────────

_METER_LABELS = {"الطويل": "taweel", "الكامل": "kamel", "البسيط": "baseet", "الوافر": "wafer", "الخفيف": "khafeef",
                 "الرجز": "rajaz", "السريع": "saree", "الرمل": "ramal", "المتقارب": "mutakareb", "المنسرح": "munsareh",
                 "المجتث": "mujtath", "الهزج": "hazaj", "المديد": "madeed", "المتدارك": "mutadarak"}


def _bench_meter(n: int, seed: int):
    import sqlite3, random, pyarud
    _patch_pyarud()
    con = sqlite3.connect(f"file:{POETRY_DB}?mode=ro", uri=True)
    rnd = random.Random(seed)
    per = max(1, n // len(_METER_LABELS))
    rows = []
    for ar, en in _METER_LABELS.items():
        ids = [r[0] for r in con.execute("SELECT id FROM poems WHERE meter = ?", (ar,))]
        for pid in rnd.sample(ids, min(per, len(ids))):
            vs = con.execute("SELECT sadr, ajuz FROM verses WHERE poem_id = ? AND ajuz != '' LIMIT 3", (pid,)).fetchall()
            if vs:
                rows.append((en, *rnd.choice(vs)))
    con.close()
    st = {"base": [0, 0], "fit": [0, 0]}
    for en, s_, a_ in rows:
        ss, aa = _strip_tashkeel(s_), _strip_tashkeel(a_)
        try:
            bs, ba = _prepare_verse_text(ss)[0], _prepare_verse_text(aa)[0]
        except Exception:
            bs, ba = ss, aa
        r = pyarud.analyze_verse(bs, ba)
        st["base"][0] += (r.meter_key or "") == en
        st["base"][1] += bool(r.is_valid)
        f, ch, r2 = _fit_meter([ss, aa], [bs, ba], None)
        r2 = r2 or r
        st["fit"][0] += (r2.meter_key or "") == en
        st["fit"][1] += bool(r2.is_valid)
    k = len(rows) or 1
    return {"العينة": len(rows), "البحور": len(_METER_LABELS),
            "بالتشكيل الآلي وحده": {"دقة البحر": round(100 * st["base"][0] / k, 1), "الموزون": round(100 * st["base"][1] / k, 1)},
            "مع الضبط الموجَّه بالوزن": {"دقة البحر": round(100 * st["fit"][0] / k, 1), "الموزون": round(100 * st["fit"][1] / k, 1)},
            "المنهج": "أبيات من قصائد معلَّمة البحر في «أشعار»، يُنزع تشكيلها ثم تُشكَّل آليًّا وتُقطَّع؛ «دقة البحر» مطابقة البحر المستخرج للمعلَّم، و«الموزون» ما استقام على نحو PyArud بلا خلل. "
                      "وفي «أشعار» أبيات مختلّة أو مقلوبة الشطرين، فالأرقام حدٌّ أدنى."}


def _bench_root(n: int, seed: int):
    import random
    words, _r, _t = _quran()
    keys = [k for k, segs in words.items() if any(f.startswith("ROOT:") for _, _, fs in segs for f in fs)]
    rnd = random.Random(seed)
    sample = rnd.sample(keys, min(n, len(keys)))
    an = _analyzer()
    ok = ok_any = cov = 0
    for k in sample:
        segs = words[k]
        form = "".join(s_[0] for s_ in segs)
        gold = next(f[5:] for _, _, fs in segs for f in fs if f.startswith("ROOT:"))
        gold = gold.translate(HAMZA_FORMS)
        import re
        bare = _strip_tashkeel(re.sub("[ۖ-ٰۭ]", "", form).replace("ٱ", "ا"))
        anal = an.analyze(bare)
        if not anal:
            continue
        cov += 1

        def m(r):
            p = (r or "").split(".")
            return len(p) == len(gold) and all(x == "#" or x.translate(HAMZA_FORMS) == y for x, y in zip(p, gold))
        top = max(anal, key=lambda x: float(x.get("pos_lex_logprob", -99) or -99))
        ok += m(top.get("root"))
        ok_any += any(m(a.get("root")) for a in anal)
    k = len(sample) or 1
    return {"العينة": len(sample), "التغطية (كلمات حللها المحلل)": round(100 * cov / k, 1),
            "دقة الجذر بأرجح تحليل بلا سياق": round(100 * ok / k, 1),
            "الجذر الصحيح بين التحليلات الممكنة": round(100 * ok_any / k, 1),
            "المنهج": "كلمات عشوائية من القرآن بجذورها في «المدوّنة القرآنية» (تحليل يدوي)، تُحلَّل برسمها الإملائي بلا تشكيل؛ ويُعدّ رمز «#» في جذر CAMeL مطابقًا لحرف العلة أو الهمزة."}


def _bench_attr(n_poets: int, seed: int):
    import sqlite3, random
    con = sqlite3.connect(f"file:{POETRY_DB}?mode=ro", uri=True)
    poets = [r[0] for r in con.execute("SELECT poet, COUNT(*) c FROM poems p WHERE era IS NOT NULL GROUP BY poet HAVING c >= 60 ORDER BY c DESC LIMIT 40")]
    rnd = random.Random(seed)
    poets = rnd.sample(poets, min(n_poets, len(poets)))
    train, tests = {}, []
    for p in poets:
        ids = [r[0] for r in con.execute("SELECT id FROM poems WHERE poet = ?", (p,))]
        rnd.shuffle(ids)
        def verses_of(idl):
            out = []
            for i in idl:
                out += [f"{s_} {a_}" for s_, a_ in con.execute("SELECT sadr, ajuz FROM verses WHERE poem_id = ?", (i,))]
            return out
        tt, k, test_keys = [], 0, set()
        while k < len(ids) // 2 and len(tt) < 1500:  # قصائد كاملة للاختبار حتى 1500 كلمة، لا تدخل في بناء الأسلوب
            for v in verses_of([ids[k]]):
                test_keys.add(" ".join(_ntoks(v)))
                tt += _ntoks(v)
            k += 1
        # في «أشعار» قصائد مكررة؛ فيُستبعد من بناء الأسلوب كل بيت ورد في نص الاختبار
        tr = [v for v in verses_of(ids[k:]) if " ".join(_ntoks(v)) not in test_keys]
        train[p] = _ntoks("\n".join(tr))[:60000]
        if len(tt) >= 1000 and len(train[p]) >= 3000:
            tests.append((p, tt[:1500]))
    con.close()
    import math
    from collections import Counter
    allc = Counter()
    for t in train.values():
        allc.update(t)
    mfw = [w for w, _ in allc.most_common(150)]

    def rel(toks):
        c = Counter(toks)
        nn = len(toks) or 1
        return [c[w] / nn for w in mfw]
    segs = [rel(t[i:i + 1500]) for t in train.values() for i in range(0, max(1, len(t) - 1500), 1500)]
    mean = [sum(s_[j] for s_ in segs) / len(segs) for j in range(len(mfw))]
    sd = [math.sqrt(sum((s_[j] - mean[j]) ** 2 for s_ in segs) / (len(segs) - 1)) or 1e-9 for j in range(len(mfw))]
    z = lambda v: [(v[j] - mean[j]) / sd[j] for j in range(len(mfw))]
    zc = {p: z(rel(t)) for p, t in train.items()}
    ok = 0
    for p, tt in tests:
        zt = z(rel(tt))
        def cosd(a, b):
            d = sum(x * y for x, y in zip(a, b))
            return 1 - d / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1)
        best = min(zc, key=lambda q: cosd(zt, zc[q]))
        ok += best == p
    return {"عدد الشعراء": len(poets), "عدد النصوص المختبرة": len(tests), "طول النص المختبر": "نحو 1500 كلمة",
            "دقة النسبة (Cosine Delta)": round(100 * ok / (len(tests) or 1), 1),
            "خط الأساس (التخمين)": round(100 / (len(poets) or 1), 1),
            "المنهج": "لكل شاعر تُعزل قصائد كاملة (نحو 1500 كلمة) للاختبار، ويُبنى أسلوبه من باقي شعره بعد حذف كل بيت مكرر منها؛ ثم يُنسب كل نص مختبر إلى أقرب الشعراء بمقياس Cosine Delta على 150 لفظًا."}


_AR_CM = {"Nom": "رفع", "Acc": "نصب", "Gen": "جر", "Ind": "رفع", "Sub": "نصب", "Jus": "جزم", "—": "بلا حكم"}


def _bench_irab(n: int, seed: int, rules: bool = True):
    """دقة الحالة الإعرابية: آيات عشوائية بلا تشكيل تُعرب بالمحلل، وتُقارن حالة كل اسم (رفع/نصب/جر)
    وحالة كل فعل مضارع (رفع/نصب/جزم) بوسم «المدوّنة القرآنية» المراجَع يدويًّا."""
    import random, re, difflib
    from collections import Counter
    words, _r, _t = _quran()
    ayat = {}
    for (su, a, w), segs in words.items():
        ayat.setdefault((su, a), []).append((w, segs))
    keys = sorted(ayat)
    rnd = random.Random(seed)
    sample = rnd.sample(keys, min(n, len(keys)))
    nlp, pkg = _stanza()
    GOLD_N = {"NOM": "Nom", "ACC": "Acc", "GEN": "Gen"}
    GOLD_V = {"MOOD:IND": "Ind", "MOOD:SUBJ": "Sub", "MOOD:JUS": "Jus"}
    NOMINAL = ("NOUN", "ADJ", "PROPN", "NUM", "X")
    def bare(form):
        # من الرسم العثماني إلى الإملاء المعتاد في أظهر الفروق، لأن الباحث يُدخل النص بالإملاء المعتاد
        t = re.sub("[\u064b-\u0652\u0653\u06d6-\u06ed]", "", form).replace("\u0671", "\u0627")
        t = re.sub("(?<=[ىي])\u0670", "", t).replace("\u0670", "ا")  # الألف الخنجرية تُكتب ألفًا: بينٰت ← بينات
        t = t.replace("\u0640\u0654\u0627", "آ").replace("\u0654\u0627", "آ").replace("\u0640\u0654", "ئ")
        t = t.replace("\u0654", "ئ").replace("\u0640", "")
        t = _strip_tashkeel(t).replace("ءا", "آ")
        for x, y in (("ذالك", "ذلك"), ("هاذ", "هذ"), ("هاؤلاء", "هؤلاء"), ("لاكن", "لكن"), ("الرحمان", "الرحمن"),
                     ("إلاه", "إله"), ("أولائك", "أولئك"), ("اللاه", "الله")):
            t = t.replace(x, y)
        return t
    stats = {"n": Counter(), "v": Counter()}
    conf = {"n": Counter(), "v": Counter()}
    feat_only = Counter()
    errors = []
    for (su, a) in sample:
        ws = sorted(ayat[(su, a)])
        gold, forms = [], []
        for w, segs in ws:
            form = "".join(x[0] for x in segs)
            forms.append(bare(form))
            g = None
            for _f, tag, fs in segs:
                if tag == "V":
                    g = next((("v", GOLD_V[x]) for x in fs if x in GOLD_V), g)
                elif tag in ("N", "PN", "ADJ"):
                    g = next((("n", GOLD_N[x]) for x in fs if x in GOLD_N), g)
            gold.append(g)
        doc = nlp(" ".join(forms))
        if rules:
            doc = _irab_rules(doc)
        toks = [(tok, s_) for s_ in doc.sentences for tok in s_.tokens]
        sm = difflib.SequenceMatcher(None, [_norm(x) for x in forms], [_norm(_strip_tashkeel(t.text)) for t, _ in toks], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "equal":
                for i in range(i1, i2):
                    if gold[i]:
                        stats[gold[i][0]]["unaligned"] += 1
                continue
            for i, j in zip(range(i1, i2), range(j1, j2)):
                g = gold[i]
                if not g:
                    continue
                kind, gv = g
                tok, s_ = toks[j]
                by_id = {x.id: x for x in s_.words}
                kids = {}
                for x in s_.words:
                    kids.setdefault(x.head, []).append(x)
                if kind == "v":
                    w = next((x for x in tok.words if x.upos in ("VERB", "AUX")), None)
                    pv = (_feats(w).get("Mood") or "Ind") if w else None
                else:
                    w = next((x for x in tok.words if x.upos in NOMINAL), None)
                    if w:
                        fc = _feats(w).get("Case")
                        _role_, rc = _role(w, s_, by_id, kids)
                        pv = fc or rc
                        feat_only["total"] += 1
                        feat_only["ok"] += (fc == gv)
                    else:
                        pv = None
                stats[kind]["total"] += 1
                if pv is None:
                    stats[kind]["no_pred"] += 1
                stats[kind]["ok"] += (pv == gv)
                conf[kind][(gv, pv or "—")] += 1
                if pv != gv and len(errors) < 25:
                    errors.append({"الموضع": f"{su}:{a}:{ws[i][0]}", "الكلمة": forms[i], "المدوّنة القرآنية": _AR_CM.get(gv, gv), "الأداة": _AR_CM.get(pv or "—", pv)})
    AR = {"Nom": "رفع", "Acc": "نصب", "Gen": "جر", "Ind": "رفع", "Sub": "نصب", "Jus": "جزم", "—": "بلا حكم"}
    def acc(k):
        t = stats[k]["total"] or 1
        return round(100 * stats[k]["ok"] / t, 1)
    def matrix(k):
        return {f"{AR[g]} ← {AR.get(p, p)}": c for (g, p), c in conf[k].most_common()}
    gold_n = Counter(g for (g, _p), c in conf["n"].items() for _ in range(c))
    base = round(100 * max(gold_n.values()) / max(1, sum(gold_n.values())), 1) if gold_n else 0
    return {
        "العينة (آيات)": len(sample),
        "الأسماء: عدد المقيس": stats["n"]["total"],
        "الأسماء: دقة الحالة الإعرابية": acc("n"),
        "الأسماء: دقة سمة الحالة وحدها دون حالة الباب": round(100 * feat_only["ok"] / max(1, feat_only["total"]), 1),
        "الأسماء: خط الأساس (الحالة الأكثر)": base,
        "الأفعال المضارعة: عدد المقيس": stats["v"]["total"],
        "الأفعال المضارعة: دقة الحالة": acc("v"),
        "لم تُطابَق كلماتها (اختلاف التقطيع)": stats["n"]["unaligned"] + stats["v"]["unaligned"],
        "مصفوفة الالتباس في الأسماء (الصواب ← حكم الأداة)": matrix("n"),
        "مصفوفة الالتباس في الأفعال": matrix("v"),
        "أمثلة من الأخطاء": errors,
        "قواعد كتب النحو": "مفعّلة" if rules else "معطّلة (للموازنة: benchmark يقيسها مفعّلة)",
        "المنهج": f"آيات عشوائية تُعطى للمحلل Stanza ({pkg}) بلا تشكيل وبالإملاء المعتاد، وتُقارن الحالة التي تحكم بها أداة irab "
                  "(سمة المحلل، ثم حالة الباب النحوي إن خلت) بوسم «المدوّنة القرآنية» المراجَع يدويًّا. "
                  "ويقاس الحكم وحده لا الباب؛ والرسم عثماني منزوع التشكيل، فقد يختلف عن الإملاء المعتاد في كلمات قليلة.",
    }


_BENCH_JOBS = {}


@mcp.tool()
def benchmark(task: str = "meter", sample: int = 300, seed: int = 1) -> dict:
    """قياس دقة الأدوات على بيانات معيارية محلية، ليعرف الباحث حدود الاعتماد عليها:
    task: «meter» دقة التقطيع ومعرفة البحر (أبيات «أشعار» المعلَّمة)، أو «root» دقة استخراج الجذر (المدوّنة القرآنية)، أو «attribution» دقة نسبة النص إلى قائله (شعراء «أشعار»)، أو «irab» دقة الحالة الإعرابية (آيات «المدوّنة القرآنية»).
    sample: حجم العينة (للبحر عدد الأبيات، وللجذر عدد الكلمات، وللنسبة عدد الشعراء، وللإعراب عدد الآيات). seed: بذرة العينة العشوائية لإعادة الإنتاج.
    القياس يستغرق دقائق، فيعمل في الخلفية: أعد الطلب نفسه بعد قليل لتأخذ النتيجة."""
    import json, threading, time
    t = task.strip().lower()
    t = "attribution" if t == "attr" else t
    fns = {"meter": (_bench_meter, 14, 2000), "root": (_bench_root, 50, 20000), "attribution": (_bench_attr, 3, 40), "irab": (_bench_irab, 20, 2000)}
    if t not in fns:
        return {"تنبيه": "المهام: meter أو root أو attribution أو irab."}
    fn, lo, hi = fns[t]
    n = max(lo, min(int(sample), hi))
    path = os.path.join(SARF_HOME, f"benchmark_{t}_{n}_{seed}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    key = (t, n, seed)
    job = _BENCH_JOBS.get(key)
    if job and job.get("error"):
        err = job["error"]
        _BENCH_JOBS.pop(key, None)
        return {"تنبيه": f"تعذّر القياس: {err}"}
    if not job:
        def run():
            try:
                r = fn(n, seed)
                r["البذرة"] = seed
                r["التاريخ"] = time.strftime("%Y-%m-%d")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(r, f, ensure_ascii=False, indent=1)
            except Exception as e:
                _BENCH_JOBS[key]["error"] = repr(e)
        _BENCH_JOBS[key] = {"start": time.time()}
        threading.Thread(target=run, daemon=True).start()
        return {"الحال": "بدأ القياس في الخلفية", "أعد الطلب": f"benchmark(task='{t}', sample={n}, seed={seed}) بعد دقائق"}
    return {"الحال": "القياس جارٍ", "مضى (ثانية)": int(time.time() - job["start"])}


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
