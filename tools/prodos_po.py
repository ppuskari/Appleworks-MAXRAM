#!/usr/bin/env python3
"""Minimal ProDOS-order .po image lister/extractor.

Designed for reproducible AppleWorks-MaxRAM research.

Supported file storage types:
  1 seedling
  2 sapling
  3 tree

This tool does not modify disk images.
"""

import argparse
import hashlib
from pathlib import Path

BLOCK_SIZE = 512
ENTRY_SIZE = 39
ENTRIES_PER_DIR_BLOCK = 13


def u16(buf, off):
    return buf[off] | (buf[off + 1] << 8)


def u24(buf, off):
    return (
        buf[off]
        | (buf[off + 1] << 8)
        | (buf[off + 2] << 16)
    )


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class ProDOSImage:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()

        if len(self.data) % BLOCK_SIZE:
            raise ValueError("image size is not a multiple of 512 bytes")

    def block(self, number):
        start = number * BLOCK_SIZE
        end = start + BLOCK_SIZE
        return self.data[start:end]

    def volume_name(self):
        header = self.block(2)
        first = header[4]
        length = first & 0x0F
        return header[5:5 + length].decode("ascii", "replace")

    def directory_entries(self, key_block=2, prefix=""):
        block_number = key_block
        first_block = True
        seen = set()

        while block_number and block_number not in seen:
            seen.add(block_number)
            block = self.block(block_number)
            next_block = u16(block, 2)

            for index in range(ENTRIES_PER_DIR_BLOCK):
                off = 4 + index * ENTRY_SIZE
                entry = block[off:off + ENTRY_SIZE]

                if len(entry) != ENTRY_SIZE:
                    continue

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

                if prefix:
                    full_path = prefix + "/" + name
                else:
                    full_path = "/" + name

                yield full_path, {
                    "storage": storage,
                    "name": name,
                    "file_type": entry[16],
                    "key_block": u16(entry, 17),
                    "blocks_used": u16(entry, 19),
                    "eof": u24(entry, 21),
                    "aux_type": u16(entry, 31),
                }

            first_block = False
            block_number = next_block

    def walk(self, key_block=2, prefix=""):
        for full_path, entry in self.directory_entries(
            key_block, prefix
        ):
            yield full_path, entry

            if entry["storage"] == 0xD:
                yield from self.walk(
                    entry["key_block"], full_path
                )

    def index_pointers(self, block_number):
        block = self.block(block_number)
        return [
            block[i] | (block[i + 256] << 8)
            for i in range(256)
        ]

    def extract_entry(self, entry):
        storage = entry["storage"]
        key_block = entry["key_block"]
        eof = entry["eof"]
        out = bytearray()

        if storage == 1:
            out.extend(self.block(key_block))

        elif storage == 2:
            for data_block in self.index_pointers(key_block):
                if data_block:
                    out.extend(self.block(data_block))
                else:
                    out.extend(bytes(BLOCK_SIZE))

                if len(out) >= eof:
                    break

        elif storage == 3:
            for index_block in self.index_pointers(key_block):
                if index_block:
                    for data_block in self.index_pointers(
                        index_block
                    ):
                        if data_block:
                            out.extend(
                                self.block(data_block)
                            )
                        else:
                            out.extend(bytes(BLOCK_SIZE))

                        if len(out) >= eof:
                            break
                else:
                    out.extend(
                        bytes(BLOCK_SIZE * 256)
                    )

                if len(out) >= eof:
                    break

        else:
            raise ValueError(
                "unsupported storage type $%X"
                % storage
            )

        return bytes(out[:eof])


def list_image(image):
    print("image: %s" % image.path)
    print("volume: /%s" % image.volume_name())
    print("size: %d" % len(image.data))
    print("sha256: %s" % sha256(image.data))

    for path, entry in image.walk():
        print(
            "%-40s st=%X type=$%02X eof=%7d"
            % (
                path,
                entry["storage"],
                entry["file_type"],
                entry["eof"],
            )
        )


def extract_paths(image, paths, output_dir):
    entries = dict(image.walk())
    output_dir.mkdir(parents=True, exist_ok=True)

    for requested in paths:
        if requested not in entries:
            raise SystemExit(
                "not found: %s" % requested
            )

        entry = entries[requested]

        if entry["storage"] == 0xD:
            raise SystemExit(
                "cannot extract directory as file: %s"
                % requested
            )

        data = image.extract_entry(entry)
        name = requested.lstrip("/").replace("/", "_")
        target = output_dir / name
        target.write_bytes(data)

        print(
            "%s -> %s size=%d sha256=%s"
            % (
                requested,
                target,
                len(data),
                sha256(data),
            )
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--extract",
        nargs="*",
        metavar="PRODOS_PATH",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/prodos-extract"),
    )
    args = parser.parse_args()

    image = ProDOSImage(args.image)

    if args.extract:
        extract_paths(
            image,
            args.extract,
            args.output_dir,
        )
    else:
        list_image(image)


if __name__ == "__main__":
    main()
