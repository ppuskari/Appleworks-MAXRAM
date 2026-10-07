"""Validate the SEG.AM HBankMask/HBkAdrMask geometry.

These tests model the mask-generation routine used by AppleWorks 5.1
and Hugh Hood's Big AuxCard patch.  They do not contain AppleWorks code.
"""


def masks(bank_count):
    if not 1 <= bank_count <= 255:
        raise ValueError("bank_count must be 1..255")

    value = bank_count - 1
    bank_mask = 0

    while True:
        bank_mask = ((bank_mask << 1) | 1) & 0xFF
        value >>= 1

        if value == 0:
            break

    return bank_mask, bank_mask ^ 0xFF


def allocation_quantum(address_mask):
    if address_mask == 0:
        return 256

    return address_mask & -address_mask


def logical_units(bank_count):
    bank_mask, address_mask = masks(bank_count)
    quantum = allocation_quantum(address_mask)

    units_per_bank = 65536 // quantum
    return bank_count * units_per_bank


def test_geometry_fits_16_bit_pointer():
    for count in range(1, 256):
        assert logical_units(count) <= 65536


def test_known_3mb_geometry():
    bank_mask, address_mask = masks(48)

    assert bank_mask == 0x3F
    assert address_mask == 0xC0
    assert allocation_quantum(address_mask) == 64
    assert logical_units(48) * 64 == 3 * 1024 * 1024


def test_hugh_6mb_geometry():
    bank_mask, address_mask = masks(96)

    assert bank_mask == 0x7F
    assert address_mask == 0x80
    assert allocation_quantum(address_mask) == 128
    assert logical_units(96) * 128 == 6 * 1024 * 1024


def test_8mb_geometry():
    bank_mask, address_mask = masks(128)

    assert bank_mask == 0x7F
    assert address_mask == 0x80
    assert allocation_quantum(address_mask) == 128
    assert logical_units(128) == 65536


def test_full_16mb_card_usable_expansion():
    bank_mask, address_mask = masks(255)

    assert bank_mask == 0xFF
    assert address_mask == 0x00
    assert allocation_quantum(address_mask) == 256
    assert logical_units(255) == 65280

    usable_bytes = logical_units(255) * 256
    assert usable_bytes == 255 * 65536
    assert usable_bytes == 16 * 1024 * 1024 - 65536
