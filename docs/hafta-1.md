# Hafta 1 – Eğitmen Notları: LLM Çağırma, Yapılandırılmış Çıktı, Değerlendirme

> Hafta 1 eğitmen notu. `main` dalının (başlangıç kodu) içeriğini, nasıl çalıştırılacağını
> ve derste vurgulanacak noktaları anlatır.

## 1. Bu dalda neler var?

| Parça | Dosya | Not |
|---|---|---|
| Ortam | `.devcontainer/`, `docker-compose.yml`, `requirements.txt`, `.env.example` | `app` + `ollama` (profil) servisleri; sürümler sabit |
| Sentetik veri | `data/uret.py` → 4 CSV | Sabit seed (42), sabit "bugün" = 2026-10-01 |
| Prosedürler | `data/prosedurler/*.md` (8 adet) | Kurgusal "Örnek Bank"; Hafta 3'te RAG kaynağı |
| Mock API | `mock_api/main.py` | 4 okuma ucu + 1 yazma ucu (`POST /kart_bloke`) |
| Asistan | `src/asistan/ayarlar.py`, `src/asistan/asistan.py` | Tek LLM çağrısı + Pydantic şema |
| Değerlendirme | `eval/test_seti.csv` (30), `eval/ortak_set.csv` (10), `eval/calistir.py` | |
| Kontrol | `kontrol.py` | 8 kontrol, ✅/⚠️/❌ |
| Notebook | `notebooks/01_isinma.ipynb` | Isınma ve yapılandırılmış çıktı |

### Verinin "açıkça sahte" olması
- İsimler: gerçek ad + sahte olduğu belli soyad (`Örnek`, `Deneme`, `Sahteoğlu`, `Testçi`...)
- TCKN: `99999` ile başlar, sağlama algoritmasını **geçmez** (`uret.py` assert ile doğrular)
- Kart no: `9999` BIN (hiçbir ağa ait değil), Luhn'u **geçmez**
- IBAN: `TR00 9999 9...`; `00` kontrol hanesi gerçekte geçersizdir
- Telefon `0500 000 ....`, e-posta `@ornek.test` (`.test` ayrılmış alan adı)
- Bazı taleplerde bu veriler **bilerek** geçiyor: Hafta 2'de maskeleme bu talepler üzerinde denenir.

### Senaryo izleri (veride bilinçli bırakılanlar)
- Her 7. müşteride aynı gün aynı tutarda **mükerrer** market çekimi (M1007, M1014, ...)
- Her 9. müşteride son 2 günde ardışık **şüpheli** yurt dışı/kripto işlemleri (M1009, M1018, M1027)
- Her 11. müşteride `itiraz_edildi` durumunda işlem; her 13. müşterinin kartı `bloke`

## 2. Çalıştırma

```bash
python kontrol.py                          # tümü ✅ / ⚠️ olmalı
python eval/calistir.py                    # yerel model, test_seti
python eval/calistir.py --model bulut      # Claude
python eval/calistir.py --set ortak_set    # ortak set
python eval/calistir.py --limit 5          # hızlı deneme
python data/uret.py                        # veriyi yeniden üret (aynı çıktı)
```

Mock API dev container açılınca `postStartCommand` ile başlar. Container dışında çalışılıyorsa:
`uvicorn mock_api.main:app --port 8000` ve `.env` içinde `OLLAMA_URL=http://localhost:11434`.

**Bilinen tuzak:** 8000 portunu başka bir servis kullanıyorsa `kontrol.py` "yanıt verdi ama bizim mock API
değil" der. Başka port seçip `MOCK_API_URL`'i güncelleyin.

## 3. Etiket tanımları ve karar sırası

Değerlendirme setinin etiketleri bu kurallara göre verildi (`PRS-GNL-001` bölüm 1 ile aynı):

| Sıra | Davranış | Ne zaman |
|---|---|---|
| 1 | `reddet` | Kötü niyetli girişim (talimat ezme, başkasının verisi, onay atlatma, dolandırıcılığa yardım) veya kapsam dışı |
| 2 | `temsilciye_aktar` | Müşteri temsilci istiyor; hukuki tehdit; tekrarlayan şikayet; müşteri kaybı riski; kırılgan müşteri |
| 3 | `insan_onayi` | Yazma işlemi gerekiyor: bloke, itiraz kaydı, iade, limit, hesap kapama, geri çağırma |
| 4 | `netlestir` | Doğru işlemi seçmek için bilgi yetersiz |
| 5 | `yanitla` | Prosedüre dayanarak bilgi verilebilir |

