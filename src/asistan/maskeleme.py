"""Kişisel veri maskeleme katmanı (Hafta 4): modele giden HER metin takma adla gider, müşteriye giden yanıt
güvenli gösterime çevrilir. Akış: gerçek değer -> [KART_1] (modele) -> "0007 ile biten kartınız" (müşteriye).
Gerçek değer ile takma ad eşleşmesi sadece bu dosyadaki bellek tablosunda durur; loga, ize ve modele gitmez.
"""

import re
from contextlib import contextmanager
from contextvars import ContextVar

# ---------------------------------------------------------------------------
# 1) Kişisel veri kalıpları (sırası önemli: IBAN içindeki rakamlar kart sanılmasın)
# ---------------------------------------------------------------------------

KALIPLAR = {
    "IBAN": re.compile(r"\bTR\d{2}(?: ?\d{4}){5} ?\d{2}\b"),
    "KART": re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
    "TCKN": re.compile(r"\b\d{11}\b"),
    "TEL": re.compile(r"\b0?5\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}\b"),
    "EPOSTA": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
}

# Araç çıktılarında (JSON) hangi alan hangi türde kişisel veri taşır. Ad-soyadı regex ile bulamayız;
# alan adından tanırız. Bir kez tanınan ad, sonra serbest metinde geçse de maskelenir.
ALAN_TURLERI = {"ad_soyad": "AD", "kart_no": "KART", "iban": "IBAN", "tckn": "TCKN", "telefon": "TEL",
                "eposta": "EPOSTA"}


def tam_veri_bul(metin: str) -> list[str]:
    """Metinde maskelenmemiş kişisel veri var mı? Bulunan TÜRLERİ döner (değerleri değil), ör. ["KART"].
    Self-check, iz ve eval bu fonksiyonla kontrol eder."""
    return [tur for tur, kalip in KALIPLAR.items() if kalip.search(metin or "")]


def maskele(metin: str) -> str:
    """Basit maskeleme: her kişisel veriyi türünün adıyla değiştirir ([KART], [IBAN]...). Eşleme tutmaz.
    İz dosyası yazılırken son güvenlik ağı olarak kullanılır (izleme.py)."""
    for tur, kalip in KALIPLAR.items():
        metin = kalip.sub(f"[{tur}]", metin)
    return metin


# ---------------------------------------------------------------------------
# 2) Eşleme tablosu: bir talebin (oturumun) bellekteki kasası
# ---------------------------------------------------------------------------

# {oturum_id: tablo}. Sadece bellekte; insan onayı sonradan gelince aynı oturumun tablosu yine bulunur.
_TABLOLAR: dict[str, dict] = {}
_AKTIF_TABLO: ContextVar[dict | None] = ContextVar("aktif_maske_tablosu", default=None)


def yeni_tablo() -> dict:
    """Boş eşleme tablosu.
    takma:   gerçek değer (boşluksuz) -> takma ad      ör. "9999000000000007" -> "[KART_1]"
    gosterim: takma ad -> müşteriye güvenli gösterim   ör. "[KART_1]" -> "0007 ile biten kartınız"
    kisa:    takma ad -> sıfat hali                    ör. "[KART_1]" -> "0007 ile biten" ("... kredi kartınız")
    adlar:   tanınan ad-soyadlar (serbest metinde de aranır)"""
    return {"takma": {}, "gosterim": {}, "kisa": {}, "sayac": {}, "adlar": []}


@contextmanager
def maske_oturumu(oturum_id: str):
    """`with maske_oturumu(oturum_id): ...` bloğundaki maskeleme bu oturumun tablosunu kullanır.
    Aynı oturum tekrar açılırsa (netleştirme turu, insan onayı) aynı tablo devam eder."""
    tablo = _TABLOLAR.setdefault(oturum_id, yeni_tablo())
    jeton = _AKTIF_TABLO.set(tablo)
    try:
        yield tablo
    finally:
        _AKTIF_TABLO.reset(jeton)


def aktif_tablo() -> dict:
    """Aktif oturumun tablosu. Oturum yoksa (ör. notebook'ta tek başına deneme) geçici bir tablo."""
    tablo = _AKTIF_TABLO.get()
    if tablo is None:
        tablo = yeni_tablo()
        _AKTIF_TABLO.set(tablo)
    return tablo


