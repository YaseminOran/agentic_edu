# Agentic Sistemler Eğitimi – Müşteri Talep ve Şikayet Asistanı

> 5 haftalık ileri seviye agentic sistemler eğitiminin uygulama reposu (Hafta 1'de oluşturuldu).
> Tüm veriler **sentetiktir**; gerçek müşteri, kart veya hesap bilgisi içermez.

Bankaya gelen müşteri taleplerini sınıflandıran, araçlarla bilgi toplayan, prosedürlerden kaynaklı
cevap bulan, yanıt taslağı hazırlayan ve riskli durumları insana aktaran bir asistanı hafta hafta inşa ediyoruz.

> **Hafta 2 (bu hafta) materyalleri `hafta-1` dalında.** Terminalde:
> ```bash
> git stash            # notebook çıktıları gibi yerel değişiklikleri kenara koyar
> git fetch origin
> git checkout hafta-1
> git pull
> ```
> Kontrol: `haftalar/hafta-2` klasöründe üç notebook olmalı (`01_tool_calling`, `02_ajan_adim_adim`, `03_olc_ve_tartis`).

| Hafta | Konu | Dal |
|---|---|---|
| 1 | LLM çağırma, yapılandırılmış çıktı, sınıflandırma, değerlendirme | `main` (başlangıç), `hafta-1` (çözüm) |
| 2 | Tek ajan ve tool calling: ajan döngüsü, API entegrasyonu, worker agent, insan onayı, hata yönetimi | `hafta-1` (başlangıç), `hafta-2` (çözüm) |
| 3 | Prosedürlerden RAG (FAISS), kaynak gösterme | `hafta-3` |
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
   - Mac (host terminalinde): `ollama pull qwen3.5:4b && ollama pull nomic-embed-text`
   - Windows/Linux: `docker compose exec ollama ollama pull qwen3.5:4b` ve `docker compose exec ollama ollama pull nomic-embed-text`
5. Container terminalinde kontrol edin:

```bash
python kontrol.py          # ortam kontrolü, hepsi ✅ / ⚠️ olmalı
python eval/calistir.py    # değerlendirme
```

Mock API container açılınca otomatik başlar (http://localhost:8000/docs). Başlamadıysa:
`uvicorn mock_api.main:app --host 0.0.0.0 --port 8000`

Her haftanın görevleri `haftalar/hafta-N/GOREVLER.md` dosyasındadır:

- Hafta 1: [haftalar/hafta-1/GOREVLER.md](haftalar/hafta-1/GOREVLER.md)
- Hafta 2 (`hafta-1` dalında): [haftalar/hafta-2/GOREVLER.md](https://github.com/YaseminOran/agentic_edu/blob/hafta-1/haftalar/hafta-2/GOREVLER.md) (sık hatalar dahil)

Her hafta bir önceki haftanın çözüm dalından başlar (Hafta 2 için `hafta-1`). O haftanın lab görevleri kodda
`# TODO (Lab N):` yorumuyla işaretlidir.

## Klasörler

```
data/          sentetik veriler ve prosedürler (yeniden üretmek için: python data/uret.py)
mock_api/      FastAPI sahte banka servisleri
haftalar/      haftalık klasörler: GOREVLER.md ve notebook'lar
src/asistan/   asistanın kodu – ortak arayüz: cevapla(talep, musteri_no) -> dict
tests/         birim testleri, Hafta 2'den itibaren (python tests/test_maskeleme.py)
prompts/       prompt şablonları (Hafta 4'ten itibaren)
eval/          değerlendirme setleri ve çalıştırıcı
```
