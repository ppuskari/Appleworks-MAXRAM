# AppleWorks 5.1 Stock Media Baseline

## Source media

The current AppleWorks 5.1 800K ProDOS-order installation media supplied for analysis are:

| Image | ProDOS volume | Size | SHA-256 |
| --- | --- | ---: | --- |
| `AppleWorks 5.1 Program.po` | `/APPLEWORKS` | 819,200 bytes | `76c569b26800b721f691e9a4019413606cf760574a8f2b28a25bbfff9d53a808` |
| `AppleWorks 5.1 Install.po` | `/EXTRAS` | 819,200 bytes | `15d5b8080663b45332f081d9db427d7b610151811c7925b711781a8de33f4efb` |

The program disk contains the exact runtime files needed for MaxRAM research.

## Relevant stock files

| ProDOS path | Type | EOF | SHA-256 |
| --- | --- | ---: | --- |
| `/APLWORKS.SYSTEM` | SYS ($FF) | 21,924 | `154baf394ea062868b2c4468caaddcdf95dd8433b7bf7f46cbc5c0e7e5f86847` |
| `/SEG.AM` | BIN ($06) | 4,074 | `371d3a93e9ee4b5c42383fd4d2f3050a5c82e6b97bf87f40e3bf720dcf07d25f` |
| `/SEG.XM` | BIN ($06) | 4,042 | `ad64307a29c7f84779b280405d9e502eeffe84b53bb73c8d1d970cecc38ebf18` |

Other relevant program-disk files include `MEM.SYSTEM`, `SEG.RM`, and the remaining AppleWorks segments.

The Extras disk contains source for several optional components such as `SEG.AX.SOURCE`, `SEG.NA.SOURCE`, and `SEG.UM.SOURCE`, but it does not contain source for `SEG.AM` or `SEG.XM`.

Original AppleWorks binaries are not committed to this repository.

## Stock vs Hugh Hood Big AuxCard

The stock `APLWORKS.SYSTEM` and Hugh Hood's Standard Big AuxCard `APLWORKS.SYSTEM` are exactly the same length: 21,924 bytes.

There are only 29 differing bytes in 13 contiguous runs.

| File offset | Bytes | Stock | Hugh Standard |
| --- | ---: | --- | --- |
| `$00F1` | 1 | `00` | `01` |
| `$043C` | 1 | `95` | `32` |
| `$2213-$2214` | 2 | `37 33` | `97 63` |
| `$2741-$2743` | 3 | `8D 09 C0` | `4C F0 37` |
| `$2769` | 1 | `37` | `97` |
| `$276B` | 1 | `30` | `60` |
| `$278A` | 1 | `37` | `97` |
| `$2790` | 1 | `37` | `97` |
| `$279C` | 1 | `37` | `97` |
| `$27B4` | 1 | `37` | `97` |
| `$27BA` | 1 | `37` | `97` |
| `$27BF` | 1 | `37` | `97` |
| `$27F0-$27FD` | 14 | all zero | Hugh table-clear/setup code |

The 27 bytes from `$2213` onward correspond directly to the Big AuxCard changes documented in Hugh's PDF.

The differences at `$00F1` and `$043C` are outside Hugh's documented Big AuxCard routines and should currently be treated as unrelated differences in the system file used to produce his distribution.

At runtime address `$143B`, the `$043C` file-byte difference changes an immediate value from `#$95` to `#$32` in a delay loop. It is not required by the published Big Aux modification.

## SEG.AM table layout

`SEG.AM` is loaded at `$D000`.

The copied RamWorks table begins at runtime `$D0CA`:

```text
$D0CA  HBankMask
$D0CB  HBkAdrMask
$D0CC  bank count
$D0CD  first physical bank number
...
```

The stock file contains zero-filled space from file offset `$00CA` through `$013E`, or 117 bytes.

Executable code begins at `$D13F`.

Therefore:

- stock 3 MB table fits;
- Hugh's approximately 99-byte 6 MB table fits;
- a 255-entry physical-bank table for a 16 MB card does not fit.

This is the first hard reason an AUX16 implementation cannot merely increase Hugh's table length.

## SEG.AM pointer-to-bank translation

The important stock routine is:

```text
D1C7  LDA $00,X
D1C9  AND $D0CA       ; HBankMask
D1CC  TAY
D1CD  LDA $D0CD,Y     ; physical bank table
D1D0  STA $C073
D1D3  RTS
```

A companion routine then applies `HBkAdrMask` to the same AppleWorks pointer byte before accessing the selected bank.

Control-flow analysis found the physical-bank list lookup at `$D1CD` to be the only `LDA $D0CD,Y` bank-table lookup in `SEG.AM`.

This creates a promising AUX16 option: for standard contiguous RamWorks-compatible bank numbering, replace the three-byte lookup:

```text
B9 CD D0    LDA $D0CD,Y
```

