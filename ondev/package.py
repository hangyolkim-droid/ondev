"""Bundle the built binary + model + config into a self-contained tarball."""

import os
import shutil
import tarfile
import time


def package(binary, model, out, env, config="ondev.json"):
    """Bundle artifacts.

    We copy file bytes with ``shutil.copy2`` and never hardlink: on modern
    Android, Bionic/FUSE denies ``link()`` with EACCES — exactly the trap this
    tool exists to route around.
    """
    stage = out + ".stage"
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)

    for src in (binary, model, config):
        if src and os.path.isfile(src):
            shutil.copy2(src, os.path.join(stage, os.path.basename(src)))  # copy, never os.link

    with open(os.path.join(stage, "MANIFEST.txt"), "w") as fh:
        fh.write("ondev package\n")
        fh.write(f"built: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
        fh.write(f"arch: {env.get('arch')}  os: {env.get('platform')}  page_size: {env.get('page_size')}\n")

    with tarfile.open(out, "w:gz") as tar:
        tar.add(stage, arcname="ondev")
    shutil.rmtree(stage)
    return out
