"""Asistanın LangGraph akışı (Hafta 2; Hafta 3'te RAG ve izleme; Hafta 4'te şablonlar, maskeleme ve self-check):
sınıflandırma -> kategoriye göre araç seti -> ajan döngüsü (prosedur_ara dahil) -> kaynaklı yanıt taslağı
-> self-check (gerekirse bir kez yeniden yaz) -> risk kontrolü -> insan onayı -> sonuç.
İstemler prompts/ altındaki şablonlardan gelir (sablonlar.py). Modele giden her metin maskelidir (maskeleme.py);
müşteriye giden yanıt takma adlardan güvenli gösterime çevrilir. Her çalıştırmanın izi logs/izler/ altına yazılır.

Komut satırından deneme (insan onayını terminalden sorar):
  python -m asistan.ajan "Kartımdan aidat iki kez kesildi" M0007 [--model bulut] [--guvensiz]
"""

import re
import sys
import uuid
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from asistan.araclar import OKUMA_ARACLARI, ApiHatasi, iade_talebi_olustur, musteri_oturumu, temsilciye_aktar
from asistan.ayarlar import model_getir
from asistan.geri_bildirim import geri_bildirim_kaydet
from asistan.gunluk import log
from asistan.izleme import IzToplayici, iz_kaydi
from asistan.kategoriler import AJANA_GITMEYENLER, KATEGORILER
from asistan.maskeleme import geri_cevir, maske_oturumu, metni_maskele
from asistan.rag.arama import baglam_olustur
from asistan.sablonlar import hazir_cumle, mesajlar
from asistan.self_check import deterministik_kontroller, elestir, elestiri_gecti_mi, kucuk_harf
from asistan.siniflandirici import siniflandir

ADIM_LIMITI = 6          # ajan döngüsünde en fazla kaç model çağrısı (kural 5)
GUVEN_ESIGI = 0.6        # sınıflandırma güveni bunun altındaysa netleştirme sorulur
NETLESTIRME_LIMITI = 1   # aynı oturumda en fazla kaç kez netleştirme sorulur, sonra temsilci
YENIDEN_YAZIM_LIMITI = 1 # self-check geçmezse taslak en fazla kaç kez yeniden yazılır, sonra temsilci

# Hazır cümleler prompts/kurallar.md'den gelir (tek yerde, okunur)
NETLESTIRME_SORUSU = hazir_cumle("netlestir")
TEMSILCI_YANITI = hazir_cumle("temsilci")


# ---------------------------------------------------------------------------
# Durum (state): grafın düğümleri arasında taşınan tek sözlük
# ---------------------------------------------------------------------------

class Durum(TypedDict, total=False):
    talep: str                  # bu turdaki talep
    talepler: list[str]         # netleştirme turu dahil oturumdaki talepler
    musteri_no: str
    kategori: str
    ikinci_konu: str
    guven: float
    netlestirme_sayisi: int
    mesajlar: list              # ajan döngüsünün mesaj geçmişi
    adim_sayisi: int            # ajan döngüsündeki model çağrısı sayısı
    kullanilan_araclar: list[str]
    getirilen_parcalar: list[dict]  # prosedur_ara'nın bu turda getirdiği parçalar (skorlarıyla)
    kaynaklar: list[str]        # yanıtta geçerli atıfla anılan kaynaklar (dosya#başlık)
    uydurma_kaynaklar: list[str]  # modelin gösterdiği ama kendisine verilmemiş kaynaklar
    taslak: dict                # yanıt taslağı (Taslak modelinin sözlük hali; takma adlı, modelin gördüğü hal)
    musteri_yaniti: str         # taslağın müşteriye gidecek hali (güvenli gösterim + okunur kaynak)
    self_check: dict            # son self-check sonucu: gecti, sorunlar, taahhut
    duzeltme: str               # self-check geçmediyse taslağa giden düzeltme notu
    yeniden_yazim: int          # bu turda taslak kaç kez yeniden yazıldı
    risk_nedenleri: list[str]
    aktarim_nedeni: str
    davranis: str
    yanit: str
    adimlar: list[str]          # okunabilir iz: her düğüm bir satır ekler


def adim_ekle(durum: Durum, metin: str) -> list[str]:
    """Adımı hem loga yazar hem de durumdaki adım listesine ekler (yeni listeyi döner)."""
    log.info("[%s] %s", durum.get("musteri_no", "?"), metin)
    return durum.get("adimlar", []) + [metin]


# ---------------------------------------------------------------------------
# 1) Yeni tur ve 2) sınıflandırma
# ---------------------------------------------------------------------------

def baslat_dugumu(durum: Durum) -> dict:
    """Yeni bir tur başlar: talep kaydedilir, önceki turdan kalan alanlar sıfırlanır."""
    talep = durum["talep"]
    # Önceki tur netleştirme sorusuyla bittiyse yeni mesaj aynı talebin devamıdır
    onceki = durum.get("talepler", []) if durum.get("davranis") == "netlestir" else []
    yeni = {"talep": talep, "talepler": onceki + [talep], "adimlar": [], "kullanilan_araclar": [],
            "getirilen_parcalar": [], "kaynaklar": [], "uydurma_kaynaklar": [], "taslak": {}, "musteri_yaniti": "",
            "self_check": {}, "duzeltme": "", "yeniden_yazim": 0, "risk_nedenleri": [], "aktarim_nedeni": "",
            "davranis": "", "yanit": ""}
    if not onceki:
        yeni["netlestirme_sayisi"] = 0
    yeni["adimlar"] = adim_ekle({**durum, **yeni}, f"talep: {talep}")
    return yeni