with an equal-length direct mapping:

```text
98          TYA
1A          INC A
EA          NOP
```

The existing `STA $C073` then selects physical bank `Y+1`.

This is still a design hypothesis and must be validated against real and emulated cards, but it removes the need for a 255-byte bank-number table.

## Why the existing mask math scales to a 16 MB card

Hugh's mask setup computes a low-bit bank-selector mask from the usable bank count, with the complement becoming the address mask.

Examples:

| Extended banks | Physical expansion | HBankMask | HBkAdrMask | implied allocation quantum |
| ---: | ---: | ---: | ---: | ---: |
| 48 | 3 MB | `$3F` | `$C0` | 64 bytes |
| 96 | 6 MB | `$7F` | `$80` | 128 bytes |
| 128 | 8 MB | `$7F` | `$80` | 128 bytes |
| 192 | 12 MB | `$FF` | `$00` | 256 bytes |
| 255 | 15.9375 MB | `$FF` | `$00` | 256 bytes |

At 255 extended banks, the scheme provides:

```text
255 banks * 64K = 15.9375 MB usable expansion
255 banks * 256 positions per bank = 65,280 logical pointer positions
65,280 * 256 bytes = 15.9375 MB
```

That fits the existing 16-bit AppleWorks virtual-pointer namespace.

This is strong evidence that the original `SEG.AM` address-partition design can represent essentially the full usable memory of a 16 MB RamWorks-compatible card.

The current obstacle is the explicit physical-bank list, not the logical pointer width.

## SEG.XM: 16-bit AppleWorks pointer to 24-bit Slinky address

Stock `SEG.XM` contains the conversion:

```text
D14C  LDA $00,X
D14E  STA $8D
D150  LDA $01,X
D152  STA $8E
D154  LDA #$00
D156  LDY $0FD6

D159  ASL $8D
D15B  ROL $8E
D15D  ROL A
D15E  DEY
D15F  BNE $D159
```

It then stores the resulting three bytes into the slot-relative Slinky address registers at `$BFF8-$BFFA,X`.

Thus AppleWorks already uses a scalable 16-bit logical pointer and expands it into a 24-bit physical Slinky address.

The Slinky hardware address width is not the primary 2 MB limitation.

## SYS.DESKTOP allocation and the 2 MB Slinky ceiling

`APLWORKS.SYSTEM` creates `SYS.DESKTOP` directly in the RamFactor/Slinky ProDOS filesystem.

The embedded 39-byte directory-entry template at runtime `$368D` is a ProDOS tree-file entry named:

```text
SYS.DESKTOP
```

The allocator:

1. reads ProDOS volume-directory block 2;
2. obtains the volume bitmap block number from the volume header;
3. reads exactly one 512-byte bitmap block;
4. copies it to a working buffer at `$BD00`;
5. scans and clears bits in that one buffer while allocating blocks;
6. copies the modified bitmap back and writes exactly that bitmap block.

One 512-byte ProDOS bitmap block represents 4096 disk blocks:

```text
4096 * 512 bytes = 2 MB
```

This directly explains the historical approximately-2-MB `SYS.DESKTOP` ceiling.

The allocation scanner itself uses a tree-file structure and arrays for index-block allocation, so the file structure is not inherently limited to a 2 MB sapling file. The immediate filesystem limitation is failure to advance through additional ProDOS bitmap blocks.

## Slinky startup scaling issue above 8 MB

`APLWORKS.SYSTEM` computes `$0FD6`, the shift count consumed by `SEG.XM`, from the ProDOS volume size.

The current implementation doubles a 16-bit block count and then repeatedly shifts it down while incrementing `$0FD6`.

This introduces additional edge cases for very large Slinky volumes:

- 8 MB requires eight shifts, causing the one-byte power-of-two companion value at `$0FD5` to wrap;
- a 16 MB ProDOS volume is 32,768 blocks (`$8000`), and the initial 16-bit doubling operation overflows to zero.

Therefore SLINKY16 will require both:

1. multi-bitmap `SYS.DESKTOP` allocation; and
2. widened or special-cased startup scaling arithmetic.

The manager's 24-bit address conversion itself is already suitable for a much larger physical address.

## Current feasibility assessment

### 16 MB Aux card

Very promising.

The existing mask/address design naturally reaches the 255 usable extended banks of a 16 MB card. A small direct-bank-mapping modification to `SEG.AM` can potentially eliminate the table-space barrier.

### 16 MB Slinky/RamFactor

Architecturally feasible, but more invasive.

`SEG.XM` already performs 24-bit addressing. The startup code must be extended to handle multiple ProDOS bitmap blocks and large-volume scaling.

### Combined Aux + Slinky

Still plausible.

Both managers expose AppleWorks to a 16-bit logical pointer while privately translating that pointer to different physical memory. That remains the strongest basis for a future unified MaxRAM memory manager.
