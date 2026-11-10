# Hafta 2 – Görevler: Tek Ajan ve Tool Calling

> Hafta 2 katılımcı görevleri. Bu hafta asistan tek bir LLM çağrısından gerçek bir **ajana** dönüşüyor:
> müşteri verisini araçlarla çekiyor, iade gibi işlemlerde insana soruyor, hata olursa temsilciye bırakıyor.
> Ajanı önce notebook'ta adım adım kendiniz kuracaksınız, sonra projedeki halini (`src/asistan/ajan.py`) okuyacaksınız.
> Tahmini süre: 5–6 saat.

## Bu haftanın hedefleri
- **Tool calling:** Model aracı **ister**, aracı bizim kodumuz **çalıştırır**.
- **Ajan döngüsü:** Ajan = model + araçlar + döngü. Döngü adım limitiyle sınırlanır.
- **API entegrasyonu:** Araç, bir servis çağrısı ve etrafındaki güvenlik katmanlarından oluşur.
- **Worker agent:** Ajan tektir. Talebin konusuna göre sadece eline verilen araçlar değişir.
- **Güvenlik sınırları ve insan onayı:** Yazma aracı modele verilmez, para hareketi insan onayı ister.
- **Hata yönetimi:** Önce yeniden denenir. Yine olmazsa cevap uydurulmaz, talep temsilciye aktarılır.
- **Ölçme:** Ajanı Hafta 1 asistanıyla karşılaştırmak.

## Bu hafta bakacağınız dosyalar

| Dosya | Ne zaman |
|---|---|
| `haftalar/hafta-2/01_tool_calling.ipynb`, `02_ajan_adim_adim.ipynb` | Sabah: ajanı adım adım kuruyoruz |
| `haftalar/hafta-2/03_olc_ve_tartis.ipynb` | Öğleden sonra: çalıştırıp tartışıyoruz (Görev 5) |
| `src/asistan/araclar.py`, `src/asistan/kategoriler.py` | Görev 3 (Lab 3): kod yazacaksınız |

Diğer dosyaları açmanız gerekmiyor. Ne işe yaradıklarını merak ederseniz:
- `ajan.py`: notebook'ta kurduğumuz ajanın projedeki hali (Görev 5'te çalıştırıyoruz).
- `ayarlar.py`: `.env`'yi okur, modeli verir. `gunluk.py`: log ayarı.
- `siniflandirici.py`: talebin konusunu bulur; notebook'ta hazır kullanıyoruz.
- `araclar_guvensiz.py`: sadece Görev 5'teki güvenlik deneyi için, bilerek hatalı yazılmış araç.
- `tek_cagri.py`: Hafta 1 asistanı; değerlendirmede karşılaştırma için duruyor.
- `mock_api/`: sahte banka servisi. `data/`: sentetik veri. `eval/`: değerlendirme (Görev 5).

## Günün akışı

| Sıra | Görev | Ne yapacaksınız | Süre |
|---|---|---|---|
| 1 | Hazırlık | Dal, kontrol | 15 dk |
| 2 | Görev 1 | `01_tool_calling.ipynb`: tek araç çağrısı, araç açıklaması | 40 dk |
| 3 | Görev 2 | `02_ajan_adim_adim.ipynb` Bölüm 1–2: döngü, API | 30 dk |
| 4 | Görev 3 (Lab 3) | `hesap_durumu` aracını yazın | 45 dk |
| 5 | Görev 4 | `02_ajan_adim_adim.ipynb` Bölüm 3–6: worker, insan onayı, hata | 60 dk |
| 6 | Görev 5 | `03_olc_ve_tartis.ipynb`: güvenlik deneyleri, ölçme, hata analizi, model karşılaştırması | 2,5 saat |

## Hazırlık (15 dk)
1. Kendi dalınızı açın: `git checkout hafta-1 && git checkout -b hafta-2-benim`
2. `python kontrol.py` çalıştırın. Mock API satırında bir ⚠️ göreceksiniz: `hesap_durumu` henüz yazılmamış.
   Bu beklenen bir durum; Görev 3'te siz yazacaksınız.
3. Mock API Dev Container'da otomatik başlar. Başlamadıysa ayrı bir terminalde:
   `uvicorn mock_api.main:app --host 0.0.0.0 --port 8000`

