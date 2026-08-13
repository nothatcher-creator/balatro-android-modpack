#!/usr/bin/env python3
"""Extract only modpack-specific files from a compatible Balatro Android APK.

This helper does not extract the Balatro base game files. Use it only with an APK
that you are legally entitled to access.
"""
from pathlib import Path
import zipfile
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: extract_from_apk.py <input.apk> <output-dir>")

apk = Path(sys.argv[1])
out = Path(sys.argv[2])

paths = {
    "assets/smods_mods/BalatroPlus/": "mods/BalatroPlus",
    "assets/bundled_mods/Bunco/": "mods/Bunco",
    "assets/bundled_mods/MikasModCollection/": "mods/MikasModCollection",
    "assets/bundled_mods/RerollPacks/": "mods/RerollPacks",
}

with zipfile.ZipFile(apk) as z:
    names = z.namelist()
    for src_prefix, dst_root in paths.items():
        for name in names:
            if name.startswith(src_prefix) and not name.endswith("/"):
                rel = name[len(src_prefix):]
                dest = out / dst_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(name))

    boot = "assets/bundled_mods_bootstrap.lua"
    if boot in names:
        dest = out / "android" / "bundled_mods_bootstrap.lua"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(z.read(boot))

print(f"Extracted modpack-specific files to {out}")
