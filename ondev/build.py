"""Build llama.cpp for the target device with the correct flags."""

import os
import shutil
import subprocess

from . import presets

LLAMA_REPO = "https://github.com/ggml-org/llama.cpp"


def ensure_source(src):
    if not os.path.isdir(src):
        subprocess.run(["git", "clone", "--depth", "1", LLAMA_REPO, src], check=True)
    return src


def has_ninja():
    return shutil.which("ninja") is not None


def build(profile, env, src="third_party/llama.cpp", build_dir="build", dry_run=False):
    log = []
    if not dry_run:
        ensure_source(src)
    ninja = has_ninja()
    configure = presets.configure_command(profile, env, src, build_dir, ninja=ninja)
    compile_cmd = presets.build_command(build_dir, env.get("cores") or 1)
    log.append("$ " + " ".join(configure))
    log.append("$ " + " ".join(compile_cmd))
    if dry_run:
        log.append("(dry run — nothing executed)")
        return {"log": log, "returncode": 0}
    subprocess.run(configure, check=True)
    subprocess.run(compile_cmd, check=True)
    log.append("build complete")
    return {"log": log, "returncode": 0}


def find_server(build_dir="build"):
    from .bench import find_binary

    return find_binary("llama-server", build_dir)
