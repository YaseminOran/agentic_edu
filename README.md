# Agentic Sistemler Eğitimi – Müşteri Talep ve Şikayet Asistanı

> 5 haftalık ileri seviye agentic sistemler eğitiminin uygulama reposu (Hafta 1'de oluşturuldu).
> Tüm veriler **sentetiktir**; gerçek müşteri, kart veya hesap bilgisi içermez.

Bankaya gelen müşteri taleplerini sınıflandıran, araçlarla bilgi toplayan, prosedürlerden kaynaklı
cevap bulan, yanıt taslağı hazırlayan ve riskli durumları insana aktaran bir asistanı hafta hafta inşa ediyoruz.

## Bu sistem ne yapıyor?

Bugün (Hafta 4 sonu) asistan bir müşteri talebi geldiğinde şunları yapar:

1. **Anlar:** Talebi kart, hesap, kredi, güvenlik ya da kapsam dışı olarak sınıflandırır; belirsizse netleştirme sorusu sorar.
2. **Bilgi toplar:** Kategoriye göre seçilen araçlarla müşterinin verisini getirir (kart işlemleri, hesap durumu...).
   Müşteri numarası modelden değil sistemden gelir.
3. **Kaynak gösterir:** Bankanın prosedürlerinde arar (RAG) ve yanıttaki her kuralın kaynağını gösterir.
   Kaynakta olmayan bilgiyi iddia etmez; temsilcilere özel dokümanlar müşteriye gitmez.
4. **Korur:** Kart numarası, IBAN, TCKN gibi kişisel veriler modele takma adla gider ([KART_1]); müşteri
   "0007 ile biten kartınız" görür. Yanıt gönderilmeden önce kendini kontrol eder (self-check).
5. **İnsana bırakır:** İade, ödeme taahhüdü ve hukuki süreç içeren yanıtlar temsilci onayı olmadan gitmez;
   şüphede talebi temsilciye aktarır. Her çalıştırmanın izi `logs/izler/` altına yazılır.

Çalıştırmak için üç komut (kurulumdan sonra, proje kökünde):

```bash
PYTHONPATH=src python -m asistan.rag.indeksle --chunk 400 --ortusme 50   # prosedür indeksini kur (bir kez)
python kontrol.py                                                         # ortam kontrolü
python demo.py                                                            # asistanı terminalde dene
```

Haftadan haftaya sonuçlar: [eval/karne.md](eval/karne.md).

> **Hafta 4 (bu hafta) materyalleri `hafta-4` dalında** (`main` de aynı içerikte). Son hali almak için terminalde:
> ```bash
> git stash            # notebook çıktıları gibi yerel değişiklikleri kenara koyar
> git fetch origin
> git checkout hafta-4
> git pull
> ```
> Kontrol: `haftalar/hafta-4` klasöründe `01_prompt.ipynb` ve `GOREVLER.md`, proje kökünde `prompts/` olmalı.

| Hafta | Konu | Dal |
|---|---|---|
| 1 | LLM çağırma, yapılandırılmış çıktı, sınıflandırma, değerlendirme (teori) | – |
| 2 | Tek ajan ve tool calling: ajan döngüsü, API entegrasyonu, worker agent, insan onayı, hata yönetimi | `hafta-1` (başlangıç), `hafta-2` (çözüm) |
| 3 | Prosedürlerden RAG (bge-m3 + FAISS), kaynak gösterme, harici veri, izleme (JSONL) | `hafta-2` (başlangıç), `hafta-3` (çözüm) |
| 4 | Prompt şablonları, banka dili, kişisel veri maskeleme, self-check, A/B testi ve hakem | `hafta-4` (başlangıç, `main` de aynı), `hafta-4-cozum` (çözüm) |
| 5 | Kapsamlı değerlendirme ve Streamlit demo | `hafta-5` |

## Kurulum

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) ve VS Code + **Dev Containers** eklentisini kurun.
2. `.env.example` dosyasını `.env` adıyla kopyalayın ve düzenleyin:
   - **Mac:** Ollama'yı [host'a kurun](https://ollama.com/download), `OLLAMA_URL=http://host.docker.internal:11434`, `COMPOSE_PROFILES=` boş.
   - **Windows / Linux:** `OLLAMA_URL=http://ollama:11434`, `COMPOSE_PROFILES=ollama` (Ollama konteynerde çalışır).
   - Eğitmenden aldığınız `ANTHROPIC_API_KEY` değerini girin.
3. VS Code'da klasörü açın → *Reopen in Container*.
4. Modelleri indirin (bir kez):
   - Mac (host terminalinde): `ollama pull qwen3.5:4b && ollama pull bge-m3`
   - Windows/Linux: `docker compose exec ollama ollama pull qwen3.5:4b` ve `docker compose exec ollama ollama pull bge-m3`
5. Container terminalinde prosedür indeksini kurun ve kontrol edin:

```bash
PYTHONPATH=src python -m asistan.rag.indeksle --chunk 400 --ortusme 50   # prosedür indeksi (data/indeks/)
python kontrol.py          # ortam kontrolü, hepsi ✅ / ⚠️ olmalı
python eval/calistir.py    # değerlendirme
python demo.py             # asistanı terminalde dene (insan onayı da terminalden sorulur)
```

Mock API container açılınca otomatik başlar (http://localhost:8000/docs). Başlamadıysa:
`uvicorn mock_api.main:app --host 0.0.0.0 --port 8000`

Her haftanın görevleri `haftalar/hafta-N/GOREVLER.md` dosyasındadır:

- Hafta 1: [haftalar/hafta-1/GOREVLER.md](haftalar/hafta-1/GOREVLER.md)
- Hafta 2: [haftalar/hafta-2/GOREVLER.md](haftalar/hafta-2/GOREVLER.md) (sık hatalar dahil)
- Hafta 3: [haftalar/hafta-3/GOREVLER.md](haftalar/hafta-3/GOREVLER.md) (sık hatalar dahil)
- Hafta 4: [haftalar/hafta-4/GOREVLER.md](haftalar/hafta-4/GOREVLER.md) (sık hatalar dahil)

Hafta 4'ten itibaren her haftanın iki dalı var: `hafta-N` (başlangıç, derste buna geçin) ve `hafta-N-cozum` (lab çözümleri).
`main` her zaman bu haftanın başlangıcıyla aynıdır. O haftanın lab görevleri kodda
`# TODO (Lab N):` yorumuyla işaretlidir.

## Klasörler

```
data/          sentetik veriler ve prosedürler (yeniden üretmek için: python data/uret.py)
data/indeks/   prosedür indeksi (FAISS; git'e girmez, indeksle komutuyla kurulur)
logs/izler/    her cevapla() çağrısının maskeli izi (JSONL; git'e girmez)
mock_api/      FastAPI sahte banka servisleri
haftalar/      haftalık klasörler: GOREVLER.md ve notebook'lar
prompts/       istem şablonları (sürümlü: taslak/v1.md, taslak/v2.md), karar kuralları, banka dili rehberi
src/asistan/   asistanın kodu – ortak arayüz: cevapla(talep, musteri_no) -> dict
eval/          değerlendirme setleri, çalıştırıcı, A/B testi, hakem (LLM-as-judge), karne
tests/         model gerektirmeyen birim testleri (python tests/test_maskeleme.py)
demo.py        uçtan uca komut satırı demosu
```
