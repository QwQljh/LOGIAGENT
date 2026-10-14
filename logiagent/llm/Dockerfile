FROM python:3.9-slim@sha256:2d97f6910b16bd338d3060f261f53f144965f755599aab1acda1e13cf1731b1b AS weights
ARG MODEL_PROFILE=production
COPY profiles.json model-manifest-*.json download_model.py /build/
RUN --mount=type=cache,target=/model-cache python /build/download_model.py --profile ${MODEL_PROFILE} --output /models --cache /model-cache

FROM ollama/ollama:0.40.3@sha256:44833c52df2a164cc1238a96ce100123c8e54082b85c5e235a9cb5a7adc55f27
ARG MODEL_PROFILE=production
LABEL org.logiagent.component="llm" org.logiagent.backend="ollama" org.logiagent.profile=${MODEL_PROFILE}
COPY --from=weights /models /models
COPY start-model.sh /opt/logiagent/start-model.sh
RUN chmod +x /opt/logiagent/start-model.sh
ENV OLLAMA_MODELS=/models OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=-1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=32768 OLLAMA_NO_CLOUD=1
EXPOSE 11434
ENTRYPOINT ["/opt/logiagent/start-model.sh"]
