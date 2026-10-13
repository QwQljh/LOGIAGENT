# LOGIAGENT

LOGIAGENT 使用 LLM 生成 REST 请求序列，复用响应资源，并进行序列和参数变异，支持 OpenAPI JSON 和 YAML。

## 一次准备

将完整目录放到 RESTGym 的 `tools/logiagent`，在平台根目录执行：

```bash
bash tools/logiagent/prepare.sh
```

脚本检查 GPU，下载固定版本的 Ollama 基础镜像和 Qwen3-14B Q4_K_M 权重，构建本地模型镜像，启动模型，从 host 网络容器检查实际生成，并启用 LOGIAGENT。不需要登录我们的镜像仓库，不需要修改模型地址、名称或密钥。服务地址为 `http://127.0.0.1:11434/v1`，名称为 `qwen3-14b`，无密钥认证，`EMPTY` 是客户端占位值。

正式部署要求一张至少 24GB 显存的 NVIDIA GPU、兼容驱动和 Docker GPU 支持，8 CPU、32GB 系统内存；被测 API 容器可能另需资源。首次准备需要联网，下载量约 13GB，建议至少预留 60GB 磁盘用于镜像和构建缓存。权重进入构建后的模型镜像，推理时不再下载。

## 正常执行 RESTGym

准备成功后，在平台选择接口、工具和预算，自行依次执行：

```bash
./restgym.sh b
./restgym.sh l
./restgym.sh v
./restgym.sh a
```

准备脚本不执行这四步，也不修改 RESTGym。`b` 构建工具和 API 镜像，不构建或启动模型。工具镜像名为 `restgym-logiagent`，修改源代码或配置后要重建。模型跨多次实验保持运行，全部完成后再停止：

```bash
bash tools/logiagent/deployment/stop-model.sh
```

## 文件和问题排查

序列测试算法、固定依赖和工具入口不变；模型调用适配了 Ollama 关闭 thinking 的参数，内部默认 LLM_BACKEND 为 ollama。`llm/` 保存模型 Dockerfile 和固定配置；`deployment/` 保存检查和清理辅助脚本；`restgym-tool-manifest.yaml` 描述正式资源要求，未知身份、工具许可证和引用字段已注释。

重复准备复用匹配镜像和容器，并再次检查生成。遇到同名冲突容器不会自动覆盖。失败时查看 `docker logs logiagent-llm`，检查 GPU、端口 11434、host 网络。验证失败不会显示准备成功。

RESTGym 收集 HTTP 交互和日志，工具内部额外持久化默认关闭（`LOGIAGENT_SAVE_ARTIFACTS=false`）。工具提示词预算和模型服务上下文是不同设置。外部 OpenAPI 引用需先打包。

[部署细节](deployment/README.md) | [English](README.md)
