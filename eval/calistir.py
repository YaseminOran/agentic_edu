"""Asistanı değerlendirme setinde çalıştırır ve doğruluk raporu verir (Hafta 1).
Her satır için cevapla() çağrılır; kategori/davranış beklenenle karşılaştırılır.
Sonuçlar eval/sonuclar/ altına CSV olarak kaydedilir (git'e girmez).

Kullanım:
  python eval/calistir.py                       # test_seti, yerel model
  python eval/calistir.py --model bulut         # Claude ile
  python eval/calistir.py --set ortak_set       # ortak set
  python eval/calistir.py --limit 5             # ilk 5 satır (hızlı deneme)
"""

import argparse
import csv
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

EVAL_KLASORU = Path(__file__).parent
sys.path.insert(0, str(EVAL_KLASORU.parent / "src"))  # "import asistan" için

from asistan import cevapla  # noqa: E402

KATEGORILER = {"kart", "kredi", "hesap", "dijital_kanal", "guvenlik", "diger"}
DAVRANISLAR = {"yanitla", "netlestir", "temsilciye_aktar", "insan_onayi", "reddet"}
# Beklenen bu davranışlardan biriyken asistan "yanitla" derse, risk insana gitmeden kapanmış olur
RISKLI_DAVRANISLAR = {"temsilciye_aktar", "insan_onayi", "reddet"}


def arayuz_hatasi(cikti) -> str:
    """cevapla() çıktısı ortak arayüze uyuyor mu? Uyuyorsa boş metin döner."""
    if not isinstance(cikti, dict):
        return "dict değil"
    eksik = {"kategori", "davranis", "yanit", "kaynaklar", "adimlar"} - set(cikti)
    if eksik:
        return f"eksik alan: {sorted(eksik)}"
    if cikti["kategori"] not in KATEGORILER:
        return f"geçersiz kategori: {cikti['kategori']}"
    if cikti["davranis"] not in DAVRANISLAR:
        return f"geçersiz davranış: {cikti['davranis']}"
    if not isinstance(cikti["kaynaklar"], list) or not isinstance(cikti["adimlar"], list):
        return "kaynaklar/adimlar liste değil"
    return ""


def karisiklik_matrisi_yaz(sonuclar: list[dict]) -> None:
    """Satır: beklenen davranış, sütun: tahmin. Köşegen dışı her sayı bir karışıklıktır (Hafta 1 bonus)."""
    davranislar = ["yanitla", "netlestir", "temsilciye_aktar", "insan_onayi", "reddet"]
    kisa = {"yanitla": "yanit", "netlestir": "netl", "temsilciye_aktar": "temsl", "insan_onayi": "onay", "reddet": "red"}
    print("\nKarışıklık matrisi (satır = beklenen, sütun = tahmin):")
    print(" " * 18 + "".join(f"{kisa[d]:>7}" for d in davranislar))
    for beklenen in davranislar:
        satir = [sum(1 for r in sonuclar if r["beklenen_davranis"] == beklenen and r["tahmin_davranis"] == t)
                 for t in davranislar]
        print(f"  {beklenen:<16}" + "".join(f"{(n or '.'):>7}" for n in satir))


def oran(pay: int, payda: int) -> str:
    return f"{pay}/{payda} (%{100 * pay / payda:.0f})" if payda else "-"


