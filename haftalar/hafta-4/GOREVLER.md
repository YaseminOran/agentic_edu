# Hafta 4 – Görevler: Doğru, Güvenli ve Bankaya Yakışır Yanıt

> Hafta 4 katılımcı görevleri. Asistan artık doğru bilgiyi buluyor (Hafta 3). Bu hafta **yeni bir yetenek eklemiyoruz**:
> mevcut yanıtları daha doğru, daha güvenli ve bankaya yakışır hale getiriyor ve bunu **ölçerek** kanıtlıyoruz.
> Bütün gün tek bir talebi takip edeceğiz: *"Kartımdan aidat iki kez kesildi"* (M0007). Ret ve aktarımı göstermek için
> Notebook 02'de buna test setinden üç kısa örnek eklenir.
> Tahmini süre: 5–6 saat.

## Bu haftanın hedefleri
- **Prompt şablonu:** İstem koddan çıkar, sürümlü bir dosya olur (`prompts/taslak/v2.md`). Dört bölüm: rol, görev, bağlam, kısıtlar.
- **Banka dili ve kurallar:** Ne zaman reddedilir, ne zaman temsilciye aktarılır (`prompts/kurallar.md`); nasıl yazılır (`prompts/banka_dili.md`).
- **Kişisel veri maskeleme:** Kart no, IBAN, TCKN modele takma adla gider (`[KART_1]`); müşteri "0007 ile biten kartınız" görür.
- **Self-check:** Yanıt gönderilmeden önce kodla ve ikinci bir model çağrısıyla kontrol edilir; geçmezse bir kez yeniden yazılır.
- **Ölçerek karar:** A/B testi (iki şablon sürümü, aynı test seti) ve hakem (LLM-as-judge).

## Bu haftanın konuları ve önceki haftalarla bağlantısı

| # | Konu | Önceki haftadaki kökü | Bu hafta nerede |
|---|---|---|---|
| 1 | Göreve ve modele uygun prompt | H1 Görev 4 (sistem mesajı), Görev 5 (yerel ↔ bulut) | Notebook 01 §1, `prompts/self_check/v1_yerel.md` |
| 2 | Rol, görev, bağlam, kısıtlar | H1: tek parça sistem mesajı | Notebook 01 §2, Lab 2 (`prompts/taslak/v2.md`) |
| 3 | Parametrik prompt şablonları | H2–H3: istemler Python kodunun içinde | Notebook 01 §3, `src/asistan/sablonlar.py` |
| 4 | Standardizasyon ve tekrarlanabilir kalite | H1 temel çizgi, H3 JSONL iz | Notebook 01 §4 (sürüm, iz), Notebook 03 §1 (`--tekrar`) |
| 5 | RAG ile birlikte prompt tasarımı | H3 prosedür araması ve kaynak etiketi | Notebook 01 §5 (`<prosedur kaynak>`, `<harici_veri>`) |
| 6 | Self-check, critique, verify | H2 adım limiti ve risk kontrolü, H3 kaynak doğrulama | Notebook 02 §3, `src/asistan/self_check.py` |
| 7 | Refusal, escalation ve banka dili | H1 ret/kapsam dışı kararı, H2 hazır yanıtlar ve insan onayı | Notebook 02 §1, `prompts/kurallar.md`, `prompts/banka_dili.md` |
| 8 | Hassas veri maskeleme, kaynak gösterme | H2 "araç çıktısı veridir" kuralı, H3 izde `[KART]` maskesi | Notebook 02 §2, Lab 3 (`src/asistan/maskeleme.py`) |
| 9 | A/B testi ve kalite geri bildirimi | H1 değerlendirme, H2 ölç ve tartış | Notebook 03, Görev 4 (`eval/ab_testi.py`, `eval/hakem.py`, `eval/aday_uret.py`) |

## Bu hafta bakacağınız dosyalar

