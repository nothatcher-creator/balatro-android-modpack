# Balatro Android Modpack

Android compatibility tooling and documentation for Brad's Balatro modpack snapshot recovered from the final tested Android build on **August 12, 2026**.

This public repository intentionally does **not** contain the paid Balatro base game, APKs, signing keys, proprietary Android binaries, or full vendored copies of third-party mods whose redistribution terms are unclear.

## Target stack

- Balatro: `1.0.1o-FULL [M]`
- Steamodded: `1.0.0~BETA-1224a`
- LÖVE: `11.5.0`
- Lovely: `0.8.0-static`
- Platform: Android
- Materializer: `2026-08-12-materialized-v10-crash-report-batchfix`

## Modpack composition

- **Balatro+** — `1.0.2-a` — SomeCoder99
- **Bunco** — `5.1` — Firch, RENREN, Peas, minichibis, J.D., Guwahavel, Ciirulean, ejwu
- **Mika's Mod Collection** — Android/Talisman compatibility snapshot — Mikadoe
- **Reroll Packs** — `1.0.1-android-compat` — DorkDad141

## What is in this repository

- `android/bundled_mods_bootstrap.lua` — Android bundled-mod materializer logic
- `scripts/extract_from_apk.py` — extracts only modpack-specific files from a compatible APK you already own
- `docs/FIXES.md` — compatibility fixes carried by the August 12 build
- `docs/KNOWN_ISSUES.md` — remaining reported issues
- `modpack-manifest.json` — exact target stack and snapshot metadata
- `snapshot-sha256.json` — hashes from the recovered compatibility snapshot
- `THIRD_PARTY.md` — attribution and redistribution notes

## Final APK used to recover the snapshot

- Filename: `balatro-v0.7-plus-modpack-all-reported-issues-fix.apk`
- SHA-256: `118eb6650ddff0cf187487bb45471587a65bd0a245e0530aa2d31552a7adb1af`
- Size: `77,717,587` bytes

The APK itself is deliberately excluded.

## Status

The August 12 compatibility pass addressed the reported Steamodded edition-tooltip crash, Mika/Talisman big-number comparisons, nil money-spend state, pack/event nil accesses, Reroll Packs booster-slot handling, and Bunco Android shader/static-patch compatibility.

Two issues remained open after that build:

1. The **Additions** tab is still not behaving as intended.
2. Some **vanilla Planet cards use the wrong image**.

## Third-party source

The recovered APK contained complete copies of the included mods. Those are not being republished wholesale in this public repository when upstream redistribution rights are unclear. See `THIRD_PARTY.md`.

If this repository is made private, the exact recovered source snapshot can be stored here for continued Android debugging without publicly redistributing those files.
