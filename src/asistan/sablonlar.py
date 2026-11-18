"""Prompt şablonlarını prompts/ klasöründen okur, sürümünü seçer ve yer tutucuları doldurur (Hafta 4, adım 1).
Şablon dosyası: prompts/<ad>/<sürüm>.md. "=== KULLANICI MESAJI ===" satırının üstü sistem mesajı, altı
kullanıcı mesajıdır. Hangi sürümün kullanılacağı SURUMLER'den gelir; .env'de SABLON_<AD>=v1 ile değişir.
"""

import os
import re

from asistan.ayarlar import PROJE_KOKU
from asistan.izleme import iz_alanina_ekle

SABLON_KLASORU = PROJE_KOKU / "prompts"
AYIRAC = "=== KULLANICI MESAJI ==="

# Varsayılan sürümler. Değiştirmek için kodu değil .env'yi düzenleyin: SABLON_TASLAK=v1
SURUMLER = {
    "siniflandirma": "v1",
    "ajan": "v1",
    "taslak": "v1",  # Lab 2: v2 A/B testinde v1'den iyiyse burayı "v2" yapın
    "self_check": "v1",
    "hakem": "v1",
}

YER_TUTUCU = re.compile(r"\{([a-z_]+)\}")
YORUM = re.compile(r"<!--.*?-->\n?", re.DOTALL)  # dosyadaki açıklamalar modele gitmez


def dosya_oku(yol) -> str:
    """Markdown dosyasını açıklama yorumları (<!-- -->) çıkarılmış olarak okur."""
    return YORUM.sub("", yol.read_text(encoding="utf-8")).strip()


def surum_sec(ad: str, model_turu: str = "yerel") -> str:
    """Kullanılacak sürüm: .env'deki SABLON_<AD> ya da SURUMLER. Yerel model için "<sürüm>_yerel.md"
    varsa o kullanılır (küçük modele daha kısa ve net talimat)."""
    surum = os.getenv(f"SABLON_{ad.upper()}", "").strip() or SURUMLER[ad]
    if model_turu == "yerel" and (SABLON_KLASORU / ad / f"{surum}_yerel.md").exists():
        surum += "_yerel"
    return surum


def doldur(metin: str, degerler: dict) -> str:
    """{ad} yer tutucularını değerlerle doldurur (tek geçişte; değerin içindeki süslü parantez bozulmaz).
    Şablonda olup değeri verilmeyen yer tutucu varsa hata verir: eksik bilgiyle model çağrılmasın."""
    eksik = sorted(set(YER_TUTUCU.findall(metin)) - set(degerler))
    if eksik:
        raise ValueError(f"Şablonda değeri verilmeyen yer tutucu var: {eksik}")
    return YER_TUTUCU.sub(lambda m: str(degerler[m.group(1)]), metin)


def kurallar_metni() -> str:
    """prompts/kurallar.md'nin karar kuralları bölümü (hazır cümleler hariç)."""
    return dosya_oku(SABLON_KLASORU / "kurallar.md").split("## Hazır cümleler")[0].strip()


def banka_dili_metni() -> str:
    return dosya_oku(SABLON_KLASORU / "banka_dili.md")


def hazir_cumle(ad: str) -> str:
    """kurallar.md'deki hazır cümle: "temsilci", "netlestir", "reddet" ya da "kapsam_disi"."""
    bolum = dosya_oku(SABLON_KLASORU / "kurallar.md").split("## Hazır cümleler")[1]
    eslesme = re.search(rf"^### {ad}\n(.+?)$", bolum, re.MULTILINE)
    if not eslesme:
        raise KeyError(f"kurallar.md içinde hazır cümle yok: {ad}")
    return eslesme.group(1).strip()


def yasak_ifadeler() -> list[str]:
    """banka_dili.md'deki "Yasak ifadeler" listesi (self-check bu ifadeleri yanıtta arar)."""
    bolum = banka_dili_metni().split("### Yasak ifadeler")[1].split("###")[0]
    return [satir[2:].strip() for satir in bolum.splitlines() if satir.startswith("- ")]


def mesajlar(ad: str, model_turu: str = "yerel", **degerler) -> list[tuple[str, str]]:
    """Şablonu okur, doldurur ve modele gidecek mesaj listesini döner: [("system", ...), ("human", ...)].
    {kurallar} ve {banka_dili} kendiliğinden doldurulur. Kullanılan sürüm ize yazılır."""
    surum = surum_sec(ad, model_turu)
    metin = dosya_oku(SABLON_KLASORU / ad / f"{surum}.md")
    iz_alanina_ekle("sablonlar", ad, surum)
    hazir = {"kurallar": kurallar_metni(), "banka_dili": banka_dili_metni()}
    gerekli = set(YER_TUTUCU.findall(metin))
    metin = doldur(metin, {**{k: v for k, v in hazir.items() if k in gerekli}, **degerler})
    sistem, _, kullanici = metin.partition(AYIRAC)
    return [("system", sistem.strip())] + ([("human", kullanici.strip())] if kullanici.strip() else [])
