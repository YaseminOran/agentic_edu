"""İnsan onayındaki temsilci geri bildirimini kaydeder (Hafta 4, adım 6).
Temsilci taslağı reddederse ya da düzelterek onaylarsa gerekçesi eval/geri_bildirim.csv'ye bir satır olarak eklenir.
Bu satırlar eval/aday_uret.py ile test seti adayına dönüşür: sahadaki hata, bir sonraki ölçümün sorusu olur.
"""

import csv
from datetime import datetime

from asistan.ayarlar import PROJE_KOKU
from asistan.gunluk import log
from asistan.maskeleme import maskele

GERI_BILDIRIM_DOSYASI = PROJE_KOKU / "eval" / "geri_bildirim.csv"
ALANLAR = ["zaman", "oturum_id", "musteri_no", "talep", "asistan_yaniti", "karar", "gerekce",
           "duzeltilmis_yanit", "onaylayan"]


def geri_bildirim_kaydet(**satir) -> None:
    """Bir geri bildirim satırı ekler. Temsilcinin yazdığı metinler de maskelenir (kişisel veri dosyaya girmesin).
    Yazma hatası akışı durdurmaz; sadece loglanır."""
    satir = {alan: maskele(str(satir.get(alan, ""))) for alan in ALANLAR}
    satir["zaman"] = datetime.now().isoformat(timespec="seconds")
    try:
        yeni = not GERI_BILDIRIM_DOSYASI.exists()
        with open(GERI_BILDIRIM_DOSYASI, "a", newline="", encoding="utf-8") as f:
            yazici = csv.DictWriter(f, fieldnames=ALANLAR)
            if yeni:
                yazici.writeheader()
            yazici.writerow(satir)
    except OSError as e:
        log.warning("geri bildirim yazılamadı: %s", e)
