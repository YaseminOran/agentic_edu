"""Müşteri talep asistanı paketi (Hafta 1'de eklendi, Hafta 2'de ajan akışına bağlandı).
Dışarıya açılan arayüz: cevapla(talep, musteri_no) -> dict ve insan onayı için onayla(oturum_id, ...).
"""

from asistan.ajan import cevapla, onayla

__all__ = ["cevapla", "onayla"]
