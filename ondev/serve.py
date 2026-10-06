"""Launch an OpenAI-compatible llama-server."""

import subprocess

from .bench import find_binary


def serve(model, host, port, ctx, binary=None, build_dir="build", threads=None):
    exe = binary or find_binary("llama-server", build_dir)
    if not exe:
        raise SystemExit("llama-server not found; run `ondev build` or pass --bin")
    cmd = [exe, "-m", model, "--host", host, "--port", str(port), "-c", str(ctx)]
    if threads:
        cmd += ["-t", str(threads)]
    return subprocess.call(cmd)
