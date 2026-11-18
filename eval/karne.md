# Karne: haftadan haftaya asistan

> `python eval/karne.py` ile üretilir; elle düzenlemeyin. Kaynak: `eval/temel_cizgi/`.
> Her hafta **bugünkü** test beklentileriyle yeniden puanlanır (ör. Hafta 4'te T33 `yanitla` oldu).
> Satır sayısı haftadan haftaya artar: test seti her hafta yeni durumlarla büyüdü.

**Nasıl okunur:** Kategori, davranış ve kaynak isabeti yüksek; gizli doküman ve kişisel veri düşük olmalı.
Kişisel veri iki sayıdır: *modele* (modele maskelenmemiş kişisel veri giden satır oranı) / *yanıtta* (müşteriye giden yanıtta tam numara olan satır oranı).
Hafta 1-3'te maskeleme yoktu: kişisel veri döndüren bir araç (musteri_bilgisi, hesap_durumu) çağrıldıysa ya da talepte numara varsa veri modele olduğu gibi gitmiştir. Hafta 4'ten itibaren bu değer izden ölçülür.
Kaynak isabeti Hafta 1-2'de ölçülemez (prosedür araması yoktu).

### test_seti, bulut model

| Hafta | Eklenen katman | Satır | Kategori | Davranış | Kaynak isabeti | Gizli doküman yanıtta | Kişisel veri (modele / yanıtta) | Ort. süre (sn) |
|---|---|---|---|---|---|---|---|---|
| Hafta 1 | Tek LLM çağrısı: sınıflandırma ve yanıt taslağı, araç yok | 30 | %97 | %87 | – (RAG yok) | %0 | %0 / %0 | 4.4 |
| Hafta 2 | Ajan: araçlarla müşteri verisi, insan onayı, hata yönetimi | 30 | %100 | %77 | – (RAG yok) | %0 | %47 / %0 | 10.8 |
| Hafta 3 | RAG: prosedürlerden kaynaklı yanıt, gizli doküman filtresi, izleme | 35 | %100 | %83 | %100 | %0 | %43 / %0 | 10.9 |
| Hafta 4 | Kalite: prompt şablonları, maskeleme (takma ad), self-check, inceltilmiş risk kontrolü | 37 | %100 | %100 | %100 | %0 | %0 / %0 | 14.7 |

### test_seti, yerel model

| Hafta | Eklenen katman | Satır | Kategori | Davranış | Kaynak isabeti | Gizli doküman yanıtta | Kişisel veri (modele / yanıtta) | Ort. süre (sn) |
|---|---|---|---|---|---|---|---|---|
| Hafta 1 | Tek LLM çağrısı: sınıflandırma ve yanıt taslağı, araç yok | 30 | %90 | %67 | – (RAG yok) | %0 | %0 / %0 | 4.6 |
| Hafta 2 | Ajan: araçlarla müşteri verisi, insan onayı, hata yönetimi | 30 | %100 | %57 | – (RAG yok) | %0 | %40 / %3 | 14.5 |
| Hafta 3 | RAG: prosedürlerden kaynaklı yanıt, gizli doküman filtresi, izleme | 35 | %94 | %57 | %89 | %0 | %31 / %3 | 18.8 |
| Hafta 4 | Kalite: prompt şablonları, maskeleme (takma ad), self-check, inceltilmiş risk kontrolü | 37 | %95 | %68 | %90 | %0 | %0 / %0 | 20.8 |

### ortak_set, bulut model

| Hafta | Eklenen katman | Satır | Kategori | Davranış | Kaynak isabeti | Gizli doküman yanıtta | Kişisel veri (modele / yanıtta) | Ort. süre (sn) |
|---|---|---|---|---|---|---|---|---|
| Hafta 1 | Tek LLM çağrısı: sınıflandırma ve yanıt taslağı, araç yok | 10 | %90 | %70 | – (RAG yok) | %0 | %0 / %0 | 4.6 |
| Hafta 2 | Ajan: araçlarla müşteri verisi, insan onayı, hata yönetimi | 10 | %90 | %70 | – (RAG yok) | %0 | %40 / %0 | 9.8 |
| Hafta 3 | RAG: prosedürlerden kaynaklı yanıt, gizli doküman filtresi, izleme | 10 | %90 | %80 | %100 | %0 | %40 / %0 | 8.9 |
| Hafta 4 | Kalite: prompt şablonları, maskeleme (takma ad), self-check, inceltilmiş risk kontrolü | 10 | %90 | %90 | %100 | %0 | %0 / %0 | 9.7 |

### ortak_set, yerel model

| Hafta | Eklenen katman | Satır | Kategori | Davranış | Kaynak isabeti | Gizli doküman yanıtta | Kişisel veri (modele / yanıtta) | Ort. süre (sn) |
|---|---|---|---|---|---|---|---|---|
| Hafta 1 | Tek LLM çağrısı: sınıflandırma ve yanıt taslağı, araç yok | 10 | %80 | %50 | – (RAG yok) | %0 | %0 / %0 | 4.0 |
| Hafta 2 | Ajan: araçlarla müşteri verisi, insan onayı, hata yönetimi | 10 | %90 | %70 | – (RAG yok) | %0 | %50 / %0 | 28.3 |
| Hafta 3 | RAG: prosedürlerden kaynaklı yanıt, gizli doküman filtresi, izleme | 10 | %90 | %70 | %100 | %0 | %50 / %0 | 13.3 |
| Hafta 4 | Kalite: prompt şablonları, maskeleme (takma ad), self-check, inceltilmiş risk kontrolü | 10 | %90 | %70 | %100 | %0 | %0 / %0 | 15.6 |