def siniflandir_dugumu(durum: Durum, config: RunnableConfig) -> Command[
        Literal["hazir_yanit", "netlestir", "temsilciye_aktar", "ajan_hazirla"]]:
    """Talebi sınıflandırır ve yolu seçer. Command = durumu güncelle + sonraki düğümü seç."""
    sonuc = siniflandir("\n".join(durum["talepler"]), config["configurable"].get("model_turu", "yerel"))
    ikinci = "" if sonuc.ikinci_konu == "yok" else sonuc.ikinci_konu
    guncelleme = {
        "kategori": sonuc.kategori, "ikinci_konu": ikinci, "guven": sonuc.guven,
        "adimlar": adim_ekle(durum, f"siniflandirma: {sonuc.kategori} (ikinci: {ikinci or '-'}, "
                                    f"guven: {sonuc.guven:.2f}) - {sonuc.gerekce}"),
    }
    if sonuc.kategori == "guvenlik":           # güvenlik her zaman önce: güven düşük olsa da reddedilir
        hedef = "hazir_yanit"
    elif sonuc.guven < GUVEN_ESIGI:            # belirsiz: önce netleştir, ikinci kez de belirsizse temsilci
        if durum.get("netlestirme_sayisi", 0) >= NETLESTIRME_LIMITI:
            guncelleme["aktarim_nedeni"] = "netleştirmeden sonra da talep belirsiz"
            hedef = "temsilciye_aktar"
        else:
            hedef = "netlestir"
    elif sonuc.kategori in AJANA_GITMEYENLER:  # diger -> hazır kapsam dışı yanıtı
        hedef = "hazir_yanit"
    else:
        hedef = "ajan_hazirla"
    return Command(update=guncelleme, goto=hedef)


def hazir_yanit_dugumu(durum: Durum) -> dict:
    """Ajana gitmeyen kategoriler (guvenlik, diger): araç yok, model yok, hazır yanıt."""
    ayar = AJANA_GITMEYENLER[durum["kategori"]]
    if durum["kategori"] == "guvenlik":
        # "Reddet ve kaydet": güvenlik olayı ayrı bir uyarı satırı olarak loglanır
        log.warning("GUVENLIK OLAYI musteri=%s talep=%r", durum["musteri_no"], durum["talep"])
    return {"davranis": ayar["davranis"], "yanit": ayar["hazir_yanit"],
            "adimlar": adim_ekle(durum, f"hazir yanit: {ayar['davranis']}")}


def netlestir_dugumu(durum: Durum) -> dict:
    """Müşteriye tek bir netleştirme sorusu sorar. Soru ajandan geldiyse onu, yoksa genel soruyu kullanır."""
    soru = durum.get("musteri_yaniti") or NETLESTIRME_SORUSU
    return {"davranis": "netlestir", "yanit": soru,
            "netlestirme_sayisi": durum.get("netlestirme_sayisi", 0) + 1,
            "adimlar": adim_ekle(durum, "netlestirme sorusu soruldu")}


# ---------------------------------------------------------------------------
# 3) Kategoriye göre araç seti ve 4) ajan döngüsü
# ---------------------------------------------------------------------------

def arac_setini_sec(durum: Durum, havuz: dict) -> dict:
    """Kategorinin (ve varsa ikinci konunun) araç listesini havuzdan seçer: {ad: arac}."""
    adlar = list(KATEGORILER[durum["kategori"]]["araclar"])
    if durum.get("ikinci_konu") in KATEGORILER:  # iki konulu talepte ikinci konunun araçları da eklenir
        adlar += [a for a in KATEGORILER[durum["ikinci_konu"]]["araclar"] if a not in adlar]
    return {ad: havuz[ad] for ad in adlar if ad in havuz}


def arama_kategorileri(durum: Durum) -> list[str]:
    """prosedur_ara'nın arayabileceği kategoriler: talebin kategorisi (+ varsa ikinci konusu).
    Sistem belirler, model değil (musteri_no gibi)."""
    return [k for k in (durum["kategori"], durum.get("ikinci_konu")) if k in KATEGORILER]


def ajan_hazirla_dugumu(durum: Durum, config: RunnableConfig) -> dict:
    araclar = arac_setini_sec(durum, config["configurable"]["arac_havuzu"])
    ek = ""
    if config["configurable"].get("guvensiz"):
        # GÜVENSİZ DENEY: naif tasarımlarda müşteri no prompta yazılır ve araç parametresi olur
        ek = f"\n- Aktif müşteri numarası: {durum['musteri_no']}. Araçlara bu numarayı ver."
    # İstem prompts/ajan/<sürüm>.md şablonundan gelir; talep zaten maskelidir (cevapla)
    (_, sistem), (_, kullanici) = mesajlar(
        "ajan", config["configurable"].get("model_turu", "yerel"), kategori=durum["kategori"],
        ikinci_konu=durum.get("ikinci_konu") or "yok", ek=ek, talep="\n".join(durum["talepler"]))
    return {
        "mesajlar": [SystemMessage(sistem), HumanMessage(kullanici)],
        "adim_sayisi": 0,
        "adimlar": adim_ekle(durum, f"arac seti ({durum['kategori']}): {', '.join(araclar)}"),
    }


