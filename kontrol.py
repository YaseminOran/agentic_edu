"""Ortam kontrolü (Hafta 1'de eklendi, Hafta 2 ve 3'te genişletildi): Python, paketler, .env, veri,
mock API uç noktaları, Ollama (sohbet + embedding modeli), prosedür indeksi, asistan akışı ve Claude erişimi.
Her haftanın başında ve sonunda çalıştırın: python kontrol.py
Her madde ✅ (tamam), ⚠️ (uyarı, devam edilebilir) veya ❌ (düzeltilmeli) olarak raporlanır.
"""

import importlib
import os
import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).parent
sys.path.insert(0, str(PROJE_KOKU / "src"))  # "import asistan" için

sonuclar = []  # (durum, ad) çiftleri; en sonda özet için


class Uyari(Exception):
    """Sorun var ama çalışmaya engel değil."""


def kontrol(ad: str, fonksiyon) -> None:
    """Bir kontrolü çalıştırır, sonucu ekrana yazar."""
    try:
        detay = fonksiyon() or ""
        durum = "✅"
    except Uyari as e:
        durum, detay = "⚠️ ", str(e)
    except Exception as e:
        durum, detay = "❌", f"{type(e).__name__}: {e}"
    sonuclar.append((durum, ad))
    print(f"{durum} {ad:<28} {detay}")


def python_surumu():
    if sys.version_info < (3, 12):
        raise RuntimeError(f"Python 3.12+ gerekli, bulunan: {sys.version.split()[0]}")
    return sys.version.split()[0]


def paketler():
    gerekli = ["langchain", "langgraph", "langchain_anthropic", "langchain_ollama",
               "langchain_mcp_adapters", "faiss", "fastapi", "uvicorn", "httpx", "streamlit", "dotenv"]
    eksik = []
    for ad in gerekli:
        try:
            importlib.import_module(ad)
        except ImportError:
            eksik.append(ad)
    if eksik:
        raise RuntimeError(f"eksik: {', '.join(eksik)} -> pip install -r requirements.txt")
    return f"{len(gerekli)} paket yüklü"


def env_dosyasi():
    if not (PROJE_KOKU / ".env").exists():
        raise RuntimeError(".env yok -> .env.example dosyasını .env adıyla kopyalayın")
    from asistan.ayarlar import ayar  # .env'yi yükler

    for ad in ["OLLAMA_URL", "OLLAMA_MODEL", "EMBED_MODEL", "MOCK_API_URL", "CLAUDE_MODEL", "CLAUDE_MODEL_GUCLU"]:
        ayar(ad)
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise Uyari("ANTHROPIC_API_KEY boş; sadece yerel model kullanılabilir")
    return "tüm alanlar dolu"


def veri_dosyalari():
    import csv

    from asistan.kategoriler import KATEGORILER

    dosyalar = ["data/musteriler.json", "data/kart_islemleri.json", "data/hesap_durumu.json",
                "data/kredi_basvurulari.json", "data/gecmis_talepler.json", "data/harici_veri.json", "data/talepler.csv",
                "eval/test_seti.csv", "eval/ortak_set.csv"]
    eksik = [d for d in dosyalar if not (PROJE_KOKU / d).exists()]
    if eksik:
        raise RuntimeError(f"eksik: {', '.join(eksik)} (veri için: python data/uret.py)")
    # Her ajan kategorisinin prosedür klasörü dolu olmalı (prosedur_ara bunları arar)
    for ad, kategori in KATEGORILER.items():
        if not list(kategori["prosedur_klasoru"].glob("*.md")):
            raise RuntimeError(f"{ad} kategorisinin prosedür klasörü boş: {kategori['prosedur_klasoru']}")
    with open(PROJE_KOKU / "eval" / "test_seti.csv", encoding="utf-8") as f:
        kolonlar = next(csv.reader(f))
    beklenen = ["id", "talep", "musteri_no", "beklenen_kategori", "ikinci_konu", "beklenen_davranis",
                "beklenen_araclar", "beklenen_kaynak", "zorluk", "not"]
    if kolonlar != beklenen:
        raise RuntimeError(f"test_seti.csv kolonları beklenen formata uymuyor: {kolonlar}")
    prosedur_sayisi = len(list((PROJE_KOKU / "data" / "prosedurler").rglob("*.md")))
    return f"{len(dosyalar)} dosya + {prosedur_sayisi} prosedür"