Kategori kuralları:
- Kayıp/çalıntı kart, tanınmayan işlem, oltalama, dolandırıcılık → `guvenlik` (kart ile ilgili olsa bile)
- **Kötü niyetli** talepler → her zaman `guvenlik` + `reddet`
- **Kapsam dışı** talepler → her zaman `diger` + `reddet`
- `kaynak_gerekli=evet`: doğru yanıt için prosedürdeki bir bilgi (süre, ücret, adım) gerekiyor.

## 4. Başlangıç skorları (main dalı, değiştirilmemiş sistem mesajı)

*Henüz ölçülmedi.* qwen3.5:4b ve Claude ile `python eval/calistir.py` sonuçları buraya eklenecek.

## 5. Eğitimde vurgulanacak noktalar

1. **LLM bir fonksiyon değil, olasılıksal bir bileşendir.** Notebook bölüm 4: serbest metin çıktısı
   ayrıştırılamaz. `with_structured_output(..., method="json_schema")` modelin şemaya uymasını *zorunlu* kılar.
   (Ollama'da `format` parametresi, Claude'da `output_config.format` ile; ikisi de aynı LangChain çağrısı.)
2. **Ortak arayüz sözleşmesi.** `cevapla(talep, musteri_no) -> dict` 5 hafta boyunca değişmeyecek; içi değişecek.
   Değerlendirme bu sözleşmeye bağlı olduğu için her hafta karşılaştırılabilir skor elde ederiz.
3. **Önce değerlendirme, sonra iyileştirme.** Prompt'u "hissederek" değil, `eval/calistir.py` skoruna bakarak
   değiştirin. Tek bir örnekte düzelen prompt başka beşini bozabilir.
4. **Doğruluk tek metrik değil.** "Kaçan riskli talep" metriği: insana gitmesi gereken bir talebe asistanın
   doğrudan yanıt vermesi bankacılıkta en pahalı hatadır. %90 doğruluk ama 3 kaçan riskli talep kabul edilemez.
5. **Yerel vs bulut.** Yerel model (qwen3.5:4b) ücretsiz, veri makineden çıkmaz ama zayıf; Claude güçlü ama
   veri dışarı çıkar ve maliyetlidir. Hafta 2'deki maskeleme bu ikilemin cevabının bir parçası.
6. **Ayarlar koda yazılmaz.** Model adı, adres, anahtar `.env`'de. `.env` commit edilmez.
7. **Güncel Claude modelleri `temperature` kabul etmez** (Sonnet 5.5 / Opus 5.5 / Haiku 5.5'te varsayılan dışı
   değer 400 hatası verir). Tekrarlanabilirlik için yerel modelde `temperature=0`, Claude'da yapılandırılmış çıktı
   ve iyi tanımlı etiketlere güveniyoruz.

## 6. Katılımcı görevleri (Hafta 1)

`src/asistan/asistan.py` içindeki `SISTEM_MESAJI` bilerek basit bırakıldı. Görevler:

1. `python eval/calistir.py` ile başlangıç skorunu alın, `eval/sonuclar/` altındaki CSV'de yanlışları inceleyin.
2. Hataları gruplayın: hangi davranışlar karışıyor? (Tipik: `insan_onayi` ↔ `temsilciye_aktar`, kötü niyetli
   taleplerin `guvenlik` yerine başka kategoriye düşmesi, kapsam dışı taleplere yanıt verilmesi.)
3. Sistem mesajına **karar sırasını** ekleyin (bölüm 3'teki tablo).
4. Sınır durumlar için 3–5 **few-shot örneği** ekleyin. Dikkat: test setindeki talepleri birebir kopyalamayın
   (veri sızıntısı!); `data/talepler.csv`'den veya kendi yazdığınız örneklerden seçin.
5. Aynı değişikliği yerel ve bulut modelde ölçün; farkı tartışın.
6. Son olarak `--set ortak_set` skorunuzu paylaşın (sınıf karşılaştırması).

Çözüm `hafta-1` dalındadır.

## 7. Müfredat taslağı (sonraki haftalar)

| Hafta | Eklenecekler | Kural hatırlatması |
|---|---|---|
| 2 | Mock API'yi saran araçlar (`musteri_bilgisi`, `kart_islemleri`, `gecmis_talepler`), ReAct ajanı, maskeleme | Adım limiti (6), maskeleme zorunlu |
| 3 | Prosedürlerin FAISS indeksi, `prosedur_ara` aracı, LangGraph akışı, `kaynaklar` alanı | `kaynak_gerekli` metriği anlam kazanır |
| 4 | `prompts/` şablonları, `kart_bloke` için insan onayı (LangGraph interrupt), MCP sunucusu | Yazma araçları onaysız çalışmaz |
| 5 | LLM-hakem ile yanıt kalitesi, maliyet/gecikme raporu, Streamlit demo | |
