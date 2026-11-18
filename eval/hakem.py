"""LLM-as-judge: güçlü model (CLAUDE_MODEL_GUCLU) müşteri yanıtlarını 1-5 arası puanlar (Hafta 4, adım 6).
Ölçütler: doğruluk (kaynağa ve eğitmen notuna göre), eksiksizlik, banka dili, empati. Her puanın gerekçesi var.
Hakem de bir modeldir ve yanılabilir: --sinama, hakemi eğitmenin elle verdiği puanlarla karşılaştırır.

Kullanım:
  python eval/hakem.py eval/sonuclar/test_seti_bulut_ajan_....csv     # bir değerlendirme koşusunun yanıtları
  python eval/hakem.py --ab ab_taslak_v1_v2_....csv                    # A/B testinin iki sürümü (1. koşu)
  python eval/hakem.py --sinama                                        # hakemi sına (eval/hakem_sinama.csv, 10 satır)
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

EVAL_KLASORU = Path(__file__).parent
sys.path.insert(0, str(EVAL_KLASORU.parent / "src"))  # "import asistan" için

from asistan.ayarlar import model_getir  # noqa: E402
from asistan.rag.indeksle import PARCA_DOSYASI  # noqa: E402
from asistan.sablonlar import mesajlar  # noqa: E402

OLCUTLER = ["dogruluk", "eksiksizlik", "banka_dili", "empati"]
# Hazır cümle dönen davranışlar puanlanmaz (hepsi aynı metin; maliyet boşa gider)
PUANLANAN = {"yanitla", "insan_onayi", "netlestir"}
SINAMA_DOSYASI = EVAL_KLASORU / "hakem_sinama.csv"


class HakemPuani(BaseModel):
    """Hakemin doldurduğu puan kartı. Önce gerekçe, sonra puan: model önce düşünür."""

    dogruluk_gerekce: str = Field(description="Doğruluk puanının tek cümlelik gerekçesi")
    dogruluk: int = Field(description="1-5: kaynaklarla ve eğitmen notuyla tutarlılık, uydurma yok")
    eksiksizlik_gerekce: str = Field(description="Eksiksizlik puanının tek cümlelik gerekçesi")
    eksiksizlik: int = Field(description="1-5: sorunun tamamı cevaplanmış mı")
    banka_dili_gerekce: str = Field(description="Banka dili puanının tek cümlelik gerekçesi")
    banka_dili: int = Field(description="1-5: siz dili, kısa, jargon yok, kesin vaat yok")
    empati_gerekce: str = Field(description="Empati puanının tek cümlelik gerekçesi")
    empati: int = Field(description="1-5: duruma uygun anlayış, abartısız")


def kaynak_metinleri(kaynaklar: str) -> str:
    """Yanıtın atıf yaptığı parçaların metni (indeksten). Atıf yoksa bunu açıkça söyler."""
    parcalar = {p["kaynak"]: p["metin"] for p in json.loads(PARCA_DOSYASI.read_text(encoding="utf-8"))["parcalar"]}
    secilen = [k for k in kaynaklar.split(";") if k in parcalar]
    return "\n\n".join(f"[{k}]\n{parcalar[k]}" for k in secilen) or "(yanıt hiçbir prosedüre atıf yapmıyor)"


def puanla(satir: dict) -> HakemPuani | None:
    model = model_getir("guclu").with_structured_output(HakemPuani, method="json_schema")
    try:
        puan = model.invoke(mesajlar(
            "hakem", "guclu", talep=satir["talep"], davranis=satir["tahmin_davranis"],
            kaynak_metinleri=kaynak_metinleri(satir.get("kaynaklar", "")),
            egitmen_notu=satir.get("not") or "(not yok)", yanit=satir["yanit"]))
    except Exception as e:
        print(f"  {satir['id']}: hakem çıktısı okunamadı ({type(e).__name__})")
        return None
    for olcut in OLCUTLER:  # model ölçek dışı bir sayı verirse 1-5'e çek
        setattr(puan, olcut, max(1, min(5, getattr(puan, olcut))))
    return puan


def puan_satiri(p: HakemPuani) -> str:
    return "  ".join(f"{o[:5]}:{getattr(p, o)}" for o in OLCUTLER)


def ortalama(puanlar: list[HakemPuani]) -> dict[str, float]:
    return {o: sum(getattr(p, o) for p in puanlar) / len(puanlar) for o in OLCUTLER} if puanlar else {}


def dosyayi_puanla(satirlar: list[dict], baslik: str) -> list[tuple[dict, HakemPuani]]:
    secilen = [s for s in satirlar if s["tahmin_davranis"] in PUANLANAN and s["yanit"]]
    print(f"\n{baslik}: {len(secilen)} yanıt puanlanıyor (hazır cümleler hariç)")
    sonuc = []
    for s in secilen:
        p = puanla(s)
        if p:
            print(f"  {s['id']} {s['tahmin_davranis']:<12} {puan_satiri(p)}")
            sonuc.append((s, p))
    ort = ortalama([p for _, p in sonuc])
    if ort:
        print("  ORTALAMA        " + "  ".join(f"{o[:5]}:{v:.1f}" for o, v in ort.items()))
    return sonuc


def sinama() -> int:
    """Hakemi eğitmenin beklenen puanlarıyla karşılaştırır: tam eşleşme ve ±1 içinde kalma oranı."""
    with open(SINAMA_DOSYASI, encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))
    print(f"Hakem sınaması: {len(satirlar)} satır ({SINAMA_DOSYASI.name})\n")
    print(f"  {'id':<5}" + "".join(f"{o:>16}" for o in OLCUTLER) + "   (hakem / eğitmen)")
    farklar = {o: [] for o in OLCUTLER}
    for s in satirlar:
        p = puanla(s)
        if p is None:
            continue
        hucreler = []
        for o in OLCUTLER:
            beklenen = int(s[f"beklenen_{o}"])
            farklar[o].append(getattr(p, o) - beklenen)
            isaret = "" if abs(getattr(p, o) - beklenen) <= 1 else " !"
            hucreler.append(f"{getattr(p, o)} / {beklenen}{isaret}")
        print(f"  {s['id']:<5}" + "".join(f"{h:>16}" for h in hucreler))
        for o in OLCUTLER:
            if abs(getattr(p, o) - int(s[f"beklenen_{o}"])) > 1:
                print(f"         {o}: hakem -> {getattr(p, f'{o}_gerekce')}")
    print("\n  Ölçüt         tam eşleşme   ±1 içinde   ortalama fark (hakem - eğitmen)")
    for o, f in farklar.items():
        if f:
            print(f"  {o:<14}{100 * sum(x == 0 for x in f) / len(f):>9.0f}%"
                  f"{100 * sum(abs(x) <= 1 for x in f) / len(f):>11.0f}%{sum(f) / len(f):>+14.1f}")
    print("\n  Yorum: ±1 içinde kalma oranı %80'in altındaysa o ölçütte hakeme tek başına güvenmeyin.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM-as-judge ile yanıtları puanla")
    parser.add_argument("dosya", nargs="?", help="eval/sonuclar/ altındaki bir calistir.py sonucu")
    parser.add_argument("--ab", help="ab_testi.py'nin ürettiği dosya (eval/sonuclar/ altında)")
    parser.add_argument("--sinama", action="store_true", help="hakemi eğitmen puanlarıyla karşılaştır")
    parser.add_argument("--limit", type=int, default=0, help="sadece ilk N yanıt")
    args = parser.parse_args()

    if args.sinama:
        return sinama()
    if args.ab:
        yol = Path(args.ab) if Path(args.ab).exists() else EVAL_KLASORU / "sonuclar" / args.ab
        with open(yol, encoding="utf-8") as f:
            satirlar = [s for s in csv.DictReader(f) if s["kosu"] == "1"]
        surumler = list(dict.fromkeys(s["surum"] for s in satirlar))
        sonuclar = {v: ortalama([p for _, p in dosyayi_puanla(
            [s for s in satirlar if s["surum"] == v][: args.limit or None], f"Sürüm {v}")]) for v in surumler}
        print("\n=== Hakem ortalamaları (1-5) ===")
        print(f"  {'':<14}" + "".join(f"{v:>8}" for v in surumler))
        for o in OLCUTLER:
            print(f"  {o:<14}" + "".join(f"{sonuclar[v].get(o, 0):>8.1f}" for v in surumler))
        return 0
    if not args.dosya:
        parser.print_help()
        return 1
    with open(args.dosya, encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))
    dosyayi_puanla(satirlar[: args.limit or None], Path(args.dosya).name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
