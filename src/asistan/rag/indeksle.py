"""Prosedür dokümanlarını parçalayıp vektörleştirir ve FAISS indeksine kaydeder (Hafta 3, adım 2).
Akış: doküman oku (frontmatter + gövde) -> "## " başlıklarına göre böl -> uzun bölümleri örtüşmeli parçala
-> EMBED_MODEL (Ollama, bge-m3) ile vektörleştir -> data/indeks/ altına kaydet.

Kullanım (proje kökünden):
  PYTHONPATH=src python -m asistan.rag.indeksle --chunk 400 --ortusme 50
Doküman ekleyince, sildikten sonra veya EMBED_MODEL değişince yeniden çalıştırın.
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np

from asistan.ayarlar import PROJE_KOKU, ayar, embedding_getir
from asistan.kategoriler import KATEGORILER, PROSEDUR_KOKU

INDEKS_KLASORU = PROJE_KOKU / "data" / "indeks"
INDEKS_DOSYASI = INDEKS_KLASORU / "prosedurler.faiss"   # vektörler
PARCA_DOSYASI = INDEKS_KLASORU / "parcalar.json"        # parça metinleri + metadata (vektörle aynı sırada)


# ---------------------------------------------------------------------------
# 1) Dokümanı oku: frontmatter (metadata) ve gövde
# ---------------------------------------------------------------------------

def dokuman_oku(yol: Path) -> tuple[dict, str]:
    """Dosyanın başındaki --- ... --- bloğunu sözlüğe çevirir, kalan gövdeyi döner.
    (YAML kütüphanesi gerekmez: her satır "anahtar: değer".)"""
    metin = yol.read_text(encoding="utf-8")
    eslesme = re.match(r"^---\n(.*?)\n---\n(.*)$", metin, re.DOTALL)
    if not eslesme:
        raise ValueError(f"{yol}: dosyanın başında --- ile ayrılmış metadata yok")
    metadata = {}
    for satir in eslesme.group(1).splitlines():
        anahtar, _, deger = satir.partition(":")
        metadata[anahtar.strip()] = deger.strip()
    for alan in ("kategori", "baslik", "gizlilik", "guncelleme_tarihi"):
        if not metadata.get(alan):
            raise ValueError(f"{yol}: metadata'da '{alan}' eksik")
    if metadata["gizlilik"] not in ("musteri", "ic"):
        raise ValueError(f"{yol}: gizlilik 'musteri' veya 'ic' olmalı, bulunan: {metadata['gizlilik']}")
    return metadata, eslesme.group(2)


# ---------------------------------------------------------------------------
# 2) Parçalama: önce başlıklar, sonra boyut
# ---------------------------------------------------------------------------

def basliklara_bol(govde: str) -> list[tuple[str, str]]:
    """Gövdeyi "## " başlıklarına göre bölümlere ayırır: [(baslik, metin), ...].
    İlk "## " başlığından önceki kısım (doküman adı ve "kurgusal belge" notu) atlanır."""
    bolumler = []
    for blok in re.split(r"^## ", govde, flags=re.MULTILINE)[1:]:
        baslik, _, metin = blok.partition("\n")
        if metin.strip():
            bolumler.append((baslik.strip(), metin.strip()))
    return bolumler


def parcala(metin: str, boyut: int, ortusme: int) -> list[str]:
    """Bölüm `boyut` karakterden kısaysa tek parça döner. Uzunsa boyut karakterlik pencerelerle böler;
    her yeni parça bir öncekinin son `ortusme` karakterini tekrar eder (bilgi sınırda kesilmesin).
    Kelimenin ortasından kesmemek için pencere sınırları boşluğa çekilir."""
    if len(metin) <= boyut:
        return [metin]
    parcalar, bas = [], 0
    while True:
        son = min(bas + boyut, len(metin))
        if son < len(metin):  # son kelimeyi bölmemek için geriye, son boşluğa çekil
            bosluk = max(metin.rfind(" ", bas, son), metin.rfind("\n", bas, son))
            if bosluk > bas:
                son = bosluk
        parcalar.append(metin[bas:son].strip())
        if son >= len(metin):
            return parcalar
        yeni_bas = max(son - ortusme, bas + 1)
        bosluk = metin.find(" ", yeni_bas, son)  # örtüşme de kelime başından başlasın
        bas = bosluk + 1 if bosluk != -1 else yeni_bas


def dokumani_parcala(yol: Path, boyut: int, ortusme: int) -> list[dict]:
    """Bir dokümanın tüm parçaları; her parça metadata'sını yanında taşır (filtre ve kaynak gösterimi için)."""
    metadata, govde = dokuman_oku(yol)
    dosya = yol.relative_to(PROSEDUR_KOKU).as_posix()   # ör. "hesap/isletim_ucreti.md"
    parcalar = []
    for baslik, bolum_metni in basliklara_bol(govde):
        for no, parca in enumerate(parcala(bolum_metni, boyut, ortusme), start=1):
            parcalar.append({
                "kaynak": f"{dosya}#{baslik}",            # yanıttaki [kaynak: ...] etiketi bu olacak
                "dosya": dosya,
                "baslik": baslik,                         # bölüm başlığı
                "dokuman": metadata["baslik"],            # doküman başlığı
                "kategori": metadata["kategori"],
                "gizlilik": metadata["gizlilik"],
                "guncelleme_tarihi": metadata["guncelleme_tarihi"],
                "parca_no": no,
                "metin": parca,
            })
    return parcalar


