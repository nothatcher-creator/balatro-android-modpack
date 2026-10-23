# Release 5678 — v124 card-area lifecycle hotfix

This October 23, 2026 update addresses the reported error:

```text
[SMODS _ "src/utils.lua"]:3654: attempt to get length of field 'cards' (a nil value)
```

The reported path enters `Card:set_edition`, immediately refreshes its owning area, and calls `CardArea:handle_card_limit`. A removed `CardArea` deliberately has no `cards` list, but can still be referenced by deferred work. The previous refresh helper called its handler anyway. Talisman's event wrapper reports the failure; its numeric backend is not changed by this hotfix. The exact callback that left the stale reference has not been established.

The fix checks the area's lifecycle state in both the edition refresh helper and the card-limit handler. Areas without table-valued `cards`, `config`, or `config.card_limits` are skipped. It does not recreate a removed area, reset its limits, or catch unrelated errors. Valid live areas continue through the original calculation, including the pack's existing Negative-edition bookkeeping.

## Artifact and baseline

- Release: [5678](https://github.com/nothatcher-creator/balatro-android-modpack/releases/tag/5678)
- New filename: `balatro-v0.10.38-v124-card-area-lifecycle-hotfix.apk`
- Signed APK size: **152,858,377 bytes**
- Signed APK SHA-256: `061ea87b72b3ae0c4251d6dd8db0316ac62b85cd33b51296ca5e9e303ed94ec4`
- Package: `com.playstack.balatro.android`
- New Android manifest: version code **74**, version name **0.10.38**
- Baseline filename: `balatro-v0.10.37-v123-negative-integrity-hotfix.apk`
- Baseline size: **152,828,825 bytes**
- Baseline SHA-256: `d55e5d8bb25763994afaa60818cfd302428aeb68a28423c686038aa981cd4040`
- Baseline manifest: version code **73**, version name **0.7**

The baseline's filename version and its Android manifest version differ. The rebuild uses the manifest's actual version code when creating an upgrade. The signed artifact's final size and SHA-256 are recorded above, in the release, and in `modpack-manifest.json`.

The tag `5678` remains at its existing historical commit. The release's update record links the separate source commit containing this hotfix. The old v123 asset is retained.

## Upgrade behavior

The materializer version becomes `2026-10-23-materialized-v124-card-area-lifecycle-hotfix`. It copies patched sources from `bundled_mods/AndroidCompatV124/Steamodded/src/` into the writable Steamodded source directory before Steamodded loads. Distinct source paths prevent an old writable destination from shadowing the APK's new source during the copy. Both files are in the forced refresh set for existing installs and the ordinary copy list for fresh installs.

Only the owned Steamodded source files are added to this refresh process. Profiles, run saves, settings, custom mods, and user configuration are not deleted. Install the new APK over the existing app to retain its app data; do not uninstall or clear storage first. The rebuilt APK must retain the original signing certificate, whose SHA-256 is `a40da80a59d170caa950cf15c18c454d47a39b26989d8b640ecd745ba71bf5dc`.

## Rebuild and regression checks

The public repository contains patch tooling and tests, not the paid base game, full bundled mod sources, APKs, or signing keys. Supply an external copy of the exact baseline APK above. The rebuild script rejects a different baseline and fails if expected source anchors do not match.

```bash
python scripts/rebuild_5678.py \
  --input /path/to/balatro-v0.10.37-v123-negative-integrity-hotfix.apk \
  --output /path/to/patched-unsigned.apk

uv run --with lupa python tests/test_card_area_lifecycle.py \
  --apk /path/to/patched-unsigned.apk
uv run --with lupa python tests/test_materializer_update.py \
  --apk /path/to/patched-unsigned.apk
python -m unittest discover -s tests -p test_android_manifest.py
```

The manifest helper exposes `read_manifest_version(data)` and `patch_manifest(data, version_code=..., version_name=..., expected_version_code=73)`. It updates the binary XML version fields without rebuilding Android resources. Other manifest values, native libraries, Java bytecode, and unrelated APK entries must remain unchanged.

Use Android's official `zipalign` before `apksigner`, with the certificate/key matching the baseline. After signing, verify the signature and certificate, ZIP alignment and integrity, package/version metadata, and the uncompressed bytes of every unrelated entry. Do not modify the signed APK afterward. Signing tools and key material remain outside Git.

The manual [release workflow](../.github/workflows/release-5678-hotfix.yml) performs the same rebuild and checks on GitHub. It verifies downloaded tools and the baseline, runs the regressions, and requires the exact reviewed unsigned, aligned, and signed hashes before publishing. Its `publish` input defaults to false. An explicitly dispatched publishing run uses GitHub's temporary release token and preserves the previous asset and tag.

## Validation scope

All **31 focused tests passed**. The signed APK verifies with v1 and v2 signatures and the original certificate, passes ZIP integrity/alignment checks, and has **2,617 unrelated payload entries byte-for-byte unchanged**. Android `aapt` reports identical non-version metadata. Complete changed Lua files compile with LuaJIT. See [the machine-readable verification record](release-5678-v124-verification.json).

The lifecycle harness reads the actual functions from the supplied APK and executes them in LuaJIT, with engine/rendering APIs doubled at their boundaries. It reproduces the original edition-refresh failure and checks removed/incomplete areas, unchanged live-area behavior, Negative add/remove behavior, numeric slot conversion, and propagation of unrelated errors.

The materializer harness executes the actual APK bootstrap against an in-memory LÖVE filesystem that models writable files shadowing APK assets. It covers fresh installs, upgrades with stale writable Steamodded sources, preserved user data, and missing hotfix assets. Binary manifest tests cover UTF-8 and UTF-16 string pools and malformed or unexpected inputs; final package metadata is also checked using Android's `aapt`.

These are focused source and packaging checks. They do not launch Android, reproduce an entire gameplay session, or prove compatibility with every possible mod interaction. No Android device playtest has been performed in this environment.
