# Supplementary deployment information

This package includes the completed RESTGym manifest and an automated Dockerfile-based local model deployment. Run `bash tools/logiagent/prepare.sh` once before RESTGym's usual `b/l/v/a` commands. It downloads fixed public base images and model blobs, builds the local model image, starts it with NVIDIA GPU access, verifies actual generation, GPU loading and context, and enables the tool. There are no additional operations between `b/l/v/a`.

The production model is Ollama qwen3:14b (Q4_K_M), not the previous Qwen3-14B-AWQ/vLLM deployment. The source archive contains no weights; initial construction requires Internet access. Runtime uses embedded weights and does not pull a model. It keeps the tool's model address/name/key preconfigured. The small model is only for author-side integration checks, not official results.

This is a Dockerfile-based build-on-site delivery, not a pre-published model image. Please confirm this delivery is acceptable under the request for an LLM Docker image. If prebuilt images are required, the same Dockerfile can be used to export the completed model image separately.

Formal 14B loading has not been validated on this author's 8 GB GPU. Previous experiment results used a different backend/quantization and do not establish this deployment's effectiveness. Consult the deployment README and accompanying verification report for completed checks.
