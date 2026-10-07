#!/usr/bin/env python3
"""Build AppleWorks-MaxRAM AUX16 R0 validation image.

R0 intentionally leaves APLWORKS.SYSTEM completely stock.  It patches
only SEG.AM's physical-bank lookup:

    LDA $D0CD,Y

to:

    TYA
    INC A
    NOP

This preserves the stock 3 MB cap while validating direct contiguous
RamWorks bank mapping before any capacity changes are attempted.

Input must be the known AppleWorks 5.1 Program.po baseline.
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
EXPECTED_SEGAM_SHA256 = (
    "371d3a93e9ee4b5c42383fd4d2f3050a5c82e6b97bf87f40e3bf720dcf07d25f"
)
EXPECTED_PATCHED_SEGAM_SHA256 = (
    "255253463f57c90b744523be4d04877d22eb3269e6fcf560994636e508a579ed"
)
EXPECTED_OUTPUT_SHA256 = (
    "00e2f1e0af3efdaf49ecf57697bac39be7b8eb7e21f8d2402e8cabbe65212747"
)

SEGAM_OFFSET = 0x01CD
SEGAM_OLD = bytes.fromhex("B9 CD D0")
SEGAM_NEW = bytes.fromhex("98 1A EA")


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
        block_number = 2
        first_block = True
        seen = set()

        while block_number and block_number not in seen:
            seen.add(block_number)
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

                yield name, {
                    "storage": storage,
                    "key_block": u16(entry, 17),
                    "eof": u24(entry, 21),
                }

            first_block = False
            block_number = next_block

    def index_pointers(self, block_number):
        block = self.block(block_number)
        return [
            block[i] | (block[i + 256] << 8)
            for i in range(256)
        ]

    def data_blocks(self, entry):
        needed = (
            entry["eof"] + BLOCK_SIZE - 1
        ) // BLOCK_SIZE
        storage = entry["storage"]
        key = entry["key_block"]

        if storage == 1:
            return [key]

        if storage == 2:
            return self.index_pointers(key)[:needed]

        raise ValueError(
            "R0 builder expected seedling/sapling file"
        )

    def read_file(self, entry):
        result = bytearray()

        for block_number in self.data_blocks(entry):
            if block_number == 0:
                result.extend(bytes(BLOCK_SIZE))
            else:
                result.extend(self.block(block_number))

        return bytes(result[:entry["eof"]])

    def write_file(self, entry, payload):
        if len(payload) != entry["eof"]:
            raise ValueError("replacement size changed")

        position = 0

        for block_number in self.data_blocks(entry):
            if block_number == 0:
                raise ValueError("cannot patch sparse block")

            chunk = payload[
                position:position + BLOCK_SIZE
            ]
            start = block_number * BLOCK_SIZE
            self.data[start:start + len(chunk)] = chunk

            position += len(chunk)

            if position >= len(payload):
                break


def build(input_path, output_path):
    original = input_path.read_bytes()
    input_hash = sha256(original)

    if input_hash != EXPECTED_IMAGE_SHA256:
        raise SystemExit(
            "Refusing unknown input image.\n"
            "Expected: %s\n"
            "Actual:   %s"
            % (EXPECTED_IMAGE_SHA256, input_hash)
        )

    image = ProDOSImage(original)
    entries = dict(image.root_entries())

    if "SEG.AM" not in entries:
        raise SystemExit("SEG.AM not found in root directory")

    entry = entries["SEG.AM"]
    segam = bytearray(image.read_file(entry))

    if sha256(segam) != EXPECTED_SEGAM_SHA256:
        raise SystemExit("SEG.AM hash does not match baseline")

    if segam[
        SEGAM_OFFSET:SEGAM_OFFSET + len(SEGAM_OLD)
    ] != SEGAM_OLD:
        raise SystemExit("SEG.AM patch signature not found")

    segam[
        SEGAM_OFFSET:SEGAM_OFFSET + len(SEGAM_NEW)
    ] = SEGAM_NEW

    patched_seg_hash = sha256(segam)

    if patched_seg_hash != EXPECTED_PATCHED_SEGAM_SHA256:
        raise SystemExit("patched SEG.AM hash mismatch")

    image.write_file(entry, segam)

    output = bytes(image.data)
    output_hash = sha256(output)

    diffs = [
        i for i, (old, new)
        in enumerate(zip(original, output))
        if old != new
    ]

    if len(diffs) != 3:
        raise SystemExit(
            "expected exactly 3 changed image bytes"
        )

    if output_hash != EXPECTED_OUTPUT_SHA256:
        raise SystemExit("output image hash mismatch")

    output_path.write_bytes(output)

    print("AUX16 R0 validation image built")
    print("input:  %s" % input_hash)
    print("SEG.AM: %s" % patched_seg_hash)
    print("output: %s" % output_hash)
    print("changed image bytes: 3")
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
            "AppleWorks-MaxRAM-AUX16-R0-3MB.po"
        ),
    )
    args = parser.parse_args()

    build(args.input, args.output)


if __name__ == "__main__":
    main()