def ajan_dugumu(durum: Durum, config: RunnableConfig) -> Command[Literal["arac_calistir", "taslak", "temsilciye_aktar"]]:
    """Modeli araçlarla çağırır. Araç istediyse arac_calistir'a, istemediyse taslak'a gider."""
    if durum["adim_sayisi"] >= ADIM_LIMITI:
        return Command(goto="temsilciye_aktar", update={
            "aktarim_nedeni": f"adım limiti ({ADIM_LIMITI}) aşıldı",
            "adimlar": adim_ekle(durum, f"adim limiti ({ADIM_LIMITI}) asildi")})

    araclar = arac_setini_sec(durum, config["configurable"]["arac_havuzu"])
    model = model_getir(config["configurable"].get("model_turu", "yerel")).bind_tools(list(araclar.values()))
    adim = durum["adim_sayisi"] + 1
    try:
        cevap: AIMessage = model.invoke(durum["mesajlar"])
    except Exception as e:  # ör. Ollama'nın bozuk araç çağrısını ayrıştıramaması: güvenli taraf
        return Command(goto="temsilciye_aktar", update={
            "aktarim_nedeni": f"model hatası: {type(e).__name__}",
            "adimlar": adim_ekle(durum, f"ajan adim {adim}: model hatasi ({type(e).__name__}: {str(e)[:100]})")})

    cagrilar = [f"{c['name']}({c['args']})" for c in cevap.tool_calls]
    cagrilar += [f"GECERSIZ:{c.get('name')}" for c in cevap.invalid_tool_calls]
    metin = f"ajan adim {adim}: " + (", ".join(cagrilar) if cagrilar else "arac cagrisi yok, bulgular yazildi")
    guncelleme = {"mesajlar": durum["mesajlar"] + [cevap], "adim_sayisi": adim, "adimlar": adim_ekle(durum, metin)}
    hedef = "arac_calistir" if (cevap.tool_calls or cevap.invalid_tool_calls) else "taslak"
    return Command(update=guncelleme, goto=hedef)


def arac_calistir_dugumu(durum: Durum, config: RunnableConfig) -> Command[Literal["ajan", "temsilciye_aktar"]]:
    """Modelin istediği araçları çalıştırır. Geçersiz çağrıları ÇALIŞTIRMAZ, hatayı modele bildirir.
    (LangGraph'ın hazır ToolNode'u da var; burada ne olduğunu görmek için elle yazıyoruz.)"""
    araclar = arac_setini_sec(durum, config["configurable"]["arac_havuzu"])
    son: AIMessage = durum["mesajlar"][-1]
    yeni_mesajlar, kullanilan, adimlar = [], list(durum.get("kullanilan_araclar", [])), durum["adimlar"]
    getirilen = list(durum.get("getirilen_parcalar", []))

    # Daha önce yapılmış çağrılar (ad + parametre): küçük modeller aynı aracı tekrar tekrar çağırabiliyor
    onceki_cagrilar = {(c["name"], str(c["args"])) for m in durum["mesajlar"][:-1]
                       if isinstance(m, AIMessage) for c in m.tool_calls}

    for cagri in son.tool_calls:
        ad, kimlik = cagri["name"], cagri["id"]
        if (ad, str(cagri["args"])) in onceki_cagrilar:
            icerik = f"Bu aracı ({ad}) aynı parametrelerle zaten çağırdın; sonucu yukarıda. Bulgularını yaz."
            adimlar = adim_ekle({**durum, "adimlar": adimlar}, f"tekrar eden cagri calistirilmadi: {ad}")
        elif ad not in araclar:
            # Ya hiç olmayan bir araç uydurdu ya da bu kategoride izinli olmayan bir aracı istedi
            icerik = (f"HATA: '{ad}' adında izinli bir araç yok. Kullanabileceğin araçlar: "
                      f"{', '.join(araclar)}. Geçerli bir araç kullan ya da bulgularını yaz.")
            adimlar = adim_ekle({**durum, "adimlar": adimlar}, f"gecersiz arac reddedildi: {ad}")
        else:
            try:
                with musteri_oturumu(durum["musteri_no"], arama_kategorileri(durum)):
                    # Araca çağrının tamamı (ToolCall) verilince ToolMessage döner; prosedur_ara'nın
                    # parça listesi (artifact) bu mesajın .artifact alanında gelir, modele gitmez.
                    arac_mesaji = araclar[ad].invoke({**cagri, "type": "tool_call"})
                icerik = arac_mesaji.content
                kullanilan.append(ad)
                if ad == "prosedur_ara":
                    getirilen += arac_mesaji.artifact or []
                    kaynaklar = ", ".join(f"{p['kaynak']} ({p['skor']:.2f})" for p in arac_mesaji.artifact or [])
                    adimlar = adim_ekle({**durum, "adimlar": adimlar}, f"prosedur_ara: {kaynaklar or 'ilgili parça yok'}")
            except ApiHatasi as e:
                # Yeniden denemeler de başarısız: güvenli taraf, temsilciye aktar
                return Command(goto="temsilciye_aktar", update={
                    "kullanilan_araclar": kullanilan, "aktarim_nedeni": f"araç hatası: {e}",
                    "adimlar": adim_ekle({**durum, "adimlar": adimlar}, f"arac hatasi ({ad}): {e}")})
            except Exception as e:  # parametre doğrulama hatası vb.: aracı çalıştırmadan modele bildir
                icerik = f"HATA: '{ad}' aracının parametreleri geçersiz: {str(e)[:200]}. Düzeltip tekrar dene."
                adimlar = adim_ekle({**durum, "adimlar": adimlar}, f"gecersiz parametre ({ad})")
        yeni_mesajlar.append(ToolMessage(content=icerik, tool_call_id=kimlik, name=ad))

    for cagri in son.invalid_tool_calls:  # JSON'u bozuk araç çağrıları (küçük modellerde olur)
        yeni_mesajlar.append(ToolMessage(
            content="HATA: Araç çağrın okunamadı (geçersiz JSON). Aracı geçerli parametrelerle tekrar çağır.",
            tool_call_id=cagri.get("id") or f"gecersiz-{uuid.uuid4().hex[:6]}", name=cagri.get("name") or "bilinmiyor"))
        adimlar = adim_ekle({**durum, "adimlar": adimlar}, "okunamayan arac cagrisi modele bildirildi")

    return Command(goto="ajan", update={"mesajlar": durum["mesajlar"] + yeni_mesajlar, "kullanilan_araclar": kullanilan,
                                        "getirilen_parcalar": getirilen, "adimlar": adimlar})


