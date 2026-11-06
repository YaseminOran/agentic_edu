# Kod haritası: "Kartımdan aidat iki kez kesildi" talebinin yolculuğu

> Hafta 2'de eklendi. Tek bir talebin asistanın içinde hangi dosyadan, hangi fonksiyondan geçtiğini
> sırayla anlatır. Kodu okurken bu sayfayı yanınızda açık tutun.

Örnek: **M0007** numaralı müşteri şunu yazıyor:

> Kartımdan yıllık aidat iki kez kesilmiş, fazla olanın iadesini istiyorum.

Veride (`data/kart_islemleri.json`) M0007'nin kartından 2026-09-03 tarihinde iki kez 750 TL'lik
`ORNEK BANK KART YILLIK AIDATI` çekimi var: `I00287` ve `I00288`. Bu senaryoyu `data/uret.py` bilinçli olarak üretiyor.

Talebi çalıştırmak için:

```bash
python -m asistan.ajan "Kartımdan yıllık aidat iki kez kesilmiş, fazla olanın iadesini istiyorum." M0007 --model bulut
```

## Akışın kuşbakışı görünümü

```
cevapla()                                   src/asistan/ajan.py
  └─ GRAF.invoke()                          LangGraph akışı
       maskele ─► siniflandir ─┬─► hazir_yanit (guvenlik / diger) ─► SON
                               ├─► netlestir (güven düşük) ─► SON
                               └─► ajan_hazirla ─► ajan ⇄ arac_calistir
                                                    │
                                                    ▼
                                                 taslak ─► risk_kontrolu ─┬─► yanitla ─► SON
                                                                          ├─► insan_onayi ─► (onay) SON
                                                                          │                └► (ret) temsilciye_aktar
                                                                          └─► temsilciye_aktar ─► SON
```

Bu örnekte talebin izlediği yol:
**maskele → siniflandir → ajan_hazirla → ajan → arac_calistir → ajan → taslak → risk_kontrolu → insan_onayi**.
Akış insan onayında durur ve temsilci onaylayınca devam eder.

---

## 1. Giriş: `cevapla()` — [src/asistan/ajan.py](../src/asistan/ajan.py)

```python
cevapla("Kartımdan yıllık aidat ...", "M0007", model_turu="bulut")
```

- `src/asistan/__init__.py` dışarıya sadece `cevapla` ve `onayla` fonksiyonlarını açar. `eval/calistir.py` ve `kontrol.py` bunları kullanır.
- `cevapla()` şunları yapar:
  1. Yeni bir **oturum_id** üretir. Bu kimlik LangGraph'ın `thread_id`'sidir; durum bu kimlikle saklanır.
  2. `arac_havuzu()` ile kullanılabilecek tüm **okuma** araçlarını toplar: `araclar.OKUMA_ARACLARI` listesi. MCP ya da güvensiz mod seçilmişse havuz ona göre değişir.
  3. Bu bilgileri `config["configurable"]` içinde grafa verir. Araç nesneleri durumda değil config'te taşınır, çünkü durum checkpointer'a kaydedilir.
  4. `GRAF.invoke({"talep": ..., "musteri_no": "M0007"}, config)` ile akışı başlatır.
- `musteri_no` modele hiçbir zaman gitmez. Sadece durumda (`Durum["musteri_no"]`) ve araç çağrılırken `musteri_oturumu()` içinde kullanılır.

## 2. Maskeleme: `maskele_dugumu()` → `maskele()` — [src/asistan/maskeleme.py](../src/asistan/maskeleme.py)

- Talepteki IBAN, kart no, TCKN ve telefon regex ile maskelenir. Bu talepte maskelenecek bir şey yok, metin aynen geçer.
  Talep "kartım 9999 0000 0000 0007" deseydi modele `[KART ****0007]` giderdi.
- Yeni bir tur başladığı için tur alanları sıfırlanır: `adimlar`, `kullanilan_araclar`, `taslak` ...
- İlk adım satırı yazılır. `adim_ekle()` her satırı hem `logs/asistan.log` dosyasına hem de dönen `adimlar` listesine ekler.
  Loglama [src/asistan/gunluk.py](../src/asistan/gunluk.py) ile yapılır; `MaskelemeFiltresi` her log satırını bir kez daha maskeler.

## 3. Sınıflandırma: `siniflandir_dugumu()` → `siniflandir()` — [src/asistan/siniflandirici.py](../src/asistan/siniflandirici.py)

