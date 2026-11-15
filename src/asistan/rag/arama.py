"""Prosedür indeksinde arama ve taslağa gidecek bağlamın hazırlanması (Hafta 3, adım 3 ve 5).
ara(): sorguyu vektörleştirir, kategori ve gizlilik filtresinden geçen en benzer k parçayı skoruyla döner.
baglam_olustur(): ajanın bir talepte getirdiği tüm parçalardan taslağa gidecekleri seçer (context yönetimi).
"""

import json

import faiss
import numpy as np

from asistan.ayarlar import ayar, embedding_getir
from asistan.rag.indeksle import INDEKS_DOSYASI, PARCA_DOSYASI

K = 3                 # her aramada en fazla kaç parça döner
SKOR_ESIGI = 0.50     # kosinüs benzerliği bunun altındaysa parça "ilgisiz" sayılır (01_rag.ipynb'de ayarlandı)
BAGLAM_SINIRI = 2500  # taslağa giden toplam prosedür metni (karakter); küçük modelin bağlamı şişmesin


class IndeksYok(RuntimeError):
    """İndeks kurulmamış ya da başka bir embedding modeliyle kurulmuş."""


_onbellek: dict = {}  # indeks her aramada diskten okunmasın


def indeksi_yukle() -> tuple[faiss.Index, list[dict]]:
    """FAISS indeksini ve parça listesini yükler (ilk çağrıda diskten, sonra bellekten)."""
    if not _onbellek:
        if not INDEKS_DOSYASI.exists() or not PARCA_DOSYASI.exists():
            raise IndeksYok("Prosedür indeksi yok -> PYTHONPATH=src python -m asistan.rag.indeksle")
        bilgi = json.loads(PARCA_DOSYASI.read_text(encoding="utf-8"))
        if bilgi["embed_model"] != ayar("EMBED_MODEL"):
            # Farklı modellerin vektörleri karşılaştırılamaz: sorgu bge-m3, indeks başka model olamaz
            raise IndeksYok(f"İndeks {bilgi['embed_model']} ile kurulmuş, .env'de EMBED_MODEL={ayar('EMBED_MODEL')}. "
                            "Yeniden kurun: python -m asistan.rag.indeksle")
        _onbellek["indeks"] = faiss.read_index(str(INDEKS_DOSYASI))
        _onbellek["parcalar"] = bilgi["parcalar"]
    return _onbellek["indeks"], _onbellek["parcalar"]


def ara(sorgu: str, kategoriler: list[str], k: int = K) -> list[dict]:
    """En benzer k parçayı skoruyla döner (yüksekten düşüğe). Eşik burada UYGULANMAZ; aracı çağıran
    (prosedur_ara) eşiğin altını eler. Böylece izde eşiğe takılan parçalar da skorlarıyla görünür.

    Filtreler: sadece ajanın kategorisindeki ve müşteriye açık (gizlilik=musteri) parçalar.
    Veri küçük (~50 parça) olduğu için tüm parçaları skorlayıp filtreyi sonra uyguluyoruz."""
    indeks, parcalar = indeksi_yukle()
    vektor = np.array([embedding_getir().embed_query(sorgu)], dtype="float32")
    faiss.normalize_L2(vektor)
    skorlar, sira_nolari = indeks.search(vektor, indeks.ntotal)  # tümü, benzerliğe göre sıralı

    sonuc = []
    for skor, i in zip(skorlar[0], sira_nolari[0]):
        parca = parcalar[i]
        # TODO (Lab 3): Şu an ajan TÜM dokümanlarda arıyor. İki filtre ekleyin (ipucu: continue):
        #   1) parçanın "kategori" alanı `kategoriler` listesinde değilse bu parçayı atlayın,
        #   2) parçanın "gizlilik" alanı "musteri" değilse atlayın ("ic" dokümanlar temsilciler içindir).
        # Test: python eval/calistir.py --id T31   ("GİZLİ DOKÜMAN getirildi" uyarısı kaybolmalı)
        sonuc.append({**parca, "skor": round(float(skor), 3)})
        if len(sonuc) == k:
            break
    return sonuc


def baglam_olustur(parcalar: list[dict], sinir: int = BAGLAM_SINIRI) -> list[dict]:
    """Ajanın bu talepte getirdiği parçalardan taslağa gidecekleri seçer:
    1) skora göre sırala (en ilgili önce),
    2) aynı kaynaktan (dosya#başlık) tekrar eden parçaları ele: ajan aynı konuyu iki kez aratınca
       aynı parça iki kez gelir; bir bölümün örtüşen iki parçası da çoğu zaman aynı şeyi söyler,
    3) toplam metin `sinir` karakteri aşmasın (sığmayan parça atlanır, daha kısa olan sığabilir)."""
    secilenler, gorulen, toplam = [], set(), 0
    for parca in sorted(parcalar, key=lambda p: p["skor"], reverse=True):
        if parca["kaynak"] in gorulen or toplam + len(parca["metin"]) > sinir:
            continue
        secilenler.append(parca)
        gorulen.add(parca["kaynak"])
        toplam += len(parca["metin"])
    return secilenler
