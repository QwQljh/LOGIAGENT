"""Validate real generation, thinking control, context and GPU model loading."""
import json
import os
from pathlib import Path
import time
import threading
from urllib.request import Request, urlopen


def call(url, payload=None, timeout=120):
    request = Request(url, data=None if payload is None else json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer EMPTY'})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def check_once(base_url, timeout=120):
    models = call(base_url+'/models', timeout=min(timeout, 10))
    names = {row['id'].removesuffix(':latest') for row in models.get('data', [])}
    if 'qwen3-14b' not in names:
        raise ValueError('Expected model alias qwen3-14b is missing')
    result = call(base_url+'/chat/completions', {'model': 'qwen3-14b',
                  'messages': [{'role': 'user', 'content': 'Reply with OK.'}],
                  'max_tokens': 64, 'temperature': 0, 'reasoning_effort': 'none'}, timeout)
    message = result['choices'][0]['message']
    content = message.get('content')
    if not isinstance(content, str) or not content.strip():
        raise ValueError('Model did not return an answer')
    if message.get('reasoning') or message.get('reasoning_content') or '<think>' in content:
        raise ValueError('Thinking was not disabled')
    runtime = call(base_url.removesuffix('/v1')+'/api/ps', timeout=10)
    loaded = next((row for row in runtime.get('models', [])
                   if row.get('name', '').removesuffix(':latest') == 'qwen3-14b'), None)
    if not loaded or loaded.get('size_vram', 0) <= 0:
        raise ValueError('Model is not loaded on the GPU')
    if loaded.get('context_length') != 32768:
        raise ValueError('Model context is not 32768')
    return {'answer': content.strip(), 'gpu_bytes': loaded['size_vram'],
            'context_length': loaded['context_length'], 'details': loaded.get('details')}


def main():
    config = json.loads(Path('/model-config.json').read_text())
    expected = {'LLM_BASE_URL': 'http://127.0.0.1:11434/v1', 'LLM_MODEL': 'qwen3-14b', 'LLM_API_KEY': 'EMPTY'}
    if config != expected:
        raise SystemExit('Restore the supplied model-config.json before preparation')
    duration = int(os.getenv('LOGIAGENT_READY_TIMEOUT', '1800'))
    if duration <= 0:
        raise ValueError('Readiness timeout must be positive')
    deadline, error = time.monotonic()+duration, None
    while time.monotonic() < deadline:
        try:
            result = check_once(os.getenv('LOGIAGENT_CHECK_URL', expected['LLM_BASE_URL']), max(1, min(120, deadline-time.monotonic())))
            print('Model, generation, no-thinking, GPU and context passed: '+json.dumps(result), flush=True)
            break
        except Exception as exc:
            error = exc
            print('Waiting for model: '+str(exc), flush=True)
            time.sleep(max(0, min(10, deadline-time.monotonic())))
    else:
        raise SystemExit('Model readiness failed: '+str(error))


if __name__ == '__main__':
    stopped = threading.Event()
    started = time.monotonic()

    def heartbeat():
        while not stopped.wait(15):
            print(f'[Model startup] Loading or checking generation; elapsed {time.monotonic()-started:.0f}s.', flush=True)

    worker = threading.Thread(target=heartbeat, daemon=True)
    worker.start()
    try:
        main()
    finally:
        stopped.set()
        worker.join()
