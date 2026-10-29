"""Sentetik banka verisini üretir: musteriler, kart_islemleri, gecmis_talepler, talepler (Hafta 1).
Tüm değerler AÇIKÇA SAHTEDİR: TCKN 99999 ile başlar ve sağlama tutmaz, kartlar 9999 BIN'li ve
Luhn'u geçmez, IBAN'lar TR00 (geçersiz kontrol hanesi), e-postalar .test alan adındadır.

Çalıştırma: python data/uret.py   (sabit seed; her çalıştırmada aynı dosyalar üretilir)
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
REFERANS_TARIH = date(2026, 10, 1)  # "bugün" kabul edilen sabit tarih; tekrar üretilebilirlik için
MUSTERI_SAYISI = 30
KLASOR = Path(__file__).parent

ADLAR = ["Ayşe", "Mehmet", "Zeynep", "Mustafa", "Elif", "Ahmet", "Fatma", "Emre", "Selin", "Burak",
         "Deniz", "Can", "Ece", "Murat", "Gizem", "Kerem", "Derya", "Hakan", "Merve", "Onur"]
# Soyadlar bilerek "sahte" olduğu belli seçildi
SOYADLAR = ["Örnek", "Deneme", "Sahteoğlu", "Testçi", "Kurmaca", "Hayalî", "Taslak", "Prova"]
SEGMENTLER = ["bireysel", "bireysel", "bireysel", "premium", "kobi"]
KREDILER = ["yok", "yok", "ihtiyac", "konut", "tasit"]

ISYERLERI = [
    ("ORNEK MARKET A.S.", 150, 2500),
    ("DENEME AKARYAKIT", 500, 3000),
    ("SAHTE ELEKTRONIK", 1500, 45000),
    ("TEST ONLINE ALISVERIS", 100, 8000),
    ("KURMACA RESTORAN", 250, 4000),
    ("ORNEK ULASIM KART", 50, 500),
    ("PROVA ECZANE", 80, 1200),
    ("DENEME GIYIM", 400, 6000),
]
SUPHELI_ISYERLERI = ["FAKE STORE LTD (USD)", "TEST GAMING ONLINE (EUR)", "SAHTE KRIPTO BORSA"]


def tckn_gecerli_mi(tckn: str) -> bool:
    """Gerçek TCKN sağlama kuralını uygular. Biz bunun False dönmesini İSTİYORUZ."""
    d = [int(c) for c in tckn]
    if d[0] == 0:
        return False
    hane10 = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    hane11 = sum(d[:10]) % 10
    return d[9] == hane10 and d[10] == hane11


def sahte_tckn(sira: int) -> str:
    """99999 ile başlayan ve sağlaması bilerek tutmayan 11 haneli numara."""
    tckn = f"99999{sira:06d}"
    if tckn_gecerli_mi(tckn):  # şans eseri tutarsa son haneyi boz
        tckn = tckn[:-1] + str((int(tckn[-1]) + 1) % 10)
    return tckn


def luhn_gecerli_mi(numara: str) -> bool:
    """Kart numarası Luhn kontrolü. Biz bunun False dönmesini İSTİYORUZ."""
    toplam = 0
    for i, c in enumerate(reversed(numara)):
        n = int(c)
        if i % 2 == 1:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        toplam += n
    return toplam % 10 == 0


def sahte_kart_no(sira: int) -> str:
    """9999 ile başlayan (hiçbir kart ağına ait olmayan) ve Luhn'u geçmeyen kart numarası."""
    numara = f"99990000{sira:08d}"
    if luhn_gecerli_mi(numara):
        numara = numara[:-1] + str((int(numara[-1]) + 1) % 10)
    return " ".join(numara[i:i + 4] for i in range(0, 16, 4))


def sahte_iban(sira: int) -> str:
    """TR00 ile başlayan IBAN; 00 kontrol hanesi gerçekte hiçbir zaman geçerli değildir."""
    ham = f"TR00999990{sira:016d}"
    return " ".join(ham[i:i + 4] for i in range(0, len(ham), 4))


def ascii_yap(metin: str) -> str:
    """E-posta adresleri için Türkçe karakterleri sadeleştirir."""
    return metin.lower().translate(str.maketrans("çğıöşüâî", "cgiosuai"))


