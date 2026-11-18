"""Yanıt taslağını müşteriye gitmeden önce kontrol eder (Hafta 4, adım 5). İki katman:
1) deterministik_kontroller(): kodla yapılan, her zaman aynı sonucu veren kontroller (ucuz, model yok)
2) elestir(): ikinci bir model çağrısı, yanıtı kontrol listesine göre değerlendirir (SelfCheck şeması)
Akıştaki yeri (ajan.py): taslak -> self_check -> (geçti) risk_kontrolu | (geçmedi) bir kez yeniden yaz | temsilci
"""

from functools import cache
from typing import Literal

from pydantic import BaseModel, Field

from asistan.ayarlar import model_getir
from asistan.gunluk import log
from asistan.kategoriler import KATEGORILER, PROSEDUR_KOKU
from asistan.maskeleme import tam_veri_bul
from asistan.rag.indeksle import basliklara_bol, dokuman_oku
from asistan.sablonlar import mesajlar, yasak_ifadeler


def kucuk_harf(metin: str) -> str:
    """Türkçe güvenli küçük harf: Python'da "İ".lower() noktalı i üretir, arama eşleşmez."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


# ---------------------------------------------------------------------------
# 1) Deterministik kontroller
# ---------------------------------------------------------------------------

def kelime_dizileri(metin: str, n: int = 5) -> set[tuple]:
    """Ardışık n kelimelik diziler. Yanıt bir iç dokümanla 5 kelimelik dizi paylaşıyorsa alıntı yapmıştır."""
    kelimeler = [k.strip(".,;:!?()\"'") for k in kucuk_harf(metin).split()]
    return {tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)}


@cache
def ic_dokuman_dizileri() -> dict[str, set[tuple]]:
    """Ajanın arayabildiği kategorilerdeki gizlilik=ic dokümanların kelime dizileri (bir kez okunur)."""
    sonuc = {}
    for yol in sorted(y for kategori in KATEGORILER for y in (PROSEDUR_KOKU / kategori).glob("*.md")):
        metadata, govde = dokuman_oku(yol)
        if metadata.get("gizlilik") == "ic":
            sonuc[yol.relative_to(PROSEDUR_KOKU).as_posix()] = kelime_dizileri(
                "\n".join(metin for _, metin in basliklara_bol(govde)))
    return sonuc


def deterministik_kontroller(musteri_yaniti: str, uydurma_kaynaklar: list[str]) -> list[str]:
    """Müşteriye gidecek (geri çevrilmiş) yanıtı kontrol eder. Bulunan sorunların listesini döner; boşsa geçti.
    1) Gösterilen her kaynak gerçekten getirilmiş mi?  2) Tam kart no, IBAN, TCKN, telefon kalmış mı?
    3) Banka dili rehberindeki yasak ifadeler var mı?   4) İç doküman içeriği var mı?"""
    sorunlar = []
    if uydurma_kaynaklar:
        sorunlar.append(f"sana verilmeyen kaynak gösterildi: {', '.join(uydurma_kaynaklar)}")
    if tam := tam_veri_bul(musteri_yaniti):
        sorunlar.append(f"yanıtta tam kişisel veri var: {', '.join(tam)}")
    yanit_k = kucuk_harf(musteri_yaniti)
    if yasak := [ifade for ifade in yasak_ifadeler() if kucuk_harf(ifade) in yanit_k]:
        sorunlar.append(f"yasak ifade: {', '.join(yasak)}")
    dizi = kelime_dizileri(musteri_yaniti)
    if ic := [dosya for dosya, d in ic_dokuman_dizileri().items() if dizi & d]:
        sorunlar.append(f"iç doküman içeriği: {', '.join(ic)}")
    return sorunlar


# ---------------------------------------------------------------------------
# 2) LLM eleştirisi
# ---------------------------------------------------------------------------

class SelfCheck(BaseModel):
    """Eleştiri modelinin doldurduğu kontrol listesi. Alan açıklamaları da modele gider."""

    gerekce: str = Field(description="Başarısız maddeler varsa tek cümlelik açıklama; hepsi iyiyse 'sorun yok'")
    kaynakla_tutarli: bool = Field(description="Yanıttaki her bilgi verilen verilerde/prosedürde var ve doğru aktarılmış")
    soruyu_cevapliyor: bool = Field(description="Yanıt müşterinin sorusunu cevaplıyor")
    banka_diline_uygun: bool = Field(description="Yanıt banka dili rehberine uyuyor")
    uydurma_var: bool = Field(description="Bağlamda olmayan bilgi ya da yapılmamış bir işlem iddiası var")
    iade_odeme_taahhut: Literal["evet", "hayir", "emin_degilim"] = Field(
        description="Yanıt bankanın adına iade, ödeme veya başka bir söz içeriyor mu? Bilgi amaçlı tutar 'hayir'dır")


def elestir(model_turu: str, **degerler) -> SelfCheck | None:
    """Taslağı kontrol listesine göre değerlendirtir. Çıktı okunamazsa None döner: akış bunu "emin değilim"
    sayar (taslağı reddetmez ama risk kontrolünde eski temkinli kural çalışır)."""
    yontem = "function_calling" if model_turu == "yerel" else "json_schema"
    model = model_getir(model_turu).with_structured_output(SelfCheck, method=yontem)
    try:
        return model.invoke(mesajlar("self_check", model_turu, **degerler))
    except Exception as e:
        log.warning("self-check çıktısı okunamadı: %s: %s", type(e).__name__, str(e)[:150])
        return None


def elestiri_gecti_mi(sonuc: SelfCheck | None) -> bool:
    if sonuc is None:
        return True  # değerlendirilemedi: taslağı reddetmiyoruz, risk kontrolü temkinli davranacak
    return (sonuc.kaynakla_tutarli and sonuc.soruyu_cevapliyor and sonuc.banka_diline_uygun
            and not sonuc.uydurma_var)