- Tek bir LLM çağrısı yapılır. Çıktı Pydantic şemasına bağlanır: `Siniflandirma{gerekce, kategori, ikinci_konu, guven}`.
- Kategori listesi ve açıklamaları [src/asistan/kategoriler.py](../src/asistan/kategoriler.py) içindeki `TUM_KATEGORILER`'den gelir. `Literal` tipi de bu sözlükten üretilir.
- Bu talep için sonuç: `kart (ikinci: -, guven: 0.95)`.
- Düğüm yolu `Command(goto=...)` ile seçer. Kontrol sırası şöyledir:
  1. `guvenlik` mi? Değil.
  2. Güven 0.6'nın altında mı? Değil.
  3. Ajana gitmeyen bir kategori mi? Değil.
  4. Sonuç: **`ajan_hazirla`**.

## 4. Araç seti: `ajan_hazirla_dugumu()` → `arac_setini_sec()` — [src/asistan/ajan.py](../src/asistan/ajan.py)

- `KATEGORILER["kart"]["araclar"]` → `musteri_bilgisi, kart_islemleri, gecmis_talepler, prosedur_ara`.
  `hesap_durumu` ve `kredi_basvuru_durumu` bu talepte modele hiç gösterilmez. İkinci konu olsaydı onun araçları da eklenirdi.
- Ajanın sistem mesajı (`AJAN_SISTEM_MESAJI`) ve `<talep>...</talep>` etiketli kullanıcı mesajı hazırlanır.

## 5. Ajan döngüsü: `ajan_dugumu()` ⇄ `arac_calistir_dugumu()`

**`ajan_dugumu()`**
- Önce adım limitini kontrol eder (`ADIM_LIMITI = 6`). Limit aşılırsa talep temsilciye aktarılır.
- `model.bind_tools(araclar)` ile modeli çağırır. Model aracı çalıştırmaz; sadece `tool_calls` döner:
  `kart_islemleri({'son_gun': 60}), musteri_bilgisi({})`.

**`arac_calistir_dugumu()`** her çağrı için sırasıyla şunları kontrol eder:
1. Aynı ad ve parametrelerle daha önce çağrıldı mı? Çağrıldıysa çalıştırmaz, modele "zaten çağırdın" der.
2. İzinli araç listesinde var mı? Yoksa çalıştırmaz, modele izinli araçların listesini bildirir.
3. Aracı `with musteri_oturumu("M0007"):` içinde çalıştırır.

Aracın içi: [src/asistan/araclar.py](../src/asistan/araclar.py)
- `kart_islemleri(son_gun=60)` müşteri numarasını `aktif_musteri()`'den alır; parametresi yoktur.
- `api_cagir("GET", "/kart_islemleri/M0007?son_gun=60")` 5xx hatasında 2 kez daha dener (0,3 sn ve 0,6 sn bekleyerek).
  Üç deneme de başarısız olursa `ApiHatasi` fırlatır ve akış **temsilciye_aktar** düğümüne gider.
- Mock API tarafında [mock_api/main.py](../mock_api/main.py) içindeki `kart_islemleri()` JSON'dan filtreleyip döner.
  Ara katman `gecikme_ve_rastgele_hata` her isteğe 0,05–0,25 sn gecikme ekler ve %5 olasılıkla 503 döner.
- `veri_olarak_etiketle()` çıktıyı maskeler ve `<arac_verisi arac="kart_islemleri">…</arac_verisi>` etiketiyle sarar.
  Model bu bloğu talimat değil, veri olarak görür.

Sonuçlar `ToolMessage` olarak mesaj geçmişine eklenir ve akış `ajan_dugumu()`'ne döner. Model bu kez araç istemeden bulgularını yazar:
"aynı gün iki aidat, I00287 ve I00288". Araç çağrısı olmadığı için akış **`taslak`** düğümüne geçer.

## 6. Yanıt taslağı: `taslak_dugumu()`

- Mesaj geçmişi düz metne çevrilir: talep + toplanan veriler + ajanın notu. Bu yapı model bağımsızdır.
- Çıktı yapılandırılmıştır: `Taslak{gerekce, karar, yanit, iade_islem_id, iade_tutari}`.
  `karar` değeri yanitla, netlestir veya temsilciye_aktar olabilir.
