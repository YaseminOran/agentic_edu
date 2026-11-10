"""Asistanın log ayarı (Hafta 2). Tüm modüller `from asistan.gunluk import log` ile kullanır.
Loglar logs/asistan.log dosyasına yazılır (git'e girmez); uyarılar ayrıca konsolda (stderr) görünür.
"""

import logging

from asistan.ayarlar import PROJE_KOKU

LOG_DOSYASI = PROJE_KOKU / "logs" / "asistan.log"


def _kur() -> logging.Logger:
    logger = logging.getLogger("asistan")
    if logger.handlers:  # notebook'ta modül tekrar yüklenirse handler'lar çoğalmasın
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    LOG_DOSYASI.parent.mkdir(exist_ok=True)
    dosya = logging.FileHandler(LOG_DOSYASI, encoding="utf-8")
    dosya.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    logger.addHandler(dosya)

    konsol = logging.StreamHandler()  # stderr
    konsol.setLevel(logging.WARNING)
    konsol.setFormatter(logging.Formatter("  [log] %(levelname)s %(message)s"))
    logger.addHandler(konsol)
    return logger


log = _kur()
