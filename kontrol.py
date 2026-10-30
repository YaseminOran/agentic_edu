"""Ortam kontrolü (Hafta 1): Python, paketler, .env, veri, mock API, Ollama ve Claude erişimi.
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
    dosyalar = ["data/musteriler.csv", "data/kart_islemleri.csv", "data/gecmis_talepler.csv",
                "data/talepler.csv", "eval/test_seti.csv", "eval/ortak_set.csv"]
    eksik = [d for d in dosyalar if not (PROJE_KOKU / d).exists()]
    if eksik:
        raise RuntimeError(f"eksik: {', '.join(eksik)} (CSV'ler için: python data/uret.py)")
    prosedur_sayisi = len(list((PROJE_KOKU / "data" / "prosedurler").glob("*.md")))
    if prosedur_sayisi == 0:
        raise RuntimeError("data/prosedurler/ boş")
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
    return f"{url} ({cevap.json()['musteri_sayisi']} müşteri)"


def ollama_modelleri():
    import httpx
    from asistan.ayarlar import ayar

    url = ayar("OLLAMA_URL")
    try:
        modeller = httpx.get(f"{url}/api/tags", timeout=5).json()["models"]
    except httpx.ConnectError:
        raise RuntimeError(f"{url} erişilemiyor. Ollama çalışıyor mu? OLLAMA_URL doğru mu?")
    yuklu = {m["name"] for m in modeller} | {m["name"].removesuffix(":latest") for m in modeller}
    eksik = [m for m in (ayar("OLLAMA_MODEL"), ayar("EMBED_MODEL")) if m not in yuklu]
    if eksik:
        raise RuntimeError(f"indirilmemiş: {', '.join(eksik)} -> ollama pull {eksik[0]}")
    return f"{ayar('OLLAMA_MODEL')}, {ayar('EMBED_MODEL')}"


def yerel_model_cagrisi():
    from asistan import cevapla

    # Düz sohbet değil, asistanın kullandığı yapılandırılmış çıktı yolu test edilir
    sonuc = cevapla("Kartımı kaybettim.", musteri_no="M1001", model_turu="yerel")
    return f"cevapla() -> {sonuc['kategori']} / {sonuc['davranis']}"


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
    kontrol("Yerel model çağrısı", yerel_model_cagrisi)
    kontrol("Claude çağrısı", claude_cagrisi)

    hatalar = [ad for durum, ad in sonuclar if durum == "❌"]
    print()
    if hatalar:
        print(f"{len(hatalar)} kontrol başarısız: {', '.join(hatalar)}")
        sys.exit(1)
    print("Ortam hazır.")
