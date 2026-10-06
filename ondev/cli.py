import argparse
import json
import os
import sys

from . import __version__
from . import bench as bench_mod
from . import build as build_mod
from . import detect as detect_mod
from . import fetch as fetch_mod
from . import package as package_mod
from . import presets
from . import profiles as profiles_mod
from . import serve as serve_mod
from . import verify as verify_mod

DEFAULT_CONFIG = "ondev.json"


def _load_config(path):
    if path and os.path.isfile(path):
        with open(path) as fh:
            return json.load(fh)
    return {}


def _profiles_dir(args, cfg):
    return args.profiles_dir or cfg.get("profiles_dir") or profiles_mod.profiles_dir()


def _resolve_profile(args, cfg, env):
    dirp = _profiles_dir(args, cfg)
    name = getattr(args, "device", None) or cfg.get("device") or detect_mod.auto_profile_name(env)
    return profiles_mod.load_profile(name, dirp), name


def _artifact_args(sp):
    sp.add_argument("--model", required=True)
    sp.add_argument("--bin")
    sp.add_argument("--build-dir", default="build")
    return sp


def build_parser():
    p = argparse.ArgumentParser(prog="ondev", description="On-device LLM builder")
    p.add_argument("--profiles-dir", help="directory of device profiles")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="print the detected build environment")

    sp = sub.add_parser("profiles", help="list device profiles")
    sp.add_argument("--verbose", action="store_true")

    sp = sub.add_parser("init", help="write ondev.json for this device")
    sp.add_argument("--device")
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("fetch", help="download a GGUF model")
    sp.add_argument("model")
    sp.add_argument("--dest", default="models")
    sp.add_argument("--url")

    sp = sub.add_parser("build", help="build llama.cpp with device-correct flags")
    sp.add_argument("--device")
    sp.add_argument("--src", default="third_party/llama.cpp")
    sp.add_argument("--build-dir", default="build")
    sp.add_argument("--jobs", type=int, default=None, help="parallel compile jobs (default: cores)")
    sp.add_argument("--dry-run", action="store_true")

    sp = _artifact_args(sub.add_parser("serve", help="launch an OpenAI-compatible server"))
    sp.add_argument("--port", type=int, default=8080)
    sp.add_argument("--ctx", type=int, default=4096)
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--threads", type=int, default=None, help="threads (default: min(cores,4))")

    sp = _artifact_args(sub.add_parser("bench", help="reproducible benchmark → device card"))
    sp.add_argument("--runs", type=int, default=3)
    sp.add_argument("--pp", type=int, default=32, help="prompt tokens for the pp test")
    sp.add_argument("--tg", type=int, default=8, help="tokens to generate for the tg test")
    sp.add_argument("--threads", type=int, default=None, help="threads (default: perf cores, else min(cores,4))")
    sp.add_argument("--out", default="ondev-bench.json")

    sp = _artifact_args(sub.add_parser("package", help="bundle binary + model into a tarball"))
    sp.add_argument("--out", default="ondev-package.tar.gz")

    sp = sub.add_parser("verify", help="check built binaries for ELF page alignment")
    sp.add_argument("--bin")
    sp.add_argument("--build-dir", default="build")
    sp.add_argument("--required", type=int, default=16384)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = _load_config(args.config)
    env = detect_mod.detect()

    if args.cmd == "doctor":
        env["tool_health"] = {
            k: detect_mod.check_tool(v) for k, v in env.get("tools", {}).items() if v
        }
        print(json.dumps(env, indent=2))
        return 0

    if args.cmd == "profiles":
        dirp = _profiles_dir(args, cfg)
        for n in profiles_mod.list_profiles(dirp):
            if args.verbose:
                pr = profiles_mod.load_profile(n, dirp)
                print(f"{n}\t{pr.get('name', '')}\t{pr.get('arch')}/{pr.get('os')}\t[{pr.get('status', 'unknown')}]")
            else:
                print(n)
        return 0

    if args.cmd == "init":
        profile, name = _resolve_profile(args, cfg, env)
        if os.path.exists(args.config) and not args.force:
            print(f"{args.config} exists (use --force to overwrite)", file=sys.stderr)
            return 1
        with open(args.config, "w") as fh:
            json.dump({"device": name, "profiles_dir": cfg.get("profiles_dir"), "detected": env},
                      fh, indent=2)
        print(f"wrote {args.config} → device={name}")
        print("build flags:", " ".join(presets.cmake_flags(profile, env)))
        return 0

    if args.cmd == "fetch":
        print(fetch_mod.fetch(args.model, args.dest, args.url))
        return 0

    if args.cmd == "build":
        profile, name = _resolve_profile(args, cfg, env)
        problems = build_mod.preflight(env)
        if problems:
            for p in problems:
                print("preflight: " + p, file=sys.stderr)
            return 1
        print("device:", name)
        result = build_mod.build(profile, env, args.src, args.build_dir,
                                 dry_run=args.dry_run, jobs=args.jobs)
        for line in result["log"]:
            print(line)
        return 0

    if args.cmd == "serve":
        threads = args.threads or min(env.get("cores") or 1, 4)
        return serve_mod.serve(args.model, args.host, args.port, args.ctx, args.bin,
                               args.build_dir, threads=threads)

    if args.cmd == "bench":
        profile, name = _resolve_profile(args, cfg, env)
        binary = args.bin or bench_mod.find_binary("llama-bench", args.build_dir)
        if not binary:
            print("llama-bench not found; run `ondev build` or pass --bin", file=sys.stderr)
            return 1
        threads = (args.threads or profile.get("threads") or env.get("perf_cores")
                   or min(env.get("cores") or 1, 4))
        try:
            res = bench_mod.run_bench(binary, args.model, args.runs,
                                      pp=args.pp, tg=args.tg, threads=threads)
            card = bench_mod.device_card(env, profile, args.model, args.runs, res["results"])
        except (RuntimeError, ValueError) as exc:
            print(f"bench failed: {exc}", file=sys.stderr)
            return 1
        bench_mod.write_card(card, args.out)
        print(bench_mod.render_markdown(card))
        print(f"\nwrote {args.out}")
        return 0

    if args.cmd == "package":
        binary = args.bin or build_mod.find_server(args.build_dir)
        if not binary:
            print("llama-server not found; run `ondev build` or pass --bin", file=sys.stderr)
            return 1
        print(package_mod.package(binary, args.model, args.out, env, args.config))
        return 0

    if args.cmd == "verify":
        targets = [args.bin] if args.bin else [
            bench_mod.find_binary("llama-bench", args.build_dir),
            build_mod.find_server(args.build_dir),
        ]
        targets = [t for t in targets if t]
        if not targets:
            print("no binaries found; run `ondev build` or pass --bin", file=sys.stderr)
            return 1
        rc = 0
        for t in targets:
            try:
                r = verify_mod.verify_binary(t, args.required)
            except (OSError, ValueError) as exc:
                print(f"FAIL  {t}: {exc}")
                rc = 1
                continue
            status = "PASS" if r["ok"] else "FAIL"
            print(f"{status}  {r['path']}  max_align=0x{r['max_align']:x} "
                  f"(required 0x{r['required']:x})  segments={r['load_alignments']}")
            if not r["ok"]:
                rc = 1
        return rc

    return 2