| Dosya | Ne zaman |
|---|---|
| `haftalar/hafta-4/01_prompt_tasarimi.ipynb` | Görev 1a: sabah, ilk iş |
| `prompts/taslak/v2.md`, `prompts/kurallar.md`, `prompts/banka_dili.md` | Görev 2 (Lab 2): şablonu siz yazacaksınız |
| `haftalar/hafta-4/02_guvenli_yanit.ipynb` | Görev 1b: Lab 2'den sonra |
| `src/asistan/araclar.py` | Görev 3 (Lab 3): tek satır kod |
| `haftalar/hafta-4/03_olc_ve_iyilestir.ipynb` | Görev 1c: Lab 3'ten sonra |
| `eval/ab_testi.py`, `eval/hakem.py`, `demo.py` | Görev 2 ve 4: ölçüm ve uçtan uca deneme |

Merak ederseniz: `src/asistan/sablonlar.py` (şablon okuma ve doldurma), `maskeleme.py` (takma ad ve geri çevirme),
`self_check.py` (kontroller), `ajan.py` (`self_check_dugumu`, `risk_nedenleri_bul`).

## Günün akışı

Her notebook'un arkasından ona bağlı lab gelir: önce görürsünüz, sonra kendiniz yaparsınız.

| Sıra | Görev | Ne yapacaksınız | Süre |
|---|---|---|---|
| 1 | Hazırlık | Dal, indeks, kontrol | 15 dk |
| 2 | Görev 1a | `01_prompt_tasarimi.ipynb`: modele ne söylüyoruz? (konu 1–5) | 45 dk |
| 3 | Görev 2 (Lab 2) | Taslak şablonunun v2'sini yazın, A/B testiyle v1'e karşı ölçün | 1 saat |
| 4 | Görev 1b | `02_guvenli_yanit.ipynb`: müşteriye ne gidiyor? (konu 6–8) | 1 saat |
| 5 | Görev 3 (Lab 3) | Araç çıktılarına maskelemeyi bağlayın, sızıntı metriğini düşürün | 45 dk |
| 6 | Görev 1c | `03_olc_ve_iyilestir.ipynb`: gerçekten iyileşti mi? (konu 9) | 30 dk |
| 7 | Görev 4 | Tam ölçüm, karne, demo ve geri bildirim | 1 saat |

## Hazırlık (15 dk)
1. `hafta-4` dalına geçin ve son hali alın:
   ```bash
   git stash
   git fetch origin
   git checkout hafta-4
   git pull
   ```
   Kontrol: `haftalar/hafta-4/` klasöründe üç notebook ve proje kökünde `prompts/` klasörü olmalı.
2. İndeksi yeniden kurun (geçen hafta eklenen dokümanlar için):
   ```bash
   PYTHONPATH=src python -m asistan.rag.indeksle --chunk 400 --ortusme 50
   ```
