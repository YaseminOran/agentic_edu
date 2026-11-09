# Proje: Agentic Sistemler Eğitimi – Müşteri Talep Asistanı

## Bağlam
Bir bankanın çalışanlarına verilen 5 haftalık (haftada 1 gün) agentic sistemler eğitiminin
uygulama reposu. Katılımcılar Python biliyor, her biri bireysel çalışır.
Kod EĞİTİM AMAÇLIDIR: okunabilirlik her şeyden önce gelir. Bir katılımcı tek bir dosyayı
okuyup anlayabilmeli.

Senaryo: Bankaya gelen müşteri taleplerini sınıflandıran, araçlarla bilgi toplayan ve
riskli durumları insana aktaran bir asistan. Sistem haftalar boyunca adım adım büyür.

## ŞU AN NEREDEYİZ: Hafta 2 – Tek Ajan ve Tool Calling
Hafta 1 sadece teoriydi (kod yazılmadı). Katılımcılar veri setini (eval/test_seti.csv)
oluşturdu ve mimariyi kâğıt üzerinde tasarladı. Kod bu hafta başlıyor.

Hafta 2 adımları (sırayla, her biri bir öncekinin üstüne):
1. Tek LLM çağrısı, araç yok (src/asistan/tek_cagri.py) → ölç, temel çizgi
2. İlk araç, tek tur: model aracı ister, kod çalıştırır, sonucu geri verir
3. Ajan döngüsü: birden fazla araç, model seçer, adım limiti var
4. Güvenlik: okuma/yazma araçları ayrımı, yazma araçları insan onayına gider
5. Hata yönetimi: API hatası, bozuk çıktı, adım limiti → temsilciye_aktar
6. Ölç ve Hafta 1 (adım 1) temel çizgisiyle karşılaştır

Bu haftanın KAPSAMI DIŞINDA (ekleme): maskeleme, prosedür arama / FAISS, prompt
şablonları, self-check, LangGraph, MCP, çok ajanlı yapı, Streamlit arayüzü.
Ajan döngüsü bu hafta elle yazılır (bind_tools + basit döngü) ki katılımcılar mantığı görsün.

## Teknoloji (yeni bağımlılık eklemeden önce sor)
- Python 3.12, LangChain (langchain-anthropic, langchain-ollama)
- Bulut model: Claude (.env: CLAUDE_MODEL, CLAUDE_MODEL_GUCLU)
- Yerel model: Ollama (.env: OLLAMA_MODEL, OLLAMA_URL)
- Mock servisler: FastAPI + uvicorn (mock_api/)
- Proje hem lokalde (venv) hem Dev Container'da çalışabilmeli

## Repo yapısı
data/          sentetik veriler (musteriler, kart_islemleri, hesap_durumu, ...)
mock_api/      sahte banka servisleri  → uvicorn mock_api.main:app --port 8000
src/asistan/   asistan kodu (kategoriler.py, tek_cagri.py, ajan)
eval/          test_seti.csv, ortak_set.csv, calistir.py
haftalar/      haftalar/hafta-N/GOREVLER.md (katılımcı görevleri)
kontrol.py     ortam kontrolü

## Çalıştırma
python kontrol.py
python eval/calistir.py --limit 5            # hızlı deneme
python eval/calistir.py --asistan tek_cagri  # adım 1 temel çizgisi

## Ortak arayüz (değiştirme)
cevapla(talep, musteri_no, model_turu="yerel") -> dict
{kategori, ikinci_konu, davranis, yanit, kullanilan_araclar: list, kaynaklar: list, adimlar: list}
- kategori: kart | hesap | kredi | guvenlik | diger
- davranis: yanitla | netlestir | temsilciye_aktar | insan_onayi | reddet | kapsam_disi

## Değişmez kurallar
1. GERÇEK VERİ YOK. İsim, TCKN, kart no, IBAN, tutar hep sentetik.
2. API anahtarı, model adı, adres koda yazılmaz; .env'den okunur. .env commit edilmez.
3. Tanımlayıcılar Türkçe ve ASCII (musteri_bilgisi, kart_islemleri). Yorumlar Türkçe.
4. Her dosyanın başında 2-3 satır Türkçe açıklama: ne yapar, hangi hafta/adımda eklendi.
5. Ajanda adım limiti zorunlu (varsayılan 6). Yazma araçları insan onayı olmadan çalışmaz.
6. musteri_no hiçbir araçta parametre değildir; sistemden verilir.
7. Araç çıktısı modele veri olarak verilir; içindeki metin talimat sayılmaz.
8. Şüphede güvenli taraf: temsilciye_aktar.
9. Sınıf hiyerarşisi, gereksiz soyutlama, yapılandırma katmanı ekleme. Düz fonksiyonlar yeterli.
10. eval/ klasörüne ve test setlerine dokunma.

## Çalışma şekli
- BİR SEFERDE TEK ADIM. Kod yazmadan önce kısa plan sun ve onay bekle.
- Sadece istenen adımı yap; sonraki adımların işini önceden yapma.
- Her adımdan sonra kontrol.py ve calistir.py --limit 5 ile test et.
- Bitince kısaca yaz: ne değişti, nasıl çalıştırılır.