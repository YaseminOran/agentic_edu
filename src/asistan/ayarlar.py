"""Ayarları .env'den okur ve model nesnelerini üretir (Hafta 1).
Model adı, adres ve anahtar asla koda yazılmaz; hepsi buradan, .env üzerinden gelir.
Diğer tüm dosyalar modeli `model_getir("yerel" | "bulut" | "guclu")` ile alır.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJE_KOKU = Path(__file__).resolve().parents[2]
load_dotenv(PROJE_KOKU / ".env")


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
