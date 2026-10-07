#!/usr/bin/env python3
"""Build AUX16 R3D: 129-bank test with 256-byte rounding fix."""

import argparse
from pathlib import Path

from build_aux16_r3 import (
    ProDOSImage,
    EXPECTED_IMAGE_SHA256,
    EXPECTED_APL_SHA256,
    EXPECTED_SEGAM_SHA256,
    patch_bytes,
    sha256,
)

EXPECTED_APL_OUT = (
    "474468b886484ed7b83e64dfe11e19dd98ba6e7718bc2f42a747cb8ae5550ec4"
)
EXPECTED_SEGAM_OUT = (
    "f61d06c4a1207106967b52581962afb02c3926ce9a029fe41f235d399d992e37"
)
EXPECTED_IMAGE_OUT = (
    "67509ea79de2a8d3766f5900eb8564845417da0f3b80c6d426a63534a6ec00ce"
)


def build(input_path, output_path):
    original = input_path.read_bytes()

    if sha256(original) != EXPECTED_IMAGE_SHA256:
        raise SystemExit("unknown input Program.po image")

    image = ProDOSImage(original)
    entries = image.root_entries()

    apl = bytearray(image.read_file(entries["APLWORKS.SYSTEM"]))
    segam = bytearray(image.read_file(entries["SEG.AM"]))

    if sha256(apl) != EXPECTED_APL_SHA256:
        raise SystemExit("APLWORKS.SYSTEM baseline mismatch")

    if sha256(segam) != EXPECTED_SEGAM_SHA256:
        raise SystemExit("SEG.AM baseline mismatch")

    # Probe $FF..$01 and accept exactly 129 extended banks.
    patch_bytes(apl, 0x2745, "7F", "FF")
    patch_bytes(apl, 0x2751, "10", "D0")
    patch_bytes(apl, 0x2766, "98 9D DE 37", "EA EA EA EA")
    patch_bytes(apl, 0x276A, "E0 30", "E0 81")
    patch_bytes(apl, 0x276F, "10", "D0")
    patch_bytes(apl, 0x278E, "BD DE 37", "8A EA EA")

    # Direct selector Y -> physical bank Y+1.
    patch_bytes(segam, 0x01CD, "B9 CD D0", "98 1A EA")

    # When HBankMask/HBkAdrMask is $FF/$00, allocation quantum is
    # 256 bytes.  The stock rounding sequence overflows while first
    # forming HBankMask+4 and underallocates most blocks by one page.
    #
    # Correct rule:
    #   round_up(size + 4, 256)
    #   low = 0
    #   high += 1 for low $00-$FC
    #   high += 2 for low $FD-$FF
    patch_bytes(
        segam,
        0x0220,
        "AD CA D0 18 69 04 65 FE 2D CB D0 8D 34 D1 "
        "A5 FF 8D 2F D1 69 00 8D 35 D1 60",
        "A5 FE C9 FD A9 00 8D 34 D1 "
        "A5 FF 8D 2F D1 69 01 8D 35 D1 60 "
        "EA EA EA EA EA",
    )

    patch_bytes(
        segam,
        0x0763,
        "AD CA D0 18 69 04 65 9E 2D CB D0 8D 34 D1 "
        "A5 9F 69 00 8D 35 D1",
        "A5 9E C9 FD A9 00 8D 34 D1 "
        "A5 9F 69 01 8D 35 D1 "
        "EA EA EA EA EA",
    )

    if sha256(apl) != EXPECTED_APL_OUT:
        raise SystemExit("patched APLWORKS.SYSTEM hash mismatch")

    if sha256(segam) != EXPECTED_SEGAM_OUT:
        raise SystemExit("patched SEG.AM hash mismatch")

    image.write_file(entries["APLWORKS.SYSTEM"], apl)
    image.write_file(entries["SEG.AM"], segam)

    output = bytes(image.data)

    if sha256(output) != EXPECTED_IMAGE_OUT:
        raise SystemExit("output hash mismatch")

    output_path.write_bytes(output)

    print("AUX16 R3D 129-bank rounding-fix image built")
    print("sha256: %s" % sha256(output))
    print("wrote: %s" % output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path(
            "AppleWorks-MaxRAM-AUX16-R3D-129BANK-ROUNDINGFIX.po"
        ),
    )
    args = parser.parse_args()
    build(args.input, args.output)


if __name__ == "__main__":
    main()
