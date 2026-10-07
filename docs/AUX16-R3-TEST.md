# AUX16 R3 9 MB Boundary Test

## Purpose

R3 is the first MaxRAM build that deliberately exercises physical
RamWorks bank numbers with bit 7 set.

Use a 16 MB RamWorks-compatible Aux configuration in the emulator.

R3 probes all extended banks from $01 through $FF but caps the accepted
pool at $90 banks (144 * 64K = 9 MB expansion).

This isolates the historical $7F/$80 boundary before attempting the full
16 MB endpoint.

## Expected architectural changes

Compared with R2:

- marker probe starts at $FF instead of $7F;
- marker loop terminates at bank $00 using BNE rather than signed BPL;
- verification scan likewise continues through $80-$FF;
- accepted-bank cap is $90;
- tableless/direct SEG.AM bank selection remains unchanged.

With more than 128 accepted banks, HBankMask/HBkAdrMask should move to:

```text
HBankMask  = $FF
HBkAdrMask = $00
```

which changes AppleWorks Desktop allocation granularity to 256 bytes.

Thus R3 validates both:

1. physical banks >= $80;
2. the next AppleWorks VM geometry.

## Test procedure

1. Configure GSSquared for a 16 MB RamWorks-compatible Aux card.
2. Boot the R3 Program image.
3. Record available Desktop immediately after startup.
4. Load the same large word-processing test file repeatedly.
5. Drive Desktop memory close to exhaustion.
6. Edit documents loaded early, in the middle, and late.
7. Confirm edits remain unique to each file.
8. Close a middle-resident document.
9. Load another large file so AppleWorks reuses freed Desktop space.
10. Return to files on both sides of the reused area and verify contents.

## Critical observations

Please record:

- startup available Desktop;
- whether startup is normal or noticeably slower;
- whether any failure occurs immediately after crossing the amount of
  data that R2 could hold;
- whether unique edits remain intact;
- whether free/reallocate works;
- any monitor address or error message if a failure occurs.

## Pass condition

R3 passes if AppleWorks can allocate and retrieve data throughout the
larger Desktop without aliasing or corruption, including storage backed
by physical bank numbers $80 and above.

A pass will justify moving directly to the full 255-extended-bank
AUX16 build.
