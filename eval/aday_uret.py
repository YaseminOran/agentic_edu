"""Temsilci geri bildirimlerini test seti adayına dönüştürür (Hafta 4, adım 6).
Okur: eval/geri_bildirim.csv (insan onayında reddedilen ya da düzeltilen yanıtlar)
Yazar: eval/test_seti_adaylari.csv (test_seti.csv ile aynı kolonlar). Adaylar eğitmen onayıyla test setine taşınır.

Kullanım:  python eval/aday_uret.py
"""

import csv
import sys
from pathlib import Path

EVAL_KLASORU = Path(__file__).parent
GIRDI = EVAL_KLASORU / "geri_bildirim.csv"
CIKTI = EVAL_KLASORU / "test_seti_adaylari.csv"

# Temsilcinin kararından beklenen davranış önerisi: reddedilen taslak temsilciye gider; düzeltilerek
# onaylanan taslak yine insan onayından geçmelidir. Son kararı eğitmen verir.
ONERILEN_DAVRANIS = {"red": "temsilciye_aktar", "duzeltme": "insan_onayi"}


def main() -> int:
    if not GIRDI.exists():
        print(f"Henüz geri bildirim yok: {GIRDI.relative_to(EVAL_KLASORU.parent)}\n"
              "demo.py ile bir insan onayını reddedin ya da düzeltin, sonra tekrar çalıştırın.")
        return 0
    with open(EVAL_KLASORU / "test_seti.csv", encoding="utf-8") as f:
        kolonlar = csv.DictReader(f).fieldnames
    with open(GIRDI, encoding="utf-8") as f:
        geri_bildirimler = list(csv.DictReader(f))

    adaylar = []
    for i, g in enumerate(geri_bildirimler, 1):
        aday = dict.fromkeys(kolonlar, "")
        aday.update({
            "id": f"A{i:02d}", "talep": g["talep"], "musteri_no": g["musteri_no"],
            "beklenen_davranis": ONERILEN_DAVRANIS.get(g["karar"], ""), "zorluk": "geri_bildirim",
            "not": f"Temsilci {g['karar']}: {g['gerekce']}"
                   + (f" | düzeltilmiş yanıt: {g['duzeltilmis_yanit']}" if g["duzeltilmis_yanit"] else ""),
        })
        adaylar.append(aday)

    with open(CIKTI, "w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=kolonlar)
        yazici.writeheader()
        yazici.writerows(adaylar)
    print(f"{len(adaylar)} aday yazıldı: {CIKTI.relative_to(EVAL_KLASORU.parent)}")
    for a in adaylar:
        print(f"  {a['id']} [{a['beklenen_davranis'] or '?'}] {a['talep'][:60]}  <- {a['not'][:80]}")
    print("\nKategori ve beklenen kaynak boş: eğitmen doldurur, onaylarsa test_seti.csv'ye taşır.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
