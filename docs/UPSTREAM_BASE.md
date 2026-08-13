# Upstream Android Base: mininxd/balatromod

The recovered August 12, 2026 APK was built from the public GitHub project `mininxd/balatromod`, then extended with additional mods and Android compatibility patches.

Upstream repository: `https://github.com/mininxd/balatromod`

## Why this matters

`mininxd/balatromod` is not just a blank Balatro Android wrapper. It is already a mobile modpack with its own gameplay changes and bundled mods. Any attempt to reproduce or debug this APK should start from that base layer rather than from unmodified Balatro alone.

## Bundled features documented upstream

### Core feature

**Sandbox Mode** adds a Play-menu mode with configurable starting Dollars, Hands, Discards, Joker Slots, Consumable Slots, Deck, Stake and Seed.

### Custom Jokers

- Aura Farming
- Rugpull
- Zombie Joker
- Lithograph
- Boilerplate
- Crossing Wires
- President Joker

### Custom tag

- Hyperinflation Tag

### Bundled/unique mods

- Talisman — upstream README links to v2.7
- JokerDisplay
- Always Show Seed
- Zodiac Cards

### Sandbox secret seeds

- `GIVESOUL`
- `RICHIE`
- `JOKERINF`

## Upstream `mods/` layout observed

At the time this repository was documented, the upstream `mods/` directory contains entries including:

- `Always_Show_Seed.lua`
- `Cards/`
- `JokerDisplay/`
- `Talisman/`
- `custom_joker.lua`
- `data.json`
- `json/`
- `nativefs.lua`
- `zodiac.lua`

This is important when diagnosing collisions: Talisman and JokerDisplay, for example, are already present in the mobile base before our added mods are materialized.

## Our added layer

The recovered final APK then adds:

- Balatro+ `1.0.2-a`
- Bunco `5.1`
- Mika's Mod Collection
- Reroll Packs `1.0.1-android-compat`

plus the Android materializer and compatibility patches documented elsewhere in this repository.

## Effective layering

```text
Balatro Android/mobile files
  -> mininxd/balatromod base
     -> Sandbox Mode + custom content
     -> Talisman
     -> JokerDisplay
     -> Always Show Seed
     -> Zodiac Cards
  -> additional bundled mods
     -> Balatro+
     -> Bunco
     -> Mika's Mod Collection
     -> Reroll Packs
  -> Android compatibility/materializer patches
```

## Exact upstream revision

The exact `mininxd/balatromod` commit used to build the recovered APK is not yet known. Do not assume current `main` is byte-for-byte identical to the base used by that APK. If we later identify the revision by comparing source files/hashes, pin it in `modpack-manifest.json`.

## Redistribution note

The `mininxd/balatromod` GitHub repository currently reports no declared repository license. For that reason this public repository links to and documents the upstream base rather than copying its entire source tree wholesale.