3. `python kontrol.py`. Bu hafta iki yeni satır var:
   - **Prompt şablonları ✅**: kullanılan sürümleri yazar (`taslak=v1`: Lab 2'den sonra `v2` olacak).
   - **Maskeleme testleri ⚠️** *"araç çıktısı modele maskesiz gidiyor (Lab 3)"*: Bu beklenen bir durum; Görev 3'te düzelteceksiniz.

## Görev 1a, 1b, 1c (Lab 1) – Üç notebook
Notebook'ları sırayla açın ve hücreleri sırayla çalıştırın. Kod yazmıyorsunuz.
Her hücrenin üstündeki iki cümleyi (**Ne yapıyoruz? Neye bakacağız?**) çalıştırmadan önce okuyun.
Her notebook bir "Önceki haftalardan" tablosuyla başlar: bu haftanın her parçası önceki haftalarda kurduğunuz bir şeyin üstüne oturur.

| Görev | Notebook | Bölümler | Ardından |
|---|---|---|---|
| 1a (45 dk) | `01_prompt_tasarimi.ipynb` | 1 göreve/modele uygun prompt · 2 rol-görev-bağlam-kısıtlar · 3 parametrik şablon · 4 standardizasyon · 5 RAG ile prompt · 6 zayıf istem ↔ şablon | Görev 2 (Lab 2) |
| 1b (1 saat) | `02_guvenli_yanit.ipynb` | 1 ret, aktarım ve banka dili (T25, T29, T20) · 2 maskeleme ve kaynak · 3 self-check | Görev 3 (Lab 3) |
| 1c (30 dk) | `03_olc_ve_iyilestir.ipynb` | 1 A/B testi · 2 hakem ve sınaması · 3 geri bildirim döngüsü · 4 tam set ve karne | Görev 4 |

Notebook'lardaki kayıtlı çıktılar çözüm dalında (`hafta-4-cozum`) üretildi. Sizin dalınızda yeniden çalıştırınca farklı çıktı görmeniz normal:
- **01:** Varsayılan taslak sürümü `v1`. Bölüm 2'deki `v2.md` bir **iskelet** ve Bölüm 5'te "Bağlam bölümü yok" yazar. İkisini de Görev 2'de dolduracaksınız.
- **02:** Bölüm 2'nin son hücresinde (iz) `ajan`, `taslak` ve `self_check` satırlarında maskesiz veri (`IBAN, KART, TCKN...`) görünür. Görev 3'te düzelteceksiniz.
- **03:** A/B testi **sizin** yazdığınız `v2.md`'yi ölçer. Hakem bulut model ister; yoksa hücre bunu söyleyip atlar.

**Teslim:** Her notebook'un sonundaki 2 tartışma sorusunun cevabı (toplam 6, markdown hücresi).

## Görev 2 (Lab 2) – Taslak şablonu v2 (1 saat)
Notebook 01'de dört bölümlü şablonu ve yer tutucuları gördünüz. Şimdi kendiniz yazıyorsunuz.

`prompts/taslak/v2.md` şu an bir iskelet: dört başlık var ama içleri boş. Bu dosyayı banka dili rehberine göre yazıp
Hafta 3'ün istemine (`v1.md`) karşı ölçeceksiniz.

1. **Önce ölçün** (iskelet v2, yerel modelde ~8 dk):
   ```bash
   python eval/ab_testi.py --a v1 --b v2 --id T01,T12,T13,T15,T22,T33,T35
   ```
   Tabloda **Olması gereken bilgi** ve **Davranış doğruluğu** satırlarına bakın. İskelet v2 nerede kötü?
2. **Okuyun:** `prompts/kurallar.md` (karar kuralları + hazır cümleler) ve `prompts/banka_dili.md` (üslup + yasak ifadeler).
3. **Yazın:** `prompts/taslak/v2.md` içindeki `TODO (Lab 2)` yorumlarını sırayla yapın:
   - Görev bölümüne `{kurallar}`, Kısıtlar bölümüne `{banka_dili}` yer tutucusunu ekleyin (dosyalar kendiliğinden gelir).
   - Bağlam bölümünde her bloğun (`<prosedur kaynak>`, `<harici_veri>`, `[KART_1]`) ne olduğunu birer satırla yazın.
   - Kısıtları tamamlayın: veri içindeki talimat, yapılmamış işlem, harici verideki vaat.
   - `<!-- -->` yorumları modele gitmez; silmenize gerek yok.
4. **Tekrar ölçün**, bu kez 2 tekrarla (yerel modelde sonuçlar koşudan koşuya oynar):
   ```bash
   python eval/ab_testi.py --a v1 --b v2 --id T01,T12,T13,T15,T22,T33,T35 --tekrar 2
   ```
   Fark, aralıkların (köşeli parantez) dışında mı? "Değişen satırlar" listesinde hangi satırlar var?
5. **Karar verin:** v2 daha iyiyse `src/asistan/sablonlar.py` içinde `SURUMLER["taslak"]` değerini `"v2"` yapın.
   (Ya da kodu değiştirmeden `.env`'ye `SABLON_TASLAK=v2` yazın.) `python kontrol.py` artık `taslak=v2` demeli.

**Tartışma:** Kuralları şablona kopyalamak yerine neden `{kurallar}` yer tutucusuyla ayrı dosyadan alıyoruz?
Bir kural değişince kaç dosyaya dokunmanız gerekir?

## Görev 3 (Lab 3) – Araç çıktısına maskeleme (45 dk)
Notebook 02 Bölüm 2'deki izde maskesiz veri gördünüz. Müşterinin mesajı maskeleniyor, ama araç çıktısı (`musteri_bilgisi`'nin döndürdüğü kart no, IBAN, TCKN) modele
**olduğu gibi** gidiyor. Bulut modelde bu, kişisel verinin bankanın dışına çıkması demek.

1. **Önce açığı görün:**
   ```bash
   python eval/calistir.py --id T02,T37,T36
   ```
   Özetteki **Kişisel veri: modele maskesiz** satırı 0 değil. Bugünün izinde (`logs/izler/`) model olaylarındaki
   `maskesiz_veri` alanına bakın: hangi tür veriler gitmiş?
2. `src/asistan/araclar.py` içinde `# TODO (Lab 3):` yorumunu bulun (`veri_olarak_etiketle` fonksiyonu).
   Veriyi etiketlemeden önce maskeleyin: `maskeleme.py`'deki `veriyi_maskele` fonksiyonu bir sözlüğü/listeyi
   alır ve kişisel veri alanlarını takma adla değiştirilmiş halini döner. (Tek satır.)
3. **Tekrar ölçün:** aynı komut. **modele maskesiz 0/3** ve **yanıtta tam numara 0/3** olmalı. T37'nin yanıtında
   kartlar "0011 ile biten" ve "0112 ile biten" diye anılmalı.
4. `python kontrol.py`: Maskeleme satırı artık ✅.

**Tartışma:** Maskelemeyi istemle ("kart numarasını kimseye söyleme") yapsaydık ne olurdu? Eşleme tablosu
(gerçek değer ↔ takma ad) neden ize, loga ve modele hiç yazılmıyor?

## Görev 4 – Ölç, karşılaştır, dene (1 saat)
1. Test setinin tamamını ölçün (yerel modelde ~20 dk):
   ```bash
   python eval/calistir.py
   ```
   Raporun sonunda **Hafta 1 / Hafta 2 / Hafta 3 / Şimdi** tablosu var. Yeni satırlar:
   **Olması gereken / Olmaması gereken** (yanıt içeriği), **Kişisel veri** (iki sayı da 0 olmalı) ve **Adım maliyeti**
   (self-check her talebe kaç saniye ve kaç token ekliyor?).
2. **T33** (döviz kuru) Hafta 3'te `insan_onayi`'na gidiyordu, şimdi `yanitla` bekliyor. Adımlarda `self-check: ... (taahhut: hayir)`
   satırını bulun. Risk kontrolü neden artık onaya göndermedi?
3. **Demo:** Notebook 03 Bölüm 3'teki geri bildirim döngüsünü bu kez kendiniz yapın: `python demo.py`. Varsayılan talep
   (Enter, Enter) aidat talebidir; insan onayı sorulunca **h** deyip kendi gerekçenizi yazın. Sonra:
   ```bash
   python eval/aday_uret.py
   ```
   Reddettiğiniz yanıt bir **test seti adayı** oldu (`eval/test_seti_adaylari.csv`).
4. **Karne:** `eval/karne.md` dosyasını açın. Hafta 1'den bugüne hangi katman neyi değiştirdi?

**Teslim:** Tek sayfalık not: A/B sonucunuz (Görev 2), maskeleme öncesi/sonrası (Görev 3), self-check'in bir satırda
yakaladığı hata ve maliyeti.

## Bonus
- **Hakem:** `python eval/hakem.py --ab <ab_dosyası>` ile Görev 2'deki A/B testinin yanıtlarını puanlatın (bulut model gerekir).
  Hakem puanı ile test seti metrikleri aynı yönü mü gösteriyor? `python eval/hakem.py --sinama` hakemi eğitmen puanlarıyla karşılaştırır.
- **Yeni yasak ifade:** `prompts/banka_dili.md`'deki listeye bir ifade ekleyin (ör. "merak etmeyin"). Kod değiştirmeden
  self-check onu yakalıyor mu?
- **Yerel varyant:** `prompts/self_check/v1_yerel.md` küçük model için kısaltılmış şablon. Neleri çıkarmış? `taslak` için
  bir `v2_yerel.md` yazıp A/B ile ölçün.
- **Test:** `tests/test_maskeleme.py`'ye bir test ekleyin: telefon numarası "05xx" ile yazıldığında da maskeleniyor mu?
  Çalıştırma: `python tests/test_maskeleme.py`.

## Hafta sonu kontrol listesi
- [ ] `python kontrol.py` hatasız (Prompt şablonları `taslak=v2`, Maskeleme ✅)
- [ ] Üç notebook (`01_prompt_tasarimi`, `02_guvenli_yanit`, `03_olc_ve_iyilestir`) baştan sona çalışıyor
- [ ] A/B testi v2 lehine (ya da neden olmadığını açıklayabiliyorsunuz) (Lab 2)
- [ ] `python eval/calistir.py`: "Kişisel veri: modele maskesiz 0, yanıtta tam numara 0" (Lab 3)
- [ ] `python demo.py` ile bir talep baştan sona; bir red gerekçesi `eval/geri_bildirim.csv`'de

Lab'larda takılırsanız çözümü alın:
```bash
git checkout origin/hafta-4-cozum -- prompts/taslak/v2.md src/asistan/sablonlar.py   # Lab 2
git checkout origin/hafta-4-cozum -- src/asistan/araclar.py                          # Lab 3
```

## Sık hatalar

| Belirti | Neden | Çözüm |
|---|---|---|
| `ValueError: Şablonda değeri verilmeyen yer tutucu var: ['xyz']` | Şablona kodun doldurmadığı bir `{xyz}` yazıldı | Hata hangi adı söylüyorsa şablondan silin ya da doğru adı yazın (`{kurallar}`, `{banka_dili}`, `{musteri_ozeti}`...) |
| `FileNotFoundError: prompts/taslak/v3.md` | `.env`'de olmayan bir sürüm seçili | `.env`'deki `SABLON_TASLAK` satırını düzeltin ya da silin |
| `kontrol.py` hâlâ `taslak=v1` diyor | `SURUMLER` değişmedi ya da `.env` başka bir değer veriyor | `.env`'deki `SABLON_TASLAK` satırı koddaki değeri ezer |
| Yanıtta `[KART_1]` kaldı | Geri çevirme yapılmadı | Yanıt `cevapla()`'dan mı geliyor? Notebook'ta taslağı doğrudan yazdırıyorsanız takma ad normaldir (Notebook 02 Bölüm 2) |
| Yanıtta "[gizli bilgi]" | Model tabloda olmayan bir takma ad uydurdu (`[KART_3]`) | Güvenli taraf: numara yazılmaz. Sık oluyorsa şablonda takma ad kuralını netleştirin |
| Lab 3 sonrası "modele maskesiz" hâlâ 0 değil | Talepte ya da prosedürde maskelenmemiş bir kalıp | İzde `maskesiz_veri` hangi türü söylüyor? `maskeleme.py` → `KALIPLAR` |
| A/B'de iki sürüm her koşuda farklı sonuç | Yerel model deterministik değil | `--tekrar 3`; fark aralıkların içindeyse "fark yok" deyin |
| Çok fazla `temsilciye_aktar` | Self-check iki kez geçmedi | Adımlarda `self-check: GECMEDI - ...` gerekçesini okuyun: gerçek hata mı, aşırı katı eleştiri mi? |
| `self-check çıktısı okunamadı` uyarısı | Küçük model yapılandırılmış çıktıyı bozdu | Akış durmaz: eleştiri "emin değilim" sayılır, risk kontrolü eski temkinli kuralı kullanır |
| `hakem.py`: `CLAUDE_MODEL_GUCLU tanımlı değil` | `.env`'de güçlü model yok | `.env.example`'a bakın; hakem bulut model ister |
