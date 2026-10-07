#!/usr/bin/env python3
"""Build AppleWorks-MaxRAM AUX16 R3 9 MB boundary image.

R3 is the first build that deliberately crosses physical RamWorks bank
$7F into banks $80 and above.

Use a 16 MB RamWorks-compatible emulator configuration.  R3 probes the
entire $01-$FF extended-bank range but caps accepted banks at $90
(144 banks = 9 MB expansion) to isolate the $7F/$80 boundary.

Input must be the known stock AppleWorks 5.1 Program.po image.
"""

import argparse
import hashlib
from pathlib import Path

BLOCK_SIZE = 512
ENTRY_SIZE = 39
ENTRIES_PER_DIR_BLOCK = 13

EXPECTED_IMAGE_SHA256 = (
    "76c569b26800b721f691e9a4019413606cf760574a8f2b28a25bbfff9d53a808"
)
EXPECTED_APL_SHA256 = (
    "154baf394ea062868b2c4468caaddcdf95dd8433b7bf7f46cbc5c0e7e5f86847"
)
EXPECTED_SEGAM_SHA256 = (
    "371d3a93e9ee4b5c42383fd4d2f3050a5c82e6b97bf87f40e3bf720dcf07d25f"
)
EXPECTED_PATCHED_APL_SHA256 = (
    "1e9297291ea04850426fce1f04e6ecd256f20ff5d951caf7fbcb0a1825e53d4c"
)
EXPECTED_PATCHED_SEGAM_SHA256 = (
    "255253463f57c90b744523be4d04877d22eb3269e6fcf560994636e508a579ed"
)
EXPECTED_OUTPUT_SHA256 = (
    "75f263c73c4448542823cc80061fd3ce6a30a5f6e55fdefc98b01e151a72ed5e"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def u16(buf, off):
    return buf[off] | (buf[off + 1] << 8)


def u24(buf, off):
    return (
        buf[off]
        | (buf[off + 1] << 8)
        | (buf[off + 2] << 16)
    )


class ProDOSImage:
    def __init__(self, data):
        self.data = bytearray(data)

    def block(self, number):
        start = number * BLOCK_SIZE
        return bytes(self.data[start:start + BLOCK_SIZE])

    def root_entries(self):
        result = {}
        block_number = 2
        first_block = True

        while block_number:
            block = self.block(block_number)
            next_block = u16(block, 2)

            for index in range(ENTRIES_PER_DIR_BLOCK):
                off = 4 + index * ENTRY_SIZE
                entry = block[off:off + ENTRY_SIZE]
                storage = entry[0] >> 4
                name_len = entry[0] & 0x0F

                if storage == 0:
                    continue

                if (
                    first_block
                    and index == 0
                    and storage in (0xE, 0xF)
                ):
                    continue

                name = entry[1:1 + name_len].decode(
                    "ascii", "replace"
                )

                result[name] = {
                    "storage": storage,
                    "key_block": u16(entry, 17),
                    "eof": u24(entry, 21),
                }

            first_block = False
            block_number = next_block

        return result

    def index_pointers(self, block_number):
        block = self.block(block_number)

        return [
            block[i] | (block[i + 256] << 8)
            for i in range(256)
        ]

    def file_blocks(self, entry):
        needed = (
            entry["eof"] + BLOCK_SIZE - 1
        ) // BLOCK_SIZE

        if entry["storage"] == 1:
            return [entry["key_block"]]

        if entry["storage"] == 2:
            return self.index_pointers(
                entry["key_block"]
            )[:needed]

        raise ValueError("unexpected storage type")

    def read_file(self, entry):
        out = bytearray()

        for block_number in self.file_blocks(entry):
            out.extend(self.block(block_number))

        return bytes(out[:entry["eof"]])

    def write_file(self, entry, payload):
        pos = 0

        for block_number in self.file_blocks(entry):
            chunk = payload[pos:pos + BLOCK_SIZE]
            start = block_number * BLOCK_SIZE
            self.data[start:start + len(chunk)] = chunk
            pos += len(chunk)

            if pos >= len(payload):
                break


def patch_bytes(buf, offset, old_hex, new_hex):
    old = bytes.fromhex(old_hex)
    new = bytes.fromhex(new_hex)

    if buf[offset:offset + len(old)] != old:
        raise ValueError(
            "patch signature missing at $%04X" % offset
        )

    if len(old) != len(new):
        raise ValueError("in-place patch size changed")

    buf[offset:offset + len(new)] = new


def build(input_path, output_path):
    original = input_path.read_bytes()

    if sha256(original) != EXPECTED_IMAGE_SHA256:
        raise SystemExit("unknown input Program.po image")

    image = ProDOSImage(original)
    entries = image.root_entries()

    apl = bytearray(
        image.read_file(entries["APLWORKS.SYSTEM"])
    )
    segam = bytearray(
        image.read_file(entries["SEG.AM"])
    )

    if sha256(apl) != EXPECTED_APL_SHA256:
        raise SystemExit("APLWORKS.SYSTEM baseline mismatch")

    if sha256(segam) != EXPECTED_SEGAM_SHA256:
        raise SystemExit("SEG.AM baseline mismatch")

    # Mark every extended bank, $FF down through $01.
    patch_bytes(
        apl, 0x2745,
        "7F",
        "FF",
    )

    # Stop marker loop when Y reaches $00, not when bit 7 is set.
    patch_bytes(
        apl, 0x2751,
        "10",
        "D0",
    )

    # Do not store physical bank numbers.
    patch_bytes(
        apl, 0x2766,
        "98 9D DE 37",
        "EA EA EA EA",
    )

    # R3 accepts 144 extended banks = 9 MB expansion.
    patch_bytes(
        apl, 0x276A,
        "E0 30",
        "E0 90",
    )

    # Permit verification through $80-$FF until Y wraps to zero.
    patch_bytes(
        apl, 0x276F,
        "10",
        "D0",
    )

    # During link creation use X as the physical bank number.
    patch_bytes(
        apl, 0x278E,
        "BD DE 37",
        "8A EA EA",
    )

    # SEG.AM selector Y -> physical bank Y+1.
    patch_bytes(
        segam, 0x01CD,
        "B9 CD D0",
        "98 1A EA",
    )

    if sha256(apl) != EXPECTED_PATCHED_APL_SHA256:
        raise SystemExit("patched APLWORKS.SYSTEM hash mismatch")

    if sha256(segam) != EXPECTED_PATCHED_SEGAM_SHA256:
        raise SystemExit("patched SEG.AM hash mismatch")

    image.write_file(
        entries["APLWORKS.SYSTEM"], apl
    )
    image.write_file(
        entries["SEG.AM"], segam
    )

    output = bytes(image.data)

    if sha256(output) != EXPECTED_OUTPUT_SHA256:
        raise SystemExit("output hash mismatch")

    output_path.write_bytes(output)

    print("AUX16 R3 9 MB boundary image built")
    print("sha256: %s" % sha256(output))
    print("wrote: %s" % output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        type=Path,
        help="stock AppleWorks 5.1 Program.po",
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path(
            "AppleWorks-MaxRAM-AUX16-R3-9MB.po"
        ),
    )
    args = parser.parse_args()

    build(args.input, args.output)


if __name__ == "__main__":
    main()
