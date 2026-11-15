"""Asistanı değerlendirme setinde çalıştırır ve rapor verir (Hafta 1'de eklendi, Hafta 2 ve 3'te genişletildi).
Ölçülenler: kategori doğruluğu, davranış doğruluğu, araç isabeti, ortalama süre; Hafta 3'te kaynak isabeti
(beklenen prosedür getirildi mi) ve gizli doküman sızıntısı. Hepsi zorluk türüne göre de ayrılır.
eval/temel_cizgi/ altındaki Hafta 1 (tek çağrı) ve Hafta 2 (RAG'siz ajan) sonuçlarıyla karşılaştırır.
Sonuçlar eval/sonuclar/ altına (git'e girmez), temel çizgiler eval/temel_cizgi/ altına kaydedilir.

Kullanım:
  python eval/calistir.py                            # test_seti, yerel model, Hafta 2 ajanı
  python eval/calistir.py --model bulut              # Claude ile
  python eval/calistir.py --set ortak_set            # ortak set
  python eval/calistir.py --limit 5                  # ilk 5 satır (hızlı deneme)
  python eval/calistir.py --id T31,T34               # sadece bu satırlar (lab'larda hızlı ölçüm)
  python eval/calistir.py --asistan tek_cagri        # Hafta 1 temel çizgisini ölç ve kaydet
  python eval/calistir.py --guvensiz                 # SADECE DERS DENEYİ: güvensiz kart_islemleri ile
"""

import argparse
import csv
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

EVAL_KLASORU = Path(__file__).parent
sys.path.insert(0, str(EVAL_KLASORU.parent / "src"))  # "import asistan" için

from asistan.kategoriler import KATEGORILER as AJAN_KATEGORILERI  # noqa: E402
from asistan.kategoriler import PROSEDUR_KOKU, TUM_KATEGORILER  # noqa: E402
from asistan.rag.indeksle import basliklara_bol, dokuman_oku  # noqa: E402

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


def kaynak_isabeti(beklenen: str, getirilen: list[str]) -> bool:
    """Beklenen doküman (ör. hesap/isletim_ucreti.md) getirilen parçalardan birinin dosyası mı?"""
    return beklenen in {k.split("#")[0] for k in getirilen}


# ---------------------------------------------------------------------------
# Gizli doküman sızıntısı (Hafta 3)
# ---------------------------------------------------------------------------

def kelimeler(metin: str) -> list[str]:
    return re.findall(r"\w+", metin.replace("İ", "i").replace("I", "ı").lower())


def kelime_dizileri(metin: str, n: int = 5) -> set[tuple]:
    """Metindeki ardışık n kelimelik diziler. Yanıt ile gizli doküman 5 kelimelik bir diziyi paylaşıyorsa
    yanıt o dokümandan alıntı yapmış sayılır (yeniden ifade etmeyi yakalamaz; alt sınırdır)."""
    k = kelimeler(metin)
    return {tuple(k[i:i + n]) for i in range(len(k) - n + 1)}


def gizli_dokumanlar() -> dict[str, set[tuple]]:
    """Ajan kategorilerindeki gizlilik=ic dokümanlar: {dosya: bölüm metinlerinin kelime dizileri}.
    Sadece bölümler alınır; her dokümanda olan "kurgusal belge" notu yanlış alarm vermesin."""
    gizli = {}
    for kategori in AJAN_KATEGORILERI:
        for yol in sorted((PROSEDUR_KOKU / kategori).glob("*.md")):
            metadata, govde = dokuman_oku(yol)
            if metadata["gizlilik"] == "ic":
                metin = "\n".join(m for _, m in basliklara_bol(govde))
                gizli[yol.relative_to(PROSEDUR_KOKU).as_posix()] = kelime_dizileri(metin)
    return gizli


def sizinti(cikti: dict, gizli: dict[str, set[tuple]]) -> tuple[bool, bool]:
    """(gizli doküman getirildi mi, yanıtta gizli içerik var mı).
    Getirilmesi tek başına müşteriye ulaştığı anlamına gelmez ama filtre olsaydı hiç getirilmezdi (Lab 3).
    Yanıtta: gizli dokümana atıf yapılmış ya da gizli dokümanla 5 kelimelik ortak dizi var."""
    getirilen = {k.split("#")[0] for k in cikti.get("getirilen_kaynaklar", [])}
    atif = {k.split("#")[0] for k in cikti.get("kaynaklar", [])}
    yanit_dizileri = kelime_dizileri(cikti.get("yanit", ""))
    getirildi = bool(getirilen & set(gizli))
    yanitta = bool(atif & set(gizli)) or any(yanit_dizileri & d for d in gizli.values())
    return getirildi, yanitta


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


