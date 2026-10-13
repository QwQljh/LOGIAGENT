#!/usr/bin/env bash
set -Eeuo pipefail
CONTAINER=logiagent-llm
if ! docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo 'No LOGIAGENT model container exists.'
  exit 0
fi
OWNER="$(docker inspect -f '{{ index .Config.Labels "org.logiagent.component" }}' "$CONTAINER")"
if [ "$OWNER" != llm ]; then
  echo 'Refusing to stop a container not labelled as a LOGIAGENT model.' >&2
  exit 1
fi
docker stop "$CONTAINER"
docker rm "$CONTAINER"
