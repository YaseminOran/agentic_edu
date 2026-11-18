"""İki şablon sürümünü aynı test setinde karşılaştırır (Hafta 4, adım 6). Lab 2'de taslak v1 ile v2 ölçülür.
Yerel modelde aynı satır iki koşuda farklı sonuç verebilir (±%5-10); --tekrar ile birkaç kez çalıştırıp
ortalamayı ve aralığı (en düşük–en yüksek) raporlarız. Fark aralıkların içinde kalıyorsa "fark yok" deriz.

Kullanım:
  python eval/ab_testi.py                                   # taslak v1 vs v2, test_seti, yerel, 1 tekrar
  python eval/ab_testi.py --a v1 --b v2 --tekrar 3          # 3 tekrar: ortalama ve aralık
  python eval/ab_testi.py --id T01,T12,T13,T33 --model bulut  # sadece bu satırlar (ders içi hızlı ölçüm)
"""

import argparse
import csv
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

EVAL_KLASORU = Path(__file__).parent
sys.path.insert(0, str(EVAL_KLASORU))  # calistir.py'deki ölçüm fonksiyonları için

from calistir import adim_maliyeti, degerlendir, metrikler, satirlari_sec  # noqa: E402


def surumu_calistir(sablon: str, surum: str, satirlar: list[dict], model: str, tekrar: int) -> list[dict]:
    """Bir sürümü `tekrar` kez çalıştırır. Her koşu: {"metrik": {...}, "satirlar": {id: sonuç}, "token": ort.}"""
    from asistan import cevapla

    os.environ[f"SABLON_{sablon.upper()}"] = surum  # sablonlar.py her çağrıda .env/ortamdan okur
    kosular = []
    for i in range(1, tekrar + 1):
        print(f"  {sablon}={surum}  koşu {i}/{tekrar} ({len(satirlar)} satır)...", flush=True)
        sonuclar, izler = degerlendir(satirlar, lambda s: cevapla(s["talep"], s["musteri_no"], model_turu=model),
                                      sessiz=True)
        maliyet = adim_maliyeti(izler)
        token = sum(sum(o.get("girdi_token") or 0 for o in iz["olaylar"] if o["tur"] == "model") for iz in izler)
        metrik = metrikler(sonuclar)
        metrik["Token / talep"] = token / len(izler) if izler else None
        metrik[f"{sablon} süresi (sn)"] = maliyet.get(sablon, {}).get("sure_ms", 0) / 1000 or None
        kosular.append({"metrik": metrik, "satirlar": {r["id"]: r for r in sonuclar}})
    return kosular


def ozetle(degerler: list[float | None]) -> str:
    """Ortalama [en düşük–en yüksek]; tek koşuysa sadece değer."""
    degerler = [d for d in degerler if d is not None]
    if not degerler:
        return "-"
    ort = sum(degerler) / len(degerler)
    bicim = ".1f" if ort < 100 and ort != int(ort) else ".0f"
    if len(degerler) == 1:
        return f"{ort:{bicim}}"
    return f"{ort:{bicim}} [{min(degerler):{bicim}}–{max(degerler):{bicim}}]"


def cogunluk(kosular: list[dict], satir_id: str) -> tuple[bool, str]:
    """Bir satırın tekrarlar boyunca çoğunluk sonucu: (davranış doğru mu, en sık davranış)."""
    sonuclar = [k["satirlar"][satir_id] for k in kosular]
    dogru = sum(r["davranis_dogru"] for r in sonuclar) > len(sonuclar) / 2
    return dogru, Counter(r["tahmin_davranis"] for r in sonuclar).most_common(1)[0][0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Şablon sürümlerini A/B testiyle karşılaştır")
    parser.add_argument("--sablon", default="taslak", help="hangi şablon (taslak, siniflandirma, ajan, self_check)")
    parser.add_argument("--a", default="v1", help="A sürümü (ör. v1)")
    parser.add_argument("--b", default="v2", help="B sürümü (ör. v2)")
    parser.add_argument("--model", default="yerel", choices=["yerel", "bulut", "guclu"])
    parser.add_argument("--set", default="test_seti", choices=["test_seti", "ortak_set"])
    parser.add_argument("--id", default="", help="sadece bu satırlar, virgülle")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--tekrar", type=int, default=1, help="her sürüm kaç kez çalışsın (yerel modelde 3 önerilir)")
    args = parser.parse_args()

    satirlar = satirlari_sec(args.set, args.id, args.limit)
    print(f"A/B testi: {args.sablon} {args.a} vs {args.b} | {args.set}, {len(satirlar)} satır, "
          f"model={args.model}, {args.tekrar} tekrar\n")
    a = surumu_calistir(args.sablon, args.a, satirlar, args.model, args.tekrar)
    b = surumu_calistir(args.sablon, args.b, satirlar, args.model, args.tekrar)

    print(f"\n=== Metrikler ({'ortalama [aralık]' if args.tekrar > 1 else 'tek koşu'}) ===")
    print(f"  {'':<28}{args.a:>20}{args.b:>20}{'fark':>8}")
    for ad in a[0]["metrik"]:
        ka = [k["metrik"][ad] for k in a]
        kb = [k["metrik"][ad] for k in b]
        fark = ""
        if all(x is not None for x in ka + kb):
            fark = f"{sum(kb) / len(kb) - sum(ka) / len(ka):+.0f}" if "süre" not in ad else \
                   f"{sum(kb) / len(kb) - sum(ka) / len(ka):+.1f}"
        print(f"  {ad:<28}{ozetle(ka):>20}{ozetle(kb):>20}{fark:>8}")

    print("\n=== Değişen satırlar (davranış doğruluğu, tekrarların çoğunluğuna göre) ===")
    degisen = 0
    for s in satirlar:
        (dogru_a, dav_a), (dogru_b, dav_b) = cogunluk(a, s["id"]), cogunluk(b, s["id"])
        if dogru_a != dogru_b:
            degisen += 1
            yon = "iyileşti" if dogru_b else "kötüleşti"
            print(f"  {s['id']}  {args.a}: {'✓' if dogru_a else '✗'} {dav_a:<16} -> {args.b}: "
                  f"{'✓' if dogru_b else '✗'} {dav_b:<16} ({yon}; beklenen {s['beklenen_davranis']})")
    print(f"  {degisen} satır değişti" if degisen else "  Davranış doğruluğu hiçbir satırda değişmedi.")

    dosya = EVAL_KLASORU / "sonuclar" / (f"ab_{args.sablon}_{args.a}_{args.b}_{args.set}_{args.model}_"
                                         f"{datetime.now():%Y%m%d_%H%M%S}.csv")
    dosya.parent.mkdir(exist_ok=True)
    with open(dosya, "w", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)
        yazici.writerow(["id", "surum", "kosu", "talep", "not", "beklenen_davranis", "tahmin_davranis",
                         "davranis_dogru", "icerik_gecti", "kaynaklar", "yanit"])
        for surum, kosular in ((args.a, a), (args.b, b)):
            for i, k in enumerate(kosular, 1):
                for r in k["satirlar"].values():
                    yazici.writerow([r["id"], surum, i, r["talep"], r["not"], r["beklenen_davranis"],
                                     r["tahmin_davranis"], r["davranis_dogru"], r["icerik_gecti"], r["kaynaklar"],
                                     r["yanit"]])
    print(f"\nAyrıntılı sonuçlar: {dosya.relative_to(EVAL_KLASORU.parent)}")
    print("Yanıtların kalitesini (dil, empati) puanlamak için: python eval/hakem.py --ab " + dosya.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
