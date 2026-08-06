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
- **Güvenlik:** API anahtarı ile korunan veri uçları (on-prem için `X-API-Key`)
- **Kalite güvencesi:** 127 otomatik test + GitHub Actions CI

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

### Bağımlılık yönü

Altın kural: **oklar hep içe doğrudur.** Dış katmanlar iç katmana bağımlıdır;
domain hiçbir somut teknolojiyi bilmez.

```mermaid
flowchart RL
    A["<b>Application</b><br/>GraphRAGCore<br/><i>ingest · answer · find_connection</i>"]
    I["<b>Infrastructure</b><br/>Ollama · PostgreSQL + pgvector · BM25<br/>KVKK maskeleme · belge okuyucular"]
    D["<b>Domain</b><br/>Entity'ler + Portlar (I...)<br/><i>saf kurallar, teknoloji yok</i>"]
    C["composition.py<br/><i>tek bağlama noktası</i>"]

    A -- "bağımlı" --> D
    I -- "portları uygular" --> D
    C -. "somut sınıfları seçer" .-> A
    C -.-> I
```

### Sorgu akışı

Belge yükleme iki indeksi birden besler; soru sorulduğunda ikisi ayrı ayrı
aranıp **RRF** ile birleştirilir ve cevap yalnızca bulunan parçalara dayanır.

```mermaid
flowchart TD
    subgraph ING["1 · Belge yükleme (ingest)"]
        DOC["Belge<br/>.txt · .pdf · .docx"] --> PII["KVKK maskeleme<br/>TCKN/VKN/IBAN → takma ad"]
        PII --> CHK["Parçalama<br/>(örtüşmeli chunking)"]
        CHK --> EMB["Embedding<br/>bge-m3"]
        CHK --> BMI["BM25 indeksleme"]
    end

    EMB --> VS[("Vektör deposu<br/>pgvector")]
    BMI --> KS[("Anahtar kelime<br/>indeksi")]

    subgraph SOR["2 · Sorgu"]
        Q["Soru"] --> QV["Anlamsal arama<br/>top-10"]
        Q --> QK["Anahtar kelime arama<br/>top-10"]
    end

    VS --> QV
    KS --> QK
    QV --> RRF["RRF<br/>(Reciprocal Rank Fusion)"]
    QK --> RRF
    RRF --> CTX["En iyi 3 parça<br/>= BAĞLAM"]
    CTX --> LLM["LLM<br/>qwen2.5:7b"]
    LLM --> ANS["Cevap<br/>+ kaynak gösterimi"]
```

> **Neden melez?** Anlamsal arama eş anlamlıları yakalar ama tam terimleri
> (sözleşme no, madde no) bulanıklaştırır; BM25 tam terimde güçlü, eş anlamlıda
> zayıftır. RRF, farklı ölçekli skorları sıra numarasıyla birleştirir.

## Teknoloji yığını

Python · FastAPI · PostgreSQL + pgvector · SQLAlchemy · Ollama (qwen2.5:7b,
bge-m3) · rank-bm25 · pytest · Docker · GitHub Actions

## Ön koşullar

