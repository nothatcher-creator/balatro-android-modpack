# Third-party notices

This project is built from multiple third-party layers.

## Mobile base

The Android APK used for this project was built on top of:

- **mininxd/balatromod** — Balatro modpack for mobile
  - Repository: `https://github.com/mininxd/balatromod`
  - Upstream repository currently declares no repository license.
  - Its documented bundled content includes Sandbox Mode, Talisman, JokerDisplay, Always Show Seed, Zodiac Cards, Hyperinflation Tag, custom Jokers and related mobile-pack support files.

Because the upstream repository currently has no declared license, this public repository does not copy the entire `mininxd/balatromod` source tree. It records the upstream dependency and keeps our compatibility layer separate.

## Additional mods layered onto the mobile base

- Balatro+ — SomeCoder99
- Bunco — Firch, RENREN, Peas, minichibis, J.D., Guwahavel, Ciirulean, ejwu
- Mika's Mod Collection — Mikadoe
- Reroll Packs — DorkDad141

Balatro itself is not included.

## Public-repository policy

This repository stores Android compatibility tooling, manifests, hashes, bug documentation and project-specific patches. It does not vendor the complete recovered copies of third-party projects when the applicable redistribution terms have not been confirmed.

Mika's Mod Collection is published from a GPL-3.0 GitHub repository. Balatro+'s upstream GitHub repository currently reports no repository license, so its recovered source is not republished wholesale here. The same conservative policy is being applied to `mininxd/balatromod` because that repository also currently reports no license.

Where practical, rebuilds should obtain third-party projects from their own upstream sources and then apply this project's Android compatibility layer.