# ---------------------------------------------------------------------------
# 5) Yanıt taslağı
# ---------------------------------------------------------------------------

class Taslak(BaseModel):
    """Ajanın bulgularından üretilen yanıt taslağı ve karar."""

    gerekce: str = Field(description="Kararın tek cümlelik gerekçesi")
    karar: Literal["yanitla", "netlestir", "temsilciye_aktar"] = Field(description="Kurallara göre karar")
    yanit: str = Field(description="Müşteriye gidecek yanıt taslağı (Türkçe, en fazla 4 cümle). Prosedürden alınan "
                                   "her bilginin arkasında [kaynak: dosya#başlık] etiketi olmalı")
    kaynaklar: list[str] = Field(default_factory=list, description="Yanıtta kullandığın prosedür kaynakları, parça "
                                 "etiketlerinden aynen (ör. hesap/isletim_ucreti.md#Muafiyetler). Prosedür kullanmadıysan boş")
    iade_islem_id: str = Field(default="", description="İade gerekiyorsa verilerdeki islem_id alanı (ör. I00123); mükerrer çekimde İKİNCİ işlemin numarası. Yoksa boş")
    iade_tutari: float = Field(default=0, description="İade gerekiyorsa tutarı (TL); yoksa 0")


KAYNAK_ETIKETI = re.compile(r"\s*\[kaynak:\s*([^\]]+)\]")


def kaynak_etiketlerini_cikar(metin: str) -> str:
    """Yanıttaki [kaynak: ...] etiketlerini siler. Risk kontrolü bu metne bakar: "...#Aidat iadesi talebi"
    gibi bir başlık adı yanıtta "iade" sözü varmış gibi onayı tetiklemesin."""
    return KAYNAK_ETIKETI.sub("", metin)


def kaynaklari_dogrula(yanit: str, beyan_edilen: list[str], baglam: list[dict]) -> tuple[str, list[str], list[str]]:
    """Yanıttaki atıfları (ve modelin kaynaklar alanında beyan ettiklerini) taslağa verilen parçalarla
    karşılaştırır. Döner: (yanıt, geçerli kaynaklar, uydurma kaynaklar). Uydurma atıf yanıttan silinir
    (self-check bunu bir sorun olarak raporlar ve taslağı yeniden yazdırır).
    Sadece dosya adı yazılmışsa (başlıksız) ve o dosyadan parça verilmişse geçerli sayılır.
    Küçük modeller bazen yanıta etiket koymayı unutup sadece kaynaklar alanını doldurur; o zaman geçerli
    kaynaklar yanıtın sonuna eklenir ki müşteri yine kaynağı görsün."""
    verilen = {p["kaynak"] for p in baglam} | {p["dosya"] for p in baglam}
    gecerli, uydurma = [], []

    def kontrol_et(eslesme: re.Match) -> str:
        kaynak = eslesme.group(1).strip()
        if kaynak in verilen:
            gecerli.append(kaynak)
            return eslesme.group(0)
        uydurma.append(kaynak)
        return ""

    temiz = KAYNAK_ETIKETI.sub(kontrol_et, yanit)
    if not gecerli:  # yanıtta geçerli etiket yok: kaynaklar alanına bak
        for kaynak in beyan_edilen:
            (gecerli if kaynak.strip() in verilen else uydurma).append(kaynak.strip())
        if gecerli:
            temiz = temiz.rstrip() + " " + " ".join(f"[kaynak: {k}]" for k in dict.fromkeys(gecerli))
    return temiz, list(dict.fromkeys(gecerli)), list(dict.fromkeys(uydurma))


def prosedur_metni(baglam: list[dict]) -> str:
    """Taslağa giden prosedür bölümü: her parça kendi <prosedur kaynak="..."> bloğunda (Hafta 4).
    Parça metni de maskelenir: prosedürde bir örnek numara olsa bile modele takma adla gider."""
    if not baglam:
        return "(prosedür parçası yok: kural, ücret, süre iddia etme)"
    return "\n\n".join(f'<prosedur kaynak="{p["kaynak"]}">\n{metni_maskele(p["metin"])}\n</prosedur>'
                       for p in baglam)


def taslak_baglami(durum: Durum) -> dict:
    """Taslak ve self-check şablonlarının yer tutucuları. İkisi de AYNI bağlamı görür: self-check, taslağı
    yazan modelin gördüğünden fazlasını ya da azını görmemeli. Hepsi maskelidir."""
    araclar = [m for m in durum["mesajlar"] if isinstance(m, ToolMessage) and m.name != "prosedur_ara"]
    musteri = [m.text for m in araclar if m.name != "doviz_kuru"]
    harici = [m.text for m in araclar if m.name == "doviz_kuru"]
    son = durum["mesajlar"][-1]
    return {
        "talep": "\n".join(durum["talepler"]),
        "kategori": durum["kategori"],
        "ikinci_konu": durum.get("ikinci_konu") or "yok",
        "musteri_ozeti": "\n".join(musteri) or "(müşteri verisi toplanmadı)",
        "harici_veri": "\n".join(harici) or "(harici veri yok)",
        "prosedur_parcalari": prosedur_metni(baglam_olustur(durum.get("getirilen_parcalar", []))),
        "ajan_notu": metni_maskele(son.text) if isinstance(son, AIMessage) and son.text else "(not yok)",
    }


