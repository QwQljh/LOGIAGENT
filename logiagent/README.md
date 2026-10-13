# LOGIAGENT

LOGIAGENT tests REST APIs with LLM-generated request sequences, response-derived resources, and sequence and parameter mutation. It accepts OpenAPI JSON and YAML.

## Prepare once

Place the complete directory at `tools/logiagent` in RESTGym. From the RESTGym root, run:

```bash
bash tools/logiagent/prepare.sh
```

The script checks GPU access, downloads the pinned Ollama base and Qwen3-14B Q4_K_M model blobs, builds a local model image, starts the model, checks actual generation from a host-network container, and enables LOGIAGENT. No model-registry login or edits to the three model settings are needed. The service uses `http://127.0.0.1:11434/v1`, model alias `qwen3-14b`, and client placeholder key `EMPTY` without API authentication.

Production requests one NVIDIA GPU with at least 24 GB VRAM, compatible drivers and Docker GPU support, 8 CPUs and 32 GB system memory. RESTGym API containers may require additional resources. First-time preparation requires Internet access and approximately 13 GB of downloads; allow at least 60 GB free disk for images and build cache. Weights are included in the built image and are not downloaded during inference.

## Run RESTGym normally

After preparation succeeds, select the APIs, tools and budget in RESTGym, then run these commands yourself:

```bash
./restgym.sh b
./restgym.sh l
./restgym.sh v
./restgym.sh a
```

Preparation does not invoke these commands or modify RESTGym. `b` builds the tool/API images, not the model. The tool image is `restgym-logiagent`; rebuild after changing source or configuration. Keep the model running across experiments. Stop it after all experiments:

```bash
bash tools/logiagent/deployment/stop-model.sh
```

## Files and output

The sequence-testing algorithms and pinned dependencies remain unchanged. Model calls now use the Ollama thinking-control parameter; the internal default LLM_BACKEND is ollama. `llm/` contains the separate model Dockerfile and fixed deployment profiles. `deployment/` contains readiness and cleanup helpers. `restgym-tool-manifest.yaml` describes production requirements; unknown identity/license/citation fields are commented out.

Repeated preparation reuses matching images and containers and verifies generation again. Conflicting containers are not automatically replaced. On failure, inspect `docker logs logiagent-llm` and check GPU compatibility, port 11434 and host networking. Failed preparation never reports success.

RESTGym supplies the target address, run metadata and budget, and collects HTTP interactions and logs. Additional tool-local artifacts remain disabled (`LOGIAGENT_SAVE_ARTIFACTS=false`). Internal `LLM_CONTEXT_WINDOW` controls the prompt budget, not the server's context capacity. Bundle external OpenAPI references first.

[Deployment details](deployment/README.md) | [中文说明](README_zh.md)
