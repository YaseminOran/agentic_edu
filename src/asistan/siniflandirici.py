"""Talep sınıflandırıcı: tek LLM çağrısı, Pydantic ile yapılandırılmış çıktı (Hafta 2; Hafta 4'te istem
prompts/siniflandirma/ şablonuna taşındı). Çıktı: kategori, ikinci_konu, guven. Kategori listesi ve
açıklamaları kategoriler.py'den gelir; yeni kategori eklemek için bu dosyaya dokunmak gerekmez.
"""

from typing import Literal

from pydantic import BaseModel, Field

from asistan.ayarlar import model_getir
from asistan.gunluk import log
from asistan.kategoriler import TUM_KATEGORILER
from asistan.sablonlar import mesajlar

# Literal tipini sözlüğün anahtarlarından üretiyoruz: model sadece bu değerlerden birini seçebilir
KategoriAdi = Literal[tuple(TUM_KATEGORILER)]
IkinciKonu = Literal[tuple(TUM_KATEGORILER) + ("yok",)]


class Siniflandirma(BaseModel):
    """Modelden istenen yapılandırılmış çıktı. Alan açıklamaları da modele gider.
    `gerekce` ilk sırada: model önce düşünüp sonra etiket seçer (Hafta 1'den bilinen hile)."""

    gerekce: str = Field(description="Kategori seçiminin tek cümlelik gerekçesi")
    kategori: KategoriAdi = Field(description="Talebin ANA konusu")
    ikinci_konu: IkinciKonu = Field(description="Talepte ikinci, farklı kategoride bir konu varsa o kategori; yoksa 'yok'")
    guven: float = Field(description="Kategori seçiminden ne kadar eminsin, 0 ile 1 arası (ör. 0.9)")


def siniflandir(talep: str, model_turu: str = "yerel") -> Siniflandirma:
    """Talebi sınıflandırır. Model şemaya uygun çıktı veremezse guven=0 döner
    (akış bunu "belirsiz" sayar ve netleştirme/temsilci yoluna gider: güvenli taraf)."""
    # Claude'da json_schema şemaya uymayı API düzeyinde zorlar; Ollama'da function_calling kullanıyoruz
    # (Mac'teki MLX motoru json_schema'yı desteklemeyebiliyor, bkz. Hafta 1 eğitmen notu).
    yontem = "function_calling" if model_turu == "yerel" else "json_schema"
    model = model_getir(model_turu).with_structured_output(Siniflandirma, method=yontem)
    try:
        kategoriler = "\n".join(f"- {ad}: {aciklama}" for ad, aciklama in TUM_KATEGORILER.items())
        sonuc = model.invoke(mesajlar("siniflandirma", model_turu, kategoriler=kategoriler, talep=talep))
    except Exception as e:  # şemaya uymayan çıktı (ör. guven="yüksek") ValidationError verir
        log.warning("sınıflandırma çıktısı okunamadı: %s", type(e).__name__)
        sonuc = None
    if sonuc is None:
        return Siniflandirma(gerekce="yapılandırılmış çıktı alınamadı", kategori="diger", ikinci_konu="yok", guven=0.0)

    # Küçük modeller bazen 85 gibi yüzde değer döndürür; 0-1 aralığına çekiyoruz
    if sonuc.guven > 1:
        sonuc.guven = sonuc.guven / 100
    sonuc.guven = max(0.0, min(sonuc.guven, 1.0))
    if sonuc.ikinci_konu == sonuc.kategori:
        sonuc.ikinci_konu = "yok"
    return sonuc
