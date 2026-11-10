"""Sahte banka servisleri (Hafta 1'de eklendi, Hafta 2'de genişletildi).
data/ altındaki sentetik JSON'ları HTTP üzerinden sunar: 5 okuma ucu ajanın araçlarıdır,
yazma uçları (temsilciye_aktar, iade_talebi_olustur, kart_bloke) sadece kod tarafından,
insan onayından sonra çağrılır. Veri bellekte tutulur; sunucu yeniden başlayınca sıfırlanır.

Hata yönetimini gösterebilmek için her istek MOCK_HATA_ORANI (.env, varsayılan 0.05) olasılıkla
503 döner ve her isteğe küçük bir gecikme eklenir. Deterministik deneme için MOCK_HATA_ORANI=0.

Çalıştırma: uvicorn mock_api.main:app --port 8000   (dev container'da otomatik başlar)
Dokümantasyon: http://localhost:8000/docs
"""

import asyncio
import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

PROJE_KOKU = Path(__file__).parent.parent
load_dotenv(PROJE_KOKU / ".env")  # container dışında da MOCK_HATA_ORANI okunabilsin

VERI_KLASORU = PROJE_KOKU / "data"
REFERANS_TARIH = date(2026, 10, 1)  # data/uret.py ile aynı "bugün"
HATA_ORANI = float(os.getenv("MOCK_HATA_ORANI", "0.05"))


def json_oku(ad: str) -> list[dict]:
    with open(VERI_KLASORU / ad, encoding="utf-8") as f:
        return json.load(f)


MUSTERILER = {m["musteri_no"]: m for m in json_oku("musteriler.json")}
KART_ISLEMLERI = json_oku("kart_islemleri.json")
HESAP_DURUMU = {h["musteri_no"]: h for h in json_oku("hesap_durumu.json")}
KREDI_BASVURULARI = json_oku("kredi_basvurulari.json")
GECMIS_TALEPLER = json_oku("gecmis_talepler.json")

# Yazma işlemlerinin kaydı (bellekte)
AKTARIMLAR: list[dict] = []
IADE_TALEPLERI: list[dict] = []
BLOKE_KAYITLARI: list[dict] = []

app = FastAPI(title="Örnek Bank – Sahte Servisler", description="Eğitim amaçlı, tüm veriler sentetiktir.")


@app.middleware("http")
async def gecikme_ve_rastgele_hata(request: Request, call_next):
    """Gerçek servisler gibi davranmak için: küçük gecikme + ara sıra 503 (yeniden deneme dersi)."""
    if request.url.path in ("/saglik", "/docs", "/openapi.json"):
        return await call_next(request)
    await asyncio.sleep(random.uniform(0.05, 0.25))
    if random.random() < HATA_ORANI:
        return JSONResponse(status_code=503, content={"detail": "Servis geçici olarak kullanılamıyor (sahte hata)."})
    return await call_next(request)


def musteri_getir(musteri_no: str) -> dict:
    musteri = MUSTERILER.get(musteri_no)
    if musteri is None:
        raise HTTPException(status_code=404, detail=f"Müşteri bulunamadı: {musteri_no}")
    return musteri


@app.get("/saglik")
def saglik():
    """kontrol.py bu ucu çağırarak servisin ayakta olduğunu doğrular."""
    return {"durum": "ok", "musteri_sayisi": len(MUSTERILER), "hata_orani": HATA_ORANI}


# ---------------------------------------------------------------------------
# Okuma uçları (ajanın araçları bunları çağırır)
# ---------------------------------------------------------------------------

@app.get("/musteri_bilgisi/{musteri_no}")
def musteri_bilgisi(musteri_no: str):
    """Müşteri profili ve kartları. Kimlik, kart no ve IBAN olduğu gibi döner (hepsi sentetik)."""
    return musteri_getir(musteri_no)


@app.get("/kart_islemleri/{musteri_no}")
def kart_islemleri(musteri_no: str, son_gun: int = 30):
    """Müşterinin son `son_gun` gündeki kart işlemleri (aidat dahil)."""
    musteri_getir(musteri_no)
    baslangic = (REFERANS_TARIH - timedelta(days=son_gun)).isoformat()
    return [i for i in KART_ISLEMLERI if i["musteri_no"] == musteri_no and i["tarih"] >= baslangic]