def mock_api():
    import httpx
    from asistan.ayarlar import ayar

    url = ayar("MOCK_API_URL")
    try:
        cevap = httpx.get(f"{url}/saglik", timeout=5)
    except httpx.ConnectError:
        raise RuntimeError(f"{url} erişilemiyor -> uvicorn mock_api.main:app --port 8000")
    if cevap.status_code != 200 or cevap.json().get("durum") != "ok":
        raise RuntimeError(f"{url} yanıt verdi ama bizim mock API değil (port başka bir serviste olabilir)")
    # Hafta 2 uç noktaları: eski bir mock API süreci açık kalmışsa burada yakalanır
    from asistan.araclar import OKUMA_ARACLARI, musteri_oturumu

    from asistan.araclar import ApiHatasi

    yazilmamis = []
    with musteri_oturumu("M0001"):
        for arac in OKUMA_ARACLARI:
            if arac.name == "prosedur_ara":  # API'yi değil indeksi kullanır: ayrı kontrol ("Prosedür indeksi")
                continue
            try:
                arac.invoke({})
            except NotImplementedError:  # lab görevi henüz yapılmamış
                yazilmamis.append(arac.name)
            except ApiHatasi as e:
                if "Not Found" in str(e):  # uç nokta yok: kod yeni, çalışan mock API süreci eski
                    raise RuntimeError(f"{arac.name} ucu yok; eski mock API açık -> pkill -f uvicorn ve yeniden başlatın")
                raise
    if yazilmamis:
        raise Uyari(f"API ayakta, ama şu araçlar henüz yazılmamış: {', '.join(yazilmamis)} (lab görevi)")
    return f"{url} ({cevap.json()['musteri_sayisi']} müşteri, {len(OKUMA_ARACLARI)} okuma aracı, hata oranı {cevap.json().get('hata_orani')})"


def ollama_modelleri():
    import httpx
    from asistan.ayarlar import ayar

    url = ayar("OLLAMA_URL")
    try:
        modeller = httpx.get(f"{url}/api/tags", timeout=5).json()["models"]
    except httpx.ConnectError:
        raise RuntimeError(f"{url} erişilemiyor. Ollama çalışıyor mu? OLLAMA_URL doğru mu?")
    yuklu = {m["name"] for m in modeller} | {m["name"].removesuffix(":latest") for m in modeller}
    if ayar("OLLAMA_MODEL") not in yuklu:
        raise RuntimeError(f"sohbet modeli indirilmemiş -> ollama pull {ayar('OLLAMA_MODEL')}")
    if ayar("EMBED_MODEL") not in yuklu:
        raise RuntimeError(f"embedding modeli ({ayar('EMBED_MODEL')}) indirilmemiş; prosedür araması çalışmaz "
                           f"-> ollama pull {ayar('EMBED_MODEL')} (bge-m3 yaklaşık 1,2 GB)")
    return f"{ayar('OLLAMA_MODEL')}, {ayar('EMBED_MODEL')}"


def prosedur_indeksi():
    """Hafta 3: FAISS indeksi kurulmuş mu, aynı embedding modeliyle mi, arama sonuç veriyor mu?"""
    from asistan.rag.arama import SKOR_ESIGI, ara, indeksi_yukle

    komut = "PYTHONPATH=src python -m asistan.rag.indeksle --chunk 400 --ortusme 50"
    indeks, _ = indeksi_yukle()  # indeks yoksa hata mesajı kurma komutunu söyler
    sonuc = ara("hesap işletim ücreti muafiyet", ["hesap"], k=1)
    if not sonuc or sonuc[0]["skor"] < SKOR_ESIGI:
        raise Uyari(f"indeks var ama deneme araması zayıf sonuç verdi; yeniden kurun -> {komut}")
    # Lab 3: kart ajanının aramasına başka kategoriden ya da gizli (ic) dokümandan parça gelmemeli
    gelenler = ara("harcama itirazı otomatik kabul kriterleri hesap işletim ücreti", ["kart"], k=10)
    if any(p["kategori"] != "kart" or p["gizlilik"] != "musteri" for p in gelenler):
        raise Uyari("arama kategori/gizlilik filtresi uygulamıyor (Lab 3: rag/arama.py)")
    return f"{indeks.ntotal} parça; deneme: {sonuc[0]['kaynak']} ({sonuc[0]['skor']:.2f})"


def yerel_model_cagrisi():
    from asistan import cevapla

    # Düz sohbet değil, asistanın tüm akışı (sınıflandırma + ajan + araç + taslak) test edilir
    sonuc = cevapla("Kartımın son kullanma tarihi ne zaman?", musteri_no="M0004", model_turu="yerel")
    return (f"cevapla() -> {sonuc['kategori']} / {sonuc['davranis']}, "
            f"araçlar: {', '.join(sonuc['kullanilan_araclar']) or '-'}")


def claude_cagrisi():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise Uyari("anahtar yok, atlandı")
    from asistan.ayarlar import model_getir

    cevap = model_getir("bulut").invoke("Sadece 'tamam' yaz.")
    return f"yanıt: {cevap.text.strip()[:30]!r}"  # yapılandırılmış çıktı eval'de test edilir


if __name__ == "__main__":
    print("Ortam kontrolü\n")
    kontrol("Python sürümü", python_surumu)
    kontrol("Paketler", paketler)
    kontrol(".env", env_dosyasi)
    kontrol("Veri dosyaları", veri_dosyalari)
    kontrol("Mock API", mock_api)
    kontrol("Ollama modelleri", ollama_modelleri)
    kontrol("Prosedür indeksi", prosedur_indeksi)
    kontrol("Yerel model + ajan akışı", yerel_model_cagrisi)
    kontrol("Claude çağrısı", claude_cagrisi)

    hatalar = [ad for durum, ad in sonuclar if durum == "❌"]
    print()
    if hatalar:
        print(f"{len(hatalar)} kontrol başarısız: {', '.join(hatalar)}")
        sys.exit(1)
    print("Ortam hazır.")
