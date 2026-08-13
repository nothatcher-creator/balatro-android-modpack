# Compatibility fixes in the August 12, 2026 snapshot

This documents the `all-reported-issues-fix` Android compatibility build.

## Crash/UI classes addressed

1. Steamodded edition-tooltip UI crash affecting Foil/Holographic/Negative card hovers.
2. Mika + Talisman big-number comparisons where money/chip values can be table-backed values instead of plain Lua numbers.
3. Mika scoring comparisons that could compare a number with a big-number object during hand evaluation.
4. Missing `money_spend_this_round` state causing arithmetic on nil during money changes.
5. Event/card-generation nil guards for modded pack, shop, and card paths.
6. Reroll Packs Android compatibility preserving the real booster-slot count instead of forcing two slots.
7. Bunco Android shader/static-patch compatibility, including the fluorescent shader path and avoiding already-baked Lovely patches being applied twice.

## Materializer behavior

Version marker:

`2026-08-12-materialized-v10-crash-report-batchfix`

The tested Android build recopied bundled mods to writable `smods_mods/` when the materializer version changed, wrote `.openai_bundled_modpack_version`, and removed Lovely patch files that must not run a second time after equivalent changes were baked into the Android build.
