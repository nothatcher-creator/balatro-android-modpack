# Changelog

## 2026-10-23 — release 5678, v124 card-area lifecycle hotfix

- Skip card-limit recalculation for removed or incomplete card areas, including edition-triggered refreshes. Removed areas keep their absent `cards` list; they are not recreated or assigned replacement limits.
- Preserve the live-area calculation path, Negative-edition slot behavior, and unrelated error propagation.
- Force-refresh both patched Steamodded source files from distinct bundled assets so writable copies from earlier installs cannot shadow the fix. Preserve profiles, saves, settings, and user mod configuration.
- Advance the actual Android manifest from version code 73 / name `0.7` to version code 74 / name `0.10.38`. The old APK filename's `v123` was not its Android version code.
- Add focused LuaJIT regressions, writable-overlay materializer checks, a binary Android manifest patcher, and a baseline-hash-checked rebuild script. These checks do not replace an Android playtest.
- Retain tag `5678` and the prior v123 APK asset. See [the hotfix record](docs/release-5678-v124.md).

## 2026-08-12 — all-reported-issues-fix

- Consolidated the Android compatibility work from prior shader, Talisman, pack UI, gameplay-audit, and deep-stability builds.
- Targeted Balatro+, Bunco, Mika's Mod Collection, and Reroll Packs.
- Updated bundled-mod materializer to `2026-08-12-materialized-v10-crash-report-batchfix`.
- Added compatibility handling for Mika/Talisman big-number values.
- Preserved the actual Reroll Packs booster-slot count.
- Added Bunco Android static-patch/shader safeguards.
- Added guards around previously reported nil UI/event/game-state paths.

### Still open

- Additions tab behavior.
- Incorrect art on some vanilla Planet cards.
