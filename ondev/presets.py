"""Turn a device profile + detected environment into correct build flags."""

PAGE_FLAG = "-Wl,-z,max-page-size=16384"

DEFAULT_CMAKE_FLAGS = [
    "-DCMAKE_BUILD_TYPE=Release",
    "-DLLAMA_CURL=OFF",        # no libcurl dependency on-device
]


def linker_flags(profile, env):
    """Linker flags, adding the 16 KB alignment flag when the device needs it."""
    flags = list(profile.get("linker_flags", []))
    force = profile.get("force_page_alignment", False)
    needs = force or bool(env.get("android") and (env.get("page_size") or 0) >= 16384)
    if needs and not any("max-page-size" in f for f in flags):
        flags.append(PAGE_FLAG)
    return flags


def cmake_flags(profile, env):
    """Full set of -D... flags for `cmake -B build -S src`."""
    flags = list(DEFAULT_CMAKE_FLAGS)
    flags += profile.get("cmake_flags", [])
    lf = linker_flags(profile, env)
    if lf:
        joined = " ".join(lf)
        flags.append("-DCMAKE_EXE_LINKER_FLAGS=" + joined)
        flags.append("-DCMAKE_SHARED_LINKER_FLAGS=" + joined)
    return flags


def configure_command(profile, env, src, build_dir, ninja=False):
    cmd = ["cmake", "-B", build_dir, "-S", src]
    if ninja:
        cmd += ["-G", "Ninja"]
    cmd += cmake_flags(profile, env)
    return cmd


def build_command(build_dir, jobs):
    return ["cmake", "--build", build_dir, "--config", "Release", "-j", str(jobs)]
