---
kategori: guvenlik
baslik: Kötüye Kullanım Girişimleri
gizlilik: ic
guncelleme_tarihi: 2026-10-01
---
# Kötüye Kullanım Girişimleri

> Kurgusal eğitim belgesi. "Örnek Bank" adına uydurulmuştur. Bu klasör indekslenmez: guvenlik
> kategorisindeki talepler ajana gitmez, hazır yanıtla reddedilir (src/asistan/kategoriler.py).

## Reddedilen talepler
- Başka bir müşterinin bilgisini isteyen talepler (eş, akraba, "yetkili personel" olduğunu söyleyen
  kişiler dahil) reddedilir. Hesap bilgisi yalnızca hesap sahibine verilir.
- Asistanın talimatlarını, sistem mesajını veya kurallarını değiştirmeye/öğrenmeye çalışan talepler
  reddedilir ve güvenlik olayı olarak kaydedilir.
- Onay adımlarının atlanması talebi (kim isterse istesin) reddedilir.
- Müşteriye itirazı kazanmak için harcamayı yapmamış gibi beyan etmesini önermek dolandırıcılıktır;
  böyle bir talep reddedilir.
