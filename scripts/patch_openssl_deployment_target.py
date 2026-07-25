#!/usr/bin/env python3
"""Correct the accidental iOS 26.0 minimum in the bundled OpenSSL framework."""

from __future__ import annotations

import plistlib
import struct
from pathlib import Path

ROOT = (
    Path(__file__).resolve().parents[1]
    / "xcfs/.build/artifacts/xcfs/openssl/openssl.xcframework"
)
TARGET_VERSION = "17.6"
TARGET_ENCODED = (17 << 16) | (6 << 8)
LC_BUILD_VERSION = 0x32
FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF
MH_MAGIC_64 = 0xFEEDFACF


def slices(data: bytearray) -> list[tuple[int, int]]:
    magic = struct.unpack_from(">I", data)[0]
    if magic == FAT_MAGIC:
        count = struct.unpack_from(">I", data, 4)[0]
        return [
            struct.unpack_from(">II", data, 8 + index * 20 + 8)
            for index in range(count)
        ]
    if magic == FAT_MAGIC_64:
        count = struct.unpack_from(">I", data, 4)[0]
        return [
            struct.unpack_from(">QQ", data, 8 + index * 32 + 8)
            for index in range(count)
        ]
    return [(0, len(data))]


def patch_binary(path: Path) -> int:
    data = bytearray(path.read_bytes())
    patched = 0

    for offset, size in slices(data):
        if offset + size > len(data):
            raise ValueError(f"Invalid Mach-O slice in {path}")
        if struct.unpack_from("<I", data, offset)[0] != MH_MAGIC_64:
            raise ValueError(f"Unsupported Mach-O format in {path}")

        command_count = struct.unpack_from("<I", data, offset + 16)[0]
        command_offset = offset + 32
        for _ in range(command_count):
            command, command_size = struct.unpack_from("<II", data, command_offset)
            if command_size < 8:
                raise ValueError(f"Invalid load command in {path}")
            if command == LC_BUILD_VERSION:
                current = struct.unpack_from("<I", data, command_offset + 12)[0]
                if current > TARGET_ENCODED:
                    struct.pack_into("<I", data, command_offset + 12, TARGET_ENCODED)
                    patched += 1
            command_offset += command_size

    if patched:
        path.write_bytes(data)
    return patched


def main() -> None:
    if not ROOT.is_dir():
        raise SystemExit(f"OpenSSL XCFramework not found: {ROOT}")

    binaries = sorted(ROOT.glob("*/openssl.framework/openssl"))
    if not binaries:
        raise SystemExit(f"No OpenSSL binaries found under {ROOT}")

    patched = sum(patch_binary(binary) for binary in binaries)
    for info_path in ROOT.glob("*/openssl.framework/Info.plist"):
        with info_path.open("rb") as stream:
            info = plistlib.load(stream)
        info["MinimumOSVersion"] = TARGET_VERSION
        with info_path.open("wb") as stream:
            plistlib.dump(info, stream, fmt=plistlib.FMT_BINARY, sort_keys=False)

    if patched == 0:
        print(f"OpenSSL already has minimum iOS {TARGET_VERSION} or lower")
    else:
        print(f"Patched {patched} OpenSSL load commands to iOS {TARGET_VERSION}")


if __name__ == "__main__":
    main()