def musteriye_hazirla(yanit: str, kaynaklar: list[str], baglam: list[dict]) -> str:
    """Taslağı müşteriye gidecek hale getirir (Hafta 4):
    1) [kaynak: dosya#başlık] etiketleri metinden çıkar, yanıtın sonuna okunur kaynak satırı eklenir
       ("Kaynak: Kart Aidatı – Aidat iadesi talebi"). İç format kaynaklar alanında ve izde kalır.
    2) Takma adlar güvenli gösterime çevrilir: [KART_1] -> "0007 ile biten kartınız"."""
    metin = geri_cevir(kaynak_etiketlerini_cikar(yanit)).strip()
    okunur = {p["kaynak"]: f"{p['dokuman']} – {p['baslik']}" for p in baglam}
    okunur |= {p["dosya"]: p["dokuman"] for p in baglam}
    satirlar = list(dict.fromkeys(f"Kaynak: {okunur[k]}" for k in kaynaklar if k in okunur))
    return metin + ("\n\n" + "\n".join(satirlar) if satirlar else "")


def taslak_dugumu(durum: Durum, config: RunnableConfig) -> Command[Literal["self_check"]]:
    """Ajanın topladığı verilerden yapılandırılmış bir yanıt taslağı üretir. İstem prompts/taslak/<sürüm>.md
    şablonundan gelir. Self-check geçmediyse düzeltme notu kullanıcı mesajının sonuna eklenir."""
    baglam = baglam_olustur(durum.get("getirilen_parcalar", []))
    duzeltme = (f"\n\n## Düzeltme isteği\nÖnceki taslağın kontrolden geçmedi: {durum['duzeltme']}\n"
                "Bu sorunları gidererek taslağı yeniden yaz.") if durum.get("duzeltme") else ""

    model_turu = config["configurable"].get("model_turu", "yerel")
    yontem = "function_calling" if model_turu == "yerel" else "json_schema"
    model = model_getir(model_turu).with_structured_output(Taslak, method=yontem)
    istem = mesajlar("taslak", model_turu, **taslak_baglami(durum), duzeltme=duzeltme)
    taslak = None
    for deneme in (1, 2):  # yapılandırılmış çıktı ara sıra bozuk gelir; bir kez daha denemek çoğu zaman yeter
        try:
            taslak = model.invoke(istem)
        except Exception as e:
            log.warning("taslak çıktısı okunamadı (deneme %d): %s: %s", deneme, type(e).__name__, str(e)[:150])
        if taslak is not None:
            break
    if taslak is None:  # yapılandırılmış çıktı alınamadı: güvenli taraf
        taslak = Taslak(gerekce="taslak üretilemedi", karar="temsilciye_aktar", yanit=TEMSILCI_YANITI)

    # Model çıktısı da maskelenir: model bir numara yazdıysa takma ada döner (müşteriye tam numara gitmez)
    taslak.yanit = metni_maskele(taslak.yanit)
    # Atıf kontrolü: model, kendisine verilmemiş bir kaynağı gösteremez (uydurma atıf silinir, self-check raporlar)
    taslak.yanit, kaynaklar, uydurma = kaynaklari_dogrula(taslak.yanit, taslak.kaynaklar, baglam)
    taslak.kaynaklar = kaynaklar
    adimlar = adim_ekle(durum, f"taslak: {taslak.karar} - {taslak.gerekce}"
                               f" | baglam: {len(baglam)} parça, kaynaklar: {', '.join(kaynaklar) or '-'}")
    if uydurma:
        adimlar = adim_ekle({**durum, "adimlar": adimlar}, f"uydurma kaynak silindi: {', '.join(uydurma)}")
    return Command(goto="self_check", update={
        "taslak": taslak.model_dump(), "kaynaklar": kaynaklar, "uydurma_kaynaklar": uydurma,
        "musteri_yaniti": musteriye_hazirla(taslak.yanit, kaynaklar, baglam), "adimlar": adimlar})


# ---------------------------------------------------------------------------
# 6) Self-check: taslak müşteriye gitmeden önce kontrol edilir (Hafta 4)
# ---------------------------------------------------------------------------

def self_check_dugumu(durum: Durum, config: RunnableConfig) -> Command[
        Literal["taslak", "risk_kontrolu", "temsilciye_aktar"]]:
    """İki katmanlı kontrol (self_check.py): önce kodla (kaynak, tam numara, yasak ifade, iç doküman),
    sonra yanıtla kararında model eleştirisi. Geçmezse gerekçesiyle bir kez yeniden yazdırır;
    ikinci kez de geçmezse temsilciye aktarır."""
    taslak = durum["taslak"]
    if taslak["karar"] == "temsilciye_aktar":  # müşteriye hazır cümle gidecek; kontrol edilecek yanıt yok
        return Command(goto="risk_kontrolu", update={"self_check": {"gecti": True, "taahhut": "emin_degilim"}})

    sorunlar = deterministik_kontroller(durum["musteri_yaniti"], durum.get("uydurma_kaynaklar", []))
    elestiri = None
    if not sorunlar and taslak["karar"] == "yanitla":  # kod geçtiyse modele sor (kod yakaladıysa boşuna sorma)
        elestiri = elestir(config["configurable"].get("model_turu", "yerel"),
                           **{k: v for k, v in taslak_baglami(durum).items() if k != "ajan_notu"},
                           taslak=taslak["yanit"], iade_onerisi=(
                               f"{taslak['iade_islem_id']} numaralı işlem, {taslak['iade_tutari']} TL "
                               "(sistem bu öneriyi temsilci onayına gönderir)" if taslak["iade_islem_id"] else "yok"))
        if not elestiri_gecti_mi(elestiri):
            sorunlar.append(f"eleştiri: {elestiri.gerekce}")
    sonuc = {"gecti": not sorunlar, "sorunlar": sorunlar,
             "taahhut": elestiri.iade_odeme_taahhut if elestiri else "emin_degilim",
             "elestiri": elestiri.model_dump() if elestiri else None}
    ozet = (f"self-check: {'GECTI' if not sorunlar else 'GECMEDI'}"
            + (f" (taahhut: {sonuc['taahhut']})" if elestiri else "")
            + (f" - {'; '.join(sorunlar)}" if sorunlar else ""))
    adimlar = adim_ekle(durum, ozet[:300])

    if not sorunlar:
        return Command(goto="risk_kontrolu", update={"self_check": sonuc, "adimlar": adimlar})
    if durum.get("yeniden_yazim", 0) < YENIDEN_YAZIM_LIMITI:
        return Command(goto="taslak", update={"self_check": sonuc, "duzeltme": "; ".join(sorunlar),
                                              "yeniden_yazim": durum.get("yeniden_yazim", 0) + 1,
                                              "adimlar": adimlar})
    return Command(goto="temsilciye_aktar", update={
        "self_check": sonuc, "aktarim_nedeni": f"self-check yeniden yazımdan sonra da geçmedi: {'; '.join(sorunlar)}",
        "adimlar": adimlar})