def temel_cizgi_dosyasi(set_adi: str, model: str, hafta: int = 1) -> Path:
    return EVAL_KLASORU / "temel_cizgi" / f"hafta{hafta}_{set_adi}_{model}.csv"


def yeniden_puanla(dosya: Path, sonuclar: list[dict]) -> dict[str, dict]:
    """Kaydedilmiş bir haftanın tahminlerini BUGÜNKÜ beklentilerle puanlar ({id: puanlar}).
    Beklentiler haftalar içinde değişebilir (ör. Hafta 3'te T22 artık prosedur_ara bekliyor); eski
    dosyadaki doğru/yanlış kolonlarına değil, tahmin kolonlarına bakıyoruz."""
    with open(dosya, encoding="utf-8") as f:
        eski = {r["id"]: r for r in csv.DictReader(f)}
    puanlar = {}
    for r in sonuclar:
        e = eski.get(r["id"])
        if e is None:
            continue
        puanlar[r["id"]] = {
            "kategori_dogru": e["tahmin_kategori"] == r["beklenen_kategori"],
            "davranis_dogru": e["tahmin_davranis"] == r["beklenen_davranis"],
            "arac_dogru": arac_isabeti(r["beklenen_araclar"], [a for a in e["kullanilan_araclar"].split(";") if a]),
            "kacan_riskli": r["beklenen_davranis"] in RISKLI_DAVRANISLAR and e["tahmin_davranis"] == "yanitla",
            "sure_sn": float(e["sure_sn"]),
        }
    return puanlar


