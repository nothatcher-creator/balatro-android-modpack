"""Binary manifest tests; real-APK check uses BALATRO_MANIFEST_TEST_APK/AAPT."""

from __future__ import annotations

import importlib.util
import copy
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/android_manifest.py"
ANDROID = "http://schemas.android.com/apk/res/android"
NONE = 0xFFFFFFFF


def chunk(kind, body, header_size=8):
    return struct.pack("<HHI", kind, header_size, 8 + len(body)) + body


def fixture(*, utf8=False, styles=False, attributes=None):
    strings = [ANDROID, "manifest", "versionCode", "versionName", "package",
               "android", "com.playstack.balatro.android", "0.7",
               "uses-permission", "name", "android.permission.INTERNET"]
    offsets, encoded = [], bytearray()
    for value in strings:
        offsets.append(len(encoded))
        if utf8:
            raw = value.encode("utf-8")
            encoded.extend(bytes([len(value), len(raw)]) + raw + b"\0")
        else:
            raw = value.encode("utf-16-le")
            encoded.extend(struct.pack("<H", len(raw) // 2) + raw + b"\0\0")
    encoded.extend(b"\0" * (-len(encoded) % 4))
    start = 28 + 4 * len(strings) + (4 if styles else 0)
    style_data = struct.pack("<III", NONE, NONE, NONE) if styles else b""
    pool = chunk(1, struct.pack("<IIIII", len(strings), int(styles),
                               0x100 if utf8 else 0, start,
                               start + len(encoded) if styles else 0)
                 + struct.pack("<" + "I" * len(offsets), *offsets)
                 + (struct.pack("<I", 0) if styles else b"")
                 + encoded + style_data, 28)

    def attribute(ns, name, raw, kind, value):
        return struct.pack("<IIIHBBI", ns, name, raw, 8, 0, kind, value)

    root_attributes = [attribute(0, 2, NONE, 0x10, 73),
                       attribute(0, 3, 7, 3, 7),
                       attribute(NONE, 4, 6, 3, 6)]
    if attributes is not None:
        root_attributes = attributes(root_attributes)

    def start_element(name, attrs):
        return chunk(0x102, struct.pack("<IIIIHHHHHH", 1, NONE, NONE, name,
                                       20, 20, len(attrs), 0, 0, 0)
                     + b"".join(attrs), 16)

    def end_element(name):
        return chunk(0x103, struct.pack("<IIII", 1, NONE, NONE, name), 16)

    # An unrelated permission element must survive byte-for-byte.
    permission = (start_element(8, [attribute(0, 9, 10, 3, 10)])
                  + end_element(8))
    resource_map = chunk(0x180, struct.pack("<" + "I" * 11,
                         0, 0, 0x0101021B, 0x0101021C, 0, 0, 0, 0, 0,
                         0x01010003, 0))
    return chunk(3, pool + resource_map
                 + start_element(1, root_attributes) + permission + end_element(1))


def children(data):
    """Independent chunk framing used to check preservation, not production code."""
    result, offset = [], 8
    while offset < len(data):
        kind, _, size = struct.unpack_from("<HHI", data, offset)
        result.append((kind, data[offset:offset + size]))
        offset += size
    return result


class AndroidManifestTests(unittest.TestCase):
    def editor(self):
        self.assertTrue(SCRIPT.is_file(), "binary AXML version editor is missing")
        spec = importlib.util.spec_from_file_location("android_manifest", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_cli_updates_raw_manifest_without_modifying_input(self):
        original = fixture()
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "input.xml", Path(directory) / "output.xml"
            source.write_bytes(original)
            result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(target),
                                     "--version-code", "74", "--version-name", "0.10.38"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(self.editor().read_manifest_version(target.read_bytes()),
                             (74, "0.10.38"))

    def test_updates_utf8_utf16_and_styled_pools_preserving_other_chunks(self):
        editor = self.editor()
        for utf8, styles in [(False, False), (True, False), (False, True), (True, True)]:
            with self.subTest(utf8=utf8, styles=styles):
                original = fixture(utf8=utf8, styles=styles)
                patched = editor.patch_manifest(original, version_code=74, version_name="0.10.38")
                self.assertEqual(editor.read_manifest_version(original), (73, "0.7"))
                self.assertEqual(editor.read_manifest_version(patched), (74, "0.10.38"))
                before, after = children(original), children(patched)
                self.assertEqual([kind for kind, _ in after], [kind for kind, _ in before])
                for index, ((_, old), (_, new)) in enumerate(zip(before, after)):
                    if index not in (0, 2):  # Only string pool and root attrs change.
                        self.assertEqual(new, old)
                # Package is the last 20-byte root attribute and is untouched.
                self.assertEqual(after[2][1][-20:], before[2][1][-20:])
                self.assertEqual(struct.unpack_from("<I", patched, 4)[0], len(patched))
                if styles:
                    self.assertEqual(after[0][1][-12:], before[0][1][-12:])

    def test_rejects_unexpected_baseline_before_any_edit(self):
        with self.assertRaisesRegex(ValueError, "[Ee]xpected.*73|[Ee]xpected.*version"):
            self.editor().patch_manifest(fixture(), version_code=74,
                                         version_name="0.10.38", expected_version_code=72)

    def test_rejects_missing_or_duplicate_version_attributes(self):
        editor = self.editor()
        for transform in [lambda attrs: attrs[1:],
                          lambda attrs: attrs[:1] + attrs[2:],
                          lambda attrs: attrs + [attrs[0]],
                          lambda attrs: attrs + [attrs[1]]]:
            with self.subTest(transform=transform):
                with self.assertRaises(ValueError):
                    editor.patch_manifest(fixture(attributes=transform),
                                          version_code=74, version_name="0.10.38")

    def test_rejects_wrong_types_namespaces_and_malformed_data(self):
        editor = self.editor()
        def wrong_type(attrs):
            attrs[0] = attrs[0][:15] + bytes([3]) + attrs[0][16:]
            return attrs
        def wrong_namespace(attrs):
            attrs[0] = struct.pack("<I", NONE) + attrs[0][4:]
            return attrs
        original = fixture()
        bad_size = original[:4] + struct.pack("<I", len(original) + 4) + original[8:]
        for data in [b"", original[:-1], bad_size,
                     fixture(attributes=wrong_type), fixture(attributes=wrong_namespace)]:
            with self.subTest(size=len(data)):
                with self.assertRaises(ValueError):
                    editor.patch_manifest(data, version_code=74, version_name="0.10.38")

    def test_rejects_version_attributes_with_wrong_android_resource_ids(self):
        original = bytearray(fixture())
        pool_size = struct.unpack_from("<I", original, 12)[0]
        resource_map = 8 + pool_size
        struct.pack_into("<I", original, resource_map + 8 + 4 * 2, 0x01010003)
        with self.assertRaises(ValueError):
            self.editor().patch_manifest(bytes(original), version_code=74,
                                         version_name="0.10.38")

    def test_cli_fails_closed_without_creating_output(self):
        self.editor()
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "input.xml", Path(directory) / "output.xml"
            source.write_bytes(fixture())
            result = subprocess.run([sys.executable, str(SCRIPT), str(source), str(target),
                                     "--expected-version-code", "72", "--version-code", "74",
                                     "--version-name", "0.10.38"], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_rejects_invalid_targets(self):
        editor = self.editor()
        for code, name in [(0, "0.10.38"), (-1, "0.10.38"), (2**32, "0.10.38"),
                           (74, ""), (74, "bad\0name")]:
            with self.subTest(code=code, name=name):
                with self.assertRaises(ValueError):
                    editor.patch_manifest(fixture(), version_code=code, version_name=name)

    @unittest.skipUnless(os.environ.get("BALATRO_MANIFEST_TEST_APK") and os.environ.get("AAPT"),
                         "set BALATRO_MANIFEST_TEST_APK and AAPT for independent APK validation")
    def test_real_apk_remains_readable_with_aapt_and_preserves_other_entries(self):
        editor = self.editor()
        with zipfile.ZipFile(os.environ["BALATRO_MANIFEST_TEST_APK"]) as original:
            old_manifest = original.read("AndroidManifest.xml")
            patched = editor.patch_manifest(old_manifest, version_code=74, version_name="0.10.38")
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "manifest-check.apk"
                with zipfile.ZipFile(path, "w") as updated:
                    for entry in original.infolist():
                        updated.writestr(copy.copy(entry), patched if entry.filename == "AndroidManifest.xml"
                                        else original.read(entry))
                output = subprocess.check_output([os.environ["AAPT"], "dump", "badging", str(path)], text=True)
                baseline = subprocess.check_output([os.environ["AAPT"], "dump", "badging",
                                                    os.environ["BALATRO_MANIFEST_TEST_APK"]], text=True)
                self.assertEqual(output, baseline.replace("versionCode='73' versionName='0.7'",
                                                          "versionCode='74' versionName='0.10.38'", 1))
                self.assertIn("name='com.playstack.balatro.android' versionCode='74' versionName='0.10.38'", output)
                self.assertIn("uses-permission: name='android.permission.INTERNET'", output)
                self.assertIn("launchable-activity: name='org.love2d.android.PlatformActivity'", output)
                with zipfile.ZipFile(path) as updated:
                    for entry in original.infolist():
                        if entry.filename != "AndroidManifest.xml":
                            self.assertEqual(updated.read(entry.filename), original.read(entry))


if __name__ == "__main__":
    unittest.main()
