"""
Arşivi tamamen sıfırlar: belge parçaları (chunk + embedding), graf düğüm ve
kenarları, KVKK denetim kayıtları.

Kullanım:
    DATABASE_URL="postgresql+psycopg://graphrag:graphrag@localhost:5432/graphrag" \
        python3 scripts/reset_archive.py

`DATABASE_URL` tanımlı değilse veri zaten yalnızca bellekte tutulur; o modda
"sıfırlama" = API sunucusunu yeniden başlatmaktır (betik bunu bildirir).

Not: Bu bir OPERASYON betiğidir; veritabanına doğrudan konuşur. Uygulama
katmanı (domain/application) bundan etkilenmez.
"""
from __future__ import annotations

import os
import sys

# Betik proje kökünden bağımsız çalışabilsin diye kök dizini yola ekle.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TABLOLAR = ("chunks", "graph_nodes", "graph_edges", "audit_events")


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL tanımlı değil — sistem bellek-içi modda çalışıyor.")
        print("Bu modda sıfırlama için API sunucusunu yeniden başlatmanız yeterli.")
        return 0

    from sqlalchemy import text

    from graphrag.infrastructure.db.engine import init_schema, make_engine

    engine = make_engine(database_url)
    init_schema(engine)  # tablolar yoksa oluştur (ilk kurulumda da çalışsın)

    with engine.connect() as conn:
        onceki = {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
                  for t in TABLOLAR}

    print("Sıfırlama öncesi:")
    for tablo, adet in onceki.items():
        print(f"  {tablo:<14} {adet}")

    with engine.begin() as conn:
        conn.execute(text(
            f"TRUNCATE TABLE {', '.join(TABLOLAR)} RESTART IDENTITY CASCADE"))

    with engine.connect() as conn:
        sonraki = {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
                   for t in TABLOLAR}

    print("Sıfırlama sonrası:")
    for tablo, adet in sonraki.items():
        print(f"  {tablo:<14} {adet}")

    if any(sonraki.values()):
        print("HATA: bazı tablolar boşalmadı.")
        return 1

    print("\nArşiv tamamen sıfırlandı.")
    print("API sunucusu çalışıyorsa yeniden başlatın — bellekteki anahtar kelime "
          "indeksi ve belge listesi de temizlensin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
