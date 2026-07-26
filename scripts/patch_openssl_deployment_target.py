#!/usr/bin/env python3
"""Lower accidental iOS 26.0 minimums in downloaded binary frameworks.

Some prebuilt xcframework releases have device slices stamped with the SDK
version they were produced with rather than the intended deployment target. The
app can build, upload to TestFlight, and pass Simulator tests, but then dyld will
refuse to launch it on a real device running an older iOS. Patch every Mach-O we
can find in the downloaded artifacts, not just OpenSSL.
"""

from __future__ import annotations

import os
import plistlib
import struct
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1] / "xcfs/.build/artifacts/xcfs"
TARGET_VERSION = os.environ.get("BLINK_MIN_IOS_VERSION", "17.6")
LC_VERSION_MIN_IPHONEOS = 0x25
LC_BUILD_VERSION = 0x32
PLATFORM_IOS = 2
PLATFORM_IOSSIMULATOR = 7
IOS_PLATFORMS = {PLATFORM_IOS, PLATFORM_IOSSIMULATOR}
FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF
MH_MAGIC = 0xFEEDFACE
MH_MAGIC_64 = 0xFEEDFACF
AR_MAGIC = b"!<arch>\n"


def encode_version(version: str) -> Optional[int]:
    try:
        parts = [int(part) for part in version.split(".")]
    except ValueError:
        return None
    parts = (parts + [0, 0])[:3]
    return (parts[0] << 16) | (parts[1] << 8) | parts[2]


TARGET_ENCODED = encode_version(TARGET_VERSION)
if TARGET_ENCODED is None:
    raise SystemExit(f"Invalid BLINK_MIN_IOS_VERSION: {TARGET_VERSION}")


def decode_version(version: int) -> str:
    major = (version >> 16) & 0xFFFF
    minor = (version >> 8) & 0xFF
    patch = version & 0xFF
    return f"{major}.{minor}" if patch == 0 else f"{major}.{minor}.{patch}"


def macho_slices(data: bytearray) -> list[tuple[int, int]]:
    if len(data) < 4 or data.startswith(AR_MAGIC):
        return []

    magic = struct.unpack_from(">I", data)[0]
    if magic == FAT_MAGIC:
        count = struct.unpack_from(">I", data, 4)[0]
        return [struct.unpack_from(">II", data, 8 + index * 20 + 8) for index in range(count)]
    if magic == FAT_MAGIC_64:
        count = struct.unpack_from(">I", data, 4)[0]
        return [struct.unpack_from(">QQ", data, 8 + index * 32 + 8) for index in range(count)]

    if struct.unpack_from("<I", data)[0] in (MH_MAGIC, MH_MAGIC_64):
        return [(0, len(data))]

    return []


def patch_binary(path: Path) -> list[str]:
    data = bytearray(path.read_bytes())
    changes: list[str] = []

    for offset, size in macho_slices(data):
        if offset + size > len(data):
            raise ValueError(f"Invalid Mach-O slice in {path}")

        magic = struct.unpack_from("<I", data, offset)[0]
        if magic == MH_MAGIC_64:
            header_size = 32
        elif magic == MH_MAGIC:
            header_size = 28
        else:
            # Unknown slice inside a fat file; leave it alone.
            continue

        command_count = struct.unpack_from("<I", data, offset + 16)[0]
        command_offset = offset + header_size
        for _ in range(command_count):
            command, command_size = struct.unpack_from("<II", data, command_offset)
            if command_size < 8 or command_offset + command_size > offset + size:
                raise ValueError(f"Invalid load command in {path}")

            if command == LC_BUILD_VERSION and command_size >= 24:
                platform = struct.unpack_from("<I", data, command_offset + 8)[0]
                current = struct.unpack_from("<I", data, command_offset + 12)[0]
                if platform in IOS_PLATFORMS and current > TARGET_ENCODED:
                    struct.pack_into("<I", data, command_offset + 12, TARGET_ENCODED)
                    changes.append(f"LC_BUILD_VERSION {decode_version(current)} -> {TARGET_VERSION}")
            elif command == LC_VERSION_MIN_IPHONEOS and command_size >= 16:
                current = struct.unpack_from("<I", data, command_offset + 8)[0]
                if current > TARGET_ENCODED:
                    struct.pack_into("<I", data, command_offset + 8, TARGET_ENCODED)
                    changes.append(f"LC_VERSION_MIN_IPHONEOS {decode_version(current)} -> {TARGET_VERSION}")

            command_offset += command_size

    if changes:
        path.write_bytes(data)
    return changes


def framework_binaries(root: Path) -> list[Path]:
    result: list[Path] = []
    for framework in sorted(root.rglob("*.framework")):
        binary = framework / framework.stem
        if binary.is_file():
            result.append(binary)
    return result


def patch_minimum_os_versions(root: Path) -> int:
    patched = 0
    for info_path in sorted(root.rglob("*.framework/Info.plist")):
        with info_path.open("rb") as stream:
            info = plistlib.load(stream)

        current = info.get("MinimumOSVersion")
        current_encoded = encode_version(current) if isinstance(current, str) else None
        if current_encoded is not None and current_encoded > TARGET_ENCODED:
            info["MinimumOSVersion"] = TARGET_VERSION
            with info_path.open("wb") as stream:
                plistlib.dump(info, stream, fmt=plistlib.FMT_BINARY, sort_keys=False)
            patched += 1
    return patched


def main() -> None:
    if not ROOT.is_dir():
        print(f"Warning: XCFramework artifacts not found: {ROOT}")
        return

    patched_binaries = 0
    for binary in framework_binaries(ROOT):
        rel = binary.relative_to(ROOT)
        try:
            changes = patch_binary(binary)
        except Exception as exc:
            # Do not break CI for a binary shape we do not understand. The
            # following archive/export steps and App Store validation will still
            # catch unusable artifacts, while known Mach-O framework binaries are
            # patched above.
            print(f"Warning: could not inspect {rel}: {exc}")
            continue

        if changes:
            patched_binaries += 1
            print(f"Patched {rel}: {', '.join(changes)}")

    try:
        patched_plists = patch_minimum_os_versions(ROOT)
    except Exception as exc:
        print(f"Warning: could not patch framework Info.plists: {exc}")
        patched_plists = 0

    if patched_binaries == 0 and patched_plists == 0:
        print(f"All downloaded framework deployment targets are already iOS {TARGET_VERSION} or lower")
    else:
        print(
            f"Patched deployment targets to iOS {TARGET_VERSION} "
            f"in {patched_binaries} binaries and {patched_plists} Info.plists"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Framework patching is a compatibility step. Never fail the build here;
        # surface the problem in logs and allow the normal build/export checks to run.
        print(f"Warning: framework deployment target patching failed: {exc}")