def musterileri_uret(rng: random.Random) -> list[dict]:
    musteriler = []
    for i in range(1, MUSTERI_SAYISI + 1):
        ad, soyad = rng.choice(ADLAR), rng.choice(SOYADLAR)
        musteriler.append({
            "musteri_no": f"M{1000 + i}",
            "ad_soyad": f"{ad} {soyad}",
            "tckn": sahte_tckn(i),
            "telefon": f"0500 000 {i:04d}",
            "eposta": f"{ascii_yap(ad)}.{ascii_yap(soyad)}{i}@ornek.test",
            "segment": rng.choice(SEGMENTLER),
            "musteri_olma_tarihi": (REFERANS_TARIH - timedelta(days=rng.randint(200, 6000))).isoformat(),
            "kart_no": sahte_kart_no(i),
            "kart_limiti": rng.choice([10000, 25000, 50000, 75000, 150000]),
            "kart_durumu": "aktif" if i % 13 else "bloke",
            "iban": sahte_iban(i),
            "aktif_kredi": rng.choice(KREDILER),
        })
    return musteriler


def kart_islemlerini_uret(rng: random.Random, musteriler: list[dict]) -> list[dict]:
    islemler = []
    sayac = 1

    def ekle(m, gun_once, isyeri, tutar, durum="onaylandi"):
        nonlocal sayac
        islemler.append({
            "islem_id": f"I{sayac:05d}",
            "musteri_no": m["musteri_no"],
            "tarih": (REFERANS_TARIH - timedelta(days=gun_once)).isoformat(),
            "isyeri": isyeri,
            "tutar": f"{tutar:.2f}",
            "para_birimi": "TRY",
            "durum": durum,
        })
        sayac += 1

    for sira, m in enumerate(musteriler, start=1):
        for _ in range(rng.randint(5, 12)):
            isyeri, alt, ust = rng.choice(ISYERLERI)
            durum = rng.choices(["onaylandi", "beklemede", "iade"], weights=[85, 10, 5])[0]
            ekle(m, rng.randint(0, 60), isyeri, rng.uniform(alt, ust), durum)

        # Senaryolar için bilinçli eklenen işlemler
        if sira % 7 == 0:  # mükerrer çekim
            tutar = rng.uniform(300, 2000)
            gun = rng.randint(2, 10)
            ekle(m, gun, "ORNEK MARKET A.S.", tutar)
            ekle(m, gun, "ORNEK MARKET A.S.", tutar)
        if sira % 9 == 0:  # şüpheli yurt dışı işlemler
            for _ in range(3):
                ekle(m, rng.randint(0, 2), rng.choice(SUPHELI_ISYERLERI), rng.uniform(1000, 9000))
        if sira % 11 == 0:  # itiraz edilmiş işlem
            ekle(m, rng.randint(15, 40), "SAHTE ELEKTRONIK", rng.uniform(5000, 20000), "itiraz_edildi")

    islemler.sort(key=lambda x: (x["musteri_no"], x["tarih"]))
    return islemler


GECMIS_SABLONLAR = [
    ("kart", "Kart aidatı iadesi talebi", "Aidat iadesi prosedüre göre yapıldı.", "cozuldu"),
    ("kart", "Mükerrer market harcaması", "İtiraz kaydı açıldı, tutar iade edildi.", "cozuldu"),
    ("kart", "Limit artırma talebi", "Gelir belgesi istendi, müşteri dönüş yapmadı.", "acik"),
    ("kredi", "Erken kapama tutarı sorgusu", "Erken kapama tutarı ve ücreti bildirildi.", "cozuldu"),
    ("kredi", "Taksit erteleme talebi", "Yapılandırma için temsilciye aktarıldı.", "temsilcide"),
    ("hesap", "Hesap işletim ücreti şikayeti", "Ücret iadesi reddedildi, gerekçe bildirildi.", "cozuldu"),
    ("hesap", "FAST transferi karşıya geçmedi", "Alıcı banka kaynaklı gecikme; 2 saatte ulaştı.", "cozuldu"),
    ("dijital_kanal", "Mobil uygulama giriş hatası", "Cihaz eşleştirmesi sıfırlandı.", "cozuldu"),
    ("dijital_kanal", "Şifre sıfırlama SMS'i gelmiyor", "Telefon numarası güncellemesi için şubeye yönlendirildi.", "cozuldu"),
    ("guvenlik", "Şüpheli SMS bildirimi", "Oltalama uyarısı yapıldı, kart bloke edildi.", "cozuldu"),
    ("guvenlik", "Tanınmayan yurt dışı işlem", "Kart bloke edildi, itiraz süreci başlatıldı.", "temsilcide"),
]


def gecmis_talepleri_uret(rng: random.Random, musteriler: list[dict]) -> list[dict]:
    talepler = []
    sayac = 1
    for m in musteriler:
        for _ in range(rng.randint(0, 3)):
            kategori, ozet, cozum, durum = rng.choice(GECMIS_SABLONLAR)
            talepler.append({
                "talep_id": f"G{sayac:04d}",
                "musteri_no": m["musteri_no"],
                "tarih": (REFERANS_TARIH - timedelta(days=rng.randint(10, 400))).isoformat(),
                "kategori": kategori,
                "ozet": ozet,
                "cozum": cozum,
                "durum": durum,
            })
            sayac += 1
    talepler.sort(key=lambda x: (x["musteri_no"], x["tarih"]))
    return talepler


