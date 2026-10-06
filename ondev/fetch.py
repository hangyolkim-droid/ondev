"""Fetch GGUF models. Small known-good aliases, or any URL."""

import os
import urllib.request

DEFAULT_BASE = "https://huggingface.co/{model}/resolve/main/{file}"

KNOWN = {
    "qwen2.5-0.5b": ("Qwen/Qwen2.5-0.5B-Instruct-GGUF", "qwen2.5-0.5b-instruct-q4_k_m.gguf"),
    "qwen2.5-3b": ("Qwen/Qwen2.5-3B-Instruct-GGUF", "qwen2.5-3b-instruct-q4_k_m.gguf"),
    "smollm2-360m": ("HuggingFaceTB/SmolLM2-360M-Instruct-GGUF", "smollm2-360m-instruct-q8_0.gguf"),
}


def resolve(model, url=None):
    if url:
        return url
    if model.startswith("http"):
        return model
    if model in KNOWN:
        repo, fn = KNOWN[model]
        return DEFAULT_BASE.format(model=repo, file=fn)
    raise SystemExit(f"unknown model alias {model!r}; pass --url to override")


def fetch(model, dest="models", url=None):
    os.makedirs(dest, exist_ok=True)
    link = resolve(model, url)
    target = os.path.join(dest, os.path.basename(link.split("?")[0]))
    if os.path.isfile(target):
        return target
    with urllib.request.urlopen(link, timeout=60) as resp, open(target, "wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    return target
