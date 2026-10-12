#!/bin/bash
# Script de inicio para llama.cpp server.
#
# Uso:
#   ./scripts/start_llm_server.sh [ruta_modelo] [capas_gpu] [contexto]
#
# También se pueden usar variables de entorno:
#   LLAMA_SERVER  -> ruta al binario llama-server
#   LLAMA_MODEL   -> ruta al modelo .gguf
#   LLAMA_NGL     -> capas GPU (default: 99)
#   LLAMA_CTX     -> tamaño de contexto (default: 8192)
#   LLAMA_EXTRA   -> argumentos extra para llama-server

set -e

LLAMA_SERVER="${LLAMA_SERVER:-$HOME/Proyectos/llama/src/llama.cpp/build/bin/llama-server}"
MODELO="${1:-${LLAMA_MODEL:-$HOME/Proyectos/llama/models/Qwen3-14B-Q5_K_M.gguf}}"
NGL="${2:-${LLAMA_NGL:-99}}"
CTX="${3:-${LLAMA_CTX:-8192}}"

# Verifica que el binario existe y es ejecutable
if [ ! -x "$LLAMA_SERVER" ]; then
    echo "❌ llama-server no encontrado o no ejecutable: $LLAMA_SERVER"
    echo "   Define LLAMA_SERVER o instala/compila llama.cpp en esa ruta."
    exit 1
fi

# Verifica que el modelo existe
if [ ! -f "$MODELO" ]; then
    echo "❌ Modelo no encontrado: $MODELO"
    echo "Uso: ./scripts/start_llm_server.sh [ruta_modelo] [capas_gpu] [contexto]"
    echo "   También puedes definir LLAMA_MODEL."
    exit 1
fi

echo "🚀 Iniciando llama.cpp server..."
echo "   Binario: $LLAMA_SERVER"
echo "   Modelo: $(basename "$MODELO")"
echo "   Capas GPU: $NGL"
echo "   Contexto: $CTX"
echo "   URL: http://localhost:8080"
echo ""

# shellcheck disable=SC2086
"$LLAMA_SERVER" \
  -m "$MODELO" \
  --host 127.0.0.1 \
  --port 8080 \
  -ngl "$NGL" \
  -c "$CTX" \
  -t 10 \
  -n 2048 \
  --timeout 300 \
  --metrics \
  --perf \
  -ctk q8_0 \
  -ctv q8_0 \
  $LLAMA_EXTRA
