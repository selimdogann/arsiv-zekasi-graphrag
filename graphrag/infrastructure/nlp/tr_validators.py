"""
Deterministik Türk kurumsal kimlik doğrulayıcıları.

Bu fonksiyonlar LLM'e HİÇ ihtiyaç duymaz — checksum (sağlama) algoritmalarıyla
çalışır. "AI'ı deterministik algoritmayla dizginleme" felsefesinin somut hâli:
bir LLM ileride bir TC Kimlik No önerirse, bu fonksiyonlarla doğrulanabilir.
"""
from __future__ import annotations


def is_valid_tckn(value: str) -> bool:
    """T.C. Kimlik No sağlaması (11 hane, iki basamaklı checksum)."""
    if not (len(value) == 11 and value.isdigit() and value[0] != "0"):
        return False
    d = [int(c) for c in value]
    odd_sum = d[0] + d[2] + d[4] + d[6] + d[8]
    even_sum = d[1] + d[3] + d[5] + d[7]
    tenth = (odd_sum * 7 - even_sum) % 10
    if tenth != d[9]:
        return False
    eleventh = sum(d[:10]) % 10
    return eleventh == d[10]


def is_valid_vkn(value: str) -> bool:
    """Vergi Kimlik No sağlaması (10 hane, Maliye algoritması)."""
    if not (len(value) == 10 and value.isdigit()):
        return False
    d = [int(c) for c in value]
    total = 0
    for i in range(9):
        tmp = (d[i] + (9 - i)) % 10
        if tmp != 0:
            tmp = (tmp * (2 ** (9 - i))) % 9
            if tmp == 0:
                tmp = 9
        total += tmp
    check = (10 - (total % 10)) % 10
    return check == d[9]


def is_valid_iban_tr(value: str) -> bool:
    """Türkiye IBAN sağlaması (26 karakter, ISO 13616 mod-97)."""
    iban = value.replace(" ", "").upper()
    if len(iban) != 26 or not iban.startswith("TR"):
        return False
    rearranged = iban[4:] + iban[:4]
    digits = "".join(
        str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearranged)
    return int(digits) % 97 == 1
