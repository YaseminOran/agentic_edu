"""Maskeleme katmanının testleri (Hafta 4). Model veya servis gerekmez, saniyeler içinde biter.
Çalıştırma:  python tests/test_maskeleme.py      (pytest kuruluysa `pytest tests` de çalışır)
Her test tek bir şeyi kontrol eder; hata olursa hangi testin düştüğü yazılır.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asistan.maskeleme import (geri_cevir, maskele, metni_maskele, tam_veri_bul,  # noqa: E402
                               veriyi_maskele, yeni_tablo)

KART = "9999 0000 0000 0007"
IBAN = "TR00 9999 9000 0000 0000 0000 07"


def test_takma_ad_verilir():
    tablo = yeni_tablo()
    sonuc = metni_maskele(f"Kartım {KART}, IBAN'ım {IBAN}.", tablo)
    assert sonuc == "Kartım [KART_1], IBAN'ım [IBAN_1].", sonuc


def test_ayni_deger_hep_ayni_takma_adi_alir():
    tablo = yeni_tablo()
    birinci = metni_maskele(f"Kart: {KART}", tablo)
    ikinci = metni_maskele("Kart: 9999-0000-0000-0007", tablo)  # aynı numara, farklı yazım
    assert birinci == ikinci == "Kart: [KART_1]", (birinci, ikinci)


def test_farkli_degerler_farkli_takma_ad_alir():
    tablo = yeni_tablo()
    sonuc = metni_maskele("9999 0000 0000 0007 ve 9999 0000 0000 0011", tablo)
    assert sonuc == "[KART_1] ve [KART_2]", sonuc


def test_geri_cevirme_tam_numara_yazmaz():
    tablo = yeni_tablo()
    maskeli = metni_maskele(f"Aidat {KART} üzerinden kesildi, iade {IBAN} adresine yapılır.", tablo)
    musteriye = geri_cevir(maskeli, tablo)
    assert "0007 ile biten kartınız" in musteriye, musteriye
    assert "07 ile biten IBAN'ınız" in musteriye, musteriye
    assert tam_veri_bul(musteriye) == [], musteriye


def test_geri_cevirme_cumleye_uyar():
    # Model "[KART_1] numaralı ..." ya da "[KART_1] kartınız" yazarsa cümle bozulmasın
    tablo = yeni_tablo()
    metni_maskele(f"{KART}", tablo)
    assert geri_cevir("[KART_1] numaralı Örnek Classic Kart aktif.", tablo) == "0007 ile biten Örnek Classic Kart aktif."
    assert geri_cevir("[KART_1] kartınızdan kesildi.", tablo) == "0007 ile biten kartınızdan kesildi."
    assert geri_cevir("Aidat [KART_1] üzerinden kesildi.", tablo) == "Aidat 0007 ile biten kartınız üzerinden kesildi."
    assert geri_cevir("[KART_1] numaralı karttan", tablo) == "0007 ile biten karttan"


def test_bilinmeyen_takma_ad_gizli_kalir():
    # Model tabloda olmayan bir takma ad uydurursa müşteriye hiçbir numara gitmez
    assert geri_cevir("[KART_9] kartınız", yeni_tablo()) == "[gizli bilgi] kartınız"


def test_arac_ciktisi_maskelenir():
    tablo = yeni_tablo()
    veri = {"musteri_no": "M0007", "ad_soyad": "Selin Prova", "tckn": "99999000007",
            "telefon": "0500 000 0007", "iban": IBAN,
            "kartlar": [{"kart_no": KART, "durum": "aktif", "limit": 25000}]}
    maskeli = veriyi_maskele(veri, tablo)
    assert maskeli["ad_soyad"] == "[AD_1]" and maskeli["tckn"] == "[TCKN_1]", maskeli
    assert maskeli["kartlar"][0]["kart_no"] == "[KART_1]", maskeli
    assert maskeli["kartlar"][0]["limit"] == 25000 and maskeli["musteri_no"] == "M0007", maskeli
    assert tam_veri_bul(str(maskeli)) == [], maskeli


def test_taninan_ad_serbest_metinde_de_maskelenir():
    tablo = yeni_tablo()
    veriyi_maskele({"ad_soyad": "Selin Prova"}, tablo)
    assert metni_maskele("Merhaba Selin Prova", tablo) == "Merhaba [AD_1]"
    assert geri_cevir("Sayın [AD_1]", tablo) == "Sayın Selin P."


def test_arac_metnindeki_numara_da_maskelenir():
    # Müşterinin serbest notunda (gecmis_talepler) geçen numara alan adından tanınmaz, kalıptan tanınır
    tablo = yeni_tablo()
    maskeli = veriyi_maskele([{"musteri_notu": f"Kartım {KART} bloke oldu"}], tablo)
    assert maskeli[0]["musteri_notu"] == "Kartım [KART_1] bloke oldu", maskeli


def test_basit_maskeleme_iz_icin():
    assert maskele(f"kart {KART}, tel 0532 123 45 67") == "kart [KART], tel [TEL]"


if __name__ == "__main__":
    testler = [(ad, f) for ad, f in sorted(globals().items()) if ad.startswith("test_")]
    hatali = 0
    for ad, f in testler:
        try:
            f()
            print(f"  ✅ {ad}")
        except AssertionError as e:
            hatali += 1
            print(f"  ❌ {ad}: {e}")
    print(f"\n{len(testler) - hatali}/{len(testler)} test geçti")
    sys.exit(1 if hatali else 0)
