# Open issues to track

## Additions tab does not behave correctly

The Additions tab in the mod UI is still not functioning as intended after the August 12, 2026 compatibility pass. Reproduce on the current Android build, identify whether the fault is navigation, state, or layout related, and verify Back navigation from mod detail views at the same time.

## Some vanilla Planet cards use incorrect art

Some vanilla Planet cards display the wrong sprite while the modpack is active. Audit atlas ownership, atlas registration order, and any mod that takes ownership of vanilla consumables. Verify all vanilla Planet cards after the fix.