def guvenli_gosterim(tur: str, deger: str) -> str:
    """Müşteriye giden yanıtta takma adın yerine yazılacak metin. Tam numara ASLA yazılmaz."""
    rakamlar = re.sub(r"\D", "", deger)
    if tur == "KART":
        return f"{rakamlar[-4:]} ile biten kartınız"
    if tur == "IBAN":
        return f"{rakamlar[-2:]} ile biten IBAN'ınız"
    if tur == "TEL":
        return f"{rakamlar[-2:]} ile biten telefon numaranız"
    if tur == "TCKN":
        return "T.C. kimlik numaranız"
    if tur == "EPOSTA":
        return "e-posta adresiniz"
    if tur == "AD":
        ad, *soyad = deger.split()
        return f"{ad} {soyad[-1][0]}." if soyad else ad
    return "[gizli bilgi]"


def takma_ad(tur: str, deger: str, tablo: dict | None = None) -> str:
    """Değere takma ad verir. Aynı değer (boşluk/tire farkı olsa da) hep aynı takma adı alır."""
    tablo = tablo if tablo is not None else aktif_tablo()
    anahtar = re.sub(r"[\s-]", "", deger) if tur != "AD" else deger.strip()
    if anahtar not in tablo["takma"]:
        tablo["sayac"][tur] = tablo["sayac"].get(tur, 0) + 1
        ad = f"[{tur}_{tablo['sayac'][tur]}]"
        tablo["takma"][anahtar] = ad
        tablo["gosterim"][ad] = guvenli_gosterim(tur, deger)
        if tur in ("KART", "IBAN", "TEL"):  # "0007 ile biten kartınız" -> sıfat hali "0007 ile biten"
            tablo["kisa"][ad] = tablo["gosterim"][ad].split(" ile biten")[0] + " ile biten"
        if tur == "AD":
            tablo["adlar"].append(anahtar)
    return tablo["takma"][anahtar]


# ---------------------------------------------------------------------------
# 3) Maskeleme (modele giderken) ve geri çevirme (müşteriye giderken)
# ---------------------------------------------------------------------------

def metni_maskele(metin: str, tablo: dict | None = None) -> str:
    """Serbest metindeki kişisel verileri takma adla değiştirir: müşteri mesajı, prosedür parçası,
    harici veri, model çıktısı."""
    tablo = tablo if tablo is not None else aktif_tablo()
    for tur, kalip in KALIPLAR.items():
        metin = kalip.sub(lambda m: takma_ad(tur, m.group(0), tablo), metin)
    for ad in tablo["adlar"]:  # daha önce bir araç çıktısında tanınan adlar
        metin = metin.replace(ad, tablo["takma"][ad])
    return metin


def veriyi_maskele(veri, tablo: dict | None = None):
    """Araç çıktısını (sözlük/liste) modele vermeden önce maskeler. Kişisel veri alanları (ALAN_TURLERI)
    takma ad alır; diğer metin alanları (ör. müşteri notu) serbest metin gibi taranır."""
    tablo = tablo if tablo is not None else aktif_tablo()
    if isinstance(veri, dict):
        return {anahtar: (takma_ad(ALAN_TURLERI[anahtar], str(deger), tablo)
                          if anahtar in ALAN_TURLERI and deger else veriyi_maskele(deger, tablo))
                for anahtar, deger in veri.items()}
    if isinstance(veri, list):
        return [veriyi_maskele(x, tablo) for x in veri]
    if isinstance(veri, str):
        return metni_maskele(veri, tablo)
    return veri


TAKMA_AD_KALIBI = re.compile(r"\[(?:IBAN|KART|TCKN|TEL|EPOSTA|AD)_\d+\]")
# Takma addan sonra "numaralı" ya da ürünün adı geliyorsa sıfat hali kullanılır:
# "[KART_1] numaralı Classic Kart" -> "0007 ile biten Classic Kart", "[KART_1] kartınız" -> "0007 ile biten kartınız"
SIFAT_KALIBI = re.compile(r"(\[(?:IBAN|KART|TEL)_\d+\])\s+(?:numaralı\s+|nolu\s+|no'lu\s+)?"
                          r"(?=(?:kart|banka|kredi|örnek|iban|hesab|telefon|numara))", re.IGNORECASE)


def geri_cevir(metin: str, tablo: dict | None = None) -> str:
    """Yanıttaki takma adları müşteriye uygun güvenli gösterime çevirir: [KART_1] -> "0007 ile biten kartınız".
    Tabloda olmayan (modelin uydurduğu) takma ad "[gizli bilgi]" olur."""
    tablo = tablo if tablo is not None else aktif_tablo()
    metin = SIFAT_KALIBI.sub(lambda m: tablo["kisa"].get(m.group(1), "[gizli bilgi]") + " ", metin)
    metin = re.sub(r"(\[(?:IBAN|KART|TEL)_\d+\])\s+(?:numaralı|nolu|no'lu)\b", r"\1", metin)
    return TAKMA_AD_KALIBI.sub(lambda m: tablo["gosterim"].get(m.group(0), "[gizli bilgi]"), metin)
