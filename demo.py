"""Asistanın uçtan uca komut satırı demosu (Hafta 4, adım 10). Tek komut:  python demo.py  [--model bulut]
Talebi ve müşteri numarasını yazarsınız; adımlar, kaynaklar ve yanıt okunur biçimde görünür. İnsan onayı
gerektiğinde terminalde evet/hayır sorulur. Hafta 5'te bunun yerine Streamlit arayüzü gelecek.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))  # "import asistan" için

from asistan import cevapla, onayla  # noqa: E402

ORNEK_TALEP = "Kartımdan aidat iki kez kesildi"
ORNEK_MUSTERI = "M0007"
CIZGI = "─" * 70


def goster(sonuc: dict) -> None:
    """Asistanın çıktısını dört bölüm halinde yazar: adımlar, kaynaklar, karar, yanıt."""
    print(f"\n{CIZGI}\nADIMLAR")
    for i, adim in enumerate(sonuc["adimlar"], 1):
        print(f"  {i:>2}. {adim[:160]}")
    print(f"\nKAYNAKLAR  {', '.join(sonuc['kaynaklar']) or '-'}")
    print(f"KARAR      {sonuc['kategori']} / {sonuc['davranis']}"
          f"   araçlar: {', '.join(sonuc['kullanilan_araclar']) or '-'}")
    print(f"\nMÜŞTERİYE GİDEN YANIT\n  {sonuc['yanit'].replace(chr(10), chr(10) + '  ')}\n{CIZGI}")


def insan_onayi_iste(sonuc: dict) -> dict:
    """Temsilci rolündeki kullanıcıya sorar: evet, hayır ya da düzelt. Hayır ve düzeltme gerekçesi
    eval/geri_bildirim.csv'ye kaydedilir (test seti adayı olur)."""
    print("\nİNSAN ONAYI GEREKLİ (yukarıdaki yanıt henüz müşteriye gitmedi)")
    cevap = input("Onaylıyor musunuz? [e]vet / [h]ayır / [d]üzelt: ").strip().lower()[:1]
    if cevap == "e":
        return onayla(sonuc["oturum_id"], True, onaylayan="Demo Temsilcisi")
    if cevap == "d":
        duzeltilmis = input("Düzeltilmiş yanıt: ").strip()
        gerekce = input("Düzeltme gerekçesi: ").strip()
        return onayla(sonuc["oturum_id"], True, onaylayan="Demo Temsilcisi", gerekce=gerekce,
                      duzeltilmis_yanit=duzeltilmis)
    gerekce = input("Ret gerekçesi: ").strip()
    return onayla(sonuc["oturum_id"], False, onaylayan="Demo Temsilcisi", gerekce=gerekce)


def main() -> int:
    parser = argparse.ArgumentParser(description="Asistanı terminalde dene")
    parser.add_argument("--model", default="yerel", choices=["yerel", "bulut", "guclu"])
    args = parser.parse_args()

    print(f"Örnek Bank müşteri asistanı (model: {args.model}). Çıkmak için talep yerine q yazın.")
    while True:
        try:
            talep = input(f"\nTalep [{ORNEK_TALEP}]: ").strip() or ORNEK_TALEP
            if talep.lower() == "q":
                return 0
            musteri_no = input(f"Müşteri no [{ORNEK_MUSTERI}]: ").strip().upper() or ORNEK_MUSTERI

            sonuc = cevapla(talep, musteri_no, model_turu=args.model)
            goster(sonuc)
            if sonuc["onay_bekliyor"]:
                sonuc = insan_onayi_iste(sonuc)
                goster(sonuc)
            elif sonuc["davranis"] == "netlestir":  # aynı oturumda müşteri cevap verir
                ek = input("\nMüşterinin cevabı (boş = geç): ").strip()
                if ek:
                    goster(cevapla(ek, musteri_no, model_turu=args.model, oturum_id=sonuc["oturum_id"]))
        except (EOFError, KeyboardInterrupt):
            print()
            return 0


if __name__ == "__main__":
    sys.exit(main())
