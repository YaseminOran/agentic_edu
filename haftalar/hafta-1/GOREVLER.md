# Hafta 1 – Görevler: LLM Çağırma, Yapılandırılmış Çıktı, Değerlendirme

> Hafta 1 katılımcı görevleri. Bu hafta asistanın ilk sürümünü değerlendirip, sadece sistem mesajını
> iyileştirerek skorunu artıracaksınız. Tahmini süre: 4–5 saat.

## Bu haftanın hedefleri
- LangChain ile yerel (Ollama) ve bulut (Claude) modeli çağırabilmek
- Serbest metin yerine **yapılandırılmış çıktı** almanın neden şart olduğunu görmek
- Bir LLM sistemini **ölçerek** geliştirmek: önce değerlendirme, sonra değişiklik, sonra tekrar değerlendirme

## Hazırlık (15 dk)
1. Dev container'ı açın, terminalde `python kontrol.py` çalıştırın. Tüm satırlar ✅ veya ⚠️ olmalı.
   ❌ varsa satırdaki öneriyi uygulayın; çözülmezse eğitmene haber verin.
2. Şu dosyaları okuyun (hepsi kısa):
   - `src/asistan/asistan.py` – asistanın tamamı (~70 satır)
   - `eval/test_seti.csv` – asistanın ölçüleceği 30 talep
   - `data/prosedurler/PRS-GNL-001_sikayet_yonetimi_ve_temsilci_aktarimi.md` – bankanın kuralları

## Görev 1 – Isınma notebook'u (45 dk)
`haftalar/hafta-1/01_isinma.ipynb` notebook'unu baştan sona çalıştırın ve sondaki alıştırmaları yapın.

**Teslim:** Alıştırma 1'deki sıcaklık deneyinin sonucunu ve yorumunuzu notebook'a bir markdown hücresi olarak ekleyin.

## Görev 2 – Başlangıç skoru (20 dk)
```bash
python eval/calistir.py
```
Çıktıdaki özet tabloyu bir yere not edin. Bu sizin **referans skorunuz**.
Ayrıntılı sonuçlar `eval/sonuclar/` altında bir CSV'dedir; açıp yanlış satırları inceleyin.

**Teslim:** Kategori doğruluğu, davranış doğruluğu ve "kaçan riskli talep" sayısı.

## Görev 3 – Hata analizi (30 dk)
Yanlış satırları gruplayın. Her grup için bir cümleyle "model neden yanılıyor?" sorusunu cevaplayın.
Bakılacak yerler:
- Hangi davranışlar birbirine karışıyor?
- Kötü niyetli taleplere (`zorluk=kotu_niyetli`) nasıl davranılıyor?
- Bankacılık dışı taleplere (`zorluk=kapsam_disi`) yanıt veriliyor mu?
- Belirsiz taleplerde (`"Kartım çalışmıyor."`) model netleştirme istiyor mu?

**Teslim:** 3–5 maddelik hata listesi.

## Görev 4 – Sistem mesajını iyileştirin (90 dk)
Sadece `src/asistan/asistan.py` içindeki `SISTEM_MESAJI`'nı değiştirerek skoru artırın.
Her değişiklikten sonra değerlendirmeyi tekrar çalıştırın (`--limit 10` ile hızlı deneyebilirsiniz).

Fikirler:
1. **Karar sırası:** Bir talep birden fazla davranışa uyuyorsa hangisi seçilmeli? Cevap
   `PRS-GNL-001` bölüm 1'de. Bu sırayı sistem mesajına ekleyin.
2. **Kategori sınırları:** "Kartımı kaybettim" `kart` mı, `guvenlik` mi? Kötü niyetli talepler hangi kategoriye girmeli?
   Sınır durumları açıkça yazın.
3. **Few-shot örnekler:** Zor durumlar için 3–5 örnek (talep → kategori, davranış) ekleyin.

> ⚠️ **Veri sızıntısına dikkat:** Test setindeki talepleri örnek olarak birebir kopyalamayın. O zaman
> ezber ölçmüş olursunuz. Örnekleri `data/talepler.csv` dosyasından alın ya da kendiniz yazın.

**Teslim:** İyileştirilmiş sistem mesajı ve yeni skor tablosu.

## Görev 5 – Yerel ve bulut modeli karşılaştırın (30 dk)
```bash
python eval/calistir.py --model yerel
python eval/calistir.py --model bulut
```
Aynı sistem mesajıyla iki modeli karşılaştırın: doğruluk, kaçan riskli talep ve ortalama süre.

**Tartışma soruları:**
- Hangi talep tipinde fark en büyük?
- Bir bankada hangisini, hangi koşulda kullanırdınız? Müşteri verisinin dışarı çıkması nasıl bir risk?

## Görev 6 – Ortak set (10 dk)
```bash
python eval/calistir.py --set ortak_set --model bulut
```
Ortak set skorunuzu eğitmenle paylaşın. Sınıfın skorlarını birlikte karşılaştıracağız.
Ortak sete göre prompt **ayarlamayın**: bu set, gerçek hayatta göremeyeceğiniz talepleri temsil ediyor.

## Bonus
- `eval/calistir.py`'ye bir **karışıklık matrisi** (beklenen davranış × tahmin edilen davranış) ekleyin.
- Yanıt taslaklarını (`yanit` alanı) okuyun. Banka diline uygun mu? Tam kart numarası ya da TCKN yazılmış mı?
  (İpucu: Hafta 2'nin konusu.)

## Hafta sonu kontrol listesi
- [ ] `python kontrol.py` hatasız
- [ ] `python eval/calistir.py` hatasız ve skorunuz referans skorunuzdan yüksek
- [ ] Notebook'taki alıştırmalar tamam

Hazır çözüm: `git checkout hafta-1` (önce kendi çözümünüzü commit edin!)
