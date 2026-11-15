"""Her cevapla() çalıştırmasının izini (trace) kaydeder (Hafta 3, adım 6).
Bir iz şunları söyler: hangi düğümler hangi sırayla ve kaç ms'de çalıştı, hangi araçlar çağrıldı, prosedür
aramasında hangi parçalar hangi skorla geldi, her model çağrısı kaç token harcadı.
Kayıt: logs/izler/YYYY-MM-DD.jsonl (her satır bir çalıştırma), kimlik bilgileri maskelenir. TRACING=kapali ise yazılmaz.
"""

import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime

from langchain_core.callbacks import BaseCallbackHandler

from asistan.ayarlar import PROJE_KOKU
from asistan.gunluk import log

IZ_KLASORU = PROJE_KOKU / "logs" / "izler"

_AKTIF_IZ: ContextVar[dict | None] = ContextVar("aktif_iz", default=None)


# ---------------------------------------------------------------------------
# Maskeleme: iz dosyası müşteri verisi taşımasın (veriler sentetik olsa da alışkanlık)
# ---------------------------------------------------------------------------

MASKELER = [
    (re.compile(r"\bTR\d{2}(?: ?\d{4}){5} ?\d{2}\b"), "[IBAN]"),
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "[KART]"),
    (re.compile(r"\b\d{11}\b"), "[TCKN]"),
    (re.compile(r"\b0?5\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}\b"), "[TELEFON]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EPOSTA]"),
]


def maskele(metin: str) -> str:
    for kalip, yerine in MASKELER:
        metin = kalip.sub(yerine, metin)
    return metin


# ---------------------------------------------------------------------------
# İz: bir çalıştırma boyunca olayların toplandığı sözlük
# ---------------------------------------------------------------------------

def olay_ekle(tur: str, **alanlar) -> None:
    """Aktif ize bir olay ekler. İz yoksa (ör. notebook'ta aracı doğrudan çağırınca) hiçbir şey yapmaz."""
    iz = _AKTIF_IZ.get()
    if iz is not None:
        iz["olaylar"].append({"tur": tur, "t_ms": round((time.perf_counter() - iz["_baslangic"]) * 1000), **alanlar})


@contextmanager
def iz_kaydi(islem: str, **bilgi):
    """`with iz_kaydi("cevapla", talep=..., musteri_no=...) as iz:` bloğundaki her şeyin izini tutar.
    Blok bitince (hata olsa da) iz JSONL dosyasına yazılır. Blok içinde iz["sonuc"] doldurulabilir."""
    iz = {"iz_id": uuid.uuid4().hex[:12], "zaman": datetime.now().isoformat(timespec="seconds"),
          "islem": islem, **bilgi, "olaylar": [], "_baslangic": time.perf_counter()}
    jeton = _AKTIF_IZ.set(iz)
    try:
        yield iz
    except Exception as e:
        iz["hata"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        _AKTIF_IZ.reset(jeton)
        iz_yaz(iz)


def iz_yaz(iz: dict) -> None:
    """İzi özetler (toplam süre, toplam token) ve maskeleyip dosyaya bir satır olarak ekler.
    Yazma hatası asistanı durdurmaz; sadece loglanır."""
    if os.getenv("TRACING", "jsonl").strip().lower() == "kapali":
        return
    modeller = [o for o in iz["olaylar"] if o["tur"] == "model"]
    iz["toplam_sure_ms"] = round((time.perf_counter() - iz.pop("_baslangic")) * 1000)
    iz["toplam_token"] = {"girdi": sum(o.get("girdi_token") or 0 for o in modeller),
                          "cikti": sum(o.get("cikti_token") or 0 for o in modeller)}
    try:
        IZ_KLASORU.mkdir(parents=True, exist_ok=True)
        with open(IZ_KLASORU / f"{datetime.now():%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
            f.write(maskele(json.dumps(iz, ensure_ascii=False, default=str)) + "\n")
    except OSError as e:
        log.warning("iz yazılamadı: %s", e)


# ---------------------------------------------------------------------------
# LangChain geri çağırmaları (callback): düğüm, model ve araç olaylarını kendiliğinden toplar
# ---------------------------------------------------------------------------

class IzToplayici(BaseCallbackHandler):
    """LangChain her düğüm, model ve araç çağrısının başında ve sonunda bu sınıfın metotlarını çağırır.
    (LangChain'in callback arayüzü bir sınıf ister; bu projede tek istisna budur.)
    Kullanım: GRAF.invoke(girdi, {"callbacks": [IzToplayici()], ...})"""

    def __init__(self):
        self.acik: dict = {}      # run_id -> (tür, ad, düğüm, başlangıç zamanı)
        self.girdiler: dict = {}  # run_id -> araç parametreleri

    def _ac(self, run_id, tur, ad, metadata):
        self.acik[run_id] = (tur, ad, (metadata or {}).get("langgraph_node", ""), time.perf_counter())

    def _kapat(self, run_id, **ek):
        if run_id not in self.acik:
            return
        tur, ad, dugum, baslangic = self.acik.pop(run_id)
        sure = round((time.perf_counter() - baslangic) * 1000)
        if tur == "dugum":
            olay_ekle("dugum", ad=ad, sure_ms=sure, **ek)
        else:
            olay_ekle(tur, ad=ad, dugum=dugum, sure_ms=sure, **ek)

    # Düğümler: LangGraph her düğümü bir "chain" olarak çalıştırır; adı düğüm adıyla aynıdır
    def on_chain_start(self, serialized, inputs, *, run_id, metadata=None, name=None, **kwargs):
        if name and name == (metadata or {}).get("langgraph_node"):
            self._ac(run_id, "dugum", name, metadata)

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        self._kapat(run_id)

    def on_chain_error(self, error, *, run_id, **kwargs):
        # insan_onayi düğümü interrupt ile durur; LangGraph bunu hata olarak bildirir
        self._kapat(run_id, durum="durdu" if type(error).__name__ == "GraphInterrupt" else f"hata: {type(error).__name__}")

    # Model çağrıları: token bilgisi yanıtın usage_metadata alanında gelir
    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        self._ac(run_id, "model", (metadata or {}).get("ls_model_name", "?"), metadata)

    def on_llm_end(self, response, *, run_id, **kwargs):
        mesaj = getattr(response.generations[0][0], "message", None) if response.generations else None
        kullanim = getattr(mesaj, "usage_metadata", None) or {}
        self._kapat(run_id, girdi_token=kullanim.get("input_tokens"), cikti_token=kullanim.get("output_tokens"))

    def on_llm_error(self, error, *, run_id, **kwargs):
        self._kapat(run_id, durum=f"hata: {type(error).__name__}")

    # Araçlar: hangi araç, hangi parametrelerle (çıktı yazılmaz: müşteri verisi içerir)
    def on_tool_start(self, serialized, input_str, *, run_id, metadata=None, inputs=None, **kwargs):
        self._ac(run_id, "arac", (serialized or {}).get("name", "?"), metadata)
        self.girdiler[run_id] = inputs if inputs is not None else input_str

    def on_tool_end(self, output, *, run_id, **kwargs):
        self._kapat(run_id, girdi=self.girdiler.pop(run_id, None))

    def on_tool_error(self, error, *, run_id, **kwargs):
        self._kapat(run_id, girdi=self.girdiler.pop(run_id, None), durum=f"hata: {type(error).__name__}")
