"""Environment detection: what are we building on, and does it need 16 KB alignment?"""

import os
import platform
import shutil

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


def detect():
    return {
        "arch": platform.machine(),
        "platform": platform.system().lower(),
        "android": is_android(),
        "termux": is_termux(),
        "termux_prefix": termux_prefix(),
        "page_size": page_size(),
        "cores": os.cpu_count() or 1,
        "python": platform.python_version(),
        "tools": {
            t: shutil.which(t)
            for t in ("git", "cmake", "clang", "gcc", "make", "ninja", "cc", "c++")
        },
    }


def auto_profile_name(env):
    """Best default profile id for the detected environment."""
    if env.get("android"):
        return "android-16k"
    if env.get("arch") in ("aarch64", "arm64"):
        return "generic-aarch64"
    if env.get("arch") in ("x86_64", "amd64"):
        return "generic-x86_64"
    return "generic-aarch64"
