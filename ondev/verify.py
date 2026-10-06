"""Verify built binaries will load on this device: ELF64 PT_LOAD alignment.

Android 15+ devices can use 16 KB memory pages. A binary whose PT_LOAD segments
are only 4 KB-aligned aborts at load. This checks the built artifacts directly,
with a small ELF parser — no reliance on readelf being installed.
"""

PT_LOAD = 1


def _u(fh, off, n, endian):
    fh.seek(off)
    return int.from_bytes(fh.read(n), endian)


def load_alignments(path):
    """Return the p_align of every PT_LOAD segment in a 64-bit ELF."""
    with open(path, "rb") as fh:
        ident = fh.read(16)
        if ident[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        if ident[4] != 2:
            raise ValueError("not a 64-bit ELF")
        endian = "<" if ident[5] == 1 else ">"
        e_phoff = _u(fh, 0x20, 8, endian)
        e_phentsize = _u(fh, 0x36, 2, endian)
        e_phnum = _u(fh, 0x38, 2, endian)
        aligns = []
        for i in range(e_phnum):
            base = e_phoff + i * e_phentsize
            if _u(fh, base, 4, endian) != PT_LOAD:
                continue
            aligns.append(_u(fh, base + 0x30, 8, endian))
        return aligns


def max_align(path):
    aligns = load_alignments(path)
    return max(aligns) if aligns else 0


def verify_binary(path, required=16384):
    aligns = load_alignments(path)
    mx = max(aligns) if aligns else 0
    return {
        "path": path,
        "load_alignments": ["0x%x" % a for a in aligns],
        "max_align": mx,
        "required": required,
        "ok": mx >= required,
    }
