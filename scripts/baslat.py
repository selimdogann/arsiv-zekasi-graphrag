#!/usr/bin/env python3
"""
Tek komutla tüm sistemi başlatır — Windows, macOS ve Linux'ta çalışır.

    python3 scripts/baslat.py

Sırasıyla Ollama'yı, (varsa) PostgreSQL'i ve API sunucusunu başlatır; her
bileşenin gerçekten hazır olmasını bekler, modelleri ÖNDEN ISITIR (ilk sorunun
12 saniye sürmemesi için) ve durumu özetler.

Docker kurulu değilse sistem bellek-içi modda çalışmaya devam eder; bu durumda
yalnızca veriler uygulama kapanınca kaybolur.
"""
from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLLAMA_URL = "http://localhost:11434"
API_URL = "http://localhost:8000"
ANAHTAR_DOSYASI = os.path.join(KOK, ".api_key")
SOHBET_MODELI, EMBED_MODELI = "qwen2.5:7b", "bge-m3"

# Windows terminalleri ANSI renklerini her zaman desteklemez; kapatılabilir.
_RENK = sys.stdout.isatty() and platform.system() != "Windows"
_M, _Y, _S, _K, _B = (
    ("\033[0;34m", "\033[0;32m", "\033[0;33m", "\033[0;31m", "\033[0m")
    if _RENK else ("", "", "", "", "")
)


def adim(m): print(f"\n{_M}> {m}{_B}")
def ok(m):   print(f"  {_Y}[+]{_B} {m}")
def uyar(m): print(f"  {_S}[!]{_B} {m}")
def hata(m): print(f"  {_K}[x]{_B} {m}")


def istek(url: str, veri: dict | None = None, zaman_asimi: int = 5):
    """Basit HTTP isteği. Başarısızsa None döner (dış kütüphane gerekmez)."""
    try:
        gövde = json.dumps(veri).encode() if veri is not None else None
        req = urllib.request.Request(
            url, data=gövde,
            headers={"Content-Type": "application/json"} if gövde else {})
        with urllib.request.urlopen(req, timeout=zaman_asimi) as yanit:
            return yanit.read()
    except Exception:
        return None


def bekle(url: str, saniye: int = 40) -> bool:
    """Adres yanıt verene kadar bekler."""
    for _ in range(saniye):
        if istek(url, zaman_asimi=2) is not None:
            return True
        time.sleep(1)
    return False


def python_yolu() -> str:
    """Sanal ortamdaki Python; yoksa çalışan yorumlayıcı."""
    alt = "Scripts" if platform.system() == "Windows" else "bin"
    ad = "python.exe" if platform.system() == "Windows" else "python3"
    venv = os.path.join(KOK, ".venv", alt, ad)
    return venv if os.path.exists(venv) else sys.executable


def arka_planda(komut: list[str], gunluk: str) -> None:
    """Süreci arka planda, terminalden bağımsız başlatır."""
    with open(gunluk, "ab") as f:
        kwargs = {"stdout": f, "stderr": f, "cwd": KOK}
        if platform.system() == "Windows":
            kwargs["creationflags"] = 0x00000008  # DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(komut, **kwargs)


def api_anahtari() -> str:
    """Anahtarı bir kez üretip dosyada saklar (dosya git'e girmez)."""
    if os.path.exists(ANAHTAR_DOSYASI):
        with open(ANAHTAR_DOSYASI, encoding="utf-8") as f:
            mevcut = f.read().strip()
            if mevcut:
                return mevcut
    yeni = secrets.token_hex(32)
    with open(ANAHTAR_DOSYASI, "w", encoding="utf-8") as f:
        f.write(yeni)
    return yeni


# --------------------------------------------------------------------- adımlar

def ollama_baslat() -> bool:
    adim("Ollama (yerel yapay zekâ sunucusu)")
    if istek(f"{OLLAMA_URL}/api/tags", zaman_asimi=3):
        ok("zaten çalışıyor")
    else:
        if not shutil.which("ollama"):
            hata("Ollama kurulu değil — https://ollama.com adresinden kurun")
            return False
        uyar("çalışmıyor, başlatılıyor...")
        arka_planda(["ollama", "serve"], os.path.join(KOK, "ollama.log"))
        if not bekle(f"{OLLAMA_URL}/api/tags"):
            hata("Ollama başlatılamadı")
            return False
        ok("başlatıldı")

    kurulu = (istek(f"{OLLAMA_URL}/api/tags") or b"").decode(errors="ignore")
    for model in (SOHBET_MODELI, EMBED_MODELI):
        if model.split(":")[0] in kurulu:
            ok(f"model hazır: {model}")
        else:
            hata(f"model eksik: {model}   ->   ollama pull {model}")
            return False
    return True


