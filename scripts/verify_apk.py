#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

EXPECTED_SHA256 = "118eb6650ddff0cf187487bb45471587a65bd0a245e0530aa2d31552a7adb1af"
EXPECTED_SIZE = 77717587

if len(sys.argv) != 2:
    raise SystemExit("usage: verify_apk.py <apk>")

p = Path(sys.argv[1])
size = p.stat().st_size
sha = hashlib.sha256(p.read_bytes()).hexdigest()

print(f"file: {p}")
print(f"size: {size} bytes")
print(f"sha256: {sha}")

if size != EXPECTED_SIZE or sha != EXPECTED_SHA256:
    raise SystemExit("APK does not match the recovered August 12, 2026 snapshot")

print("OK: APK matches the recovered all-reported-issues-fix build")
