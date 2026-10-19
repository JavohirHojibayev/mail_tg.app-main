"""
O'zbek tili Lotin-Krill transliteratsiyasi va qidiruvni normalizatsiya qilish moduli.
Katta-kichik harflar, apostroflar, x/h, yev/ev, o/a va norboyev=narbayev kabi variantlarga to'liq moslashgan.
"""

import re

# Krill -> Lotin lug'ati
CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ҳ': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': "'", 'ь': "", 'э': 'e', 'ю': 'yu', 'я': 'ya', 'ў': "o'", 'ғ': "g'", 'қ': 'q'
}

VOWELS = set("аеёиоуыэюяaouiey")

def cyrillic_to_latin(text: str) -> str:
    """Krill matnni lotinga o'giradi (unlilardan keyingi 'е' -> 'ye' qoidasi bilan)"""
    if not text:
        return ""
    result = []
    text_lower = text.lower()
    for idx, char in enumerate(text_lower):
        if char == 'е':
            prev_char = text_lower[idx - 1] if idx > 0 else ' '
            if idx == 0 or prev_char in VOWELS or prev_char in ' \t\n-_.':
                result.append('ye')
            else:
                result.append('e')
        else:
            result.append(CYR_TO_LAT.get(char, char))
    return "".join(result)

def normalize_text(text: str) -> str:
    """
    Qidiruv uchun matnni tozalaydi va barcha variantlarni bir xillashtiradi:
    1. Kichik harfga o'tkazadi
    2. Barcha apostroflarni (', `, ʻ, ʼ, ’) tozalaydi
    3. Krill harflarini lotinga o'giradi
    4. Familiya qo'shimchalarini bir xillashtiradi:
       -boyev = -bayev = -boev = -baev
    5. -yev / -ev / -yov / -ov qo'shimchalarini tekislaydi
    6. 'o' va 'a' farqlarini tekislaydi (norboyev = narbayev = narboyev = norbaev)
    7. 'x' va 'h' farqini tekislaydi (xojiboyev = hojibayev)
    8. 'q' va 'k' farqini tekislaydi
    """
    if not text:
        return ""
    t = text.lower()
    # Apostroflar
    t = re.sub(r"[`ʻʼ’']", "", t)
    # Krill -> Lotin
    t = cyrillic_to_latin(t)

    # Familiya suffikslari (-boyev, -bayev, -boev, -baev)
    t = re.sub(r"b[oa]y?[eo]v\b", "baev", t)
    t = re.sub(r"b[oa]y?[eo]v(?=[^a-z]|$)", "baev", t)

    # -yev / -ev / -yov / -ov
    t = re.sub(r"y?ev\b", "ev", t)
    t = re.sub(r"y?ev(?=[^a-z]|$)", "ev", t)
    t = re.sub(r"y?ov\b", "ev", t)
    t = re.sub(r"y?ov(?=[^a-z]|$)", "ev", t)

    # x va h
    t = t.replace("x", "h")

    # o va a harflari (norboyev = narbayev)
    t = t.replace("o", "a")

    # q va k harflari
    t = t.replace("q", "k")

    # Probellar
    t = re.sub(r"\s+", " ", t).strip()
    return t

def calculate_match_score(user: dict, query: str) -> int:
    """
    Foydalanuvchi qidiruv so'ziga qanchalik mos kelishini baholaydi.
    Ism + familiya yozilganda:
    - Ham ism, ham familiya mos kelsa: ENG YUQORI BALL
    - Familiya mos kelib, ism initsiali mos kelsa: YUQORI BALL
    - Ism yoki familiyadan biri mos kelsa: O'RTA BALL
    """
    if not query or not query.strip():
        return 0

    name_raw = user.get("name", "")
    email_raw = user.get("email", "")
    pos_raw = user.get("position", "")
    phone_raw = user.get("phone", "")
    ip_phone_raw = user.get("ip_phone", "")

    name_norm = normalize_text(name_raw)
    email_norm = normalize_text(email_raw)
    pos_norm = normalize_text(pos_raw) if pos_raw and pos_raw != "—" else ""
    email_prefix = email_norm.split("@")[0] if "@" in email_norm else email_norm

    target_tokens = set(name_norm.replace(".", " ").replace("_", " ").replace("-", " ").split())
    email_tokens = set(email_prefix.replace(".", " ").replace("_", " ").replace("-", " ").split())
    pos_tokens = set(pos_norm.replace(".", " ").replace("_", " ").replace("-", " ").split()) if pos_norm else set()
    all_tokens = target_tokens.union(email_tokens).union(pos_tokens)

    query_clean = query.strip()
    query_norm = normalize_text(query_clean)
    query_digits = re.sub(r'\D', '', query_clean)

    # Telefon raqam yoki IP telefon bo'yicha qidiruv
    if len(query_digits) >= 3:
        user_phone_digits = re.sub(r'\D', '', str(phone_raw))
        user_ip_digits = re.sub(r'\D', '', str(ip_phone_raw))
        if (user_phone_digits and query_digits in user_phone_digits) or (user_ip_digits and query_digits in user_ip_digits):
            return 100

    query_words = query_norm.split()

    full_target = f"{name_norm} {email_prefix} {pos_norm}"
    if query_norm in full_target or query_norm in name_norm or (pos_norm and query_norm in pos_norm):
        return 100

    score = 0
    words_matched = 0

    for qw in query_words:
        matched_this_qw = False

        # A. To'liq token mosligi
        for tok in all_tokens:
            if qw == tok:
                score += 30
                matched_this_qw = True
                break

        # B. Qisqartma yoki qism mosligi (kamida 3 belgi)
        if not matched_this_qw and len(qw) >= 3:
            for tok in all_tokens:
                if (qw in tok and len(tok) >= 3) or (tok in qw and len(tok) >= 3):
                    score += 20
                    matched_this_qw = True
                    break

        # C. Initsial / bosh harf mosligi (masalan 'damir' -> 'd.' yoki 'D')
        if not matched_this_qw and len(qw) >= 2:
            first_char = qw[0]
            if email_prefix.startswith(f"{first_char}.") or email_prefix.startswith(f"{first_char}_"):
                score += 15
                matched_this_qw = True
            elif first_char in target_tokens or first_char in email_tokens:
                score += 15
                matched_this_qw = True

        if matched_this_qw:
            words_matched += 1

    # Barcha so'zlar mos kelgan bo'lsa (ham ism, ham familiya)
    if len(query_words) > 1 and words_matched >= len(query_words):
        score += 40

    if words_matched > 0:
        return score

    return 0

def matches_query(target: str, query: str) -> bool:
    if not target or not query:
        return False
    norm_t = normalize_text(target)
    norm_q = normalize_text(query)
    return norm_q in norm_t or norm_t in norm_q
