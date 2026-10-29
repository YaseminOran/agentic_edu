"""Müşteri talep asistanı – Hafta 1 başlangıç sürümü.
Tek bir LLM çağrısıyla talebi sınıflandırır (kategori + davranış) ve kısa bir yanıt taslağı yazar.
Henüz araç, kaynak (RAG), maskeleme veya ajan döngüsü yok; bunlar sonraki haftalarda eklenir.
"""

from typing import Literal

from pydantic import BaseModel, Field

from asistan.ayarlar import model_getir

# Sabit etiket kümeleri (eval/test_seti.csv ile birebir aynı olmalı)
Kategori = Literal["kart", "kredi", "hesap", "dijital_kanal", "guvenlik", "diger"]
Davranis = Literal["yanitla", "netlestir", "temsilciye_aktar", "insan_onayi", "reddet"]


class Siniflandirma(BaseModel):
    """Modelden istediğimiz yapılandırılmış çıktı. Alan açıklamaları da modele gider."""

    kategori: Kategori = Field(description="Talebin konusu")
    davranis: Davranis = Field(description="Asistanın bu talep karşısında ne yapması gerektiği")
    yanit: str = Field(description="Müşteriye gönderilecek kısa yanıt taslağı (Türkçe, en fazla 3 cümle)")


# HAFTA 1 GÖREVİ: Bu sistem mesajı bilerek basit tutuldu. Değerlendirme sonuçlarına bakarak
# iyileştirin: karar sırası, sınır durumları, birkaç örnek (few-shot) ... (bkz. haftalar/hafta-1/GOREVLER.md)
SISTEM_MESAJI = """Sen Örnek Bank'ın müşteri talep asistanısın. Gelen talebi sınıflandır ve kısa bir yanıt taslağı yaz.

Kategoriler:
- kart: kredi/banka kartı, ekstre, limit, aidat, harcama itirazı
- kredi: kredi başvurusu, faiz, taksit, erken kapama, yapılandırma
- hesap: vadesiz/vadeli hesap, ücretler, IBAN, EFT/havale/FAST
- dijital_kanal: mobil şube, internet şube, şifre, giriş sorunları
- guvenlik: kayıp/çalıntı kart, şüpheli işlem, dolandırıcılık
- diger: yukarıdakilere uymayan her şey

Davranışlar:
- yanitla: bilgi verilerek doğrudan yanıtlanabilir
- netlestir: talep belirsiz, müşteriden ek bilgi istenmeli
- temsilciye_aktar: bir müşteri temsilcisinin ilgilenmesi gerekir
- insan_onayi: bir işlem yapılması gerekir (ör. kart bloke, iade), insan onayı şart
- reddet: talep karşılanmamalı

Yanıt dili resmî ve nazik olsun, müşteriye "siz" diye hitap et."""


def cevapla(talep: str, musteri_no: str, model_turu: str = "yerel") -> dict:
    """Projenin ortak arayüzü. Her hafta içi değişir, imzası ve dönen sözlük değişmez.

    Dönen sözlük: {kategori, davranis, yanit, kaynaklar: list, adimlar: list}
    musteri_no Hafta 1'de kullanılmıyor; Hafta 2'de araçlar müşteri bilgisini bununla çeker.
    """
    # method="json_schema": model çıktısı şemaya uymak ZORUNDA (Ollama'da format, Claude'da output_config)
    model = model_getir(model_turu).with_structured_output(Siniflandirma, method="json_schema")
    sonuc: Siniflandirma = model.invoke([
        ("system", SISTEM_MESAJI),
        ("human", talep),
    ])

    return {
        "kategori": sonuc.kategori,
        "davranis": sonuc.davranis,
        "yanit": sonuc.yanit,
        "kaynaklar": [],  # Hafta 3'te prosedür kaynakları buraya gelecek
        "adimlar": [f"model={model_turu}", f"siniflandirma: {sonuc.kategori} / {sonuc.davranis}"],
    }
