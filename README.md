# Enterprise Multimodal GraphRAG Archival Intelligence Platform

Kurumsal arşivler için, yapay zekâyı deterministik algoritmalarla (graf arama,
Dijkstra, durum makinesi) dizginleyen, sektörden bağımsız (domain-agnostic)
hibrit bir GraphRAG mimarisi.

Yerel LLM ile çalışır; Ports & Adapters (Clean Architecture) ile kurulmuştur —
çekirdek mimari herhangi bir kurumsal arşiv sistemine uyarlanabilir.

## Türkçe Kurumsal Vertical

Platformun derinlemesine bir özelleşme örneği olarak, Türk kurumsal/hukuki
belgelere özgü bir katman geliştiriliyor: Türkçe varlık çıkarımı (TCKN, VKN,
IBAN, mevzuat referansı) ve KVKK (6698 sayılı Kanun) uyumlu PII maskeleme.

## Durum

🚧 Yapım aşamasında — mimari ve modüller adım adım inşa ediliyor.

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