# Gelen talep şablonları. {ad}, {kart_no}, {tckn}, {iban}, {tutar} müşteri verisiyle doldurulur.
# Bazı şablonlar bilerek hassas veri içerir: Hafta 2'de maskeleme bunlar üzerinde denenir.
TALEP_SABLONLARI = [
    "Merhaba, kredi kartı ekstremin kesim tarihini nereden görebilirim?",
    "Kartımdan {tutar} TL iki kez çekilmiş, birini iade etmenizi istiyorum.",
    "Kartımı kaybettim, numarası {kart_no}. Lütfen hemen kapatın!",
    "Konut kredimi erken kapatmak istiyorum, ne kadar ücret çıkar?",
    "Mobil uygulamaya giremiyorum, şifremi unuttum.",
    "FAST ile para gönderdim ama karşı tarafa ulaşmamış, ne oldu?",
    "Hesabımdan hesap işletim ücreti kesilmiş, bunu kabul etmiyorum, iadesini istiyorum.",
    "Ben {ad}, TCKN {tckn}. IBAN'ım {iban}, maaşım yatmamış görünüyor, kontrol eder misiniz?",
    "Ekstremde tanımadığım yurt dışı harcamalar var, ben yapmadım!",
    "İnternet şubesinde sürekli oturum zaman aşımı hatası alıyorum.",
    "Kredi kartı limitimi artırmak istiyorum.",
    "Taksitlerimi ödeyemiyorum, işimi kaybettim. Ne yapabilirim?",
    "Bankanızdan aradılar, telefonuma gelen kodu istediler, verdim. Sorun olur mu?",
    "Kartım çalışmıyor.",
    "Üç haftadır aynı şikayeti yapıyorum, kimse dönmüyor. Bir yetkiliyle görüşmek istiyorum.",
    "EFT'yi yanlış IBAN'a gönderdim, {tutar} TL. Geri alabilir miyim?",
    "Hesabımı kapatmak istiyorum.",
    "Uygulama her açılışta çöküyor, güncelledim yine olmadı.",
    "Şubeleriniz cumartesi açık mı?",
    "Merhaba ben {ad}, kart numaram {kart_no}, son ödeme tarihim hafta sonuna denk geldi, faiz işler mi?",
]
KANALLAR = ["mobil", "web", "cagri_merkezi", "eposta", "sube"]


def talepleri_uret(rng: random.Random, musteriler: list[dict]) -> list[dict]:
    talepler = []
    for i in range(1, 41):
        m = rng.choice(musteriler)
        sablon = TALEP_SABLONLARI[(i - 1) % len(TALEP_SABLONLARI)]
        metin = sablon.format(
            ad=m["ad_soyad"], kart_no=m["kart_no"], tckn=m["tckn"], iban=m["iban"],
            tutar=f"{rng.uniform(150, 5000):.2f}".replace(".", ","),
        )
        talepler.append({
            "talep_id": f"T{i:04d}",
            "musteri_no": m["musteri_no"],
            "kanal": rng.choice(KANALLAR),
            "tarih": (REFERANS_TARIH - timedelta(days=rng.randint(0, 3))).isoformat(),
            "talep": metin,
        })
    return talepler


def csv_yaz(ad: str, satirlar: list[dict]) -> None:
    yol = KLASOR / ad
    with open(yol, "w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
        yazici.writeheader()
        yazici.writerows(satirlar)
    print(f"  {ad}: {len(satirlar)} satır")


def main() -> None:
    rng = random.Random(SEED)
    musteriler = musterileri_uret(rng)

    # Güvenlik ağı: hiçbir değer gerçek bir kimlik/kart formatını geçmemeli
    for m in musteriler:
        assert not tckn_gecerli_mi(m["tckn"]), m["tckn"]
        assert not luhn_gecerli_mi(m["kart_no"].replace(" ", "")), m["kart_no"]

    print("Sentetik veri üretiliyor:")
    csv_yaz("musteriler.csv", musteriler)
    csv_yaz("kart_islemleri.csv", kart_islemlerini_uret(rng, musteriler))
    csv_yaz("gecmis_talepler.csv", gecmis_talepleri_uret(rng, musteriler))
    csv_yaz("talepler.csv", talepleri_uret(rng, musteriler))


if __name__ == "__main__":
    main()
