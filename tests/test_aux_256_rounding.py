"""Verify the 256-byte allocation rounding used by AUX16 R3D."""


def expected(size):
    return ((size + 4 + 255) // 256) * 256


def r3d_round(size):
    high = (size >> 8) & 0xFF
    low = size & 0xFF

    pages = 2 if low >= 0xFD else 1
    return ((high + pages) & 0xFF) << 8


def test_all_16_bit_sizes():
    for size in range(0x10000):
        assert r3d_round(size) == (expected(size) & 0xFFFF)
