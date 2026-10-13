# Model settings

The previous experiment used vLLM with Qwen3-14B-AWQ. The packaged deployment uses Ollama with qwen3:14b (Q4_K_M). The local connectivity test uses qwen3:0.6b. These are different weights and quantization formats; the connectivity test does not establish equivalent testing effectiveness.

| Setting | Previous vLLM deployment | Packaged Ollama deployment |
| --- | --- | --- |
| Client model name | `qwen3-14b` | Local alias `qwen3-14b` |
| OpenAI-compatible endpoint | Port 11434, `/v1` | Port 11434, `/v1` |
| Model context | `--max-model-len 32768` | Alias `PARAMETER num_ctx 32768`; server `OLLAMA_CONTEXT_LENGTH=32768` |
| Thinking | `enable_thinking: false` in chat template settings | Client sends `reasoning_effort: none`; preparation checks an actual response |
| Model residence | vLLM server owns the model | `OLLAMA_KEEP_ALIVE=-1`, one loaded model, one parallel request |
| Quantization | AWQ | Model's fixed Q4_K_M GGUF weights |
| GPU allocation | `--gpu-memory-utilization 0.9` | Ollama selects GPU offload; preparation checks positive GPU memory use |
| Precision and model code | `--dtype float16`, `--trust-remote-code` | No direct translation for the GGUF runtime |
| Tool parser | `--enable-auto-tool-choice --tool-call-parser hermes` | LOGIAGENT uses chat completion content and its existing parsing; these vLLM flags are not passed to Ollama |

The tool's prompt and output token budgets remain unchanged. A successful small-model test verifies deployment and API compatibility only. The formal model still requires validation on the organizers' GPU hardware.
