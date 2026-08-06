#!/usr/bin/env bash
#
# Tek komutla tüm sistemi başlatır.
#
#   ./scripts/baslat.sh
#
# Sırasıyla: Ollama → Docker/PostgreSQL → API sunucusu; ardından modelleri
# ÖNDEN ISITIR (ilk soru 12 saniye yerine ~6 saniye sürsün) ve her bileşenin
# gerçekten hazır olduğunu doğrular.
#
# Docker kurulu değilse sistem bellek-içi modda çalışmaya devam eder.

set -uo pipefail
cd "$(dirname "$0")/.."

MAVI="\033[0;34m"; YESIL="\033[0;32m"; SARI="\033[0;33m"; KIRMIZI="\033[0;31m"; BITIR="\033[0m"
adim() { echo -e "\n${MAVI}▸ $1${BITIR}"; }
ok()   { echo -e "  ${YESIL}✓${BITIR} $1"; }
uyar() { echo -e "  ${SARI}!${BITIR} $1"; }
hata() { echo -e "  ${KIRMIZI}✗${BITIR} $1"; }

OLLAMA_URL="http://localhost:11434"
API_URL="http://localhost:8000"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://graphrag:graphrag@localhost:5432/graphrag}"

# --- API anahtarı: bir kez üretilir, dosyada saklanır (git'e girmez) ---------
ANAHTAR_DOSYASI=".api_key"
if [ ! -f "$ANAHTAR_DOSYASI" ]; then
    openssl rand -hex 32 > "$ANAHTAR_DOSYASI"
fi
export API_KEY="$(cat "$ANAHTAR_DOSYASI")"

# --- 1) Ollama ---------------------------------------------------------------
adim "Ollama (yerel LLM sunucusu)"
if curl -sf "$OLLAMA_URL/api/tags" -o /dev/null --max-time 3; then
    ok "zaten çalışıyor"
else
    uyar "çalışmıyor, başlatılıyor…"
    nohup ollama serve >/tmp/ollama.log 2>&1 &
    curl -sf --retry 30 --retry-connrefused --retry-delay 1 "$OLLAMA_URL/api/tags" -o /dev/null \
        && ok "başlatıldı" || { hata "Ollama başlatılamadı"; exit 1; }
fi

# NOT: `ollama list | grep -q` KULLANILMAZ. `grep -q` ilk eşleşmede çıkar,
# bu da yukarı akışa SIGPIPE gönderir; `set -o pipefail` altında boru hattı
# başarısız sayılır ve mevcut model "eksik" görünür.
MODEL_LISTESI="$(ollama list 2>/dev/null || true)"
for model in qwen2.5:7b bge-m3; do
    case "$MODEL_LISTESI" in
        *"${model%%:*}"*) ok "model hazır: $model" ;;
        *) hata "model eksik: $model  →  ollama pull $model"; exit 1 ;;
    esac
done

# --- 2) PostgreSQL -----------------------------------------------------------
adim "PostgreSQL (kalıcı depolama)"
if ! docker info >/dev/null 2>&1; then
    uyar "Docker kapalı, açılıyor… (biraz sürebilir)"
    open -a Docker 2>/dev/null || true
    for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
if docker info >/dev/null 2>&1; then
    docker compose up -d >/dev/null 2>&1
    for _ in $(seq 1 30); do
        DURUM="$(docker compose ps --format '{{.Status}}' 2>/dev/null || true)"
        case "$DURUM" in *healthy*) break ;; esac
        sleep 2
    done
    DURUM="$(docker compose ps --format '{{.Status}}' 2>/dev/null || true)"
    case "$DURUM" in
        *healthy*) ok "hazır (healthy)" ;;
        *) uyar "sağlık kontrolü geçmedi — sistem bellek-içi moda düşebilir" ;;
    esac
else
    uyar "Docker açılamadı; sistem bellek-içi modda çalışacak (veriler kalıcı olmaz)"
    unset DATABASE_URL
fi

# --- 3) API sunucusu ---------------------------------------------------------
adim "API sunucusu"
pkill -f "uvicorn graphrag.api" 2>/dev/null; sleep 1
PY_BIN=".venv/bin/python3"; [ -x "$PY_BIN" ] || PY_BIN="python3"
nohup "$PY_BIN" -m uvicorn graphrag.api:app --port 8000 >/tmp/graphrag_api.log 2>&1 &
curl -sf --retry 30 --retry-connrefused --retry-delay 1 "$API_URL/" -o /dev/null \
    && ok "çalışıyor ($API_URL)" \
    || { hata "API başlatılamadı — bkz. /tmp/graphrag_api.log"; exit 1; }

# --- 4) Modelleri önden ısıt -------------------------------------------------
adim "Modeller ısıtılıyor (ilk sorunun 12 sn sürmemesi için)"
curl -sf "$OLLAMA_URL/api/embeddings" -o /dev/null --max-time 120 \
     -d '{"model":"bge-m3","prompt":"ısınma","keep_alive":"30m"}' \
    && ok "embedding modeli bellekte (bge-m3)" || uyar "embedding ısıtılamadı"
curl -sf "$OLLAMA_URL/api/chat" -o /dev/null --max-time 180 \
     -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"merhaba"}],"stream":false,"keep_alive":"30m"}' \
    && ok "sohbet modeli bellekte (qwen2.5:7b)" || uyar "sohbet modeli ısıtılamadı"

# --- 5) Özet -----------------------------------------------------------------
adim "Durum"
curl -s "$API_URL/" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"  LLM        : {'hazır' if d['llm'] else 'KAPALI'}\")
print(f\"  Depolama   : {d['storage']}\")
print(f\"  Doğrulama  : {'açık' if d['auth_enabled'] else 'KAPALI'}\")
print(f\"  Modeller   : {d['chat_model']} · {d['embed_model']}\")
"
curl -s -H "X-API-Key: $API_KEY" "$API_URL/stats" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"  Arşiv      : {d['documents']} belge · {d['chunks']} parça · \"
      f\"{d['entities']} varlık · {d['pii_masked']} maskelenen veri\")
"

echo -e "\n${YESIL}▸ Sistem hazır${BITIR}"
echo "  Arayüz      : $API_URL/app/"
echo "  API anahtarı: $API_KEY"
echo "  (Anahtarı arayüzde sağ üstteki kilit düğmesinden bir kez girin.)"
