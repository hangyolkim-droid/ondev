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


def build_env(env):
    """Environment for build subprocesses.

    CMake 4.x's Android-**host** branch in CMakeDetermineSystem.cmake reads
    $ENV{PREFIX}/include/android/api-level.h. In a bare/agent shell PREFIX is
    often unset, the path collapses to /include/android/api-level.h, and
    configuration fails with no obvious cause. We restore PREFIX from the
    detected Termux prefix so the branch resolves.
    """
    run_env = dict(os.environ)
    if env.get("termux_prefix") and not run_env.get("PREFIX"):
        run_env["PREFIX"] = env["termux_prefix"]
    return run_env


def build(profile, env, src="third_party/llama.cpp", build_dir="build", dry_run=False, jobs=None):
    log = []
    if not dry_run:
        ensure_source(src)
    ninja = has_ninja()
    configure = presets.configure_command(profile, env, src, build_dir, ninja=ninja)
    compile_cmd = presets.build_command(build_dir, jobs or env.get("cores") or 1)
    log.append("$ " + " ".join(configure))
    log.append("$ " + " ".join(compile_cmd))
    if dry_run:
        log.append("(dry run — nothing executed)")
        return {"log": log, "returncode": 0}
    run_env = build_env(env)
    subprocess.run(configure, check=True, env=run_env)
    subprocess.run(compile_cmd, check=True, env=run_env)
    log.append("build complete")
    return {"log": log, "returncode": 0}


def find_server(build_dir="build"):
    from .bench import find_binary

    return find_binary("llama-server", build_dir)
