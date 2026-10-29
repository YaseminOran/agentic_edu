# Proje: Agentic Sistemler Eğitimi – Müşteri Talep ve Şikayet Asistanı

## Bağlam
Bu repo, bir bankanın çalışanlarına verilen 5 haftalık (haftada 1 gün) ileri seviye
agentic sistemler eğitiminin uygulama reposudur. Katılımcılar Python ve temel deep
learning biliyor. Her katılımcı bireysel çalışır. Kod EĞİTİM AMAÇLIDIR: okunabilirlik,
performanstan ve soyutlamadan önce gelir.

Senaryo: Bankaya gelen müşteri taleplerini sınıflandıran, araçlarla bilgi toplayan,
prosedürlerden kaynaklı cevap bulan, banka diline uygun yanıt taslağı hazırlayan ve
riskli durumları insana aktaran bir asistan. Sistem 5 hafta boyunca katman katman büyür.

## Teknoloji yığını (değiştirme, yeni bağımlılık eklemeden önce sor)
- Python 3.12, VS Code Dev Containers, docker-compose (servisler: app, ollama)
- LangChain, LangGraph, langchain-anthropic, langchain-ollama, langchain-mcp-adapters
- Bulut model: Claude (model adı .env'deki CLAUDE_MODEL ve CLAUDE_MODEL_GUCLU'dan okunur)
- Yerel model: Ollama üzerinden qwen3.5:4b (adres .env'deki OLLAMA_URL'den okunur)
- Vektör arama: FAISS (faiss-cpu); embedding modeli .env'deki EMBED_MODEL'den okunur
- Mock servisler: FastAPI + uvicorn
- Demo arayüzü (Hafta 5): Streamlit

## Repo yapısı
.devcontainer/  docker-compose.yml  requirements.txt  .env.example  kontrol.py
data/          sentetik veriler (talepler, musteriler, kart_islemleri, gecmis_talepler, prosedurler/)
mock_api/      FastAPI sahte servisler
notebooks/     keşif notebook'ları (numaralı: 01_isinma.ipynb ...)
src/asistan/   asıl proje kodu
prompts/       prompt şablonları (Hafta 4'ten itibaren)
eval/          test_seti.csv, ortak_set.csv, calistir.py
docs/          haftalık eğitmen notları ve örnek çözümler

## Değişmez kurallar
1. GERÇEK VERİ YOK. Tüm isim, TCKN, kart no, IBAN, tutar sentetik ve açıkça sahte olmalı.
2. API anahtarı, model adı ve adresler asla koda yazılmaz; hepsi .env'den okunur.
   .env asla commit edilmez; .env.example güncel tutulur.
3. Kod içi tanımlayıcılar Türkçe ve ASCII: musteri_bilgisi, kart_islemleri, prosedur_ara.
   Yorumlar ve docstring'ler Türkçe.
4. Her dosyanın başında 2-3 satırlık Türkçe açıklama: ne yapar, hangi haftada eklendi.
5. Ajanlarda adım limiti zorunlu (varsayılan 6). Yazma araçları insan onayı olmadan çalışmaz.
6. Hassas veri modele gönderilmeden önce maskelenir (Hafta 2'den itibaren).
7. Her hafta sonunda `python kontrol.py` ve `python eval/calistir.py` hatasız çalışmalı.
8. Gereksiz soyutlama, sınıf hiyerarşisi veya framework ekleme. Bir katılımcı tek bir
   dosyayı okuyup anlayabilmeli.
9. Windows, Linux ve Mac'te çalışmalı. Mac'te Ollama host'ta çalışır
   (OLLAMA_URL=http://host.docker.internal:11434).

## Değerlendirme formatı (sabit)
eval/test_seti.csv sütunları: id, talep, beklenen_kategori, beklenen_davranis,
kaynak_gerekli, zorluk
- beklenen_kategori: kart | kredi | hesap | dijital_kanal | guvenlik | diger
- beklenen_davranis: yanitla | netlestir | temsilciye_aktar | insan_onayi | reddet
- kaynak_gerekli: evet | hayir
- zorluk: kolay | zor | kotu_niyetli | kapsam_disi
Asistanın ortak arayüzü: `cevapla(talep: str, musteri_no: str) -> dict`
dönen dict: {kategori, davranis, yanit, kaynaklar: list, adimlar: list}

## Git dalları
main = Hafta 1 başlangıç kodu. hafta-1 ... hafta-5 = o haftanın hazır çözümü.
Her hafta bir öncekinin üzerine kurulur.

## Çalışma şekli
- Kod yazmadan önce kısa bir plan sun ve onay bekle.
- Her adımdan sonra çalıştırıp test et; hata varsa düzelt, sonra devam et.
- Bitince: neyi değiştirdiğini, nasıl çalıştırılacağını ve eğitimde vurgulanacak
  noktaları docs/hafta-N.md dosyasına yaz.