# ---------------------------------------------------------------------------
# 7) Risk kontrolü ve 8) insan onayı
# ---------------------------------------------------------------------------

# Deterministik kurallar: modelin "bu riskli değil" demesine tek başına güvenmiyoruz.
IADE_KALIBI = re.compile(r"iade|geri öde|geri al|geri yatır")
TUTAR_KALIBI = re.compile(r"\d[\d.,]*\s*(?:tl|₺|lira)\b")
HUKUKI_KALIBI = re.compile(r"avukat|dava|icra|mahkeme|hukuk|yasal takip|yasal süreç|tüketici hakem|bddk")


def risk_nedenleri_bul(yanit: str, talep: str, iade_var: bool, taahhut: str = "emin_degilim") -> list[str]:
    """İnsan onayı gerektiren nedenler. Hafta 4'te inceltildi: kelimeye değil anlama bakılır.
    taahhut = self-check'in "yanıt iade/ödeme/taahhüt içeriyor mu" cevabı (evet | hayir | emin_degilim).
    - "evet": onaya gider.  - "hayir": yanıttaki tutar ve "iade" kelimesi bilgi amaçlıdır, onaya gitmez.
    - "emin_degilim" (ya da self-check çalışamadı): Hafta 3'ün temkinli kelime kuralları geçerli."""
    yanit_k, talep_k = kucuk_harf(yanit), kucuk_harf(talep)
    nedenler = []
    if iade_var:                                  # taslak somut bir iade öneriyor (islem_id dolu)
        nedenler.append("iade")
    if taahhut == "evet":
        nedenler.append("taahhut")
    elif taahhut != "hayir":                      # emin değil: eski kurallar
        if IADE_KALIBI.search(yanit_k) and "iade" not in nedenler:
            nedenler.append("iade")
        if TUTAR_KALIBI.search(yanit_k):
            nedenler.append("tutar")
    if HUKUKI_KALIBI.search(yanit_k) or HUKUKI_KALIBI.search(talep_k):
        nedenler.append("hukuki")
    return nedenler


def risk_kontrolu_dugumu(durum: Durum) -> Command[Literal["yanitla", "netlestir", "insan_onayi", "temsilciye_aktar"]]:
    taslak = durum["taslak"]
    if taslak["karar"] == "temsilciye_aktar":
        return Command(goto="temsilciye_aktar", update={
            "aktarim_nedeni": f"ajan kararı: {taslak['gerekce']}",
            "adimlar": adim_ekle(durum, "risk kontrolu: ajan temsilciye aktarmayi secti")})
    if taslak["karar"] == "netlestir":
        if durum.get("netlestirme_sayisi", 0) >= NETLESTIRME_LIMITI:
            return Command(goto="temsilciye_aktar", update={
                "aktarim_nedeni": "netleştirmeden sonra da bilgi yetersiz",
                "adimlar": adim_ekle(durum, "risk kontrolu: ikinci netlestirme yerine temsilci")})
        return Command(goto="netlestir")

    # Kaynak etiketleri çıkarılmış metne bakılır: dosya/başlık adındaki "iade" onayı tetiklemesin
    nedenler = risk_nedenleri_bul(kaynak_etiketlerini_cikar(taslak["yanit"]), "\n".join(durum["talepler"]),
                                  bool(taslak["iade_islem_id"]), durum.get("self_check", {}).get("taahhut", "emin_degilim"))
    hedef = "insan_onayi" if nedenler else "yanitla"
    return Command(goto=hedef, update={
        "risk_nedenleri": nedenler,
        "adimlar": adim_ekle(durum, f"risk kontrolu: {', '.join(nedenler) or 'risk yok'} -> {hedef}")})