Önceden okumanız gereken bir dosya yok. Her dosyayı notebook'ta sırası gelince açacağız.

## Görev 1 – Tool calling (40 dk)
`haftalar/hafta-2/01_tool_calling.ipynb` dosyasının **1. ve 2. bölümlerini** çalıştırın:
1. Model aracı nasıl **ister** (`tool_calls`) ve aracı kim çalıştırır?
2. Kötü ve iyi açıklamalı araçlarla aynı 6 soru: açıklama, model seçimini nasıl değiştiriyor?

3. bölüm (Claude ve Qwen karşılaştırması) Bonus'tur.

## Görev 2 – Ajanı kurmaya başlayın (30 dk)
`haftalar/hafta-2/02_ajan_adim_adim.ipynb` dosyasında **Bölüm 1 ve 2**:
1. **Ajan döngüsü:** `ajan_calistir` fonksiyonu. Model araç istedikçe çalıştır, istemeyince dur.
   `adim_limiti=1` ile deneyin: ne oldu?
2. **API entegrasyonu:** Servisi doğrudan çağırın, sonra aynı veriyi araç üzerinden alın. Araç hangi iki güvenlik katmanını ekliyor?

## Görev 3 (Lab 3) – `hesap_durumu` aracını yazın (45 dk)
`# TODO (Lab 3):` yorumlarını arayın: `src/asistan/araclar.py` ve `src/asistan/kategoriler.py`.
1. **Gövde:** `GET /hesap_durumu/{musteri_no}` ucunu çağırın. Notebook Bölüm 2'deki kalıbı kullanın:
   `api_cagir()` + `aktif_musteri()` + `veri_olarak_etiketle()`. **`musteri_no` parametre olmayacak.**
2. **Açıklama (docstring):** Ne yapar / Ne zaman kullan / Ne zaman KULLANMA. Uç noktanın ne döndürdüğüne
   `http://localhost:8000/docs` adresinden bakın.
3. **Kategoriye bağlayın:** `KATEGORILER["hesap"]["araclar"]` listesine ekleyin.
4. Test edin:
   ```bash
   python kontrol.py                                          # ⚠️ kaybolmalı
   python -m asistan.ajan "Hesabımda neden bloke var?" M0012  # hesap_durumu çağrılmalı
   ```

**Tartışma:** Açıklamanıza "Ne zaman KULLANMA" kısmını yazmasaydınız, "Kartım neden bloke?" sorusunda model hangi aracı seçerdi?

## Görev 4 – Ajanı tamamlayın (60 dk)
Notebook'u yeniden başlatın (*Restart*), çünkü Lab 3'teki aracınızın yüklenmesi gerekiyor.
`02_ajan_adim_adim.ipynb` dosyasında **Bölüm 3–6**:
3. **Worker agent:** Talebin konusunu bulun, ajana sadece o konunun araçlarını verin.
4. **İnsan onayı:** Yanıt taslağı ve iade önerisi. Onay sorusuna bir kez `e`, bir kez `h` deyin.
5. **Hata yönetimi:** Servisi "çökertin". Ajan ne yaptı?
6. **Hepsi bir arada:** `talep_isle` ile üç talep. Notebook'un sonundaki tabloyla parçaları `ajan.py`'de bulun.

