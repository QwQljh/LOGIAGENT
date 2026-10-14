#!/usr/bin/env bash
set -Eeuo pipefail
TOOL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROFILE=production
if [ "${1:-}" = --test ]; then PROFILE=test; shift; fi
if [ "$#" -ne 0 ]; then echo "Usage: $0 [--test]" >&2; exit 2; fi
PARALLEL="${OLLAMA_NUM_PARALLEL:-2}"
[[ "$PARALLEL" =~ ^[1-9][0-9]*$ ]] || { echo 'OLLAMA_NUM_PARALLEL must be a positive integer (for example 1 or 2).' >&2; exit 2; }
echo "Model request concurrency: $PARALLEL. Higher values require more GPU memory."
command -v docker >/dev/null || { echo 'Docker is required.' >&2; exit 1; }
docker info >/dev/null || { echo 'Start the Docker engine first.' >&2; exit 1; }
IMAGE="logiagent-llm:ollama-${PROFILE}-1.0.2"
CONTAINER=logiagent-llm
OLLAMA_IMAGE=ollama/ollama:0.40.3@sha256:44833c52df2a164cc1238a96ce100123c8e54082b85c5e235a9cb5a7adc55f27
PROBE_IMAGE=python:3.9-slim@sha256:2d97f6910b16bd338d3060f261f53f144965f755599aab1acda1e13cf1731b1b
echo "[1/4] Checking Docker and GPU access (profile: $PROFILE)."
if ! docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo 'Checking NVIDIA GPU access before downloading weights.'
  GPU_IMAGE="$OLLAMA_IMAGE"
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then GPU_IMAGE="$IMAGE"; fi
  GPU_MIB="$(docker run --rm --gpus all --entrypoint nvidia-smi "$GPU_IMAGE" --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 | tr -d '[:space:]')"
  MIN_MIB=23000
  if [ "$PROFILE" = test ]; then MIN_MIB=6000; fi
  [[ "$GPU_MIB" =~ ^[0-9]+$ ]] && [ "$GPU_MIB" -ge "$MIN_MIB" ] || { echo 'Insufficient GPU VRAM or unavailable GPU runtime.' >&2; exit 1; }
fi
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo '[2/4] Downloading and building Ollama/model image. First preparation needs Internet access.'
  docker build --progress plain --platform linux/amd64 --build-arg "MODEL_PROFILE=$PROFILE" -t "$IMAGE" -f "$TOOL_DIR/llm/Dockerfile" "$TOOL_DIR/llm"
else
  echo '[2/4] Existing model image found; reusing it.'
fi
COMPONENT="$(docker image inspect -f '{{ index .Config.Labels "org.logiagent.component" }}' "$IMAGE")"
BACKEND="$(docker image inspect -f '{{ index .Config.Labels "org.logiagent.backend" }}' "$IMAGE")"
IMAGE_PROFILE="$(docker image inspect -f '{{ index .Config.Labels "org.logiagent.profile" }}' "$IMAGE")"
if [ "$COMPONENT" != llm ] || [ "$BACKEND" != ollama ] || [ "$IMAGE_PROFILE" != "$PROFILE" ]; then
  echo 'Unexpected image labels. Inspect the image before rebuilding.' >&2; exit 1
fi
echo '[3/4] Starting the model container.'
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  OWNER="$(docker inspect -f '{{ index .Config.Labels "org.logiagent.component" }}' "$CONTAINER")"
  CURRENT_IMAGE="$(docker inspect -f '{{.Image}}' "$CONTAINER")"
  WANTED_IMAGE="$(docker image inspect -f '{{.Id}}' "$IMAGE")"
  if [ "$OWNER" != llm ] || [ "$CURRENT_IMAGE" != "$WANTED_IMAGE" ]; then
    echo 'Conflicting logiagent-llm container. Stop your previous owned model before switching.' >&2; exit 1
  fi
  CURRENT_PARALLEL="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER" | sed -n 's/^OLLAMA_NUM_PARALLEL=//p')"
  CURRENT_PARALLEL="${CURRENT_PARALLEL:-1}"
  if [ "$CURRENT_PARALLEL" != "$PARALLEL" ]; then
    echo "Existing model container uses concurrency $CURRENT_PARALLEL; requested $PARALLEL. Finish active experiments, run tools/logiagent/deployment/stop-model.sh, then prepare again. The model image is retained." >&2
    exit 1
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" != true ]; then docker start "$CONTAINER" >/dev/null; fi
else
  docker run -d --name "$CONTAINER" --gpus all -e "OLLAMA_NUM_PARALLEL=$PARALLEL" --label org.logiagent.component=llm --label "org.logiagent.profile=$PROFILE" -p 127.0.0.1:11434:11434 "$IMAGE" >/dev/null
fi
echo '[4/4] Waiting for model loading; checking generation, thinking control, GPU and context.'
if ! docker run --rm --network host -e "LOGIAGENT_READY_TIMEOUT=${LOGIAGENT_READY_TIMEOUT:-1800}" -v "$TOOL_DIR/deployment:/checks:ro" -v "$TOOL_DIR/model-config.json:/model-config.json:ro" "$PROBE_IMAGE" python -u /checks/check_model.py; then
  docker logs --tail 80 "$CONTAINER" >&2 || true
  echo 'Preparation failed. Check model logs, GPU access, port 11434 and host networking.' >&2; exit 1
fi
printf 'enabled: true\n' > "$TOOL_DIR/restgym-tool-config.yml"
if docker image inspect restgym-logiagent:latest >/dev/null 2>&1; then
  TOOL_BACKEND="$(docker image inspect -f '{{ index .Config.Labels "org.logiagent.backend" }}' restgym-logiagent:latest)"
  TOOL_VERSION="$(docker image inspect -f '{{ index .Config.Labels "org.logiagent.version" }}' restgym-logiagent:latest)"
  if [ "$TOOL_BACKEND" != ollama ] || [ "$TOOL_VERSION" != 1.0.2 ]; then
    OLD_ID="$(docker image inspect -f '{{.Id}}' restgym-logiagent:latest)"
    OLD_ID="${OLD_ID#sha256:}"
    BACKUP_TAG="restgym-logiagent:before-ollama-${OLD_ID:0:12}"
    docker tag restgym-logiagent:latest "$BACKUP_TAG"
    docker image rm restgym-logiagent:latest >/dev/null
    echo "Old tool image retained as $BACKUP_TAG; RESTGym b will build the new default image."
  fi
fi
if [ "$PROFILE" = test ]; then echo 'TEST ONLY: Qwen3-0.6B uses the tool alias qwen3-14b. Not for official experiments.'; fi
echo 'Preparation succeeded. No edits to the three model settings are required.'
echo 'From the RESTGym root, run ./restgym.sh b, then l, v and a yourself.'
echo 'Keep the model running; stop it after all experiments with tools/logiagent/deployment/stop-model.sh.'