def insan_onayi_dugumu(durum: Durum, config: RunnableConfig) -> Command[Literal["temsilciye_aktar", "__end__"]]:
    """Akışı DURDURUR (interrupt) ve bir temsilcinin onayını bekler. onayla() ile devam eder.
    Not: devam edildiğinde düğüm BAŞTAN çalışır; interrupt'tan önce yan etkili iş yapılmamalı.
    Hafta 4: temsilci reddeder ya da yanıtı düzeltirse gerekçesi eval/geri_bildirim.csv'ye yazılır."""
    taslak = durum["taslak"]
    karar = interrupt({
        "musteri_no": durum["musteri_no"],
        "talep": durum["talep"],
        "yanit_taslagi": durum["musteri_yaniti"],  # temsilci de tam numara görmez
        "risk_nedenleri": durum["risk_nedenleri"],
        "iade_onerisi": {"islem_id": taslak["iade_islem_id"], "tutar": taslak["iade_tutari"]}
                        if taslak["iade_islem_id"] else None,
    })
    geri_bildirim = {"oturum_id": config["configurable"]["thread_id"], "musteri_no": durum["musteri_no"],
                     "talep": "\n".join(durum["talepler"]), "asistan_yaniti": durum["musteri_yaniti"],
                     "gerekce": karar.get("gerekce", ""), "duzeltilmis_yanit": karar.get("duzeltilmis_yanit", ""),
                     "onaylayan": karar.get("onaylayan", "")}
    if not karar.get("onay"):
        geri_bildirim_kaydet(**geri_bildirim, karar="red")
        return Command(goto="temsilciye_aktar", update={
            "aktarim_nedeni": "insan onayı reddedildi",
            "adimlar": adim_ekle(durum, f"insan onayi: REDDEDILDI ({karar.get('onaylayan', '?')})")})

    adimlar = adim_ekle(durum, f"insan onayi: ONAYLANDI ({karar.get('onaylayan', '?')})")
    if taslak["iade_islem_id"]:
        # Yazma aracı SADECE burada, onaydan sonra ve kod tarafından çağrılır (model çağıramaz)
        try:
            with musteri_oturumu(durum["musteri_no"]):
                sonuc = iade_talebi_olustur.invoke({
                    "islem_id": taslak["iade_islem_id"], "tutar": taslak["iade_tutari"],
                    "sebep": durum["talep"][:200], "onaylayan": karar.get("onaylayan", "")})
            adimlar = adim_ekle({**durum, "adimlar": adimlar}, f"iade_talebi_olustur: {sonuc}")
        except ApiHatasi as e:
            return Command(goto="temsilciye_aktar", update={
                "aktarim_nedeni": f"iade talebi açılamadı: {e}",
                "adimlar": adim_ekle({**durum, "adimlar": adimlar}, f"iade hatasi: {e}")})
    yanit = durum["musteri_yaniti"]
    if karar.get("duzeltilmis_yanit"):  # temsilci yanıtı düzelterek onayladı: müşteriye düzeltilmiş hali gider
        geri_bildirim_kaydet(**geri_bildirim, karar="duzeltme")
        yanit = karar["duzeltilmis_yanit"]
        adimlar = adim_ekle({**durum, "adimlar": adimlar}, "insan onayi: yanit temsilci tarafindan duzeltildi")
    return Command(goto=END, update={"davranis": "insan_onayi", "yanit": yanit, "adimlar": adimlar})


# ---------------------------------------------------------------------------
# 9) Sonuç düğümleri
# ---------------------------------------------------------------------------

def yanitla_dugumu(durum: Durum) -> dict:
    return {"davranis": "yanitla", "yanit": durum["musteri_yaniti"], "adimlar": adim_ekle(durum, "yanit gonderildi")}


def temsilciye_aktar_dugumu(durum: Durum) -> dict:
    """Güvenli taraf: talebi temsilci kuyruğuna yazar. Kuyruğa yazılamasa da müşteriye aynı yanıt
    döner ve durum loglanır (temsilciler logdan da takip edebilir)."""
    neden = durum.get("aktarim_nedeni") or "belirtilmedi"
    try:
        with musteri_oturumu(durum["musteri_no"]):
            temsilciye_aktar.invoke({"ozet": "\n".join(durum["talepler"]), "neden": neden})
    except Exception as e:
        log.error("temsilci kuyruğuna yazılamadı (%s): %s", durum["musteri_no"], e)
    return {"davranis": "temsilciye_aktar", "yanit": TEMSILCI_YANITI,
            "adimlar": adim_ekle(durum, f"temsilciye aktarildi: {neden}")}


# ---------------------------------------------------------------------------
# Grafı kur
# ---------------------------------------------------------------------------

def graf_olustur():
    g = StateGraph(Durum)
    g.add_node("baslat", baslat_dugumu)
    g.add_node("siniflandir", siniflandir_dugumu)
    g.add_node("hazir_yanit", hazir_yanit_dugumu)
    g.add_node("netlestir", netlestir_dugumu)
    g.add_node("ajan_hazirla", ajan_hazirla_dugumu)
    g.add_node("ajan", ajan_dugumu)
    g.add_node("arac_calistir", arac_calistir_dugumu)
    g.add_node("taslak", taslak_dugumu)
    g.add_node("self_check", self_check_dugumu)
    g.add_node("risk_kontrolu", risk_kontrolu_dugumu)
    g.add_node("insan_onayi", insan_onayi_dugumu)
    g.add_node("yanitla", yanitla_dugumu)
    g.add_node("temsilciye_aktar", temsilciye_aktar_dugumu)

    # Sabit kenarlar. Diğer geçişleri düğümler Command(goto=...) ile kendileri seçer.
    g.add_edge(START, "baslat")
    g.add_edge("baslat", "siniflandir")
    g.add_edge("ajan_hazirla", "ajan")
    for son in ("hazir_yanit", "netlestir", "yanitla", "temsilciye_aktar"):
        g.add_edge(son, END)
    # Checkpointer: interrupt (insan onayı) ve çok turlu netleştirme için durumu oturum bazında saklar
    return g.compile(checkpointer=InMemorySaver())


GRAF = graf_olustur()


# ---------------------------------------------------------------------------
# Dış arayüz
# ---------------------------------------------------------------------------

def arac_havuzu(guvensiz: bool = False) -> dict:
    """Ajanın kullanabileceği tüm okuma araçları {ad: arac}. Kategori bunlardan alt küme seçer."""
    havuz = {a.name: a for a in OKUMA_ARACLARI}
    if guvensiz:
        from asistan.araclar_guvensiz import kart_islemleri_guvensiz
        log.warning("GUVENSIZ ARAC MODU: kart_islemleri musteri_no parametresi alıyor (sadece ders deneyi)")
        havuz["kart_islemleri"] = kart_islemleri_guvensiz
    return havuz