**Teslim:** Notebook sonundaki tartışma sorularının cevapları (notebook'a markdown hücresi olarak).

## Görev 5 – Ölç ve tartış (öğleden sonra, ~2,5 saat)
`haftalar/hafta-2/03_olc_ve_tartis.ipynb` dosyasını açın ve hücreleri sırayla çalıştırın. Kod yazmıyorsunuz;
her bölümün sonundaki **💬 Tartışma** sorularını birlikte konuşuyoruz.

| Bölüm | Ne yapıyorsunuz | Süre |
|---|---|---|
| 1 | Projenin ajanı (`ajan.py`) ve iki güvenlik deneyi | 40 dk |
| 2 | Puan: ajanı ölçüp Hafta 1 ile karşılaştırma | 30 dk |
| 3 | Hata analizi: ajan nerede, neden yanılıyor? | 50 dk |
| 4 | Yerel model mi, Claude mu? | 30 dk |
| 5 | Kapanış | 15 dk |

**Teslim:** Tartışma sorularının cevapları (notebook'a markdown hücresi olarak).

## Bonus
- **Claude ve Qwen:** `01_tool_calling.ipynb` Bölüm 3. Aynı soruda 5'er deneme yapın. Bir bankada hangi işi hangi modele verirdiniz?
- **LangGraph'ı okuyun:** `ajan.py` içinde `graf_olustur()`, `Command(goto=...)` ve `interrupt`. Notebook'taki
  `talep_isle` fonksiyonu ile aynı akış nasıl düğümlere bölünmüş?
- **Netleştirme:** `python -m asistan.ajan "Kartım çalışmıyor." M0013` ve aynı talebi `M0004` ile çalıştırın.
  Neden farklı davranışa gittiler? Python'dan `cevapla("Bir sorun var.", "M0001")` çağırıp dönen `oturum_id` ile
  ikinci bir tur gönderin.
- **Yeni kategori (5. haftaya hazırlık):** `kategoriler.py`'ye kod değiştirmeden bir kategori ekleyebilir misiniz?
  Neler gerekir (veri, uç nokta, araç, kategori tanımı)?

## Hafta sonu kontrol listesi
- [ ] `python kontrol.py` hatasız (⚠️ kalmadı)
- [ ] `02_ajan_adim_adim.ipynb` ve `03_olc_ve_tartis.ipynb` baştan sona çalışıyor
- [ ] `python eval/calistir.py` hatasız; T05 ve T22'de `hesap_durumu` çağrılıyor
- [ ] Notebook ve görevlerdeki tartışma soruları cevaplandı

Hazır çözüm: `git checkout hafta-2` (önce kendi çözümünüzü commit edin!)

## Sık hatalar

| Belirti | Neden | Çözüm |
|---|---|---|
| `kontrol.py`: Mock API ❌ "erişilemiyor" | Mock API çalışmıyor | Ayrı terminalde: `uvicorn mock_api.main:app --host 0.0.0.0 --port 8000` |
| `kontrol.py`: Mock API ❌ `404 ... /musteri_bilgisi/...` | Hafta 1'den kalma eski bir mock API süreci açık | `pkill -f uvicorn`, sonra yeniden başlatın |
| `Müşteri bulunamadı: M1001` | Hafta 1 müşteri numaraları kullanılıyor | Numaralar artık `M0001`–`M0030` |
| Logda `API ... deneme 1/3 başarısız: HTTP 503` | Mock API bilerek ara sıra hata veriyor | Normal: araç yeniden dener (notebook Bölüm 5) |
| `NotImplementedError: TODO (Lab 3)` | `hesap_durumu` henüz yazılmadı | Görev 3. Yazdıysanız notebook'u yeniden başlatın (*Restart*) |
| `RuntimeError: Aktif müşteri yok` | Araç `musteri_oturumu()` dışında çağrıldı | `with musteri_oturumu("M0007"): arac.invoke({...})` |
| Notebook'ta `ModuleNotFoundError` ya da kernel/venv seçmenizi istiyor | VS Code penceresi container'da değil | Sol altta "Dev Container" yazmalı; yoksa *Reopen in Container*. Kernel: `/usr/local/bin/python` |
| Notebook'ta `NameError` (ör. `TALEP` tanımlı değil) | Üstteki hücreler çalıştırılmamış (ya da kernel yeniden başlamış) | Hatalı hücrenin `...` menüsü → **Execute Above Cells** |
| Notebook onay hücresi bekliyor | `input()` cevap bekliyor | VS Code'un üstünde açılan kutuya `e` ya da `h` yazıp Enter |
| Bölüm 5'ten sonra her araç hata veriyor | Servis adresi geri alınmamış | Notebook'u yeniden başlatın (*Restart*) |
| Talep beklenmedik şekilde temsilciye gitti | Adım limiti, araç hatası ya da bilgi yetersiz | Çıktının son satırı nedeni söyler (`temsilciye aktarildi: ...` / `TEMSİLCİYE AKTAR: ...`) |
| Yerel modelde `taslak çıktısı okunamadı` | Küçük model yapılandırılmış çıktıyı bozuk üretti | Akış bir kez daha dener, olmazsa temsilciye düşer. Normal |
| Çıktı arkadaşınızınkinden farklı | Yerel modelde değişkenlik | Normal. Aynı talebi `--model bulut` ile karşılaştırın |
