# Android materializer notes

The tested August 12, 2026 APK used a bundled-mod materializer identified as:

`2026-08-12-materialized-v10-crash-report-batchfix`

Its job was to copy the bundled modpack into the writable `smods_mods/` location on Android, record the installed materializer version, and avoid applying Lovely patches twice when equivalent compatibility changes were already baked into the Android build.

The exact recovered `bundled_mods_bootstrap.lua` is intentionally not published in this public repository because it enumerates and packages files from third-party mods whose redistribution terms are not all confirmed.

For private development, recover it locally from a compatible APK with:

```bash
python scripts/extract_from_apk.py /path/to/your.apk recovered
```

The recovered file will be written to `recovered/android/bundled_mods_bootstrap.lua` when present in the APK.
