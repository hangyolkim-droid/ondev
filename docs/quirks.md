# Quirks ondev handles

Each of these cost real debugging time. They are the reason ondev exists: a quirk found once
becomes a preset, not tribal knowledge.

## 1. CMake's Android-**host** branch crashes without `$PREFIX`

**Symptom.** `cmake` configuration dies with:

```
CMake Error at .../Modules/CMakeDetermineSystem.cmake:40 (file):
  file failed to open for reading (No such file or directory):
    /include/android/api-level.h
```

— a path that points nowhere near the actual problem.

**Cause.** On an Android/Termux host, CMake 4.x takes an Android branch that reads
`$ENV{PREFIX}/include/android/api-level.h`. In a bare or agent shell `PREFIX` is often **unset**, so
the path collapses to `/include/android/api-level.h`. Passing `-DCMAKE_SYSTEM_NAME=Linux` does *not*
help — this is the **host** branch, not the target.

**Fix.** Ensure `PREFIX` is exported (`/data/data/com.termux/files/usr`). ondev restores it from the
detected Termux prefix before invoking CMake.

## 2. big.LITTLE: threads = logical cores collapses ggml

**Symptom.** Generation crawls — **0.24 tok/s**, ~200x slower than expected — and `llama-bench` may
abort.

**Cause.** `os.cpu_count()` / `nproc` reports *logical* cores (e.g. 8). On a big.LITTLE SoC most of
those are efficiency cores. ggml's spin-barrier makes every fast core wait on the slow cluster, so
adding threads makes it dramatically *worse*.

**Fix.** Use the **performance cluster** count, not the logical count. ondev derives it from
`cpuinfo_max_freq` (top cluster) and falls back to `min(cores, 4)`.

**Measured on this device (Qwen2.5-0.5B Q4_K_M):**

| threads | prompt tok/s | gen tok/s |
|---|---|---|
| 8 | 9.2 | **0.24** |
| 4 | 118.9 | **53.7** |

## 3. `llama-bench` aborts at teardown, truncating its JSON

**Symptom.** `llama-bench ... -o json` exits `134` (SIGABRT) and writes a JSON array that is cut off
mid-object — so `json.loads` fails. Under a pipe the buffered output can be lost entirely.

**Cause.** In constrained/emulated environments (here: PRoot + memory pressure) the process aborts
during teardown, after writing part of the array.

**Fix.** Write stdout to a file (not a pipe), then salvage the complete objects from a truncated
array. ondev does both.

## Open / untested

- **SVE / SME.** The build detected `dotprod i8mm sve sme` and compiled a `-mcpu=native+...` variant.
  Whether that helps or hurts under this kernel/host is **unmeasured** — worth a controlled A/B
  (baseline `armv8.2-a+dotprod+i8mm` vs native) before claiming anything.
- **PRoot tax.** These numbers were taken inside a PRoot layer; native Termux should differ.
