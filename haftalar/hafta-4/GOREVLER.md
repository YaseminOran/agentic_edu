# Hafta 4 – Görevler: Doğru, Güvenli ve Bankaya Yakışır Yanıt

> Hafta 4 katılımcı görevleri. Asistan artık doğru bilgiyi buluyor (Hafta 3). Bu hafta **yeni bir yetenek eklemiyoruz**:
> mevcut yanıtları daha doğru, daha güvenli ve bankaya yakışır hale getiriyor ve bunu **ölçerek** kanıtlıyoruz.
> Bütün gün tek bir talebi takip edeceğiz: *"Kartımdan aidat iki kez kesildi"* (M0007).
> Tahmini süre: 5–6 saat.

## Bu haftanın hedefleri
- **Prompt şablonu:** İstem koddan çıkar, sürümlü bir dosya olur (`prompts/taslak/v2.md`). Dört bölüm: rol, görev, bağlam, kısıtlar.
- **Banka dili ve kurallar:** Ne zaman reddedilir, ne zaman temsilciye aktarılır (`prompts/kurallar.md`); nasıl yazılır (`prompts/banka_dili.md`).
- **Kişisel veri maskeleme:** Kart no, IBAN, TCKN modele takma adla gider (`[KART_1]`); müşteri "0007 ile biten kartınız" görür.
- **Self-check:** Yanıt gönderilmeden önce kodla ve ikinci bir model çağrısıyla kontrol edilir; geçmezse bir kez yeniden yazılır.
- **Ölçerek karar:** A/B testi (iki şablon sürümü, aynı test seti) ve hakem (LLM-as-judge).

## Bu hafta bakacağınız dosyalar

| Dosya | Ne zaman |
|---|---|
| `haftalar/hafta-4/01_prompt.ipynb` | Görev 1 (Lab 1): sabah |
| `prompts/kurallar.md`, `prompts/banka_dili.md` | Görev 1'de okuyacaksınız, Görev 2'de kullanacaksınız |
| `prompts/taslak/v2.md` | Görev 2 (Lab 2): şablonu siz yazacaksınız |
| `src/asistan/araclar.py` | Görev 3 (Lab 3): tek satır kod |
| `eval/ab_testi.py`, `eval/hakem.py` | Görev 2 ve 4: ölçüm |
| `demo.py` | Görev 4: uçtan uca deneme |

Merak ederseniz: `src/asistan/sablonlar.py` (şablon okuma ve doldurma), `maskeleme.py` (takma ad ve geri çevirme),
`self_check.py` (kontroller), `ajan.py` (`self_check_dugumu`, `risk_nedenleri_bul`).

## Günün akışı

| Sıra | Görev | Ne yapacaksınız | Süre |
|---|---|---|---|
| 1 | Hazırlık | Dal, indeks, kontrol | 15 dk |
| 2 | Görev 1 (Lab 1) | `01_prompt.ipynb`: şablon, maskeleme, self-check, A/B ve hakem | 2 saat |
| 3 | Görev 2 (Lab 2) | Taslak şablonunun v2'sini yazın, A/B testiyle v1'e karşı ölçün | 1 saat |
| 4 | Görev 3 (Lab 3) | Araç çıktılarına maskelemeyi bağlayın, sızıntı metriğini düşürün | 45 dk |
| 5 | Görev 4 | Tam ölçüm, karne, demo ve geri bildirim | 1 saat |

## Hazırlık (15 dk)
1. `hafta-4` dalına geçin ve son hali alın:
   ```bash
   git stash
   git fetch origin
   git checkout hafta-4
   git pull
   ```
   Kontrol: `haftalar/hafta-4/` klasörü ve proje kökünde `prompts/` klasörü olmalı.
2. İndeksi yeniden kurun (geçen hafta eklenen dokümanlar için):
   ```bash
   PYTHONPATH=src python -m asistan.rag.indeksle --chunk 400 --ortusme 50
   ```
