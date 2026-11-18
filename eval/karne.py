"""Hafta 1'den bugüne tüm haftaların sonuçlarını tek tabloda toplar ve eval/karne.md'yi yazar (Hafta 4, adım 10).
Kaynak: eval/temel_cizgi/haftaN_<set>_<model>.csv (her haftanın kaydedilmiş tahminleri). Her hafta BUGÜNKÜ
beklentilerle yeniden puanlanır; satır sayısı haftadan haftaya artar (test seti büyüdü), tabloda yazılıdır.

Kullanım:  python eval/karne.py     (yeni bir haftanın temel çizgisi eklenince tekrar çalıştırın)
"""

import csv
import sys
from pathlib import Path

EVAL_KLASORU = Path(__file__).parent
sys.path.insert(0, str(EVAL_KLASORU))

from calistir import gizli_dokumanlar, kaynak_isabeti, kelime_dizileri  # noqa: E402

from asistan.maskeleme import tam_veri_bul  # noqa: E402

KATMANLAR = {
    1: "Tek LLM çağrısı: sınıflandırma ve yanıt taslağı, araç yok",
    2: "Ajan: araçlarla müşteri verisi, insan onayı, hata yönetimi",
    3: "RAG: prosedürlerden kaynaklı yanıt, gizli doküman filtresi, izleme",
    4: "Kalite: prompt şablonları, maskeleme (takma ad), self-check, inceltilmiş risk kontrolü",
}
# Kişisel veri döndüren araçlar (ad, TCKN, kart no, IBAN, telefon). Hafta 2-3'te bunların çıktısı modele
# maskesiz gidiyordu; Hafta 4'te takma adla gidiyor ve izden ölçülüyor.
KISISEL_VERI_ARACLARI = {"musteri_bilgisi", "hesap_durumu"}


def yuzde(satirlar: list, kosul) -> str:
    if not satirlar:
        return "–"
    return f"%{100 * sum(1 for r in satirlar if kosul(r)) / len(satirlar):.0f}"


def modele_maskesiz(r: dict, hafta: int) -> bool:
    """Bu satırda modele maskesiz kişisel veri gitti mi? Hafta 4+ izden ölçülür (modele_maskesiz kolonu).
    Önceki haftalarda maskeleme yoktu: talepte kişisel veri varsa ya da kişisel veri döndüren bir araç
    çağrıldıysa veri modele olduğu gibi gitmiştir."""
    if hafta >= 4:
        return bool(r.get("modele_maskesiz"))
    araclar = set(filter(None, r.get("kullanilan_araclar", "").split(";")))
    return bool(tam_veri_bul(r["talep"])) or bool(araclar & KISISEL_VERI_ARACLARI)


def hafta_satiri(hafta: int, dosya: Path, beklenen: dict[str, dict], gizli: dict) -> list[str]:
    with open(dosya, encoding="utf-8") as f:
        satirlar = [r for r in csv.DictReader(f) if r["id"] in beklenen]
    for r in satirlar:  # bugünkü beklentilerle yeniden puanla
        r.update({k: beklenen[r["id"]][k] for k in ("beklenen_kategori", "beklenen_davranis", "beklenen_kaynak",
                                                     "beklenen_araclar")})
    olculen = [r for r in satirlar if r["beklenen_kaynak"] and "prosedur_ara" in r["beklenen_araclar"]]
    kaynak = (yuzde(olculen, lambda r: kaynak_isabeti(r["beklenen_kaynak"], r["getirilen_kaynaklar"].split(";")))
              if "getirilen_kaynaklar" in (satirlar[0] if satirlar else {}) else "– (RAG yok)")

    def gizli_yanitta(r):
        dizi = kelime_dizileri(r["yanit"])
        atif = {k.split("#")[0] for k in r.get("kaynaklar", "").split(";") if k}
        return bool(atif & set(gizli)) or any(dizi & d for d in gizli.values())

    return [
        f"Hafta {hafta}", KATMANLAR[hafta], str(len(satirlar)),
        yuzde(satirlar, lambda r: r["tahmin_kategori"] == r["beklenen_kategori"]),
        yuzde(satirlar, lambda r: r["tahmin_davranis"] == r["beklenen_davranis"]),
        kaynak,
        yuzde(satirlar, gizli_yanitta),
        yuzde(satirlar, lambda r: modele_maskesiz(r, hafta)) + " / " + yuzde(satirlar, lambda r: tam_veri_bul(r["yanit"])),
        f"{sum(float(r['sure_sn']) for r in satirlar) / len(satirlar):.1f}" if satirlar else "–",
    ]


def tablo(set_adi: str, model: str, gizli: dict) -> list[str]:
    with open(EVAL_KLASORU / f"{set_adi}.csv", encoding="utf-8") as f:
        beklenen = {r["id"]: r for r in csv.DictReader(f)}
    basliklar = ["Hafta", "Eklenen katman", "Satır", "Kategori", "Davranış", "Kaynak isabeti",
                 "Gizli doküman yanıtta", "Kişisel veri (modele / yanıtta)", "Ort. süre (sn)"]
    satirlar = []
    for hafta in KATMANLAR:
        dosya = EVAL_KLASORU / "temel_cizgi" / f"hafta{hafta}_{set_adi}_{model}.csv"
        if dosya.exists():
            satirlar.append(hafta_satiri(hafta, dosya, beklenen, gizli))
        else:
            satirlar.append([f"Hafta {hafta}", KATMANLAR[hafta]] + ["(ölçülmedi)"] + [""] * 6)
    return ([f"### {set_adi}, {model} model", "", "| " + " | ".join(basliklar) + " |",
             "|" + "---|" * len(basliklar)] + ["| " + " | ".join(s) + " |" for s in satirlar] + [""])


def main() -> int:
    gizli = gizli_dokumanlar()
    satirlar = [
        "# Karne: haftadan haftaya asistan",
        "",
        "> `python eval/karne.py` ile üretilir; elle düzenlemeyin. Kaynak: `eval/temel_cizgi/`.",
        "> Her hafta **bugünkü** test beklentileriyle yeniden puanlanır (ör. Hafta 4'te T33 `yanitla` oldu).",
        "> Satır sayısı haftadan haftaya artar: test seti her hafta yeni durumlarla büyüdü.",
        "",
        "**Nasıl okunur:** Kategori, davranış ve kaynak isabeti yüksek; gizli doküman ve kişisel veri düşük olmalı.",
        "Kişisel veri iki sayıdır: *modele* (modele maskelenmemiş kişisel veri giden satır oranı) / "
        "*yanıtta* (müşteriye giden yanıtta tam numara olan satır oranı).",
        "Hafta 1-3'te maskeleme yoktu: kişisel veri döndüren bir araç (musteri_bilgisi, hesap_durumu) çağrıldıysa "
        "ya da talepte numara varsa veri modele olduğu gibi gitmiştir. Hafta 4'ten itibaren bu değer izden ölçülür.",
        "Kaynak isabeti Hafta 1-2'de ölçülemez (prosedür araması yoktu).",
        "",
    ]
    for set_adi in ("test_seti", "ortak_set"):
        for model in ("bulut", "yerel"):
            satirlar += tablo(set_adi, model, gizli)
    (EVAL_KLASORU / "karne.md").write_text("\n".join(satirlar), encoding="utf-8")
    print("\n".join(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