def postgres_baslat() -> bool:
    """PostgreSQL'i başlatmayı dener. Başaramazsa bellek-içi moda düşülür."""
    adim("PostgreSQL (kalıcı depolama — opsiyonel)")
    if not shutil.which("docker"):
        uyar("Docker kurulu değil; sistem bellek-içi modda çalışacak")
        return False

    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        if platform.system() == "Darwin":
            uyar("Docker kapalı, açılıyor... (biraz sürebilir)")
            subprocess.run(["open", "-a", "Docker"], capture_output=True)
            for _ in range(60):
                if subprocess.run(["docker", "info"],
                                  capture_output=True).returncode == 0:
                    break
                time.sleep(2)
        else:
            uyar("Docker çalışmıyor; sistem bellek-içi modda çalışacak")
            return False

    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        uyar("Docker açılamadı; sistem bellek-içi modda çalışacak")
        return False

    subprocess.run(["docker", "compose", "up", "-d"],
                   cwd=KOK, capture_output=True)
    for _ in range(30):
        sonuc = subprocess.run(["docker", "compose", "ps", "--format", "{{.Status}}"],
                               cwd=KOK, capture_output=True, text=True)
        if "healthy" in sonuc.stdout:
            ok("hazır (healthy)")
            return True
        time.sleep(2)
    uyar("veritabanı hazır olmadı; sistem bellek-içi modda çalışacak")
    return False


def api_baslat(kalici: bool, anahtar: str) -> bool:
    adim("API sunucusu")
    # Çalışan eski sunucuyu kapat (port çakışmasın)
    if platform.system() == "Windows":
        subprocess.run(["taskkill", "/F", "/IM", "uvicorn.exe"], capture_output=True)
    else:
        subprocess.run(["pkill", "-f", "uvicorn graphrag.api"], capture_output=True)
    time.sleep(1)

    os.environ["API_KEY"] = anahtar
    if kalici:
        os.environ["DATABASE_URL"] = (
            "postgresql+psycopg://graphrag:graphrag@localhost:5432/graphrag")
    else:
        os.environ.pop("DATABASE_URL", None)

    arka_planda([python_yolu(), "-m", "uvicorn", "graphrag.api:app", "--port", "8000"],
                os.path.join(KOK, "api.log"))
    if not bekle(f"{API_URL}/"):
        hata("API başlatılamadı — ayrıntı için api.log dosyasına bakın")
        return False
    ok(f"çalışıyor ({API_URL})")
    return True


def modelleri_isit() -> None:
    adim("Modeller ısıtılıyor (ilk sorunun 12 saniye sürmemesi için)")
    if istek(f"{OLLAMA_URL}/api/embeddings",
             {"model": EMBED_MODELI, "prompt": "ısınma", "keep_alive": "30m"}, 180):
        ok(f"embedding modeli bellekte ({EMBED_MODELI})")
    else:
        uyar("embedding modeli ısıtılamadı")
    if istek(f"{OLLAMA_URL}/api/chat",
             {"model": SOHBET_MODELI, "stream": False, "keep_alive": "30m",
              "messages": [{"role": "user", "content": "merhaba"}]}, 240):
        ok(f"sohbet modeli bellekte ({SOHBET_MODELI})")
    else:
        uyar("sohbet modeli ısıtılamadı")


def ozet(anahtar: str) -> None:
    adim("Durum")
    saglik = istek(f"{API_URL}/")
    if saglik:
        d = json.loads(saglik)
        print(f"  Yapay zekâ : {'hazır' if d['llm'] else 'KAPALI'}")
        print(f"  Depolama   : {d['storage']}")
        print(f"  Modeller   : {d['chat_model']} · {d['embed_model']}")

    try:
        req = urllib.request.Request(f"{API_URL}/stats",
                                     headers={"X-API-Key": anahtar})
        with urllib.request.urlopen(req, timeout=10) as y:
            s = json.loads(y.read())
        print(f"  Arşiv      : {s['documents']} belge · {s['chunks']} parça · "
              f"{s['entities']} varlık · {s['pii_masked']} maskelenen veri")
    except Exception:
        pass

    print(f"\n{_Y}> Sistem hazır{_B}")
    print(f"  Arayüz       : {API_URL}/app/")
    print(f"  API anahtarı : {anahtar}")
    print("  (Anahtarı arayüzde sağ üstteki kilit düğmesinden bir kez girin.)")


def main() -> int:
    anahtar = api_anahtari()
    if not ollama_baslat():
        return 1
    kalici = postgres_baslat()
    if not api_baslat(kalici, anahtar):
        return 1
    modelleri_isit()
    ozet(anahtar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
