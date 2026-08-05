# Enterprise GraphRAG — Kurumsal Arşiv Zekâsı

Kurumsal ve hukuki belge arşivleri için **on-premise (yerel), KVKK-uyumlu,
hibrit bir GraphRAG** sistemi. Yapay zekâyı deterministik algoritmalarla (graf
araması, Dijkstra, durum makineleri, checksum) dizginler — ve **veriler
sunucudan hiç çıkmaz.**

## Ne yapar?

Belgeler üzerinde üç yaklaşımı birleştirir:

1. **Hibrit arama (RAG):** anlamsal (embedding) + anahtar kelime (BM25)
   aramalarını birleştirip (RRF) en ilgili metni bulur, yerel bir dil modeliyle
   (LLM) doğal dilde cevap üretir.
2. **İlişki bulma (graf):** belgelerden çıkarılan varlıklar arası **gizli
   bağlantıları** bilgi grafı üzerinde, güven skoruyla (Dijkstra) bulur.
3. **KVKK uyumu:** kişisel verileri (TCKN/VKN/IBAN, e-posta, telefon) işleme
   girmeden maskeler.

> **Örnek:** İki farklı belgede geçen "Acme Holding" ve "Gamma Danışmanlık",
> ortak "Proje Zeus" üzerinden dolaylı olarak bağlıdır. Sıradan bir arama bunu
> bulamaz; bu sistem `Acme Holding → Proje Zeus → Gamma Danışmanlık` zincirini
> bir güven skoruyla çıkarır.

## Neden farklı? (On-prem + KVKK)

Bulut tabanlı GraphRAG çözümlerinin aksine, tamamen **yerelde** çalışır:
yerel LLM (Ollama) ve kendi veritabanınız (PostgreSQL). Veri Türkiye dışına ya
da üçüncü taraf buluta gitmez — Türk kurumsal/hukuki müşteriler için **KVKK
(6698 sayılı Kanun)** açısından belirleyici bir avantaj.

## Özellikler

- **Belge yükleme:** `.txt`, `.pdf`, `.docx` (otomatik format yönlendirme)
- **Belge parçalama (chunking):** kelime bütünlüğünü koruyan, örtüşmeli parçalama
- **Hibrit retrieval:** anlamsal (bge-m3 embedding) + anahtar kelime (BM25) +
  Reciprocal Rank Fusion (RRF)
- **LLM tabanlı varlık çıkarımı** ile bilgi grafı kurma
- **Graf bağlantı bulma:** güven skorlu en iyi yol (Dijkstra, `-log(güven)` hilesi)
- **KVKK / PII maskeleme:** TCKN/VKN/IBAN checksum doğrulama + takma adlaştırma
  (pseudonymization) + denetim kaydı (audit log)
- **Türkçe-farkında metin işleme** (İ/ı normalizasyonu)
- **Kalıcılık:** PostgreSQL + pgvector (tek veritabanı; vektör + graf + denetim)
- **API + Web arayüzü:** FastAPI REST API ve basit bir web arayüzü
- **Yerel LLM:** Ollama (`qwen2.5:7b` sohbet, `bge-m3` çok dilli embedding)
- **Kalite güvencesi:** ~70 otomatik test + GitHub Actions CI

## Mimari

**Clean Architecture (Ports & Adapters):** `domain → application → infrastructure`.
Çekirdek (`GraphRAGCore`) yalnızca soyut sözleşmelere (portlara) bağımlıdır;
somut teknolojiler (LLM, veritabanı, arama motoru) bu portları dolduran
değiştirilebilir adaptörlerdir. Bu sayede, örneğin bellek-içi depodan
PostgreSQL'e geçiş çekirdeğe hiç dokunmadan yapılabilir.

```
graphrag/
├── domain/           # Saf kurallar: entity'ler, sözleşmeler (portlar)
├── application/      # GraphRAGCore (kullanım senaryoları)
├── infrastructure/   # Adaptörler: LLM, vektör, graf, keyword, kalıcılık, KVKK
└── composition.py    # Bağımlılıkların bağlandığı tek yer
```

## Teknoloji yığını

Python · FastAPI · PostgreSQL + pgvector · SQLAlchemy · Ollama (qwen2.5:7b,
bge-m3) · rank-bm25 · pytest · Docker · GitHub Actions

## Kurulum & Çalıştırma

### 1. Bağımlılıklar
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Yerel modeller (Ollama)
```bash
ollama pull qwen2.5:7b
ollama pull bge-m3
```

### 3. (Opsiyonel) Kalıcılık — PostgreSQL
```bash
docker compose up -d
export DATABASE_URL="postgresql+psycopg://graphrag:graphrag@localhost:5432/graphrag"
```
> `DATABASE_URL` tanımlı değilse sistem bellek-içi (in-memory) modda çalışır —
> demo ve testler için veritabanı gerekmez.

### 4. API + Web arayüzü
```bash
uvicorn graphrag.api:app --reload
```
- Web arayüzü: <http://localhost:8000/app/>
- Otomatik API dokümanı (Swagger UI): <http://localhost:8000/docs>

### 5. Arşivi sıfırlama (gerektiğinde)
```bash
DATABASE_URL="postgresql+psycopg://graphrag:graphrag@localhost:5432/graphrag" \
    python3 scripts/reset_archive.py
```
> Tüm belge parçalarını, grafı ve denetim kayıtlarını siler. Sistem hazır/örnek
> belge içermez; tek veri kaynağı sizin yüklediğiniz belgelerdir.

### 6. Testler
```bash
python -m pytest
```

## Durum

Çalışan, uçtan uca bir sistem: belge yükleme → hibrit arama → graf bağlantı
bulma → yerel LLM cevabı; kalıcı PostgreSQL, REST API + web arayüzü, ~70
otomatik test ve sürekli entegrasyon (CI). Aktif olarak geliştirilmektedir.
