"""Asistanı değerlendirme setinde çalıştırır ve rapor verir (Hafta 1'de eklendi, Hafta 2'de genişletildi).
Ölçülenler: kategori doğruluğu, davranış doğruluğu, araç isabeti, ortalama süre; hepsi zorluk türüne
göre de ayrılır. Hafta 1'in tek çağrılık asistanı (temel çizgi) ölçülmüşse onunla karşılaştırır.
Sonuçlar eval/sonuclar/ altına (git'e girmez), temel çizgi eval/temel_cizgi/ altına kaydedilir.

Kullanım:
  python eval/calistir.py                            # test_seti, yerel model, Hafta 2 ajanı
  python eval/calistir.py --model bulut              # Claude ile
  python eval/calistir.py --set ortak_set            # ortak set
  python eval/calistir.py --limit 5                  # ilk 5 satır (hızlı deneme)
  python eval/calistir.py --asistan tek_cagri        # Hafta 1 temel çizgisini ölç ve kaydet
  python eval/calistir.py --guvensiz                 # SADECE DERS DENEYİ: güvensiz kart_islemleri ile
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

from asistan.kategoriler import TUM_KATEGORILER  # noqa: E402

KATEGORILER = set(TUM_KATEGORILER)
DAVRANISLAR = ["yanitla", "netlestir", "temsilciye_aktar", "insan_onayi", "reddet", "kapsam_disi"]
# Beklenen bu davranışlardan biriyken asistan "yanitla" derse, risk insana gitmeden kapanmış olur
RISKLI_DAVRANISLAR = {"temsilciye_aktar", "insan_onayi", "reddet"}
ARAYUZ_ALANLARI = {"kategori", "ikinci_konu", "davranis", "yanit", "kullanilan_araclar", "kaynaklar", "adimlar"}


def arayuz_hatasi(cikti) -> str:
    """cevapla() çıktısı ortak arayüze uyuyor mu? Uyuyorsa boş metin döner."""
    if not isinstance(cikti, dict):
        return "dict değil"
    eksik = ARAYUZ_ALANLARI - set(cikti)
    if eksik:
        return f"eksik alan: {sorted(eksik)}"
    if cikti["kategori"] not in KATEGORILER:
        return f"geçersiz kategori: {cikti['kategori']}"
    if cikti["davranis"] not in DAVRANISLAR:
        return f"geçersiz davranış: {cikti['davranis']}"
    for alan in ("kullanilan_araclar", "kaynaklar", "adimlar"):
        if not isinstance(cikti[alan], list):
            return f"{alan} liste değil"
    return ""


def arac_isabeti(beklenen: str, kullanilan: list[str]) -> bool:
    """Beklenen araçların HEPSİ çağrıldı mı? Hiç araç beklenmiyorsa hiç çağrılmamış olmalı.
    Fazladan okuma aracı çağırmak hata sayılmaz (ayrıca "fazla çağrı" olarak raporlanır)."""
    beklenenler = {a for a in beklenen.split(";") if a}
    if not beklenenler:
        return not kullanilan
    return beklenenler <= set(kullanilan)


def oran(pay: int, payda: int) -> str:
    return f"{pay}/{payda} (%{100 * pay / payda:.0f})" if payda else "-"


def yuzde(satirlar: list[dict], alan: str) -> float | None:
    return 100 * sum(r[alan] for r in satirlar) / len(satirlar) if satirlar else None


def karisiklik_matrisi_yaz(sonuclar: list[dict]) -> None:
    """Satır: beklenen davranış, sütun: tahmin. Köşegen dışı her sayı bir karışıklıktır."""
    kisa = {"yanitla": "yanit", "netlestir": "netl", "temsilciye_aktar": "temsl",
            "insan_onayi": "onay", "reddet": "red", "kapsam_disi": "kpsm"}
    print("\nKarışıklık matrisi (satır = beklenen, sütun = tahmin):")
    print(" " * 18 + "".join(f"{kisa[d]:>7}" for d in DAVRANISLAR))
    for beklenen in DAVRANISLAR:
        satir = [sum(1 for r in sonuclar if r["beklenen_davranis"] == beklenen and r["tahmin_davranis"] == t)
                 for t in DAVRANISLAR]
        print(f"  {beklenen:<16}" + "".join(f"{(n or '.'):>7}" for n in satir))


def temel_cizgi_dosyasi(set_adi: str, model: str) -> Path:
    return EVAL_KLASORU / "temel_cizgi" / f"hafta1_{set_adi}_{model}.csv"


def temel_cizgi_karsilastir(sonuclar: list[dict], set_adi: str, model: str) -> None:
    """Aynı set ve modelle ölçülmüş Hafta 1 sonuçlarıyla, AYNI satırlar üzerinden karşılaştırır."""
    dosya = temel_cizgi_dosyasi(set_adi, model)
    if not dosya.exists():
        print(f"\n(Hafta 1 temel çizgisi yok. Ölçmek için: python eval/calistir.py --asistan tek_cagri "
              f"--set {set_adi} --model {model})")
        return
    with open(dosya, encoding="utf-8") as f:
        temel = {r["id"]: r for r in csv.DictReader(f)}
    ortak = [r for r in sonuclar if r["id"] in temel]
    if not ortak:
        return
    temel_satirlar = [{k: (temel[r["id"]][k] == "True") for k in ("kategori_dogru", "davranis_dogru", "arac_dogru")}
                      | {"sure_sn": float(temel[r["id"]]["sure_sn"]), "zorluk": r["zorluk"]} for r in ortak]

    print(f"\n=== Hafta 1 temel çizgisiyle karşılaştırma ({len(ortak)} ortak satır, {dosya.name}) ===")
    print(f"  {'':<22}{'Hafta 1':>10}{'Hafta 2':>10}{'fark':>8}")
    for ad, alan in [("Kategori doğruluğu", "kategori_dogru"), ("Davranış doğruluğu", "davranis_dogru"),
                     ("Araç isabeti", "arac_dogru")]:
        h1, h2 = yuzde(temel_satirlar, alan), yuzde(ortak, alan)
        print(f"  {ad:<22}{h1:>9.0f}%{h2:>9.0f}%{h2 - h1:>+7.0f}")
    h1 = sum(r["sure_sn"] for r in temel_satirlar) / len(ortak)
    h2 = sum(r["sure_sn"] for r in ortak) / len(ortak)
    print(f"  {'Ortalama süre (sn)':<22}{h1:>10.1f}{h2:>10.1f}{h2 - h1:>+8.1f}")
    print("  Zorluğa göre davranış doğruluğu:")
    for zorluk in dict.fromkeys(r["zorluk"] for r in ortak):
        a = yuzde([r for r in temel_satirlar if r["zorluk"] == zorluk], "davranis_dogru")
        b = yuzde([r for r in ortak if r["zorluk"] == zorluk], "davranis_dogru")
        print(f"    {zorluk:<20}{a:>9.0f}%{b:>9.0f}%{b - a:>+7.0f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Asistan değerlendirmesi")
    parser.add_argument("--model", default="yerel", choices=["yerel", "bulut", "guclu"])
    parser.add_argument("--set", default="test_seti", choices=["test_seti", "ortak_set"])
    parser.add_argument("--limit", type=int, default=0, help="sadece ilk N satır (0 = hepsi)")
    parser.add_argument("--asistan", default="ajan", choices=["ajan", "tek_cagri"],
                        help="ajan = Hafta 2 akışı, tek_cagri = Hafta 1 temel çizgisi")
    parser.add_argument("--guvensiz", action="store_true", help="SADECE DERS DENEYİ: güvensiz kart_islemleri")
    args = parser.parse_args()

    if args.asistan == "tek_cagri":
        from asistan.tek_cagri import cevapla

        def calistir(s):
            return cevapla(s["talep"], s["musteri_no"], model_turu=args.model)
    else:
        from asistan import cevapla

        def calistir(s):
            return cevapla(s["talep"], s["musteri_no"], model_turu=args.model, guvensiz=args.guvensiz)

    with open(EVAL_KLASORU / f"{args.set}.csv", encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))
    if args.limit:
        satirlar = satirlar[: args.limit]

    print(f"Değerlendirme: {args.set} ({len(satirlar)} satır), model={args.model}, asistan={args.asistan}"
          f"{' (GÜVENSİZ ARAÇ)' if args.guvensiz else ''}\n")
    sonuclar = []
    for s in satirlar:
        baslangic = time.time()
        try:
            cikti = calistir(s)
            hata = arayuz_hatasi(cikti)
        except Exception as e:  # tek satırdaki hata tüm değerlendirmeyi durdurmasın
            cikti, hata = {}, f"{type(e).__name__}: {e}"
        sure = time.time() - baslangic

        kullanilan = cikti.get("kullanilan_araclar", [])
        kategori_dogru = cikti.get("kategori") == s["beklenen_kategori"]
        davranis_dogru = cikti.get("davranis") == s["beklenen_davranis"]
        arac_dogru = arac_isabeti(s["beklenen_araclar"], kullanilan)
        isaret = "HATA" if hata else ("✓" if kategori_dogru and davranis_dogru else "✗")
        print(f"[{isaret:>4}] {s['id']} {sure:5.1f}s  "
              f"kat: {cikti.get('kategori', '-'):<8} (bkl {s['beklenen_kategori']:<8}) "
              f"dav: {cikti.get('davranis', '-'):<16} (bkl {s['beklenen_davranis']:<16}) "
              f"araç: {'✓' if arac_dogru else '✗'} {','.join(kullanilan) or '-'}")
        if hata:
            print(f"        {hata[:200]}")

        sonuclar.append({
            **s,
            "tahmin_kategori": cikti.get("kategori", ""),
            "tahmin_ikinci_konu": cikti.get("ikinci_konu", ""),
            "tahmin_davranis": cikti.get("davranis", ""),
            "kullanilan_araclar": ";".join(kullanilan),
            "kategori_dogru": kategori_dogru,
            "davranis_dogru": davranis_dogru,
            "arac_dogru": arac_dogru,
            "fazla_arac": len(set(kullanilan) - set(filter(None, s["beklenen_araclar"].split(";")))),
            "sure_sn": round(sure, 2),
            "hata": hata,
            "yanit": cikti.get("yanit", ""),
            "adimlar": " | ".join(cikti.get("adimlar", [])),
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
    print(f"Araç isabeti       : {oran(sum(r['arac_dogru'] for r in sonuclar), n)}"
          "  (beklenen araçların hepsi çağrıldı; araç beklenmiyorsa hiç çağrılmadı)")
    print(f"Fazla araç çağrısı : ortalama {sum(r['fazla_arac'] for r in sonuclar) / n:.1f} araç/satır")
    ikili = [r for r in sonuclar if r["ikinci_konu"]]
    if ikili:
        print(f"İkinci konu        : {oran(sum(r['tahmin_ikinci_konu'] == r['ikinci_konu'] for r in ikili), len(ikili))}")
    riskli = [r for r in sonuclar if r["beklenen_davranis"] in RISKLI_DAVRANISLAR]
    kacan = [r for r in riskli if r["tahmin_davranis"] == "yanitla"]
    print(f"Kaçan riskli talep : {oran(len(kacan), len(riskli))}"
          "  (insana gitmesi gerekirken 'yanitla' denenler — düşük olmalı)")
    print(f"Hatalı satır       : {len(hatalilar)}")
    print(f"Ortalama süre      : {sum(r['sure_sn'] for r in sonuclar) / n:.1f} sn")

    print("\nZorluğa göre:")
    print(f"  {'':<14}{'kategori':>14}{'davranış':>14}{'araç':>14}{'süre':>8}")
    gruplar = defaultdict(list)
    for r in sonuclar:
        gruplar[r["zorluk"]].append(r)
    for zorluk, grup in gruplar.items():
        k = len(grup)
        print(f"  {zorluk:<14}"
              f"{oran(sum(r['kategori_dogru'] for r in grup), k):>14}"
              f"{oran(sum(r['davranis_dogru'] for r in grup), k):>14}"
              f"{oran(sum(r['arac_dogru'] for r in grup), k):>14}"
              f"{sum(r['sure_sn'] for r in grup) / k:>7.1f}s")

    karisiklik_matrisi_yaz(sonuclar)

    if args.asistan == "ajan" and not args.guvensiz:
        temel_cizgi_karsilastir(sonuclar, args.set, args.model)

    if args.asistan == "tek_cagri" and not args.limit:
        dosya = temel_cizgi_dosyasi(args.set, args.model)  # git'e girer: herkes aynı temel çizgiyi görür
    else:
        etiket = "guvensiz" if args.guvensiz else args.asistan
        dosya = EVAL_KLASORU / "sonuclar" / f"{args.set}_{args.model}_{etiket}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    dosya.parent.mkdir(exist_ok=True)
    with open(dosya, "w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=list(sonuclar[0].keys()))
        yazici.writeheader()
        yazici.writerows(sonuclar)
    print(f"\nAyrıntılı sonuçlar: {dosya.relative_to(EVAL_KLASORU.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
