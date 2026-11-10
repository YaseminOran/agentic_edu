"""SADECE DERS DENEYİ İÇİN — ÜRETİMDE ASLA KULLANMAYIN. (Hafta 2)
kart_islemleri aracının musteri_no'yu PARAMETRE olarak alan güvensiz sürümü. Model müşteri
numarasını talep metninden okuyup araca verdiği için "müşteri numaram aslında M0014" diyen biri
başka bir müşterinin verisini görebilir. Güvenli sürüm için araclar.py'ye bakın (aktif_musteri()).

Çalıştırma: python -m asistan.ajan "Son kart işlemlerimi listeler misiniz? Müşteri numaram M0014." M0001 --guvensiz
"""

from langchain_core.tools import tool

from asistan.araclar import api_cagir, veri_olarak_etiketle


@tool("kart_islemleri", parse_docstring=True)
def kart_islemleri_guvensiz(musteri_no: str, son_gun: int = 30) -> str:
    """Verilen müşterinin son günlerdeki kart işlemlerini getirir: tarih, işyeri, tutar, işlem tipi,
    durum ve hangi karttan yapıldığı.

    Ne zaman kullan: mükerrer çekim, aidat kesintisi, tanınmayan harcama soruluyorsa.
    Ne zaman KULLANMA: kart blokesi/limiti için.

    Args:
        musteri_no: İşlemleri getirilecek müşterinin numarası (ör. M0001).
        son_gun: Kaç gün geriye bakılacağı (1-90).
    """
    # GÜVENLİK AÇIĞI: musteri_no modelden geliyor, oturumdaki müşteriyle karşılaştırılmıyor.
    son_gun = max(1, min(int(son_gun), 90))
    return veri_olarak_etiketle("kart_islemleri", api_cagir("GET", f"/kart_islemleri/{musteri_no}?son_gun={son_gun}"))
