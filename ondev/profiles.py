"""Load device profiles (JSON) that describe how to build for a target."""

import json
import os


def profiles_dir(override=None):
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "profiles")


def list_profiles(dirp):
    if not os.path.isdir(dirp):
        return []
    return sorted(fn[:-5] for fn in os.listdir(dirp) if fn.endswith(".json"))


def load_profile(name, dirp):
    path = os.path.join(dirp, name + ".json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"profile not found: {name!r} in {dirp}")
    with open(path) as fh:
        profile = json.load(fh)
    profile.setdefault("id", name)
    return profile
