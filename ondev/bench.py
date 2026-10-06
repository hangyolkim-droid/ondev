"""Reproducible benchmarks — the credibility layer.

Every run records the method (tool, runs, model, device, thermal state) so the
resulting number is citable rather than asserted.
"""

import glob
import json
import os
import subprocess
import tempfile
import time


def find_binary(name, build_dir, extra_dirs=()):
    for d in (build_dir, build_dir + "/bin", *extra_dirs):
        for cand in (os.path.join(d, name), os.path.join(d, name + ".exe")):
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
    for d in glob.glob(os.path.join(build_dir, "**", name), recursive=True):
        if os.access(d, os.X_OK):
            return d
    from shutil import which
    return which(name)


def thermal_state():
    """Best-effort thermal snapshot (Android/Linux)."""
    zones = []
    for p in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp"))[:8]:
        try:
            with open(p) as fh:
                raw = int(fh.read().strip())
            zones.append(round(raw / 1000.0, 1))
        except (OSError, ValueError):
            continue
    return {"celsius_zones": zones, "max_celsius": max(zones) if zones else None}


def parse_bench_json(text):
    """Parse llama-bench JSON, tolerating a truncated tail.

    In constrained/emulated environments llama-bench can abort mid-write,
    leaving the array cut off before its closing bracket. Salvage the complete
    objects so a partially written run still yields a usable card.
    """
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cut = text.rfind("}")
        if cut != -1:
            return json.loads(text[: cut + 1] + "]")
        raise


def run_bench(binary, model, runs, build_dir="build", timeout=1800, pp=None, tg=None, threads=None):
    cmd = [binary, "-m", model, "-r", str(runs), "-o", "json"]
    if pp:
        cmd += ["-p", str(pp)]
    if tg:
        cmd += ["-n", str(tg)]
    if threads:
        cmd += ["-t", str(threads)]
    proc = None
    # Write stdout to a file, not a pipe: llama-bench can abort (SIGABRT) during
    # teardown in constrained/emulated environments, and a pipe loses the
    # buffered JSON that a file keeps.
    fd, outpath = tempfile.mkstemp(suffix=".ondev-bench.json")
    try:
        with os.fdopen(fd, "wb") as fh:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE, timeout=timeout)
        with open(outpath) as fh:
            out = fh.read().strip()
    finally:
        try:
            os.unlink(outpath)
        except OSError:
            pass
    try:
        data = parse_bench_json(out)
    except json.JSONDecodeError:
        detail = (proc.stderr or b"")[-2000:] if proc else b""
        raise RuntimeError(f"benchmark produced no usable JSON (exit {proc.returncode if proc else '?'}):\n{detail!r}")
    return {"command": cmd, "results": data}


def device_card(env, profile, model, runs, results):
    rows = []
    for r in results:
        label = r.get("test") or r.get("name") or ""
        if not label:
            np_, ng = r.get("n_prompt", 0), r.get("n_gen", 0)
            if np_ and ng:
                label = f"pp{np_}+tg{ng}"
            elif np_:
                label = f"pp{np_}"
            elif ng:
                label = f"tg{ng}"
        rows.append({
            "test": label,
            "tokens_per_second": r.get("avg_ts"),
            "stdev": r.get("stddev_ts"),
            "n_runs": runs,
        })
    return {
        "tool": "llama-bench",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device_profile": profile.get("id"),
        "device_name": profile.get("name"),
        "arch": env.get("arch"),
        "os": env.get("platform"),
        "page_size": env.get("page_size"),
        "cores": env.get("cores"),
        "perf_cores": env.get("perf_cores"),
        "threads": results[0].get("n_threads") if results else None,
        "model": os.path.basename(model),
        "runs": runs,
        "thermal": thermal_state(),
        "results": rows,
    }


def write_card(card, path):
    with open(path, "w") as fh:
        json.dump(card, fh, indent=2)
    return path


def render_markdown(card):
    lines = [
        f"### Device card — {card['device_name']} ({card['arch']}, {card['os']})",
        "",
        f"- **Model:** `{card['model']}`",
        f"- **Page size:** {card['page_size']} B · **cores:** {card['cores']} · **threads:** {card.get('threads')}",
        f"- **Runs:** {card['runs']} · **thermal max:** {card['thermal'].get('max_celsius')} °C",
        "",
        "| Test | tokens/s | stdev |",
        "|---|---|---|",
    ]
    for r in card["results"]:
        tps = r["tokens_per_second"]
        sd = r["stdev"]
        lines.append(f"| {r['test']} | {tps:.2f} | {sd:.2f} |" if tps else f"| {r['test']} | — | — |")
    lines.append("")
    lines.append(f"_Method: `llama-bench -r {card['runs']}`, recorded {card['generated_at']}._")
    return "\n".join(lines)