def embedding_metni(parca: dict) -> str:
    """Vektörleştirilen metin: parçanın başına doküman ve bölüm adı eklenir. "%1'idir" gibi kısa bir parça
    tek başına anlamsızdır; "Kredi Erken Kapama / Erken kapama ücreti" bağlamıyla aranabilir olur."""
    return f"{parca['dokuman']} / {parca['baslik']}\n{parca['metin']}"


# ---------------------------------------------------------------------------
# 3) Vektörleştir ve kaydet
# ---------------------------------------------------------------------------

def indeksle(boyut: int = 400, ortusme: int = 50) -> list[dict]:
    """Ajan kategorilerinin (kart, hesap, kredi) prosedür klasörlerini indeksler ve parçaları döner."""
    if not 0 <= ortusme < boyut:
        raise ValueError("örtüşme 0 ile chunk boyutu arasında olmalı")
    parcalar = []
    for kategori, ayarlar in KATEGORILER.items():
        for yol in sorted(ayarlar["prosedur_klasoru"].glob("*.md")):
            dokuman_parcalari = dokumani_parcala(yol, boyut, ortusme)
            if dokuman_parcalari and dokuman_parcalari[0]["kategori"] != kategori:
                raise ValueError(f"{yol}: metadata kategorisi klasörle uyuşmuyor")
            parcalar += dokuman_parcalari

    # Vektörleri birim uzunluğa getirip iç çarpım (IP) indeksi kullanıyoruz: iç çarpım = kosinüs benzerliği.
    # Skor 1'e yaklaştıkça anlam yakın; ~0 ilgisiz.
    vektorler = np.array(embedding_getir().embed_documents([embedding_metni(p) for p in parcalar]), dtype="float32")
    faiss.normalize_L2(vektorler)
    indeks = faiss.IndexFlatIP(vektorler.shape[1])  # "Flat": her sorguda tüm vektörlere bakar; küçük veri için ideal
    indeks.add(vektorler)

    INDEKS_KLASORU.mkdir(parents=True, exist_ok=True)
    faiss.write_index(indeks, str(INDEKS_DOSYASI))
    PARCA_DOSYASI.write_text(json.dumps({
        "embed_model": ayar("EMBED_MODEL"), "chunk": boyut, "ortusme": ortusme,
        "olusturma": datetime.now().isoformat(timespec="seconds"), "parcalar": parcalar,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return parcalar


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prosedür dokümanlarını FAISS indeksine kaydeder")
    parser.add_argument("--chunk", type=int, default=400, help="parça boyutu (karakter)")
    parser.add_argument("--ortusme", type=int, default=50, help="ardışık parçalar arasındaki örtüşme (karakter)")
    args = parser.parse_args()

    parcalar = indeksle(args.chunk, args.ortusme)
    print(f"{len(parcalar)} parça indekslendi (chunk={args.chunk}, ortusme={args.ortusme}, "
          f"model={ayar('EMBED_MODEL')}) -> {INDEKS_KLASORU.relative_to(PROJE_KOKU)}/")
    for dosya, sayi in Counter(p["dosya"] for p in parcalar).items():
        gizli = " (ic)" if any(p["gizlilik"] == "ic" for p in parcalar if p["dosya"] == dosya) else ""
        print(f"  {sayi:>2} parça  {dosya}{gizli}")
