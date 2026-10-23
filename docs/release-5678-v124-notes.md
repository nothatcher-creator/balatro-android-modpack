## v124 — card-area crash hotfix (October 23, 2026)

**Recommended download:** [balatro-v0.10.38-v124-card-area-lifecycle-hotfix.apk](https://github.com/nothatcher-creator/balatro-android-modpack/releases/download/5678/balatro-v0.10.38-v124-card-area-lifecycle-hotfix.apk)

Fixes the reported Steamodded `handle_card_limit` / `attempt to get length of field 'cards' (a nil value)` crash when an edition change reaches a removed card area. Removed and incomplete areas are skipped safely; live card-limit calculations and existing Negative-edition slot fixes are preserved. Talisman's event wrapper reports this error; its numeric backend is unchanged.

The installer also refreshes both patched Steamodded files on existing Android installs so stale writable copies cannot hide the fix. Profiles, saves, settings, and user mod configuration are preserved by the focused upgrade checks.

**Install over your existing app. Do not uninstall or clear storage first.** Package and signing certificate match the previous release; the actual Android version code advances from 73 to 74 (version name `0.10.38`). The old v123 APK is retained below.

### Verification

- All 31 focused regression tests pass, including the reproduced crash, Negative slot behavior, fresh installs, and updates with stale writable files.
- Complete changed Lua files compile in LuaJIT.
- Android signatures verify with v1 and v2; ZIP alignment and integrity pass.
- All 2,617 unrelated payload entries remain byte-for-byte unchanged; only the intended Lua/bootstrap/manifest changes and two upgrade source copies are included.
- No Android device playtest was available. These checks cover the reported failure path and packaging, not every possible mod interaction.

Size: **152,858,377 bytes**

SHA-256:
```text
061ea87b72b3ae0c4251d6dd8db0316ac62b85cd33b51296ca5e9e303ed94ec4
```

[Hotfix source and tests](https://github.com/nothatcher-creator/balatro-android-modpack/commit/a1b57049e28b0d83b6fca060c9984a1da5f36005) · [Detailed build and validation record](https://github.com/nothatcher-creator/balatro-android-modpack/blob/a1b57049e28b0d83b6fca060c9984a1da5f36005/docs/release-5678-v124.md)

Tag `5678` remains at its original historical commit; the links above identify the source for this updated asset.
