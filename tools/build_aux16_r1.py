#!/usr/bin/env python3
"""Build AppleWorks-MaxRAM AUX16 R1 6 MB validation image.

Input: stock AppleWorks 5.1 Program.po
Output: AppleWorks-MaxRAM-AUX16-R1-6MB.po

R1 keeps stock/Hugh 6 MB geometry but removes the physical-bank table:
- APLWORKS.SYSTEM caps at 96 extended banks
- bank numbers are not stored in the table
- bank-link setup selects physical bank X directly
- SEG.AM maps logical selector Y to physical bank Y+1
"""

import argparse
import hashlib
from pathlib import Path

BLOCK = 512
ENTRY = 39
ENTRIES = 13

EXPECTED_IMAGE = "76c569b26800b721f691e9a4019413606cf760574a8f2b28a25bbfff9d53a808"
EXPECTED_APL = "154baf394ea062868b2c4468caaddcdf95dd8433b7bf7f46cbc5c0e7e5f86847"
EXPECTED_SEGAM = "371d3a93e9ee4b5c42383fd4d2f3050a5c82e6b97bf87f40e3bf720dcf07d25f"
EXPECTED_OUT = "9284f8813e049b1e7ec94d7cc4c337e71d6a16fa347e84412f6c979599775464"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def u16(buf, off):
    return buf[off] | (buf[off + 1] << 8)

def u24(buf, off):
    return buf[off] | (buf[off + 1] << 8) | (buf[off + 2] << 16)

def root_entries(data):
    out = {}
    block = 2
    first = True
    while block:
        b = data[block * BLOCK:(block + 1) * BLOCK]
        nxt = u16(b, 2)
        for i in range(ENTRIES):
            off = 4 + i * ENTRY
            e = b[off:off + ENTRY]
            st = e[0] >> 4
            nl = e[0] & 0x0F
            if st == 0:
                continue
            if first and i == 0 and st in (0xE, 0xF):
                continue
            name = e[1:1 + nl].decode("ascii", "replace")
            out[name] = {
                "storage": st,
                "key": u16(e, 17),
                "eof": u24(e, 21),
            }
        first = False
        block = nxt
    return out

def index_ptrs(data, block):
    b = data[block * BLOCK:(block + 1) * BLOCK]
    return [b[i] | (b[i + 256] << 8) for i in range(256)]

def blocks(data, entry):
    count = (entry["eof"] + BLOCK - 1) // BLOCK
    if entry["storage"] == 1:
        return [entry["key"]]
    if entry["storage"] == 2:
        return index_ptrs(data, entry["key"])[:count]
    raise ValueError("unsupported file storage type")

def read_file(data, entry):
    out = bytearray()
    for bn in blocks(data, entry):
        out.extend(data[bn * BLOCK:(bn + 1) * BLOCK])
    return bytes(out[:entry["eof"]])

def write_file(data, entry, payload):
    pos = 0
    for bn in blocks(data, entry):
        chunk = payload[pos:pos + BLOCK]
        start = bn * BLOCK
        data[start:start + len(chunk)] = chunk
        pos += len(chunk)
        if pos >= len(payload):
            break

def patch(input_path, output_path):
    image = bytearray(input_path.read_bytes())
    if sha(image) != EXPECTED_IMAGE:
        raise SystemExit("input image SHA-256 does not match stock AppleWorks 5.1 Program.po")

    entries = root_entries(image)
    apl = bytearray(read_file(image, entries["APLWORKS.SYSTEM"]))
    seg = bytearray(read_file(image, entries["SEG.AM"]))

    if sha(apl) != EXPECTED_APL or sha(seg) != EXPECTED_SEGAM:
        raise SystemExit("stock file hash mismatch")

    assert apl[0x2766:0x276A] == bytes.fromhex("98 9D DE 37")
    apl[0x2766:0x276A] = bytes.fromhex("EA EA EA EA")

    assert apl[0x276A:0x276C] == bytes.fromhex("E0 30")
    apl[0x276A:0x276C] = bytes.fromhex("E0 60")

    assert apl[0x278E:0x2791] == bytes.fromhex("BD DE 37")
    apl[0x278E:0x2791] = bytes.fromhex("8A EA EA")

    assert seg[0x01CD:0x01D0] == bytes.fromhex("B9 CD D0")
    seg[0x01CD:0x01D0] = bytes.fromhex("98 1A EA")

    write_file(image, entries["APLWORKS.SYSTEM"], apl)
    write_file(image, entries["SEG.AM"], seg)

    if sha(image) != EXPECTED_OUT:
        raise SystemExit("output hash mismatch")

    output_path.write_bytes(image)
    print("wrote", output_path)
    print("sha256", sha(image))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path, nargs="?", default=Path("AppleWorks-MaxRAM-AUX16-R1-6MB.po"))
    args = ap.parse_args()
    patch(args.input, args.output)

if __name__ == "__main__":
    main()