def main() -> int:
    parser = argparse.ArgumentParser(description="Asistan değerlendirmesi")
    parser.add_argument("--model", default="yerel", choices=["yerel", "bulut", "guclu"])
    parser.add_argument("--set", default="test_seti", choices=["test_seti", "ortak_set"])
    parser.add_argument("--limit", type=int, default=0, help="sadece ilk N satır (0 = hepsi)")
    args = parser.parse_args()

    with open(EVAL_KLASORU / f"{args.set}.csv", encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))
    if args.limit:
        satirlar = satirlar[: args.limit]

    print(f"Değerlendirme: {args.set} ({len(satirlar)} satır), model={args.model}\n")
    sonuclar = []
    for s in satirlar:
        baslangic = time.time()
        try:
            # Test setinde müşteri no yok; tüm satırlar aynı sentetik müşteriyle çalışır
            cikti = cevapla(s["talep"], musteri_no="M1001", model_turu=args.model)
            hata = arayuz_hatasi(cikti)
        except Exception as e:  # tek satırdaki hata tüm değerlendirmeyi durdurmasın
            cikti, hata = {}, f"{type(e).__name__}: {e}"
        sure = time.time() - baslangic

        kategori_dogru = cikti.get("kategori") == s["beklenen_kategori"]
        davranis_dogru = cikti.get("davranis") == s["beklenen_davranis"]
        isaret = "HATA" if hata else ("✓" if kategori_dogru and davranis_dogru else "✗")
        print(f"[{isaret:>4}] {s['id']} {sure:4.1f}s  "
              f"kategori: {cikti.get('kategori', '-'):<13} (beklenen {s['beklenen_kategori']:<13}) "
              f"davranış: {cikti.get('davranis', '-'):<16} (beklenen {s['beklenen_davranis']})")
        if hata:
            print(f"        {hata[:200]}")

        sonuclar.append({
            **s,
            "tahmin_kategori": cikti.get("kategori", ""),
            "tahmin_davranis": cikti.get("davranis", ""),
            "kategori_dogru": kategori_dogru,
            "davranis_dogru": davranis_dogru,
            "kaynak_var": bool(cikti.get("kaynaklar")),
            "sure_sn": round(sure, 2),
            "hata": hata,
            "yanit": cikti.get("yanit", ""),
        })

    # --- Rapor ---
    n = len(sonuclar)
    hatalilar = [r for r in sonuclar if r["hata"]]
    if len(hatalilar) == n:
        print("\nTüm satırlar hata verdi. Önce `python kontrol.py` çalıştırıp ortamı kontrol edin.")
        return 1

    print("\n=== Özet ===")
    print(f"Kategori doğruluğu : {oran(sum(r['kategori_dogru'] for r in sonuclar), n)}")
    print(f"Davranış doğruluğu : {oran(sum(r['davranis_dogru'] for r in sonuclar), n)}")
    print(f"İkisi birden       : {oran(sum(r['kategori_dogru'] and r['davranis_dogru'] for r in sonuclar), n)}")
    kaynakli = [r for r in sonuclar if r["kaynak_gerekli"] == "evet"]
    print(f"Kaynak gösterme    : {oran(sum(r['kaynak_var'] for r in kaynakli), len(kaynakli))}"
          "  (Hafta 3'e kadar 0 olması normal)")
    riskli = [r for r in sonuclar if r["beklenen_davranis"] in RISKLI_DAVRANISLAR]
    kacan = [r for r in riskli if r["tahmin_davranis"] == "yanitla"]
    print(f"Kaçan riskli talep : {oran(len(kacan), len(riskli))}"
          "  (insana gitmesi gerekirken 'yanitla' denenler — düşük olmalı)")
    print(f"Hatalı satır       : {len(hatalilar)}")
    print(f"Ortalama süre      : {sum(r['sure_sn'] for r in sonuclar) / n:.1f} sn")

    print("\nZorluğa göre davranış doğruluğu:")
    gruplar = defaultdict(list)
    for r in sonuclar:
        gruplar[r["zorluk"]].append(r)
    for zorluk, grup in gruplar.items():
        print(f"  {zorluk:<13} {oran(sum(r['davranis_dogru'] for r in grup), len(grup))}")

    karisiklik_matrisi_yaz(sonuclar)

    klasor = EVAL_KLASORU / "sonuclar"
    klasor.mkdir(exist_ok=True)
    dosya = klasor / f"{args.set}_{args.model}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with open(dosya, "w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=list(sonuclar[0].keys()))
        yazici.writeheader()
        yazici.writerows(sonuclar)
    print(f"\nAyrıntılı sonuçlar: {dosya.relative_to(EVAL_KLASORU.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
