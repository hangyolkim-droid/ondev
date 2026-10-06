# ondev — the on-device LLM builder

Run an LLM on a phone, and you lose two days to the same yak-shave every time: the linker flag
that stops it aborting at load, the hardlink call that Bionic refuses, the thread count, the
quantization, the benchmark nobody recorded the method for. **ondev** folds all of that into one
tool.

```
ondev init      # detect the target: page size, cores, toolchain → ondev.json
ondev fetch     # pull / quantize a GGUF
ondev build     # compile llama.cpp with the right preset
ondev serve     # OpenAI-compatible llama-server
ondev bench     # N runs, thermal noted, TTFT + tok/s → a JSON device card
ondev package   # self-contained tarball (Termux + generic aarch64)
```

## Why it exists

Every hard-won quirk of running local models on constrained hardware becomes a **preset** instead
of a blog post:

- **16 KB page alignment.** Android 15+ devices may ship 16 KB pages; a default 4 KB build aborts
  at load. ondev adds `-Wl,-z,max-page-size=16384` when the target needs it.
- **The hardlink trap.** On modern Android, Bionic/FUSE denies `link()` with `EACCES`. The packager
  copies bytes (`shutil.copy2`) and never hardlinks.
- **Reproducible numbers.** Every `bench` records the method — tool, runs, model, device, thermal
  state — so the number is citable, not asserted.

The build wraps [llama.cpp](https://github.com/ggml-org/llama.cpp); ondev does not reinvent
inference. Its value is the build/config/package/measure layer.

## Install

```sh
git clone https://github.com/hangyolkim-droid/ondev
cd ondev
pip install -e .        # or: python -m ondev ...
```

Requires Python 3.8+. For building, a working `git`, `cmake`, and a C/C++ toolchain.

## Usage

```sh
ondev doctor                          # what did it detect?
ondev profiles --verbose              # which devices are known?
ondev init --device fold8-ultra       # write ondev.json
ondev build --dry-run                 # print the exact cmake commands (no execution)
ondev build                           # clone + compile llama.cpp
ondev fetch qwen2.5-0.5b             # grab a small model to test with
ondev bench --model models/qwen2.5-0.5b-instruct-q4_k_m.gguf --runs 3
```

## Device profiles

Profiles are plain JSON in `profiles/` — copy one, change the flags, contribute it back.

| id | target |
|---|---|
| `generic-aarch64` | ARM64 Linux |
| `generic-x86_64` | desktop / dev |
| `android-16k` | Android 15+ with 16 KB pages |
| `fold8-ultra` | verified: Galaxy Z Fold 8 Ultra |

Schema (all fields optional except `id`): `name`, `arch`, `os`, `page_size`, `cores`,
`linker_flags`, `cmake_flags`, `force_page_alignment`, `notes`.

> Flags track llama.cpp's CMake options, which move between releases. Profiles are editable on
> purpose — if a flag drifts, fix it in the profile, not in the code.

## Status

v0.1 — early. `init` / `fetch` / `build` / `serve` / `bench` / `package` are implemented.
See [`docs/quirks.md`](docs/quirks.md) for the environment traps this handles, and
[`docs/devices.md`](docs/devices.md) for what is **tested** vs **theoretical**.
Next: GPU/NPU offload profiles, auto-tuning, a published device-card registry.

## License

MIT.
