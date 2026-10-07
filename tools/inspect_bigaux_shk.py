#!/usr/bin/env python3
"""Inspect Hugh Hood's Big AuxCard NuFX/ShrinkIt distribution.

This intentionally does not contain or redistribute AppleWorks binaries.
It inventories a supplied .SHK and can optionally extract its data forks
to a private working directory for local comparison.
"""

import argparse
import hashlib
import struct
from pathlib import Path

NUFX_MASTER = bytes([0x4E, 0xF5, 0x46, 0xE9, 0x6C, 0xE5])
NUFX_RECORD = bytes([0x4E, 0xF5, 0x46, 0xD8])


def u16(buf, off):
    return struct.unpack_from("<H", buf, off)[0]


def u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def rle_decode(buf, escape):
    out = bytearray()
    i = 0
    while i < len(buf):
        if buf[i] != escape:
            out.append(buf[i])
            i += 1
            continue
        if i + 2 >= len(buf):
            raise ValueError("truncated RLE sequence")
        value = buf[i + 1]
        count_minus_1 = buf[i + 2]
        out.extend([value] * (count_minus_1 + 1))
        i += 3
    return bytes(out)


class LZW2State:
    def __init__(self):
        self.reset()

    def reset(self):
        self.table = {i: bytes([i]) for i in range(256)}
        self.next_code = 257
        self.width = 9
        self.prev = None

    def decode_chunk(self, encoded, target_len):
        bitpos = 0
        out = bytearray()

        def getcode(width):
            nonlocal bitpos
            if bitpos + width > len(encoded) * 8:
                return None
            byte_index = bitpos // 8
            shift = bitpos % 8
            value = 0
            for j in range(3):
                if byte_index + j < len(encoded):
                    value |= encoded[byte_index + j] << (8 * j)
            bitpos += width
            return (value >> shift) & ((1 << width) - 1)

        while len(out) < target_len:
            code = getcode(self.width)
            if code is None:
                raise ValueError("compressed LZW/2 chunk ended early")
            if code == 0x100:
                self.reset()
                continue
            if code in self.table:
                entry = self.table[code]
            elif code == self.next_code and self.prev is not None:
                entry = self.prev + self.prev[:1]
            else:
                raise ValueError("invalid LZW/2 code")

            out.extend(entry)

            if self.prev is not None and self.next_code < 4096:
                self.table[self.next_code] = self.prev + entry[:1]
                self.next_code += 1
                # ShrinkIt LZW/2 changes code width one entry ahead.
                if self.next_code + 1 >= (1 << self.width) and self.width < 12:
                    self.width += 1

            self.prev = entry

        return bytes(out[:target_len])


def expand_lzw2(payload, eof):
    if len(payload) < 2:
        raise ValueError("short LZW/2 payload")

    escape = payload[1]
    pos = 2
    logical = bytearray()
    state = LZW2State()

    while len(logical) < eof:
        if pos + 2 > len(payload):
            raise ValueError("truncated LZW/2 chunk header")

        header = u16(payload, pos)
        pos += 2
        is_lzw = bool(header & 0x8000)
        rle_len = header & 0x1FFF

        if is_lzw:
            if pos + 2 > len(payload):
                raise ValueError("truncated LZW/2 encoded length")
            total_len = u16(payload, pos)
            pos += 2
            data_len = total_len - 4
            encoded = payload[pos:pos + data_len]
            pos += data_len
            pre_rle = state.decode_chunk(encoded, rle_len)
        else:
            pre_rle = bytes(payload[pos:pos + rle_len])
            pos += rle_len
            state.reset()

        raw = pre_rle if rle_len == 4096 else rle_decode(pre_rle, escape)
        if len(raw) != 4096:
            raise ValueError("LZW/2 chunk did not expand to 4096 bytes")
        logical.extend(raw)

    return bytes(logical[:eof])


def parse_records(buf):
    if buf[:6] != NUFX_MASTER:
        raise ValueError("not a NuFX/ShrinkIt archive")

    count = u32(buf, 8)
    records = []
    offset = 48

    for record_index in range(count):
        if buf[offset:offset + 4] != NUFX_RECORD:
            raise ValueError(
                "bad record signature at record %d" % record_index
            )

        attrib_count = u16(buf, offset + 6)
        thread_count = u32(buf, offset + 10)
        filename_len = u16(buf, offset + attrib_count - 2)
        old_name = buf[
            offset + attrib_count:
            offset + attrib_count + filename_len
        ]
        thread_headers = offset + attrib_count + filename_len
        payload_pos = thread_headers + 16 * thread_count

        if filename_len:
            name = old_name.decode("mac_roman", "replace")
        else:
            name = None

        data = None

        for thread_index in range(thread_count):
            th = thread_headers + 16 * thread_index
            thread_class, fmt, kind, _crc = struct.unpack_from(
                "<HHHH", buf, th
            )
            eof, compressed_eof = struct.unpack_from("<II", buf, th + 8)
            payload = buf[payload_pos:payload_pos + compressed_eof]

            if thread_class == 3 and kind == 0:
                name = payload[:eof].decode("mac_roman", "replace")
            elif thread_class == 2 and kind == 0:
                if fmt == 0:
                    data = bytes(payload[:eof])
                elif fmt == 3:
                    data = expand_lzw2(payload, eof)
                else:
                    raise ValueError(
                        "unsupported data thread format %d" % fmt
                    )

            payload_pos += compressed_eof

        records.append((name, data))
        offset = payload_pos

    return records


def show_differences(records):
    data_records = [(name, data) for name, data in records if data is not None]
    if len(data_records) != 2:
        return

    name_a, data_a = data_records[0]
    name_b, data_b = data_records[1]

    if len(data_a) != len(data_b):
        print("payload lengths differ; byte comparison skipped")
        return

    diffs = [
        (i, a, b)
        for i, (a, b) in enumerate(zip(data_a, data_b))
        if a != b
    ]

    print("")
    print("payload comparison:")
    print("  %s" % name_a)
    print("  %s" % name_b)
    print("  differing bytes: %d" % len(diffs))
    for offset, value_a, value_b in diffs:
        print(
            "  $%04X: $%02X / $%02X"
            % (offset, value_a, value_b)
        )


def main():
    parser = argparse.ArgumentParser(
        description="Inspect Hugh Hood Big AuxCard ShrinkIt archive"
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--extract-dir", type=Path)
    args = parser.parse_args()

    blob = args.archive.read_bytes()

    print("archive: %s" % args.archive)
    print("size: %d" % len(blob))
    print("sha256: %s" % sha256(blob))

    records = parse_records(blob)

    for index, (name, data) in enumerate(records, 1):
        print("%d: %s" % (index, name))
        if data is None:
            continue

        print("   size=%d sha256=%s" % (len(data), sha256(data)))

        if args.extract_dir:
            args.extract_dir.mkdir(parents=True, exist_ok=True)
            safe_name = name.replace(":", "_").replace("/", "_")
            path = args.extract_dir / safe_name
            path.write_bytes(data)
            print("   extracted=%s" % path)

    show_differences(records)


if __name__ == "__main__":
    main()
