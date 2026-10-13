#!/usr/bin/env bash
set -Eeuo pipefail
ollama serve &
SERVER_PID=$!
cleanup() { kill -TERM "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
READY=false
for ((attempt=0; attempt<120; attempt++)); do
  kill -0 "$SERVER_PID" 2>/dev/null || { echo 'Ollama exited before readiness.' >&2; exit 1; }
  if ollama list >/dev/null 2>&1; then READY=true; break; fi
  sleep 1
done
[ "$READY" = true ] || { echo 'Ollama startup timed out.' >&2; exit 1; }
# FROM resolves the model already installed in /models; no pull is performed.
ollama create qwen3-14b -f /models/Modelfile
echo 'LOGIAGENT Ollama model registered from embedded weights.'
wait "$SERVER_PID"
