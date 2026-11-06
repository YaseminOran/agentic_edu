"""Hassas veriyi (IBAN, kart no, TCKN, telefon, e-posta) regex ile maskeler (Hafta 2).
Kural 6: hassas veri modele gönderilmeden ÖNCE maskelenir. Loglar da sadece maskelenmiş veri içerir.
Testler: python tests/test_maskeleme.py
"""

import re

# Sıra önemli: önce e-posta ve uzun kalıplar (IBAN), sonra kart (16 hane), TCKN (11 hane), en son telefon.
# Aksi halde IBAN'ın içindeki rakamlar kart/TCKN kalıbına takılıp yarım maskelenirdi.
# (?<!\d) ve (?!\d): kalıbın daha uzun bir sayının ortasında eşleşmesini engeller.

# TODO (Lab 2) çözümü: e-posta (kullanıcı adının ilk harfi ve alan adı görünür kalır)
EPOSTA = re.compile(r"\b([A-Za-z0-9])[A-Za-z0-9._%+-]*@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
# TR + 2 kontrol hanesi + 22 rakam; 4'erli gruplar arasında boşluk olabilir
IBAN = re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.IGNORECASE)
# 16 hane; 4'erli gruplar arasında boşluk veya tire olabilir
KART_NO = re.compile(r"(?<!\d)\d{4}(?:[ -]?\d{4}){3}(?!\d)")
# 11 hane, 0 ile başlamaz (TCKN kuralı); 0 ile başlayan 11 haneli sayı telefondur
TCKN = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
# Türkiye cep telefonu: +90 / 0 ön eki isteğe bağlı, 5xx xxx xx xx (boşluk/tire serbest)
TELEFON = re.compile(r"(?<!\d)(?:\+90[\s-]?|0)?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")


def _son4(eslesme: re.Match) -> str:
    """Eşleşen metindeki rakamların son 4'ü (müşteri kartını/hesabını tanıyabilsin diye)."""
    return re.sub(r"\D", "", eslesme.group())[-4:]


def maskele(metin: str) -> str:
    """Metindeki e-posta, IBAN, kart no, TCKN ve telefonu maskeler; geri kalanına dokunmaz.

    >>> maskele("Kartım 9999 0000 0000 0007, TCKN 99999000007")
    'Kartım [KART ****0007], TCKN [TCKN]'
    """
    if not metin:
        return metin
    metin = EPOSTA.sub(lambda e: f"[EPOSTA {e.group(1)}***@{e.group(2)}]", metin)  # TODO (Lab 2) çözümü
    metin = IBAN.sub(lambda e: f"[IBAN ****{_son4(e)}]", metin)
    metin = KART_NO.sub(lambda e: f"[KART ****{_son4(e)}]", metin)
    metin = TCKN.sub("[TCKN]", metin)  # TCKN'nin hiçbir hanesi gösterilmez
    metin = TELEFON.sub(lambda e: f"[TELEFON ****{_son4(e)}]", metin)
    return metin
