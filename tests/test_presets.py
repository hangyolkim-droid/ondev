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


if __name__ == "__main__":
    unittest.main()
