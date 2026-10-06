# Device compatibility

ondev ships **device profiles**. Every profile is labelled by how much we actually know about it —
because "it should work" and "we measured it" are different claims.

- **tested** — built *and* benchmarked on real hardware; numbers recorded below.
- **theoretical** — the target is supported by the toolchain/profile, but we have never run it. No
  performance claims.
- **community** — a profile exists, awaiting a device card. Contributions welcome.

## Requirements

| | Minimum |
|---|---|
| Arch / OS | aarch64 Linux · Android (Termux) · x86_64 Linux (dev) |
| Toolchain | `git`, `cmake`, `clang`, `make` (or `ninja`), Python 3.8+ |
| RAM | ≥ ~1 GB free for a 0.5B Q4 · ≥ ~3 GB for a 3B Q4 |
| Disk | ~1 GB (llama.cpp build + a 0.5B model) |
| 16 KB-page devices | handled automatically via `-Wl,-z,max-page-size=16384` |

## Compatibility matrix

| Device | Arch / OS | Page size | Threads | Status | Measured (Qwen2.5-0.5B Q4) |
|---|---|---|---|---|---|
| Galaxy Z Fold 8 Ultra | aarch64 / Android 17 (SDK 37), native Termux | 4096 | 4 | **tested** | pp 276 / tg 120 tok/s · 67 °C |
| Generic ARM64 Linux (inside PRoot) | aarch64 / Linux | 4096 | 4 | **tested (container)** | pp 71.6 / tg 39.5 tok/s |
| Pixel-class Android 15+ | aarch64 / Android | 16384 | — | **theoretical** | — |
| Generic x86_64 | x86_64 / Linux | 4096 | — | **theoretical** | — |

`pp` = prompt processing (32 tokens) · `tg` = text generation (8 tokens) · measured with
`llama-bench -r 3`. Full cards ship in each `ondev bench` output.

## Recommendations

- **Use the performance-core count, not the logical core count.** On the Fold, 8 threads ran ~16%
  *slower* than 4, with ~4× the variance. `ondev` selects this automatically; override with
  `--threads`.
- **Run native — not inside a container or emulation layer.** The same binary in a PRoot layer
  generated at **0.24 tok/s** where native did **120**. That measured the harness, not the silicon.
- **Validate with a 0.5B first**, then scale the model to the RAM you actually have.
- **Quote the device card, not the marketing number** — `ondev bench` records the method alongside
  the result so the figure is reproducible.

## Contributing a device

Run `ondev bench` on your device, then open a PR with the generated `ondev-bench.json` and a new
`profiles/<device>.json`. Tested entries get promoted into the matrix above.
