# Balatro Android Modpack

Android compatibility tooling and documentation for Brad's Balatro modpack snapshot recovered from the final tested Android build on **August 12, 2026**.

This build was made on top of **mininxd/balatromod**, a Balatro mobile modpack base, and then extended with additional Steamodded mods and Android compatibility fixes.

This public repository intentionally does **not** contain the paid Balatro base game, APKs, signing keys, proprietary Android binaries, or full vendored copies of third-party projects whose redistribution terms are unclear.

## Target stack

- Balatro: `1.0.1o-FULL [M]`
- Steamodded: `1.0.0~BETA-1224a`
- LÖVE: `11.5.0`
- Lovely: `0.8.0-static`
- Platform: Android
- Materializer: `2026-08-12-materialized-v10-crash-report-batchfix`

## Base mobile modpack

Upstream base: `mininxd/balatromod`

The upstream mobile pack includes its own gameplay/mod layer before our additional mods are added. Its documented components include:

- **Sandbox Mode** with configurable starting money, hands, discards, Joker slots, consumable slots, deck, stake and seed
- **Talisman** — upstream README references v2.7
- **JokerDisplay**
- **Always Show Seed**
- **Zodiac Cards**
- **Hyperinflation Tag**
- Custom Jokers including Aura Farming, Rugpull, Zombie Joker, Lithograph, Boilerplate, Crossing Wires and President Joker
- Sandbox secret seeds including `GIVESOUL`, `RICHIE` and `JOKERINF`

The upstream `mods/` directory also contains the packaged Talisman, JokerDisplay, Cards, Always Show Seed, Zodiac and support files used by that mobile build.

The exact upstream commit used to create the recovered APK has not yet been pinned, so the manifest records the repository and branch while leaving the exact commit unknown.

## Additional mods layered onto that base

- **Balatro+** — `1.0.2-a` — SomeCoder99
- **Bunco** — `5.1` — Firch, RENREN, Peas, minichibis, J.D., Guwahavel, Ciirulean, ejwu
- **Mika's Mod Collection** — Android/Talisman compatibility snapshot — Mikadoe
- **Reroll Packs** — `1.0.1-android-compat` — DorkDad141

So the real build structure is:

`Balatro mobile base (mininxd/balatromod) -> its bundled mods/features -> added modpack mods -> Android compatibility patches/materializer`

## What is in this repository

- `android/bundled_mods_bootstrap.lua` — Android bundled-mod materializer logic
- `scripts/extract_from_apk.py` — extracts only modpack-specific files from a compatible APK you already own
- `docs/UPSTREAM_BASE.md` — documents the mininxd/balatromod base and its bundled components
- `docs/FIXES.md` — compatibility fixes carried by the August 12 build
- `docs/KNOWN_ISSUES.md` — remaining reported issues
- `modpack-manifest.json` — target stack, upstream base and added-mod snapshot metadata
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

The recovered APK contained copies of the upstream mobile base and included mods. Those are not being republished wholesale in this public repository when upstream redistribution rights are unclear. Instead, this repository records where each component came from and keeps our Android compatibility layer separate. See `THIRD_PARTY.md` and `docs/UPSTREAM_BASE.md`.
