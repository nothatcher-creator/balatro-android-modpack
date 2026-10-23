"""Run the APK's actual bundled-mod bootstrap against an in-memory LÖVE FS.

An external APK fixture is required; no game/mod source is vendored. Run:
    uv run --with lupa python tests/test_materializer_update.py --apk /path/app.apk
Or set BALATRO_TEST_APK (default: build/release-5678.apk).

These checks model writable files shadowing APK assets. They do not launch
LÖVE or Android, and they do not replace an on-device upgrade/playtest.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import unittest
import zipfile

from lupa.luajit21 import LuaError, LuaRuntime


DEFAULT_APK = Path("build/release-5678.apk")
BOOTSTRAP = "assets/bundled_mods_bootstrap.lua"
MARKER = b"smods_mods/.openai_bundled_modpack_version"
OLD_MARKER = b"2026-09-01-materialized-v123-previous-install"
PATCH_FILES = ("utils.lua", "overrides.lua")
CORE_FILES = (
    b"smods_mods/Ortalab/main.lua",
    b"smods_mods/Entropy/Entropy.lua",
    b"smods_mods/RevosVault/main.lua",
    b"smods_mods/Cryptid/Cryptid.lua",
    b"smods_mods/Bunco/Bunco.lua",
)
USER_FILES = {
    b"1/profile.jkr": b"profile one sentinel\x00\xff",
    b"1/save.jkr": b"run save sentinel\x00\x80",
    b"2/profile.jkr": b"profile two sentinel",
    b"settings.jkr": b"user settings sentinel",
    b"smods_mods/UserCustomMod/main.lua": b"return 'user mod sentinel'",
    b"smods_mods/UserCustomMod/config.lua": b"return {user_option = true}",
    b"smods_mods/Steamodded/config.lua": b"return {user_setting = 'keep'}",
    b"config/UserCustomMod.jkr": b"user mod saved configuration sentinel",
}


def destination(name: str) -> bytes:
    return f"smods_mods/Steamodded/src/{name}".encode()


def patch_asset(name: str) -> bytes:
    return f"bundled_mods/AndroidCompatV124/Steamodded/src/{name}".encode()


class MemoryLoveFS:
    """The only double: LÖVE's read/write overlay, with binary data intact."""

    def __init__(self, apk, writable=None, missing_assets=()):
        self.apk = apk
        self.writable = dict(writable or {})
        self.missing_assets = set(missing_assets)
        self.directories = set()
        self.lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
        filesystem = self.lua.table_from(
            {
                b"read": self.read,
                b"getInfo": self.get_info,
                b"write": self.write,
                b"createDirectory": self.create_directory,
                b"remove": self.remove,
            }
        )
        self.lua.globals()[b"love"] = self.lua.table_from({b"filesystem": filesystem})

    def read(self, path):
        # A source path equal to an old writable destination returns the OLD
        # bytes here. This catches an ineffective self-copy on APK upgrades.
        if path in self.writable:
            data = self.writable[path]
            return data, len(data)
        if path not in self.missing_assets:
            try:
                data = self.apk.read("assets/" + path.decode())
                return data, len(data)
            except KeyError:
                pass
        return None, b"File not found"

    def get_info(self, path):
        if path in self.writable:
            size = len(self.writable[path])
        elif path not in self.missing_assets:
            try:
                size = self.apk.getinfo("assets/" + path.decode()).file_size
            except KeyError:
                return None
        else:
            return None
        return self.lua.table_from({b"type": b"file", b"size": size})

    def write(self, path, data):
        self.writable[path] = data
        return True

    def create_directory(self, path):
        self.directories.add(path)
        return True

    def remove(self, path):
        return self.writable.pop(path, None) is not None

    def run_bootstrap(self):
        bootstrap = self.lua.execute(self.apk.read(BOOTSTRAP), name=b"@" + BOOTSTRAP.encode())
        return bootstrap()


class MaterializerUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get("BALATRO_TEST_APK", DEFAULT_APK)).expanduser()
        if not path.is_file():
            raise FileNotFoundError(
                f"APK fixture missing: {path}. Set BALATRO_TEST_APK or --apk."
            )
        cls.apk = zipfile.ZipFile(path)
        cls.expected = {
            name: cls.apk.read("assets/" + destination(name).decode())
            for name in PATCH_FILES
        }

    @classmethod
    def tearDownClass(cls):
        cls.apk.close()

    def existing_install(self):
        files = dict(USER_FILES)
        files.update({path: b"old bundled core sentinel" for path in CORE_FILES})
        files.update(
            {destination(name): b"old writable Steamodded " + name.encode() for name in PATCH_FILES}
        )
        files[MARKER] = OLD_MARKER
        return files

    def assert_user_data_preserved(self, fs):
        for path, contents in USER_FILES.items():
            with self.subTest(user_file=path.decode()):
                self.assertEqual(fs.writable.get(path), contents)

    def assert_both_sources_updated(self, fs):
        for name in PATCH_FILES:
            with self.subTest(source_file=name):
                self.assertTrue(
                    fs.writable.get(destination(name)) == self.expected[name],
                    f"Materializer did not install the APK's Steamodded {name}",
                )

    def test_fresh_install_materializes_both_steamodded_hotfix_sources(self):
        fs = MemoryLoveFS(self.apk, USER_FILES)
        self.assertTrue(fs.run_bootstrap())
        self.assert_both_sources_updated(fs)
        self.assert_user_data_preserved(fs)

    def test_upgrade_replaces_shadowing_old_writable_steamodded_sources(self):
        fs = MemoryLoveFS(self.apk, self.existing_install())
        self.assertTrue(fs.run_bootstrap())
        self.assert_both_sources_updated(fs)
        self.assert_user_data_preserved(fs)
        self.assertNotEqual(fs.writable.get(MARKER), OLD_MARKER)

    def test_upgrade_preserves_profiles_saves_and_custom_mod_settings(self):
        fs = MemoryLoveFS(self.apk, self.existing_install())
        self.assertTrue(fs.run_bootstrap())
        self.assert_user_data_preserved(fs)

    def test_hotfix_asset_copies_match_the_loaded_steamodded_sources(self):
        # The materializer's unique source path must carry the same fix as the
        # APK source used by lifecycle tests, not a stale second copy.
        for name in PATCH_FILES:
            with self.subTest(source_file=name):
                source = "assets/" + patch_asset(name).decode()
                self.assertTrue(source in self.apk.namelist(), f"Missing upgrade source: {source}")
                self.assertTrue(
                    self.apk.read(source) == self.expected[name],
                    f"Upgrade copy differs from loaded Steamodded {name}",
                )

    def test_missing_hotfix_asset_does_not_write_a_completed_upgrade_marker(self):
        for installed in (False, True):
            for name in PATCH_FILES:
                with self.subTest(installed=installed, missing_source=name):
                    initial = self.existing_install() if installed else dict(USER_FILES)
                    fs = MemoryLoveFS(self.apk, initial, missing_assets={patch_asset(name)})
                    error = None
                    try:
                        fs.run_bootstrap()
                    except LuaError as caught:
                        error = caught
                    with self.subTest(behavior="missing-source error"):
                        self.assertIsNotNone(error, "Missing required hotfix source was ignored")
                        if error is not None:
                            self.assertIn(patch_asset(name).decode(), str(error))
                    with self.subTest(behavior="completion marker"):
                        self.assertEqual(fs.writable.get(MARKER), initial.get(MARKER))
                    self.assert_user_data_preserved(fs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--apk")
    options, unittest_args = parser.parse_known_args()
    if options.apk:
        os.environ["BALATRO_TEST_APK"] = options.apk
    unittest.main(argv=[sys.argv[0], *unittest_args])