def _sonuc(durum: dict, oturum_id: str) -> dict:
    """Graf çıktısını ortak arayüz sözlüğüne çevirir."""
    onay_bekliyor = "__interrupt__" in durum
    return {
        "kategori": durum.get("kategori", ""),
        "ikinci_konu": durum.get("ikinci_konu", ""),
        "davranis": "insan_onayi" if onay_bekliyor else durum.get("davranis", ""),
        "yanit": durum.get("musteri_yaniti", "") if onay_bekliyor else durum.get("yanit", ""),
        "kullanilan_araclar": list(dict.fromkeys(durum.get("kullanilan_araclar", []))),  # sırayı koru, tekrarı at
        "kaynaklar": durum.get("kaynaklar", []),  # yanıtta atıf yapılan prosedür kaynakları
        # ek alan: prosedur_ara'nın getirdiği tüm kaynaklar (eval'de kaynak isabeti ve sızıntı için)
        "getirilen_kaynaklar": list(dict.fromkeys(p["kaynak"] for p in durum.get("getirilen_parcalar", []))),
        "adimlar": durum.get("adimlar", []),
        "oturum_id": oturum_id,
        "onay_bekliyor": onay_bekliyor,
    }


def cevapla(talep: str, musteri_no: str, model_turu: str = "yerel", oturum_id: str | None = None,
            guvensiz: bool = False) -> dict:
    """Projenin ortak arayüzü. Dönen sözlük: {kategori, ikinci_konu, davranis, yanit,
    kullanilan_araclar, kaynaklar, adimlar} + oturum_id, onay_bekliyor.

    oturum_id: netleştirme sorusuna verilen cevabı aynı oturumda göndermek ve insan onayını
    sonradan vermek için. Verilmezse yeni oturum açılır.

    Hafta 4: talep grafa girmeden maskelenir. Akışın hiçbir yeri (model, log, iz) gerçek numarayı görmez;
    takma ad <-> gerçek değer eşlemesi sadece bu oturumun bellekteki tablosunda durur (maskeleme.py).
    """
    oturum_id = oturum_id or uuid.uuid4().hex[:8]
    config = {"configurable": {"thread_id": oturum_id, "model_turu": model_turu, "guvensiz": guvensiz,
                               "arac_havuzu": arac_havuzu(guvensiz)},
              "callbacks": [IzToplayici()]}  # düğüm, model ve araç olaylarını ize yazar
    with maske_oturumu(oturum_id):
        maskeli_talep = metni_maskele(talep)
        with iz_kaydi("cevapla", oturum_id=oturum_id, musteri_no=musteri_no, model_turu=model_turu,
                      talep=maskeli_talep) as iz:
            sonuc = _sonuc(GRAF.invoke({"talep": maskeli_talep, "musteri_no": musteri_no}, config), oturum_id)
            iz["sonuc"] = {k: sonuc[k] for k in ("kategori", "davranis", "kaynaklar", "kullanilan_araclar", "yanit", "adimlar")}
    return sonuc


def onayla(oturum_id: str, onay: bool, onaylayan: str, gerekce: str = "", duzeltilmis_yanit: str = "") -> dict:
    """İnsan onayı bekleyen oturumu devam ettirir. onay=False ise talep temsilciye aktarılır.
    gerekce / duzeltilmis_yanit (Hafta 4): ret ya da düzeltme gerekçesi eval/geri_bildirim.csv'ye kaydedilir."""
    config = {"configurable": {"thread_id": oturum_id}, "callbacks": [IzToplayici()]}
    karar = {"onay": onay, "onaylayan": onaylayan, "gerekce": gerekce, "duzeltilmis_yanit": duzeltilmis_yanit}
    with maske_oturumu(oturum_id), iz_kaydi("onayla", oturum_id=oturum_id, onay=onay) as iz:
        sonuc = _sonuc(GRAF.invoke(Command(resume=karar), config), oturum_id)
        iz["sonuc"] = {k: sonuc[k] for k in ("davranis", "yanit", "adimlar")}
    return sonuc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Asistanı tek bir talep için çalıştırır")
    parser.add_argument("talep")
    parser.add_argument("musteri_no")
    parser.add_argument("--model", default="yerel", choices=["yerel", "bulut", "guclu"])
    parser.add_argument("--guvensiz", action="store_true", help="SADECE DERS DENEYİ: güvensiz kart_islemleri")
    args = parser.parse_args()

    sonuc = cevapla(args.talep, args.musteri_no, args.model, guvensiz=args.guvensiz)
    print("\n".join(f"  - {a}" for a in sonuc["adimlar"]))
    if sonuc["onay_bekliyor"]:
        print(f"\nİNSAN ONAYI GEREKLİ. Yanıt taslağı:\n  {sonuc['yanit']}")
        cevap = input("Onaylıyor musunuz? (e/h): ").strip().lower()
        sonuc = onayla(sonuc["oturum_id"], cevap == "e", onaylayan="Terminal Temsilcisi")
        print("\n".join(f"  - {a}" for a in sonuc["adimlar"][-2:]))
    print(f"\n{sonuc['kategori']} / {sonuc['davranis']}  araçlar: {sonuc['kullanilan_araclar']}")
    print(f"Kaynaklar: {sonuc['kaynaklar'] or '-'}  (getirilen: {sonuc['getirilen_kaynaklar'] or '-'})")
    print(f"Yanıt: {sonuc['yanit']}")
    sys.exit(0)
