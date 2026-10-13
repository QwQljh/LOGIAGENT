"""Install fixed Ollama model blobs; downloads are build-time only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import threading
import time
from urllib.request import Request, urlopen


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


class Progress:
    def __init__(self):
        self.state = ('Preparing model files', None, None)
        self.stop = threading.Event()

    def show(self):
        stage, done, total = self.state
        detail = '' if not total else f': {done/total:.1%} ({done}/{total} bytes)'
        print('[Model preparation] '+stage+detail, flush=True)

    def update(self, stage, done=None, total=None):
        self.state = (stage, done, total)

    def __enter__(self):
        def heartbeat():
            while not self.stop.wait(15):
                self.show()
        self.thread = threading.Thread(target=heartbeat, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()


def download(profile, output, build_root, cache=None):
    print('Preparing fixed model: '+profile['model'], flush=True)
    with Progress() as progress:
        _download(profile, output, build_root, cache, progress)


def _download(profile, output, build_root, cache, progress):
    manifest_bytes = (build_root/profile['manifest_file']).read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != profile['manifest_sha256']:
        raise ValueError('Model manifest checksum mismatch')
    manifest = json.loads(manifest_bytes)
    blobs = output/'blobs'
    blobs.mkdir(parents=True, exist_ok=True)
    cache = blobs if cache is None else cache
    cache.mkdir(parents=True, exist_ok=True)
    entries = [manifest['config']]+manifest['layers']
    for entry in entries:
        digest, size = entry['digest'], entry['size']
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest) or not isinstance(size, int) or size < 0:
            raise ValueError('Invalid blob metadata')
        final = cache/digest.replace(':', '-')
        progress.update('Checking cached blob '+digest[:19])
        if final.exists() and final.stat().st_size == size and checksum(final) == digest[7:]:
            print('Verified cached blob '+digest[:19], flush=True)
            if final.parent != blobs:
                progress.update('Installing verified blob '+digest[:19])
                shutil.copyfile(final, blobs/final.name)
            continue
        partial = final.with_suffix('.part')
        for attempt in range(6):
            try:
                offset = partial.stat().st_size if partial.exists() else 0
                if offset > size:
                    partial.unlink()
                    offset = 0
                progress.update('Downloading '+digest[:19], offset, size)
                progress.show()
                while offset < size:
                    end = min(size-1, offset+64*1024*1024-1)
                    headers = {'User-Agent': 'LOGIAGENT-model-build'}
                    headers['Range'] = f'bytes={offset}-{end}'
                    request = Request('https://registry.ollama.ai/v2/library/qwen3/blobs/'+digest, headers=headers)
                    with urlopen(request, timeout=120) as response:
                        if offset and response.status != 206:
                            raise ValueError('Resume not supported')
                        elif offset and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                            raise ValueError('Invalid resumed range')
                        written, marker = offset, offset//(64*1024*1024)
                        with partial.open('ab' if offset else 'wb') as stream:
                            remaining = end-offset+1
                            while remaining:
                                chunk = response.read(min(4*1024*1024, remaining))
                                if not chunk:
                                    raise ValueError('Incomplete range')
                                stream.write(chunk)
                                written += len(chunk)
                                progress.update('Downloading '+digest[:19], written, size)
                                remaining -= len(chunk)
                                if written > size:
                                    raise ValueError('Oversized blob')
                                if written//(64*1024*1024) > marker:
                                    marker = written//(64*1024*1024)
                                    print(f'{digest[:19]}: {written/size:.1%} ({written}/{size} bytes)', flush=True)
                        offset = partial.stat().st_size
                if partial.stat().st_size != size:
                    raise ValueError('Incomplete blob')
                progress.update('Verifying SHA256 '+digest[:19])
                if checksum(partial) != digest[7:]:
                    partial.unlink()
                    raise ValueError('Blob checksum mismatch')
                partial.replace(final)
                if final.parent != blobs:
                    progress.update('Installing verified blob '+digest[:19])
                    shutil.copyfile(final, blobs/final.name)
                print('Verified '+digest+f' ({size} bytes)', flush=True)
                break
            except Exception as exc:
                if attempt == 5:
                    raise
                progress.update(f'Retrying {digest[:19]} after {type(exc).__name__} (attempt {attempt+2}/6)')
                progress.show()
                time.sleep(min(30, 2**attempt))
    tag = profile['model'].split(':', 1)[1]
    progress.update('Writing model manifest and context settings')
    destination = output/'manifests/registry.ollama.ai/library/qwen3'/tag
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(manifest_bytes)
    config = json.loads((blobs/manifest['config']['digest'].replace(':', '-')).read_text())
    (output/'model-profile.json').write_text(json.dumps(dict(profile, details=config), indent=2)+'\n')
    (output/'Modelfile').write_text('FROM '+profile['model']+'\nPARAMETER num_ctx '+str(profile['num_ctx'])+'\n')
    print('Model files and SHA256 verification complete.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=('production', 'test'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path)
    args = parser.parse_args()
    build_root = Path(__file__).parent
    profile = json.loads((build_root/'profiles.json').read_text())[args.profile]
    download(profile, args.output, build_root, args.cache)
