"""Reproducible benchmarks — the credibility layer.

Every run records the method (tool, runs, model, device, thermal state) so the
resulting number is citable rather than asserted.
"""

import glob
import json
import os
import subprocess
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


def run_bench(binary, model, runs, build_dir="build", timeout=1800):
    cmd = [binary, "-m", model, "-r", str(runs), "-o", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"benchmark failed ({proc.returncode}):\n{proc.stderr[-2000:]}")
    data = json.loads(proc.stdout)
    return {"command": cmd, "results": data}


def device_card(env, profile, model, runs, results):
    rows = []
    for r in results:
        rows.append({
            "test": r.get("test") or r.get("name", ""),
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
        f"- **Page size:** {card['page_size']} B · **cores:** {card['cores']}",
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