3. `python kontrol.py`. Bu hafta iki yeni satır var:
   - **Prompt şablonları ✅**: kullanılan sürümleri yazar (`taslak=v1`: Lab 2'den sonra `v2` olacak).
   - **Maskeleme testleri ⚠️** *"araç çıktısı modele maskesiz gidiyor (Lab 3)"*: Bu beklenen bir durum; Görev 3'te düzelteceksiniz.

## Görev 1 (Lab 1) – Notebook (2 saat)
`haftalar/hafta-4/01_prompt.ipynb` dosyasını açın ve hücreleri sırayla çalıştırın. Kod yazmıyorsunuz.
Her hücrenin üstündeki iki cümleyi (**Ne yapıyoruz? Neye bakacağız?**) çalıştırmadan önce okuyun.

| Bölüm | Soru | Ne göreceksiniz |
|---|---|---|
| 1 | İyi bir talimat nasıl yazılır? | Zayıf istem ile dört bölümlü şablonun aynı veriyle yazdığı yanıt, yan yana |
| 2 | Müşteriye ne gider? | Gerçek veri ↔ modele giden takma ad; modelin yazdığı ↔ müşterinin gördüğü |
| 3 | Gönderilmeden kim kontrol ediyor? | Kötü bir taslağı kod ve model nasıl yakalıyor, yeniden yazım |
| 4 | Gerçekten iyileşti mi? | v1 ve v2 küçük A/B testi, hakemin puanları |

Notebook'taki kayıtlı çıktılar çözüm dalında (`hafta-4-cozum`) üretildi. Sizin dalınızda Bölüm 1'deki v2 bir **iskelet**
(Görev 2'de dolduracaksınız) ve araç çıktısı henüz maskelenmiyor (Görev 3). Yeniden çalıştırınca farklı çıktı görmeniz normal.

**Teslim:** Notebook sonundaki 4 tartışma sorusunun cevabı (markdown hücresi).

## Görev 2 (Lab 2) – Taslak şablonu v2 (1 saat)
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
Müşterinin mesajı maskeleniyor, ama araç çıktısı (`musteri_bilgisi`'nin döndürdüğü kart no, IBAN, TCKN) modele
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
3. **Demo:** `python demo.py`. Varsayılan talep (Enter, Enter) aidat talebidir; insan onayı sorulunca **h** deyip bir
   gerekçe yazın. Sonra:
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
- [ ] `01_prompt.ipynb` baştan sona çalışıyor
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
| Yanıtta `[KART_1]` kaldı | Geri çevirme yapılmadı | Yanıt `cevapla()`'dan mı geliyor? Notebook'ta taslağı doğrudan yazdırıyorsanız takma ad normaldir (Bölüm 2) |
| Yanıtta "[gizli bilgi]" | Model tabloda olmayan bir takma ad uydurdu (`[KART_3]`) | Güvenli taraf: numara yazılmaz. Sık oluyorsa şablonda takma ad kuralını netleştirin |
| Lab 3 sonrası "modele maskesiz" hâlâ 0 değil | Talepte ya da prosedürde maskelenmemiş bir kalıp | İzde `maskesiz_veri` hangi türü söylüyor? `maskeleme.py` → `KALIPLAR` |
| A/B'de iki sürüm her koşuda farklı sonuç | Yerel model deterministik değil | `--tekrar 3`; fark aralıkların içindeyse "fark yok" deyin |
| Çok fazla `temsilciye_aktar` | Self-check iki kez geçmedi | Adımlarda `self-check: GECMEDI - ...` gerekçesini okuyun: gerçek hata mı, aşırı katı eleştiri mi? |
| `self-check çıktısı okunamadı` uyarısı | Küçük model yapılandırılmış çıktıyı bozdu | Akış durmaz: eleştiri "emin değilim" sayılır, risk kontrolü eski temkinli kuralı kullanır |
| `hakem.py`: `CLAUDE_MODEL_GUCLU tanımlı değil` | `.env`'de güçlü model yok | `.env.example`'a bakın; hakem bulut model ister |