| Gereksinim | Durum | Not |
|---|---|---|
| **Python 3.x** | Zorunlu | Sanal ortam (`venv`) önerilir |
| **[Ollama](https://ollama.com)** | Zorunlu | Kurulu **ve çalışır** olmalı (`ollama serve`); modeller yerelde çalışır |
| **Docker** | Opsiyonel | Yalnızca kalıcı depolama (PostgreSQL + pgvector) için |

> Docker kurmazsanız sistem **bellek-içi** modda tam olarak çalışır; yalnızca
> veriler uygulama kapanınca kaybolur.

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

### 4. Güvenlik — API anahtarı

```bash
export API_KEY="$(openssl rand -hex 24)"   # güçlü, rastgele bir anahtar üretin
```

`API_KEY` tanımlıysa tüm **veri uçları** `X-API-Key` başlığı ister:

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8000/stats
```

| Uç | Koruma |
|---|---|
| `/stats` · `/documents` · `/upload` · `/ask` · `/connection` · `/entities` · `/audit` | 🔒 Anahtar gerekli |
| `/` (sağlık) · `/app/` (arayüz) · `/docs` | Açık — veri içermez |

Web arayüzünde anahtar, sağ üstteki **kilit düğmesinden** girilir; yalnızca
tarayıcıda (`localStorage`) saklanır ve her isteğe başlık olarak eklenir.

> ⚠️ `API_KEY` tanımlı **değilse doğrulama kapalıdır** (yerel geliştirme
> kolaylığı). Bu durum sağlık ucunda `auth_enabled: false` olarak bildirilir.
> **On-premise kurulumda `API_KEY` mutlaka tanımlanmalıdır.**

### 5. API + Web arayüzü
```bash
uvicorn graphrag.api:app --reload
```
- Web arayüzü: <http://localhost:8000/app/>
- Otomatik API dokümanı (Swagger UI): <http://localhost:8000/docs>

### 6. Arşivi sıfırlama (gerektiğinde)
```bash
DATABASE_URL="postgresql+psycopg://graphrag:graphrag@localhost:5432/graphrag" \
    python3 scripts/reset_archive.py
```
> Tüm belge parçalarını, grafı ve denetim kayıtlarını siler. Sistem hazır/örnek
> belge içermez; tek veri kaynağı sizin yüklediğiniz belgelerdir.

### 7. Testler
```bash
python -m pytest
```
> 127 test; `DATABASE_URL` tanımlı değilse 5 PostgreSQL testi atlanır.

## Örnek kullanım

`ornek_belgeler/` klasöründe, sistemi denemek için hazırlanmış **5 sentetik
kurumsal belge** vardır (sözleşme, toplantı tutanağı, fizibilite raporu,
kurumsal yazışma, İK notu). İçlerindeki kişiler, şirketler ve numaralar
tamamen uydurmadır — gerçek kişisel veri içermez.

### 1) Belgeleri yükleyin
Web arayüzünde (<http://localhost:8000/app/>) **01 · Belge Yükle** kartına
`ornek_belgeler/` içindeki dosyaları sürükleyin. Ya da terminalden:

```bash
for f in ornek_belgeler/*.txt; do
  curl -s -X POST http://localhost:8000/upload \
    -H "X-API-Key: $API_KEY" -F "files=@$f" > /dev/null
done
```
> `API_KEY` tanımlamadıysanız `-H "X-API-Key: …"` satırını atlayın.

### 2) Soru sorun (RAG + kaynak gösterimi)
```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"question":"Gamma Danışmanlık ne iş yaptı?"}'
```
Cevapla birlikte **hangi belgeden geldiği** de döner:
```json
{
  "answer": "Gamma Danışmanlık, Proje Zeus kapsamında fizibilite çalışmasını yürüttü.",
  "sources": [{ "document_name": "03_gamma_fizibilite_raporu.txt", "text": "FİZİBİLİTE RAPORU …" }]
}
```
> Cevabın ifadesi çalıştırmadan çalıştırmaya değişebilir (LLM üretimi
> belirlenimci değildir); `sources` ise her zaman cevabın dayandığı gerçek
> belgeyi gösterir.

### 3) Gizli bağlantıyı bulun (grafın asıl değeri)
"Acme Holding" ile "Gamma Danışmanlık" **aynı belgede geçmez**; ortak
"Proje Zeus" üzerinden dolaylı bağlıdırlar:

```bash
curl -s -G http://localhost:8000/connection -H "X-API-Key: $API_KEY" \
  --data-urlencode "source=Acme Holding" \
  --data-urlencode "target=Gamma Danışmanlık"
```
```json
{ "result": "Bağlantı bulundu: Acme Holding -> Proje Zeus -> Gamma Danışmanlık  (güven: 0.25)" }
```

### 4) KVKK denetim kaydını görün
Belgelerdeki TCKN, VKN ve IBAN değerleri **işlemeye girmeden** maskelenir:

```bash
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/audit
```
Örnek belgelerde 7 kişisel veri maskelenir (3 TCKN, 2 IBAN, 2 VKN). Denetim
kaydı yalnızca veri **tipini** ve takma adı tutar; orijinal değer hiçbir yerde
saklanmaz (veri minimizasyonu).

## Durum

Çalışan, uçtan uca bir sistem: belge yükleme → hibrit arama → graf bağlantı
bulma → yerel LLM cevabı; kalıcı PostgreSQL, REST API + web arayüzü, 127
otomatik test ve sürekli entegrasyon (CI). Aktif olarak geliştirilmektedir.
