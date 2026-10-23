#!/usr/bin/env python3
"""Apply the v124 lifecycle hotfix to the exact, externally supplied v123 APK.

No game source, signing material, downloads, or publishing are included here.
Output is unsigned; align and sign it separately with the existing app's key.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from android_manifest import patch_manifest, read_manifest_version


BASELINE_SHA256 = "d55e5d8bb25763994afaa60818cfd302428aeb68a28423c686038aa981cd4040"
BASELINE_SIZE = 152828825
VERSION_CODE = 74
VERSION_NAME = "0.10.38"
MATERIALIZER_VERSION = "2026-10-23-materialized-v124-card-area-lifecycle-hotfix"
UTILS = "assets/smods_mods/Steamodded/src/utils.lua"
OVERRIDES = "assets/smods_mods/Steamodded/src/overrides.lua"
BOOTSTRAP = "assets/bundled_mods_bootstrap.lua"
HOTFIX_ROOT = "assets/bundled_mods/AndroidCompatV124/Steamodded/src/"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def replace_once(data: bytes, old: str, new: str) -> bytes:
    old_bytes = old.encode("utf-8")
    if data.count(old_bytes) != 1:
        raise ValueError(f"Expected exactly one patch anchor: {old.splitlines()[0]}")
    return data.replace(old_bytes, new.encode("utf-8"), 1)


def signature_entry(name: str) -> bool:
    upper = name.upper()
    return upper == "META-INF/MANIFEST.MF" or (
        upper.startswith("META-INF/")
        and "/" not in upper[len("META-INF/"):]
        and upper.endswith((".SF", ".RSA", ".DSA", ".EC"))
    )


def patched_assets(apk: zipfile.ZipFile) -> dict[str, bytes]:
    """Fail closed if any expected original code has changed."""
    utils = replace_once(
        apk.read(UTILS),
        "function CardArea:handle_card_limit()\n    if SMODS.should_handle_limit(self) then",
        """function CardArea:handle_card_limit()
    -- Removed areas deliberately lose cards; deferred callbacks can outlive them.
    -- Do not recreate the list or alter cached limits on an incomplete area.
    if type(self) ~= 'table' or type(self.cards) ~= 'table'
        or type(self.config) ~= 'table' or type(self.config.card_limits) ~= 'table' then
        return
    end
    if SMODS.should_handle_limit(self) then""",
    )
    overrides = replace_once(
        apk.read(OVERRIDES),
        "local function refresh_card_limit_area(card)\n"
        "\tlocal area = card and card.area\n"
        "\tif area and type(area.handle_card_limit) == 'function' then\n"
        "\t\tarea:handle_card_limit()\n\tend\nend",
        "local function refresh_card_limit_area(card)\n"
        "\tlocal area = card and card.area\n"
        "\t-- Edition changes may finish after the previous owning area was removed.\n"
        "\tif type(area) == 'table' and type(area.cards) == 'table'\n"
        "\t\tand type(area.config) == 'table' and type(area.config.card_limits) == 'table'\n"
        "\t\tand type(area.handle_card_limit) == 'function' then\n"
        "\t\tarea:handle_card_limit()\n\tend\nend",
    )
    bootstrap = replace_once(
        apk.read(BOOTSTRAP),
        '  local VERSION = "2026-08-31-materialized-v116-general-stability-hotfix"',
        f'  local VERSION = "{MATERIALIZER_VERSION}"',
    )
    pairs, refresh = [], []
    for name in ("utils.lua", "overrides.lua"):
        source = f"bundled_mods/AndroidCompatV124/Steamodded/src/{name}"
        destination = f"smods_mods/Steamodded/src/{name}"
        pairs.append(f'    {{"{source}", "{destination}"}},\n')
        refresh.append(f'    ["{destination}"] = true,\n')
    bootstrap = replace_once(
        bootstrap, "  local files = {\n",
        "  local files = {\n" + "".join(pairs),
    )
    bootstrap = replace_once(
        bootstrap, "  local force_refresh = {\n",
        "  local force_refresh = {\n" + "".join(refresh),
    )
    return {
        "AndroidManifest.xml": patch_manifest(
            apk.read("AndroidManifest.xml"),
            version_code=VERSION_CODE, version_name=VERSION_NAME,
            expected_version_code=73,
        ),
        UTILS: utils,
        OVERRIDES: overrides,
        BOOTSTRAP: bootstrap,
        HOTFIX_ROOT + "utils.lua": utils,
        HOTFIX_ROOT + "overrides.lua": overrides,
    }


def validate_baseline(path: Path) -> None:
    if path.stat().st_size != BASELINE_SIZE or file_sha256(path) != BASELINE_SHA256:
        raise ValueError("Input is not the exact release-5678 v123 baseline APK")


def verify_delta(baseline: Path, candidate: Path) -> dict:
    """Check every payload byte and compression method, including signed APKs."""
    validate_baseline(baseline)
    with zipfile.ZipFile(baseline) as original, zipfile.ZipFile(candidate) as final:
        for archive in (original, final):
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate ZIP filenames")
            if archive.testzip() is not None:
                raise ValueError("Corrupt ZIP entry")
        expected = patched_assets(original)
        old_names = {n for n in original.namelist() if not signature_entry(n)}
        new_names = {n for n in final.namelist() if not signature_entry(n)}
        if new_names != old_names | expected.keys():
            raise ValueError("Unexpected added or removed APK payload entries")
        unchanged = 0
        for name in new_names:
            wanted = expected[name] if name in expected else original.read(name)
            if final.read(name) != wanted:
                raise ValueError(f"Unexpected APK payload change: {name}")
            if name in old_names:
                if final.getinfo(name).compress_type != original.getinfo(name).compress_type:
                    raise ValueError(f"Compression method changed: {name}")
                unchanged += name not in expected
        if read_manifest_version(final.read("AndroidManifest.xml")) != (VERSION_CODE, VERSION_NAME):
            raise ValueError("Wrong Android version")
        return {
            "baseline_sha256": BASELINE_SHA256,
            "output_sha256": file_sha256(candidate),
            "output_size_bytes": candidate.stat().st_size,
            "version_code": VERSION_CODE,
            "version_name": VERSION_NAME,
            "materializer_version": MATERIALIZER_VERSION,
            "unchanged_payload_entries": unchanged,
            "changed_or_added_payloads": {
                name: sha256(data) for name, data in sorted(expected.items())
            },
        }


def rebuild(baseline: Path, output: Path) -> dict:
    validate_baseline(baseline)
    if baseline.resolve() == output.resolve() or output.exists():
        raise ValueError("Output must be a new path distinct from the baseline")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="v124-", dir=output.parent) as temporary:
        staged = Path(temporary) / "unsigned.apk"
        with zipfile.ZipFile(baseline) as original:
            if len(original.namelist()) != len(set(original.namelist())):
                raise ValueError("Duplicate baseline filenames")
            changes = patched_assets(original)
            existing = set(original.namelist())
            if any(name in existing for name in changes if name.startswith(HOTFIX_ROOT)):
                raise ValueError("Hotfix source path already exists in baseline")
            with zipfile.ZipFile(staged, "w") as target:
                target.comment = original.comment
                for item in original.infolist():
                    if signature_entry(item.filename):
                        continue
                    data = changes[item.filename] if item.filename in changes else original.read(item.filename)
                    target.writestr(copy.copy(item), data)
                for name in sorted(changes.keys() - existing):
                    item = zipfile.ZipInfo(name, date_time=(2026, 10, 23, 0, 0, 0))
                    item.compress_type = zipfile.ZIP_DEFLATED
                    item.external_attr = 0o100644 << 16
                    target.writestr(item, changes[name])
        report = verify_delta(baseline, staged)
        staged.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Exact v123 APK")
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--output", type=Path, help="New unsigned APK path")
    operation.add_argument("--verify", type=Path, help="Verify a built/signed candidate")
    parser.add_argument("--report", type=Path, help="Write JSON verification report")
    args = parser.parse_args()
    report = (rebuild(args.input, args.output) if args.output
              else verify_delta(args.input, args.verify))
    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
