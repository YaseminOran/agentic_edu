"""Okuma araçlarını bir MCP sunucusu olarak yayınlar ve ajanın bağlanması için istemci tarafını içerir (Hafta 2).
Sunucu: araclar.py'deki aynı araçları MCP (stdio) üzerinden sunar. Aktif müşteri, sunucu başlatılırken
AKTIF_MUSTERI ortam değişkeniyle verilir: model müşteri numarasını yine göremez ve değiştiremez.
İstemci: mcp_araclarini_yukle() langchain-mcp-adapters ile bağlanıp LangChain araçları döner.

Ajanı MCP ile çalıştırma:  python -m asistan.ajan "Kartımın son kullanma tarihi ne zaman?" M0004 --mcp
Sunucuyu tek başına başlatma (MCP Inspector vb. için):  AKTIF_MUSTERI=M0004 python -m asistan.mcp_sunucu
"""

import asyncio
import logging
import os
import sys
from typing import Annotated

from langchain_core.tools import StructuredTool
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from asistan import araclar
from asistan.ayarlar import PROJE_KOKU

# ---------------------------------------------------------------------------
# SUNUCU: sadece OKUMA araçları yayınlanır; yazma araçları bilerek yok.
# Açıklamalar araclar.py'den alınır, böylece iki giriş noktası aynı metni kullanır.
# ---------------------------------------------------------------------------

mcp = FastMCP("ornek-bank-okuma", log_level="WARNING")


def calistir(arac, **parametreler) -> str:
    """Aracı sunucunun müşterisi için çalıştırır. İstemci başka bir müşteri isteyemez."""
    with araclar.musteri_oturumu(os.environ["AKTIF_MUSTERI"]):
        try:
            return arac.invoke(parametreler)
        except araclar.ApiHatasi as e:
            return f"HATA: {e}"


@mcp.tool(description=araclar.musteri_bilgisi.description)
def musteri_bilgisi() -> str:
    return calistir(araclar.musteri_bilgisi)


@mcp.tool(description=araclar.kart_islemleri.description)
def kart_islemleri(son_gun: Annotated[int, Field(description="Kaç gün geriye bakılacağı (1-90)")] = 30) -> str:
    return calistir(araclar.kart_islemleri, son_gun=son_gun)


@mcp.tool(description=araclar.hesap_durumu.description)
def hesap_durumu() -> str:
    return calistir(araclar.hesap_durumu)


@mcp.tool(description=araclar.kredi_basvuru_durumu.description)
def kredi_basvuru_durumu() -> str:
    return calistir(araclar.kredi_basvuru_durumu)


@mcp.tool(description=araclar.gecmis_talepler.description)
def gecmis_talepler() -> str:
    return calistir(araclar.gecmis_talepler)


@mcp.tool(description=araclar.prosedur_ara.description)
def prosedur_ara(sorgu: Annotated[str, Field(description="Aranacak konu, kısa ve anahtar kelimelerle")]) -> str:
    return calistir(araclar.prosedur_ara, sorgu=sorgu)


# ---------------------------------------------------------------------------
# İSTEMCİ (ajan tarafı)
# ---------------------------------------------------------------------------


def mcp_araclarini_yukle(musteri_no: str) -> list:
    """MCP sunucusunu alt süreç olarak başlatır, araçlarını LangChain aracı olarak döner.

    langchain-mcp-adapters araçları asenkrondur; ajanımız senkron çalıştığı için her aracı
    asyncio.run ile saran küçük bir senkron araca çeviriyoruz. Her çağrı yeni bir MCP oturumu
    (yeni alt süreç) açar: yavaş ama basit."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    istemci = MultiServerMCPClient({
        "banka": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "asistan.mcp_sunucu"],
            "cwd": str(PROJE_KOKU),
            # Sadece gereken değişkenler: API anahtarı gibi sırlar araç sunucusuna geçmez.
            # (Sunucu MOCK_API_URL'i .env'den kendisi okur.)
            "env": {"AKTIF_MUSTERI": musteri_no, "PYTHONPATH": str(PROJE_KOKU / "src")},
        }
    })
    asenkron_araclar = asyncio.run(istemci.get_tools())

    def senkron_yap(arac):
        return StructuredTool.from_function(
            func=lambda **parametreler: asyncio.run(arac.ainvoke(parametreler)),
            name=arac.name, description=arac.description, args_schema=arac.args_schema)

    return [senkron_yap(a) for a in asenkron_araclar]


if __name__ == "__main__":
    if not os.environ.get("AKTIF_MUSTERI"):
        sys.exit("AKTIF_MUSTERI ortam değişkeni gerekli (ör. AKTIF_MUSTERI=M0004).")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # her HTTP isteğini stderr'e basmasın
    mcp.run(transport="stdio")