@app.get("/hesap_durumu/{musteri_no}")
def hesap_durumu(musteri_no: str):
    """Vadesiz hesap bakiyesi, blokeler ve son hareketler."""
    musteri_getir(musteri_no)
    return HESAP_DURUMU[musteri_no]


@app.get("/kredi_basvuru_durumu/{musteri_no}")
def kredi_basvuru_durumu(musteri_no: str):
    """Kredi başvuruları ve kullandırılmış kredilerin taksit/gecikme durumu."""
    musteri_getir(musteri_no)
    return [k for k in KREDI_BASVURULARI if k["musteri_no"] == musteri_no]


@app.get("/gecmis_talepler/{musteri_no}")
def gecmis_talepler(musteri_no: str):
    """Müşterinin daha önce açtığı talepler. musteri_notu alanı müşterinin kendi yazdığı serbest metindir."""
    musteri_getir(musteri_no)
    return [t for t in GECMIS_TALEPLER if t["musteri_no"] == musteri_no]


# ---------------------------------------------------------------------------
# Yazma uçları (ajan bunları doğrudan çağıramaz; akış kodu çağırır)
# ---------------------------------------------------------------------------

class AktarimIstegi(BaseModel):
    musteri_no: str
    ozet: str      # talep özeti
    neden: str     # neden aktarıldı (adım limiti, araç hatası, ret...)


@app.post("/temsilciye_aktar")
def temsilciye_aktar(istek: AktarimIstegi):
    """YAZMA: talebi temsilci kuyruğuna ekler. Güvenli taraf olduğu için onay gerektirmez."""
    musteri_getir(istek.musteri_no)
    kayit = {"aktarim_no": f"AKT{len(AKTARIMLAR) + 1:04d}", **istek.model_dump(), "durum": "kuyrukta"}
    AKTARIMLAR.append(kayit)
    return kayit


class IadeIstegi(BaseModel):
    musteri_no: str
    islem_id: str
    tutar: float
    sebep: str
    onaylayan: str  # onayı veren temsilci; boş olamaz


@app.post("/iade_talebi_olustur")
def iade_talebi_olustur(istek: IadeIstegi):
    """YAZMA: iade talebi açar. Ajan bunu ASLA insan onayı olmadan çağırmamalı."""
    musteri_getir(istek.musteri_no)
    if not istek.onaylayan.strip():
        raise HTTPException(status_code=400, detail="Onaylayan temsilci boş olamaz.")
    islem = next((i for i in KART_ISLEMLERI
                  if i["islem_id"] == istek.islem_id and i["musteri_no"] == istek.musteri_no), None)
    if islem is None:
        raise HTTPException(status_code=404, detail=f"Bu müşteriye ait işlem bulunamadı: {istek.islem_id}")
    if istek.tutar <= 0 or istek.tutar > islem["tutar"]:
        raise HTTPException(status_code=400, detail="İade tutarı işlem tutarını aşamaz ve sıfırdan büyük olmalı.")
    kayit = {"iade_no": f"IAD{len(IADE_TALEPLERI) + 1:04d}", **istek.model_dump(), "durum": "acildi"}
    IADE_TALEPLERI.append(kayit)
    return kayit


class KartBlokeIstegi(BaseModel):
    musteri_no: str
    sebep: str
    onaylayan: str  # onayı veren temsilcinin adı; Hafta 4'te insan onayı adımından gelir


@app.post("/kart_bloke")
def kart_bloke(istek: KartBlokeIstegi):
    """YAZMA: müşterinin ilk kartını bloke eder (Hafta 4'te kullanılacak)."""
    musteri = musteri_getir(istek.musteri_no)
    if not istek.onaylayan.strip():
        raise HTTPException(status_code=400, detail="Onaylayan temsilci boş olamaz.")
    kart = musteri["kartlar"][0]
    kart["durum"], kart["bloke_nedeni"] = "bloke", istek.sebep
    kayit = {"islem_no": f"BLK{len(BLOKE_KAYITLARI) + 1:04d}", "musteri_no": istek.musteri_no,
             "kart_son4": kart["kart_no"][-4:], "sebep": istek.sebep, "onaylayan": istek.onaylayan}
    BLOKE_KAYITLARI.append(kayit)
    return kayit