- Bu talep için sonuç: `karar="yanitla"`, `iade_islem_id="I00288"`, `iade_tutari=750`.
  Yanıt: "…fazla çekilen tutarın iade talebini onaya ilettik…"
- Yapılandırılmış çıktı bozuk gelirse bir kez daha denenir. Yine olmazsa karar `temsilciye_aktar` olur (güvenli taraf).

## 7. Risk kontrolü: `risk_kontrolu_dugumu()` → `risk_nedenleri_bul()`

- Kontroller **deterministiktir** (regex). Modelin "bu riskli değil" demesine güvenilmez.
  - `IADE_KALIBI`: yanıtta "iade" geçiyor **ve** `iade_islem_id` dolu → `iade`.
  - `TUTAR_KALIBI`: yanıtta "750 TL" gibi bir tutar varsa `tutar`.
  - `HUKUKI_KALIBI`: yanıtta ya da talepte avukat, dava, icra, BDDK... geçiyorsa `hukuki`.
- Sonuç: `risk kontrolu: iade -> insan_onayi`.

## 8. İnsan onayı: `insan_onayi_dugumu()` → `interrupt()` → `onayla()`

- `interrupt({...})` akışı **durdurur**. Durum `InMemorySaver` checkpointer'ında oturum_id ile saklanır.
- `cevapla()` bu sonucu döner: `davranis="insan_onayi"`, `onay_bekliyor=True`, `yanit=<taslak>`.
  Eval bu noktada durur ve davranışı `insan_onayi` olarak sayar.
- Temsilci karar verince şu çağrı yapılır:
  ```python
  onayla(oturum_id, onay=True, onaylayan="Ayşe Temsilci")
  ```
  `Command(resume=...)` ile akış kaldığı yerden devam eder. Dikkat: düğüm **baştan** çalışır, `interrupt()` bu kez onay değerini döner.
- Onay verildiyse **yazma aracı** `iade_talebi_olustur` burada çağrılır: modelden bağımsız olarak, kod tarafından,
  onaylayanın adıyla. Mock API `IAD0001` numaralı iade kaydını açar.
- Reddedildiyse akış `temsilciye_aktar` düğümüne gider.

## 9. Çıktı: `_sonuc()`

```python
{
  "kategori": "kart", "ikinci_konu": "", "davranis": "insan_onayi",
  "yanit": "…fazla çekilen tutarın iade talebini onaya ilettik…",
  "kullanilan_araclar": ["kart_islemleri", "musteri_bilgisi"],
  "kaynaklar": [],                 # Hafta 3'te prosedür dosyaları
  "adimlar": ["maskeleme: …", "siniflandirma: kart …", "arac seti (kart): …",
              "ajan adim 1: kart_islemleri({'son_gun': 60}), musteri_bilgisi({})",
              "ajan adim 2: arac cagrisi yok, bulgular yazildi",
              "taslak: yanitla - …I00288…", "risk kontrolu: iade -> insan_onayi"],
  "oturum_id": "3f9c2a1b", "onay_bekliyor": True,
}
```

## Aynı talep başka yollara nasıl sapabilir?

| Ne olursa | Hangi fonksiyonda | Sonuç |
|---|---|---|
| Talepte "avukatıma gideceğim" de geçerse | `risk_nedenleri_bul()` / taslak kararı | `temsilciye_aktar` (ajan seçerse) veya `insan_onayi` |
| Mock API 3 denemede de 503 dönerse | `api_cagir()` → `ApiHatasi` → `arac_calistir_dugumu()` | `temsilciye_aktar` (neden: araç hatası) |
| Model 6 adımda bitiremezse | `ajan_dugumu()` | `temsilciye_aktar` (neden: adım limiti) |
| Model `kredi_basvuru_durumu`'nu isterse | `arac_calistir_dugumu()` | Çalıştırılmaz; modele izinli araçlar bildirilir |
| Temsilci onayı reddederse | `insan_onayi_dugumu()` | `temsilciye_aktar` |
| `--guvensiz` ile çalıştırılırsa | `arac_havuzu()` → `araclar_guvensiz.py` | `kart_islemleri` parametre olarak `musteri_no` alır: talepteki numara başka bir müşteriye ait olabilir |
| `--mcp` ile çalıştırılırsa | `arac_havuzu()` → `mcp_sunucu.mcp_araclarini_yukle()` | Aynı araçlar ayrı bir süreçten MCP üzerinden çağrılır |