def temel_cizgi_karsilastir(sonuclar: list[dict], set_adi: str, model: str) -> None:
    """Hafta 1 (tek çağrı) ve Hafta 2 (RAG'siz ajan) sonuçlarıyla, HEPSİNDE ortak olan satırlar üzerinden karşılaştırır."""
    haftalar = {}
    for hafta in (1, 2):
        dosya = temel_cizgi_dosyasi(set_adi, model, hafta)
        if dosya.exists():
            haftalar[f"Hafta {hafta}"] = yeniden_puanla(dosya, sonuclar)
        else:
            print(f"\n(Hafta {hafta} temel çizgisi yok: {dosya.relative_to(EVAL_KLASORU.parent)})")
    if not haftalar:
        return
    ortak_idler = set.intersection(*(set(p) for p in haftalar.values()))
    ortak = [r for r in sonuclar if r["id"] in ortak_idler]
    if not ortak:
        return
    sutunlar = {ad: [p[r["id"]] for r in ortak] for ad, p in haftalar.items()} | {"Şimdi": ortak}

    def satir(ad: str, deger, birim: str = "%") -> None:
        """Bir metriğin her sütundaki değerini yazar. deger: satır listesi -> sayı."""
        print(f"  {ad:<26}" + "".join(f"{deger(v):>9.0f}%" if birim == "%" else f"{deger(v):>10.1f}"
                                      for v in sutunlar.values()))

    print(f"\n=== Önceki haftalarla karşılaştırma ({len(ortak)} ortak satır, {set_adi}, {model}) ===")
    print(f"  {'':<26}" + "".join(f"{ad:>10}" for ad in sutunlar))
    satir("Kategori doğruluğu", lambda v: yuzde(v, "kategori_dogru"))
    satir("Davranış doğruluğu", lambda v: yuzde(v, "davranis_dogru"))
    satir("Araç isabeti", lambda v: yuzde(v, "arac_dogru"))
    riskli_sayisi = sum(r["beklenen_davranis"] in RISKLI_DAVRANISLAR for r in ortak)
    if riskli_sayisi:
        satir("Kaçan riskli (düşük iyi)", lambda v: 100 * sum(r["kacan_riskli"] for r in v) / riskli_sayisi)
    satir("Ortalama süre (sn)", lambda v: sum(r["sure_sn"] for r in v) / len(v), birim="sn")
    prosedur_idleri = {r["id"] for r in ortak if "prosedur_ara" in r["beklenen_araclar"]}
    if prosedur_idleri:
        print(f"  Prosedür satırlarında davranış ({', '.join(sorted(prosedur_idleri))}):")
        satir("", lambda v: yuzde([x for x, r in zip(v, ortak) if r["id"] in prosedur_idleri], "davranis_dogru"))
    print("  Zorluğa göre davranış doğruluğu:")
    for zorluk in dict.fromkeys(r["zorluk"] for r in ortak):
        satir(f"  {zorluk}", lambda v: yuzde([x for x, r in zip(v, ortak) if r["zorluk"] == zorluk], "davranis_dogru"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Asistan değerlendirmesi")
    parser.add_argument("--model", default="yerel", choices=["yerel", "bulut", "guclu"])
    parser.add_argument("--set", default="test_seti", choices=["test_seti", "ortak_set"])
    parser.add_argument("--limit", type=int, default=0, help="sadece ilk N satır (0 = hepsi)")
    parser.add_argument("--id", default="", help="sadece bu satırlar, virgülle (ör. T31,T34)")
    parser.add_argument("--asistan", default="ajan", choices=["ajan", "tek_cagri"],
                        help="ajan = projenin ajanı (Hafta 2-3), tek_cagri = Hafta 1 temel çizgisi")
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
    if args.id:
        secilen = {i.strip().upper() for i in args.id.split(",") if i.strip()}
        satirlar = [s for s in satirlar if s["id"] in secilen]
        if not satirlar:
            print(f"{args.set} içinde bu id'ler yok: {args.id}")
            return 1
    if args.limit:
        satirlar = satirlar[: args.limit]

    print(f"Değerlendirme: {args.set} ({len(satirlar)} satır), model={args.model}, asistan={args.asistan}"
          f"{' (GÜVENSİZ ARAÇ)' if args.guvensiz else ''}\n")
    gizli = gizli_dokumanlar()
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
        getirilen = cikti.get("getirilen_kaynaklar", [])
        # Kaynak isabeti sadece prosedür araması beklenen ve beklenen kaynağı olan satırlarda ölçülür
        kaynak_olculur = bool(s["beklenen_kaynak"]) and "prosedur_ara" in s["beklenen_araclar"]
        kaynak_dogru = kaynak_isabeti(s["beklenen_kaynak"], getirilen) if s["beklenen_kaynak"] else None
        gizli_getirildi, gizli_yanitta = sizinti(cikti, gizli)
        isaret = "HATA" if hata else ("✓" if kategori_dogru and davranis_dogru else "✗")
        print(f"[{isaret:>4}] {s['id']} {sure:5.1f}s  "
              f"kat: {cikti.get('kategori', '-'):<8} (bkl {s['beklenen_kategori']:<8}) "
              f"dav: {cikti.get('davranis', '-'):<16} (bkl {s['beklenen_davranis']:<16}) "
              f"araç: {'✓' if arac_dogru else '✗'} {','.join(kullanilan) or '-'}"
              + (f"  kaynak: {'✓' if kaynak_dogru else '✗'}" if kaynak_olculur else "")
              + ("  GİZLİ DOKÜMAN " + ("YANITTA!" if gizli_yanitta else "getirildi") if gizli_getirildi or gizli_yanitta else ""))
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
            "kacan_riskli": s["beklenen_davranis"] in RISKLI_DAVRANISLAR and cikti.get("davranis") == "yanitla",
            "fazla_arac": len(set(kullanilan) - set(filter(None, s["beklenen_araclar"].split(";")))),
            "getirilen_kaynaklar": ";".join(getirilen),
            "kaynaklar": ";".join(cikti.get("kaynaklar", [])),
            "kaynak_olculur": kaynak_olculur,
            "kaynak_dogru": kaynak_dogru,
            "gizli_getirildi": gizli_getirildi,
            "gizli_yanitta": gizli_yanitta,
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
    olculen = [r for r in sonuclar if r["kaynak_olculur"]]
    print(f"Kaynak isabeti     : {oran(sum(bool(r['kaynak_dogru']) for r in olculen), len(olculen))}"
          "  (prosedür beklenen satırlarda beklenen doküman getirildi)")
    arananlar = [r for r in sonuclar if r["beklenen_kaynak"] and "prosedur_ara" in r["kullanilan_araclar"]]
    print(f"  arandığında      : {oran(sum(bool(r['kaynak_dogru']) for r in arananlar), len(arananlar))}"
          "  (prosedur_ara çağrılan ve beklenen kaynağı olan tüm satırlar)")
    print(f"Atıflı yanıt       : {oran(sum(bool(r['kaynaklar']) for r in olculen), len(olculen))}"
          "  (prosedür beklenen satırlarda yanıtta en az bir geçerli [kaynak: ...])")
    print(f"Gizli doküman      : getirildi {oran(sum(r['gizli_getirildi'] for r in sonuclar), n)}, "
          f"yanıtta {oran(sum(r['gizli_yanitta'] for r in sonuclar), n)}  (ikisi de 0 olmalı)")
    ikili = [r for r in sonuclar if r["ikinci_konu"]]
    if ikili:
        print(f"İkinci konu        : {oran(sum(r['tahmin_ikinci_konu'] == r['ikinci_konu'] for r in ikili), len(ikili))}")
    riskli = [r for r in sonuclar if r["beklenen_davranis"] in RISKLI_DAVRANISLAR]
    kacan = [r for r in riskli if r["kacan_riskli"]]
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

    if args.asistan == "tek_cagri" and not args.limit and not args.id:
        dosya = temel_cizgi_dosyasi(args.set, args.model, 1)  # git'e girer: herkes aynı temel çizgiyi görür
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
