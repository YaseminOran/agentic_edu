"""Müşteri talep asistanı paketi (Hafta 1'de eklendi, Hafta 2'de ajan akışına bağlandı).
Dışarıya açılan arayüz: cevapla(talep, musteri_no) -> dict ve insan onayı için onayla(oturum_id, ...).
"""

# Not: ajan.py burada en üstte import edilmez, fonksiyonların içinde import edilir.
# En üstte import edilseydi, `python -m asistan.ajan` komutu ajan.py'yi iki kez yükler ve
# Python "RuntimeWarning: 'asistan.ajan' found in sys.modules" uyarısı verirdi.


def cevapla(*args, **kwargs) -> dict:
    """Talebi ajan akışından geçirir. Parametreler ve ayrıntılar: asistan/ajan.py içindeki cevapla()."""
    from asistan.ajan import cevapla as ajan_cevapla
    return ajan_cevapla(*args, **kwargs)


def onayla(*args, **kwargs) -> dict:
    """İnsan onayı bekleyen oturumu devam ettirir. Ayrıntılar: asistan/ajan.py içindeki onayla()."""
    from asistan.ajan import onayla as ajan_onayla
    return ajan_onayla(*args, **kwargs)


__all__ = ["cevapla", "onayla"]
