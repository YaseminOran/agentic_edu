"""Asistanın log ayarı (Hafta 2). Tüm modüller `from asistan.gunluk import log` ile kullanır.
Loglar logs/asistan.log dosyasına yazılır (git'e girmez); uyarılar ayrıca konsolda (stderr) görünür.
MaskelemeFiltresi her log satırını yazılmadan önce maskeler: kod bir yerde maskelemeyi unutsa bile
loglara TCKN, kart no, IBAN veya telefon düşmez (kural: loglara sadece maskelenmiş veri).
"""

import logging

from asistan.ayarlar import PROJE_KOKU
from asistan.maskeleme import maskele

LOG_DOSYASI = PROJE_KOKU / "logs" / "asistan.log"


class MaskelemeFiltresi(logging.Filter):
    """Log kaydının mesajını (argümanlar yerleştirilmiş hâliyle) maskeler."""

    def filter(self, kayit: logging.LogRecord) -> bool:
        kayit.msg = maskele(kayit.getMessage())
        kayit.args = None
        return True


def _kur() -> logging.Logger:
    logger = logging.getLogger("asistan")
    if logger.handlers:  # notebook'ta modül tekrar yüklenirse handler'lar çoğalmasın
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addFilter(MaskelemeFiltresi())

    LOG_DOSYASI.parent.mkdir(exist_ok=True)
    dosya = logging.FileHandler(LOG_DOSYASI, encoding="utf-8")
    dosya.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    logger.addHandler(dosya)

    konsol = logging.StreamHandler()  # stderr; MCP sunucusunda stdout protokole ayrılmıştır
    konsol.setLevel(logging.WARNING)
    konsol.setFormatter(logging.Formatter("  [log] %(levelname)s %(message)s"))
    logger.addHandler(konsol)
    return logger


log = _kur()
