"""Environment detection: what are we building on, and does it need 16 KB alignment?"""

import os
import platform
import shutil
import subprocess

PAGE_ALIGN_THRESHOLD = 16384


def page_size():
    """Kernel page size in bytes, or None if it can't be read."""
    try:
        return os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError, AttributeError):
        return None


TERMUX_PREFIX_FALLBACK = "/data/data/com.termux/files/usr"


def termux_prefix():
    """The Termux prefix, from $PREFIX or the well-known path, or None."""
    prefix = os.environ.get("PREFIX", "")
    if prefix and "com.termux" in prefix:
        return prefix
    if os.path.isdir(TERMUX_PREFIX_FALLBACK):
        return TERMUX_PREFIX_FALLBACK
    return None


def is_termux():
    return termux_prefix() is not None


def is_android():
    if is_termux():
        return True
    return "android" in platform.platform().lower()


def needs_page_alignment(env):
    """True when the target needs 16 KB-aligned ELF segments.

    Android 15+ devices may ship 16 KB pages; binaries built with the default
    4 KB max-page-size abort at load. We also honour an explicit profile flag.
    """
    ps = env.get("page_size")
    return bool(env.get("android") and ps and ps >= PAGE_ALIGN_THRESHOLD)


def check_tool(path, args=("--version",), timeout=20):
    """True if the tool actually executes — not merely exists on PATH."""
    if not path:
        return False
    try:
        proc = subprocess.run([path, *args], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=timeout)
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def detect():
    return {
        "arch": platform.machine(),
        "platform": platform.system().lower(),
        "android": is_android(),
        "termux": is_termux(),
        "termux_prefix": termux_prefix(),
        "page_size": page_size(),
        "cores": os.cpu_count() or 1,
        "perf_cores": performance_cores(),
        "python": platform.python_version(),
        "tools": {
            t: shutil.which(t)
            for t in ("git", "cmake", "clang", "gcc", "make", "ninja", "cc", "c++")
        },
    }


def performance_cores():
    """Count the 'big' cluster on a big.LITTLE SoC, or None if unknown.

    ggml's spin-barrier can collapse when threads are spread across slow and fast
    cores: on a phone with 8 logical cores, using all 8 can be ~100x slower than 4.
    """
    import glob

    freqs = []
    for p in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/cpuinfo_max_freq"):
        try:
            with open(p) as fh:
                freqs.append(int(fh.read().strip()))
        except (OSError, ValueError):
            continue
    if not freqs:
        return None
    top = max(freqs)
    return max(1, sum(1 for f in freqs if f >= top * 0.9))


def auto_profile_name(env):
    """Best default profile id for the detected environment."""
    if env.get("android"):
        return "android-16k"
    if env.get("arch") in ("aarch64", "arm64"):
        return "generic-aarch64"
    if env.get("arch") in ("x86_64", "amd64"):
        return "generic-x86_64"
    return "generic-aarch64"
