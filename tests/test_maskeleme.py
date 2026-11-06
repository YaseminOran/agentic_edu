"""maskeleme.py testleri (Hafta 2). pytest gerekmez: python tests/test_maskeleme.py
Her test "girdi -> beklenen çıktı" çiftidir; yeni bir kalıp eklerken önce buraya test yazın.
kontrol.py de bu testleri çalıştırır.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asistan.maskeleme import maskele  # noqa: E402

ORNEKLER = [
    # (açıklama, girdi, beklenen)
    ("kart, boşluklu", "Kartım 9999 0000 0000 0007 bloke", "Kartım [KART ****0007] bloke"),
    ("kart, bitişik", "kart no: 9999000000000011.", "kart no: [KART ****0011]."),
    ("kart, tireli", "9999-0000-0000-0004", "[KART ****0004]"),
    ("IBAN, boşluklu", "IBAN'ım TR00 9999 9000 0000 0000 0000 07", "IBAN'ım [IBAN ****0007]"),
    ("IBAN, bitişik", "TR000999990000000000000012 hesabına", "[IBAN ****0012] hesabına"),
    ("TCKN", "TCKN 99999000005 olan müşteri", "TCKN [TCKN] olan müşteri"),
    ("telefon, boşluklu", "Beni 0500 000 0020 numarasından arayın", "Beni [TELEFON ****0020] numarasından arayın"),
    ("telefon, +90", "+90 532 123 45 67", "[TELEFON ****4567]"),
    ("telefon, bitişik", "05321234567", "[TELEFON ****4567]"),
    ("hepsi bir arada",
     "Ben Ayşe, TCKN 99999000001, kart 9999 0000 0000 0001, IBAN TR00 9999 9000 0000 0000 0000 01, tel 0500 000 0001",
     "Ben Ayşe, TCKN [TCKN], kart [KART ****0001], IBAN [IBAN ****0001], tel [TELEFON ****0001]"),
    # TODO (Lab 2) çözümü: e-posta testleri
    ("e-posta", "Bana ayse.ornek1@ornek.test adresinden yazın", "Bana [EPOSTA a***@ornek.test] adresinden yazın"),
    ("e-posta, JSON içinde", '"eposta": "deniz.kurmaca4@ornek.test"', '"eposta": "[EPOSTA d***@ornek.test]"'),
    # Maskelenmemesi gerekenler (yanlış pozitif kontrolü)
    ("tutar", "Kartımdan 4.250 TL ve 750,00 TL çekildi", "Kartımdan 4.250 TL ve 750,00 TL çekildi"),
    ("müşteri no", "M0007 müşterisi", "M0007 müşterisi"),
    ("tarih", "2026-09-03 tarihinde", "2026-09-03 tarihinde"),
    ("işlem no", "I00287 numaralı işlem", "I00287 numaralı işlem"),
    ("boş metin", "", ""),
]


def test_maskeleme():
    hatalar = []
    for aciklama, girdi, beklenen in ORNEKLER:
        cikti = maskele(girdi)
        if cikti != beklenen:
            hatalar.append(f"{aciklama}: {girdi!r}\n   beklenen: {beklenen!r}\n   çıktı   : {cikti!r}")
    assert not hatalar, "\n".join(hatalar)


def test_iki_kez_maskelemek_bozmaz():
    """Maskelenmiş metin tekrar maskelenince değişmemeli (log + model yolunda iki kez geçebilir)."""
    metin = maskele("TCKN 99999000001, kart 9999 0000 0000 0001, e-posta can.deneme2@ornek.test")
    assert maskele(metin) == metin


if __name__ == "__main__":
    test_maskeleme()
    test_iki_kez_maskelemek_bozmaz()
    print(f"Maskeleme testleri geçti ({len(ORNEKLER)} örnek + 1 kararlılık testi).")
