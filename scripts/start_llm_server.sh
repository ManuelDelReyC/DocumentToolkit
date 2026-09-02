#!/bin/bash
MODELO="$HOME/Proyectos/llama/models/qwen2.5-coder-7b-instruct-q4_k_m-00001-of-00002.gguf"
NGL="${1:-12}"
CTX="${2:-6144}"

~/Proyectos/llama/src/llama.cpp/build/bin/llama-server \
  -m "$MODELO" \
  --host 127.0.0.1 \
  --port 8080 \
  -ngl "$NGL" \
  -c "$CTX" \
  -t 10 \
  -n 2048 \
  --timeout 300 \
  --mlock