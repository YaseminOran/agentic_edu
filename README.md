# Agentic Sistemler Eğitimi – Müşteri Talep ve Şikayet Asistanı

> 5 haftalık ileri seviye agentic sistemler eğitiminin uygulama reposu (Hafta 1'de oluşturuldu).
> Tüm veriler **sentetiktir**; gerçek müşteri, kart veya hesap bilgisi içermez.

Bankaya gelen müşteri taleplerini sınıflandıran, araçlarla bilgi toplayan, prosedürlerden kaynaklı
cevap bulan, yanıt taslağı hazırlayan ve riskli durumları insana aktaran bir asistanı hafta hafta inşa ediyoruz.

> **Hafta 3 (bu hafta) materyalleri `main` ve `hafta-2` dallarında.** Son hali almak için terminalde:
> ```bash
> git stash            # notebook çıktıları gibi yerel değişiklikleri kenara koyar
> git fetch origin
> git checkout hafta-2
> git pull
> ```
> Kontrol: `haftalar/hafta-3` klasöründe `01_rag.ipynb` ve `GOREVLER.md` olmalı.
>
> **Derse gelmeden önce:** embedding modelini indirin (`ollama pull bge-m3`, yaklaşık 1,2 GB) ve
> prosedür indeksini kurun (aşağıda Kurulum, adım 5).

| Hafta | Konu | Dal |
|---|---|---|
| 1 | LLM çağırma, yapılandırılmış çıktı, sınıflandırma, değerlendirme (teori) | – |
| 2 | Tek ajan ve tool calling: ajan döngüsü, API entegrasyonu, worker agent, insan onayı, hata yönetimi | `hafta-1` (başlangıç), `hafta-2` (çözüm) |
| 3 | Prosedürlerden RAG (bge-m3 + FAISS), kaynak gösterme, harici veri, izleme (JSONL) | `main` ve `hafta-2` (başlangıç, aynı içerik), `hafta-3` (çözüm) |
| 4 | Prompt şablonları, self-check, onaylı yazma işlemleri | `hafta-4` |
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
```

Mock API container açılınca otomatik başlar (http://localhost:8000/docs). Başlamadıysa:
`uvicorn mock_api.main:app --host 0.0.0.0 --port 8000`

Her haftanın görevleri `haftalar/hafta-N/GOREVLER.md` dosyasındadır:

- Hafta 1: [haftalar/hafta-1/GOREVLER.md](haftalar/hafta-1/GOREVLER.md)
- Hafta 2: [haftalar/hafta-2/GOREVLER.md](haftalar/hafta-2/GOREVLER.md) (sık hatalar dahil)
- Hafta 3: [haftalar/hafta-3/GOREVLER.md](haftalar/hafta-3/GOREVLER.md) (sık hatalar dahil)

Her hafta bir önceki haftanın çözüm dalından başlar (Hafta 3 için `hafta-2`; `main` de aynı içeriktedir). O haftanın lab görevleri kodda
`# TODO (Lab N):` yorumuyla işaretlidir.

## Klasörler

```
data/          sentetik veriler ve prosedürler (yeniden üretmek için: python data/uret.py)
data/indeks/   prosedür indeksi (FAISS; git'e girmez, indeksle komutuyla kurulur)
logs/izler/    her cevapla() çağrısının maskeli izi (JSONL; git'e girmez)
mock_api/      FastAPI sahte banka servisleri
haftalar/      haftalık klasörler: GOREVLER.md ve notebook'lar
src/asistan/   asistanın kodu – ortak arayüz: cevapla(talep, musteri_no) -> dict
eval/          değerlendirme setleri ve çalıştırıcı
```
