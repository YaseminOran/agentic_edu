"""Sahte banka servisleri (Hafta 1). data/ altındaki sentetik CSV'leri HTTP üzerinden sunar.
Okuma uçları Hafta 2'de ajan araçlarına dönüşür; tek yazma ucu (kart_bloke) Hafta 4'te
insan onayı akışıyla kullanılır. Veri bellekte tutulur, sunucu yeniden başlayınca sıfırlanır.

Çalıştırma: uvicorn mock_api.main:app --port 8000   (dev container'da otomatik başlar)
Dokümantasyon: http://localhost:8000/docs
"""

import csv
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

VERI_KLASORU = Path(__file__).parent.parent / "data"
REFERANS_TARIH = date(2026, 10, 1)  # data/uret.py ile aynı "bugün"


def csv_oku(ad: str) -> list[dict]:
    with open(VERI_KLASORU / ad, encoding="utf-8") as f:
        return list(csv.DictReader(f))


MUSTERILER = {m["musteri_no"]: m for m in csv_oku("musteriler.csv")}
KART_ISLEMLERI = csv_oku("kart_islemleri.csv")
GECMIS_TALEPLER = csv_oku("gecmis_talepler.csv")
BLOKE_KAYITLARI: list[dict] = []  # yazma işlemlerinin kaydı (bellekte)

app = FastAPI(title="Örnek Bank – Sahte Servisler", description="Eğitim amaçlı, tüm veriler sentetiktir.")


def musteri_getir(musteri_no: str) -> dict:
    musteri = MUSTERILER.get(musteri_no)
    if musteri is None:
        raise HTTPException(status_code=404, detail=f"Müşteri bulunamadı: {musteri_no}")
    return musteri


@app.get("/saglik")
def saglik():
    """kontrol.py bu ucu çağırarak servisin ayakta olduğunu doğrular."""
    return {"durum": "ok", "musteri_sayisi": len(MUSTERILER)}


@app.get("/musteri/{musteri_no}")
def musteri_bilgisi(musteri_no: str):
    """Müşteri profilini döner. DİKKAT: TCKN, kart no ve IBAN maskesiz gelir (Hafta 2 konusu)."""
    return musteri_getir(musteri_no)


@app.get("/kart_islemleri/{musteri_no}")
def kart_islemleri(musteri_no: str, son_gun: int = 30):
    """Müşterinin son `son_gun` gündeki kart işlemlerini döner."""
    musteri_getir(musteri_no)
    baslangic = (REFERANS_TARIH - timedelta(days=son_gun)).isoformat()
    return [i for i in KART_ISLEMLERI if i["musteri_no"] == musteri_no and i["tarih"] >= baslangic]


@app.get("/gecmis_talepler/{musteri_no}")
def gecmis_talepler(musteri_no: str):
    """Müşterinin daha önce açtığı talepleri döner."""
    musteri_getir(musteri_no)
    return [t for t in GECMIS_TALEPLER if t["musteri_no"] == musteri_no]


class KartBlokeIstegi(BaseModel):
    musteri_no: str
    sebep: str
    onaylayan: str  # onayı veren temsilcinin adı; Hafta 4'te insan onayı adımından gelir


@app.post("/kart_bloke")
def kart_bloke(istek: KartBlokeIstegi):
    """YAZMA İŞLEMİ: kartı bloke eder. Ajan bunu ASLA insan onayı olmadan çağırmamalı."""
    musteri = musteri_getir(istek.musteri_no)
    if not istek.onaylayan.strip():
        raise HTTPException(status_code=400, detail="Onaylayan temsilci boş olamaz.")
    musteri["kart_durumu"] = "bloke"
    kayit = {
        "islem_no": f"BLK{len(BLOKE_KAYITLARI) + 1:04d}",
        "musteri_no": istek.musteri_no,
        "kart_son4": musteri["kart_no"][-4:],
        "sebep": istek.sebep,
        "onaylayan": istek.onaylayan,
    }
    BLOKE_KAYITLARI.append(kayit)
    return kayit
