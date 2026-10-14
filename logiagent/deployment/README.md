# Model deployment

All submitted files stay inside tools/logiagent. Before the normal RESTGym b/l/v/a steps, run `bash tools/logiagent/prepare.sh`. It builds a separate local model image and starts the model. No image publishing account or model configuration edits are required. Internet is needed for the first build, not for subsequent model inference.

## Production model

The base is Ollama 0.40.3, fixed by image digest. The formal model is qwen3:14b (Q4_K_M), with manifest SHA256 bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8. All model, template, parameter and license blobs are installed into /models at build time and individually SHA256-verified. The runtime only registers the local qwen3-14b alias; it never performs an ollama pull. The three tool settings stay at http://127.0.0.1:11434/v1, qwen3-14b and EMPTY.

The custom alias sets context 32768. The server keeps one loaded model resident. Set request concurrency with OLLAMA_NUM_PARALLEL when running prepare.sh; the default is 2. For example, `OLLAMA_NUM_PARALLEL=2 bash tools/logiagent/prepare.sh` starts two request slots without rebuilding the image. Higher concurrency requires more memory and must be validated for the number of concurrent experiment instances; 24 GB VRAM is not a guarantee for arbitrary concurrency. A changed value requires stopping the existing owned container after active experiments finish, then preparing again. LOGIAGENT requests reasoning_effort=none on its OpenAI-compatible calls. Preparation checks nonempty generation, disabled thinking, context 32768 and positive GPU memory usage through /api/ps. Host GPU access still requires compatible NVIDIA drivers and Docker GPU support; the GPU's presence alone is insufficient. Formal deployment requests 24 GB VRAM and 32 GB system RAM; this is a conservative allocation, not a newly measured minimum.

The model port is published only at host loopback 127.0.0.1:11434. A host-network probe container uses the same network mode as RESTGym's tool. Preparation does not change RESTGym or run b/l/v/a. It enables the tool after successful checks. Keep the model running through all experiments, then run `bash tools/logiagent/deployment/stop-model.sh`.

Repeated preparation checks the matching image/container again. A different owned profile or an unrelated same-name container requires explicit cleanup; it is never overwritten automatically. Readiness defaults to 1800 seconds, configurable with LOGIAGENT_READY_TIMEOUT. Inspect `docker logs logiagent-llm` if loading fails.

## Local small-model test

Run `bash tools/logiagent/prepare.sh --test` to use qwen3:0.6b (manifest SHA256 7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435). It uses the same service, alias and context with different embedded weights. Output explicitly states TEST ONLY. Stop the owned model before switching profiles. Do not use the test profile for official results.

Small-model integration cannot establish the 14B model's GPU memory needs, latency or testing effectiveness. Q4_K_M with Ollama also differs from the previous AWQ/vLLM experiment; previous results must not be represented as measured with this backend. The formal model may be built without loading it on this local GPU.

Docker Desktop local tests need enabled host networking and GPU support. Formal deployment targets Linux. CPU-only fallback does not count as successful preparation.

## Rebuild and cleanup

To rebuild model packaging explicitly:

```bash
docker build --platform linux/amd64 --build-arg MODEL_PROFILE=production -t logiagent-llm:ollama-production-1.0.2 tools/logiagent/llm
```

Stop the old model, then prepare again. Cleanup removes only the labelled model container and retains built images. No model weights enter Git or the source ZIP.
