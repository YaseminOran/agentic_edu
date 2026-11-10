"""Ayarları .env'den okur ve model nesnelerini üretir (Hafta 1).
Model adı, adres ve anahtar asla koda yazılmaz; hepsi buradan, .env üzerinden gelir.
Diğer tüm dosyalar modeli `model_getir("yerel" | "bulut" | "guclu")` ile alır.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJE_KOKU = Path(__file__).resolve().parents[2]
load_dotenv(PROJE_KOKU / ".env")

# .env'deki "host.docker.internal" adresi sadece container içinden çözülür. Container dışında
# (ör. Mac'te .venv ile) aynı makinedeki Ollama'ya localhost üzerinden ulaşılır. Böylece .env'yi
# değiştirmeden proje hem container'da hem lokalde çalışır. (/.dockerenv: Docker container'ı işareti)
if not Path("/.dockerenv").exists() and "host.docker.internal" in os.getenv("OLLAMA_URL", ""):
    os.environ["OLLAMA_URL"] = os.environ["OLLAMA_URL"].replace("host.docker.internal", "localhost")

# Kurumsal proxy: bilgisayarda HTTP_PROXY tanımlıysa Python, yerel servislere (mock API, Ollama) giden
# istekleri de proxy'ye gönderir; proxy bu adreslere ulaşamaz ve 503 döner. Yerel adresleri proxy dışında
# tutuyoruz. Buluta (Claude) giden istekler proxy'yi kullanmaya devam eder.
YEREL_ADRESLER = ["localhost", "127.0.0.1", "host.docker.internal", "ollama"]
for _degisken in ("NO_PROXY", "no_proxy"):
    _mevcut = [a.strip() for a in os.getenv(_degisken, "").split(",") if a.strip()]
    os.environ[_degisken] = ",".join(_mevcut + [a for a in YEREL_ADRESLER if a not in _mevcut])


def ayar(ad: str) -> str:
    """.env'deki bir değeri okur; boşsa anlaşılır bir hata verir."""
    deger = os.getenv(ad, "").strip()
    if not deger:
        raise RuntimeError(f"{ad} tanımlı değil. .env dosyasını kontrol edin (.env.example'a bakın).")
    return deger


def model_getir(tur: str = "yerel"):
    """LangChain sohbet modeli döner.

    tur="yerel"  -> Ollama (OLLAMA_MODEL), ücretsiz, makinede çalışır
    tur="bulut"  -> Claude (CLAUDE_MODEL)
    tur="guclu"  -> Claude (CLAUDE_MODEL_GUCLU), zor görevler için
    """
    if tur == "yerel":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=ayar("OLLAMA_MODEL"),
            base_url=ayar("OLLAMA_URL"),
            temperature=0,     # sınıflandırmada tekrarlanabilir sonuç istiyoruz
            reasoning=False,   # qwen3.5'in "düşünme" modunu kapatır; Hafta 1 için hızlı yanıt yeterli
        )

    if tur in ("bulut", "guclu"):
        from langchain_anthropic import ChatAnthropic

        ayar("ANTHROPIC_API_KEY")  # yoksa erken ve anlaşılır hata
        # Not: Güncel Claude modelleri temperature ayarını kabul etmez; bu yüzden göndermiyoruz.
        return ChatAnthropic(
            model=ayar("CLAUDE_MODEL" if tur == "bulut" else "CLAUDE_MODEL_GUCLU"),
            max_tokens=4096,
        )

    raise ValueError(f"Bilinmeyen model türü: {tur!r}. 'yerel', 'bulut' veya 'guclu' olmalı.")


def embedding_getir():
    """Metinleri vektöre çeviren embedding modeli (Hafta 3'te FAISS ile kullanılır)."""
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(model=ayar("EMBED_MODEL"), base_url=ayar("OLLAMA_URL"))
