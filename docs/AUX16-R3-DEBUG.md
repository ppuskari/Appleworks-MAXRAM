# AUX16 R3 Boundary Debug

## Observed result

R3 at a 144-extended-bank cap crashed during the AppleWorks program-load screen.

Visible screen corruption included:

```text
34AF = 2Y0 =5SB
```

R0 (3 MB), R1 (6 MB), and R2 (127 extended banks / 7.9375 MB) passed sustained Desktop allocation tests.

## Why R3 combined two new variables

R3 was the first build to:

1. probe and accept physical RamWorks bank numbers with bit 7 set; and
2. exceed 128 extended banks, causing HBankMask/HBkAdrMask to change from $7F/$80 to $FF/$00.

The crash therefore did not identify which transition failed.

## R3A discriminator

R3A accepts exactly 128 extended banks: physical banks $01-$80.

This deliberately crosses into physical bank $80 while preserving the proven mask geometry:

```text
HBankMask  = $7F
HBkAdrMask = $80
```

It also uses the new full-range $FF..$01 marker probe and wrap-based verification loop.

Interpretation:

- R3A PASS => bank $80 and the new probe loops are valid; investigate the 129-bank $FF/$00 mask transition.
- R3A FAIL => investigate high-bank probing/selection before changing VM geometry.

## R3B if R3A passes

The next diagnostic should accept exactly 129 extended banks.

That is the smallest configuration that forces:

```text
HBankMask  = $FF
HBkAdrMask = $00
```

and will isolate the VM geometry transition with only one additional bank beyond R3A.
