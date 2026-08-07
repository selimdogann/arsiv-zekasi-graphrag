#!/usr/bin/env python3
"""
`baslat.py` ile açılan servisleri durdurur — Windows, macOS ve Linux'ta çalışır.

    python3 scripts/durdur.py            # API sunucusu + PostgreSQL
    python3 scripts/durdur.py --hepsi    # ek olarak Ollama'yı da durdurur

NEDEN AYRI BİR BETİK? `baslat.py` sunucuyu terminalden KOPARILMIŞ (detached)
başlatır; böylece betik bitince terminal serbest kalır ve terminali kapatsanız
bile sistem çalışmaya devam eder. Bunun bedeli, Ctrl+C'nin sunucuyu
durdurmamasıdır — durdurmak için bu betik kullanılır.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RENK = sys.stdout.isatty() and platform.system() != "Windows"
_Y, _S, _B = ("\033[0;32m", "\033[0;33m", "\033[0m") if _RENK else ("", "", "")


def ok(m): print(f"  {_Y}[+]{_B} {m}")
def uyar(m): print(f"  {_S}[!]{_B} {m}")


def surec_durdur(desen: str, ad: str) -> None:
    """Verilen komut desenine uyan süreçleri sonlandırır."""
    if platform.system() == "Windows":
        # Windows'ta komut satırına göre eşleştirme WMIC üzerinden yapılır.
        sonuc = subprocess.run(
            ["wmic", "process", "where",
             f"CommandLine like '%{desen}%' and name like '%python%'",
             "delete"], capture_output=True, text=True)
        basarili = "deleted" in sonuc.stdout.lower()
    else:
        basarili = subprocess.run(["pkill", "-f", desen],
                                  capture_output=True).returncode == 0
    ok(f"{ad} durduruldu") if basarili else uyar(f"{ad} zaten çalışmıyordu")


def main() -> int:
    hepsi = "--hepsi" in sys.argv

    print("\nServisler durduruluyor")
    surec_durdur("uvicorn graphrag.api", "API sunucusu")

    if subprocess.run(["docker", "info"], capture_output=True).returncode == 0:
        subprocess.run(["docker", "compose", "stop"], cwd=KOK, capture_output=True)
        ok("PostgreSQL durduruldu (veriler korunur)")
    else:
        uyar("Docker çalışmıyor; PostgreSQL zaten kapalı")

    if hepsi:
        surec_durdur("ollama serve", "Ollama")
    else:
        print("\n  Ollama çalışmaya devam ediyor (başka projeler kullanıyor olabilir).")
        print("  Onu da durdurmak için: python3 scripts/durdur.py --hepsi")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
