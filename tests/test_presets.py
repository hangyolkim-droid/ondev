import os
import unittest

from ondev import presets, profiles

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDIR = os.path.join(HERE, "profiles")


class PresetTests(unittest.TestCase):
    def test_android_profile_adds_page_flag(self):
        env = {"android": True, "page_size": 16384}
        prof = profiles.load_profile("android-16k", PDIR)
        flags = presets.cmake_flags(prof, env)
        self.assertIn("max-page-size=16384", " ".join(flags))

    def test_linux_profile_has_no_page_flag(self):
        env = {"android": False, "page_size": 4096}
        prof = profiles.load_profile("generic-aarch64", PDIR)
        flags = presets.cmake_flags(prof, env)
        self.assertNotIn("max-page-size", " ".join(flags))

    def test_auto_page_flag_on_16k_android(self):
        env = {"android": True, "page_size": 16384}
        prof = {"linker_flags": [], "force_page_alignment": False}
        self.assertIn("-Wl,-z,max-page-size=16384", presets.linker_flags(prof, env))

    def test_force_alignment_flag(self):
        env = {"android": False, "page_size": 4096}
        prof = {"linker_flags": [], "force_page_alignment": True}
        self.assertIn("-Wl,-z,max-page-size=16384", presets.linker_flags(prof, env))

    def test_all_profiles_load(self):
        for name in profiles.list_profiles(PDIR):
            prof = profiles.load_profile(name, PDIR)
            self.assertEqual(prof["id"], name)

    def test_build_env_sets_prefix(self):
        import os

        from ondev import build

        saved = os.environ.pop("PREFIX", None)
        try:
            e = build.build_env({"termux_prefix": "/data/data/com.termux/files/usr"})
            self.assertEqual(e["PREFIX"], "/data/data/com.termux/files/usr")
        finally:
            if saved is not None:
                os.environ["PREFIX"] = saved

    def test_build_env_preserves_existing_prefix(self):
        import os

        from ondev import build

        saved = os.environ.get("PREFIX")
        os.environ["PREFIX"] = "/already/set"
        try:
            e = build.build_env({"termux_prefix": "/data/data/com.termux/files/usr"})
            self.assertEqual(e["PREFIX"], "/already/set")
        finally:
            if saved is None:
                os.environ.pop("PREFIX", None)
            else:
                os.environ["PREFIX"] = saved

    def test_parse_bench_json_tolerates_truncation(self):
        from ondev import bench

        self.assertEqual(bench.parse_bench_json('[{"a":1},{"b":2}]'), [{"a": 1}, {"b": 2}])
        # truncated mid-array -> keep the complete objects
        self.assertEqual(bench.parse_bench_json('[{"a":1},{"b":2},{"c"'), [{"a": 1}, {"b": 2}])

    def test_verify_alignment(self):
        import os as _os
        import struct
        import tempfile

        from ondev import verify

        def minimal_elf64(align):
            ident = b"\x7fELF" + bytes([2, 1, 1, 0]) + bytes(8)
            hdr = ident
            hdr += struct.pack("<H", 2)      # e_type
            hdr += struct.pack("<H", 0xB7)   # e_machine (AArch64)
            hdr += struct.pack("<I", 1)      # e_version
            hdr += struct.pack("<Q", 0)      # e_entry
            hdr += struct.pack("<Q", 0x40)   # e_phoff
            hdr += struct.pack("<Q", 0)      # e_shoff
            hdr += struct.pack("<I", 0)      # e_flags
            hdr += struct.pack("<H", 0x40)   # e_ehsize
            hdr += struct.pack("<H", 0x38)   # e_phentsize
            hdr += struct.pack("<H", 1)      # e_phnum
            hdr += struct.pack("<H", 0) * 3  # shentsize, shnum, shstrndx
            ph = struct.pack("<IIQQQQQQ", 1, 5, 0, 0, 0, 0x100, 0x100, align)
            return hdr + ph

        for align, expect_ok in ((0x4000, True), (0x1000, False)):
            with tempfile.NamedTemporaryFile(suffix=".elf", delete=False) as fh:
                fh.write(minimal_elf64(align))
                p = fh.name
            try:
                r = verify.verify_binary(p, required=16384)
                self.assertEqual(r["ok"], expect_ok)
                self.assertEqual(r["max_align"], align)
            finally:
                _os.unlink(p)

    def test_preflight_flags_missing_cmake(self):
        from ondev import build

        problems = build.preflight({"tools": {}})
        self.assertTrue(any("cmake" in p for p in problems))

    def test_preflight_passes_with_runnable_tools(self):
        import sys

        from ondev import build

        problems = build.preflight({"tools": {"cmake": sys.executable, "clang": sys.executable}})
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
