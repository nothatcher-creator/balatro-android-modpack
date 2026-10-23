#!/usr/bin/env python3
"""Change only root version attributes in Android binary XML, without apktool.

The input/output CLI files are raw AndroidManifest.xml bytes, not whole APKs.
Existing strings, styles, resources and XML chunks are retained. A new version
name is appended to the string pool; the old string is never changed in place.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import struct


NONE = 0xFFFFFFFF
ANDROID = "http://schemas.android.com/apk/res/android"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _chunks(data):
    _require(len(data) >= 8, "Truncated binary XML header")
    kind, header, size = struct.unpack_from("<HHI", data)
    _require((kind, header, size) == (3, 8, len(data)), "Invalid binary XML header/size")
    offset, chunks = 8, []
    while offset < len(data):
        _require(offset + 8 <= len(data), "Truncated XML chunk header")
        kind, header, size = struct.unpack_from("<HHI", data, offset)
        _require(8 <= header <= size and size % 4 == 0 and offset + size <= len(data),
                 "Invalid XML chunk size")
        chunks.append((offset, kind, header, size))
        offset += size
    return chunks


class _StringPool:
    def __init__(self, data):
        self.data = data
        _require(len(data) >= 28, "Truncated string pool")
        kind, header, size = struct.unpack_from("<HHI", data)
        _require(kind == 1 and header == 28 and size == len(data), "Unsupported string pool header")
        self.count, self.styles, self.flags, self.start, self.style_start = struct.unpack_from("<IIIII", data, 8)
        table_end = 28 + 4 * (self.count + self.styles)
        _require(self.styles <= self.count and table_end <= self.start <= size,
                 "Invalid string pool offsets")
        _require((self.styles == 0 and self.style_start == 0)
                 or (self.styles > 0 and self.start <= self.style_start <= size),
                 "Invalid style pool offset")
        self.end = self.style_start or size
        self.utf8 = bool(self.flags & 0x100)
        self.strings = []
        for index in range(self.count):
            pos = self.start + struct.unpack_from("<I", data, 28 + 4 * index)[0]
            if self.utf8:
                units, pos = self._length(pos, 1)
                length, pos = self._length(pos, 1)
                _require(pos + length < self.end and data[pos + length] == 0,
                         "Truncated UTF-8 string")
                value = data[pos:pos + length].decode("utf-8")
                _require(len(value.encode("utf-16-le")) // 2 == units, "Invalid UTF-8 string length")
            else:
                units, pos = self._length(pos, 2)
                length = units * 2
                _require(pos + length + 2 <= self.end and data[pos + length:pos + length + 2] == b"\0\0",
                         "Truncated UTF-16 string")
                value = data[pos:pos + length].decode("utf-16-le")
            self.strings.append(value)

    def _length(self, pos, width):
        _require(self.start <= pos and pos + width <= self.end, "Invalid string offset")
        code = "<B" if width == 1 else "<H"
        value = struct.unpack_from(code, self.data, pos)[0]
        pos += width
        high = 1 << (width * 8 - 1)
        if value & high:
            _require(pos + width <= self.end, "Truncated string length")
            value = ((value & (high - 1)) << (width * 8)) | struct.unpack_from(code, self.data, pos)[0]
            pos += width
        return value, pos

    def string(self, index):
        _require(index < self.count, "Invalid string reference")
        return self.strings[index]

    def append(self, value):
        units = len(value.encode("utf-16-le")) // 2
        if self.utf8:
            raw = value.encode("utf-8")
            _require(max(units, len(raw)) <= 0x7FFF, "Version name is too long")
            def length(number):
                return bytes([number]) if number < 128 else bytes([0x80 | (number >> 8), number & 0xFF])
            encoded = length(units) + length(len(raw)) + raw + b"\0"
        else:
            _require(units <= 0x7FFFFFFF, "Version name is too long")
            prefix = (struct.pack("<H", units) if units < 0x8000
                      else struct.pack("<HH", 0x8000 | (units >> 16), units & 0xFFFF))
            encoded = prefix + value.encode("utf-16-le") + b"\0\0"
        encoded += b"\0" * (-len(encoded) % 4)
        # Preserve old string data including padding, and all existing styles.
        table_end = 28 + 4 * self.count
        result = bytearray(self.data[:table_end] + struct.pack("<I", self.end - self.start)
                           + self.data[table_end:self.end] + encoded + self.data[self.end:])
        struct.pack_into("<I", result, 4, len(result))
        struct.pack_into("<I", result, 8, self.count + 1)
        struct.pack_into("<I", result, 16, self.flags & ~1)  # Appended strings need not remain sorted.
        struct.pack_into("<I", result, 20, self.start + 4)
        if self.style_start:
            struct.pack_into("<I", result, 24, self.style_start + 4 + len(encoded))
        return bytes(result)


def _parse(data):
    chunks = _chunks(data)
    pools = [entry for entry in chunks if entry[1] == 1]
    _require(len(pools) == 1, "Expected exactly one string pool")
    pool_offset, _, _, pool_size = pools[0]
    try:
        pool = _StringPool(data[pool_offset:pool_offset + pool_size])
    except (UnicodeError, struct.error) as error:
        raise ValueError("Malformed string pool") from error
    maps = [entry for entry in chunks if entry[1] == 0x180]
    _require(len(maps) == 1 and maps[0][2] == 8, "Expected one Android resource map")
    map_offset, _, _, map_size = maps[0]
    resource_ids = struct.unpack_from("<" + "I" * ((map_size - 8) // 4), data, map_offset + 8)
    _require(len(resource_ids) <= pool.count, "Invalid Android resource map")
    stack, root_seen, found = [], False, {}
    for offset, kind, header, size in chunks:
        if kind == 0x102:
            _require(offset > pool_offset and header == 16 and size >= 36, "Invalid start-element chunk")
            ns, name, attr_start, attr_size, count = struct.unpack_from("<IIHHH", data, offset + 16)
            tag = pool.string(name)
            if ns != NONE:
                pool.string(ns)
            _require(attr_start >= 20 and attr_size >= 20
                     and 16 + attr_start + count * attr_size <= size, "Invalid XML attributes")
            is_root = not stack
            if is_root:
                _require(not root_seen and tag == "manifest" and ns == NONE, "Expected one root manifest element")
                root_seen = True
            for index in range(count):
                pos = offset + 16 + attr_start + index * attr_size
                ans, aname, raw, value_size, reserved, value_type, value = struct.unpack_from("<IIIHBBI", data, pos)
                label = pool.string(aname)
                if ans != NONE:
                    pool.string(ans)
                if raw != NONE:
                    pool.string(raw)
                if value_type == 3:
                    pool.string(value)
                _require(value_size == 8 and reserved == 0, "Invalid typed attribute")
                if is_root and label in ("versionCode", "versionName"):
                    _require(label not in found and ans != NONE and pool.string(ans) == ANDROID,
                             "Missing, duplicate or wrongly namespaced version attribute")
                    expected_id = 0x0101021B if label == "versionCode" else 0x0101021C
                    _require(aname < len(resource_ids) and resource_ids[aname] == expected_id,
                             "Unexpected Android version attribute resource ID")
                    found[label] = (pos, raw, value_type, value)
            stack.append((ns, name))
        elif kind == 0x103:
            _require(header == 16 and size == 24 and stack, "Invalid end-element chunk")
            _require(struct.unpack_from("<II", data, offset + 16) == stack.pop(), "Mismatched XML elements")
    _require(root_seen and not stack, "Incomplete root manifest element")
    _require(set(found) == {"versionCode", "versionName"}, "Missing versionCode or versionName attribute")
    code, name = found["versionCode"], found["versionName"]
    _require(code[2] == 0x10 and code[1] == NONE, "Unsupported versionCode type or raw value")
    _require(name[2] == 3 and (name[1] == NONE or name[1] == name[3]), "Unsupported versionName type or raw value")
    return pools[0], pool, code, name


def read_manifest_version(data: bytes) -> tuple[int, str]:
    """Read and validate the unique root android version attributes."""
    _, pool, code, name = _parse(data)
    return code[3], pool.string(name[3])


def patch_manifest(data: bytes, *, version_code: int, version_name: str,
                   expected_version_code: int | None = 73) -> bytes:
    """Patch a validated binary manifest, rejecting an unexpected baseline."""
    _require(type(version_code) is int and 0 < version_code <= 0x7FFFFFFF, "Invalid target versionCode")
    _require(isinstance(version_name, str) and version_name and "\0" not in version_name,
             "Invalid target versionName")
    chunk_info, pool, code, name = _parse(data)
    if expected_version_code is not None:
        _require(code[3] == expected_version_code,
                 f"Expected versionCode {expected_version_code}, found {code[3]}")
    updated = bytearray(data)
    struct.pack_into("<I", updated, code[0] + 16, version_code)
    struct.pack_into("<I", updated, name[0] + 16, pool.count)
    if name[1] != NONE:
        struct.pack_into("<I", updated, name[0] + 8, pool.count)
    offset, _, _, size = chunk_info
    updated[offset:offset + size] = pool.append(version_name)
    struct.pack_into("<I", updated, 4, len(updated))
    result = bytes(updated)
    _require(read_manifest_version(result) == (version_code, version_name), "Patched version did not validate")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-version-code", type=int, default=73)
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--version-name", required=True)
    args = parser.parse_args()
    try:
        result = patch_manifest(args.input.read_bytes(), version_code=args.version_code,
                                version_name=args.version_name,
                                expected_version_code=args.expected_version_code)
        with args.output.open("xb") as output:
            output.write(result)
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
