# LaciTek GraphRAG — Enterprise Multimodal Archival Intelligence System

Kurumsal arşivler için, yapay zekâyı deterministik algoritmalarla (graf arama,
Dijkstra, durum makinesi) dizginleyen hibrit bir GraphRAG mimarisi.

Yerel LLM (Microsoft Foundry Local) ile çalışır, Türkçe kurumsal/hukuki
varlıkları (TCKN, VKN, IBAN, mevzuat) tanır ve KVKK uyumlu PII maskeleme içerir.

## Durum

🚧 Yapım aşamasında — mimari ve modüller adım adım inşa ediliyor.

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
