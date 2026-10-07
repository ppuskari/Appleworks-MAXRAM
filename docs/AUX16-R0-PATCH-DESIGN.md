# AUX16 R0 Patch Design

Status: design only; not yet released as a runnable patch.

This design is based on the stock AppleWorks 5.1 files from the supplied 800K Program disk.

## Design principle

Do not enlarge Hugh Hood's physical-bank table to 255 entries.

Instead:

1. keep the existing destructive marker probe to discover how many unique RamWorks banks exist;
2. assume standard RamWorks-compatible bank numbering is contiguous from bank 1 upward;
3. stop storing a per-bank physical-number list;
4. link detected banks directly using their bank number;
5. patch `SEG.AM` so logical selector `Y` maps directly to physical bank `Y+1`.

This removes the table-size barrier while retaining AppleWorks' existing HBankMask/HBkAdrMask geometry.

## Why direct numbering preserves the existing linked-bank model

The original table layout makes logical table index 0 select physical bank 1.

During startup the link writer stores X=1 in bank 1's link, X=2 in bank 2's link, etc.

Thus a link value of 1 means "next bank-table entry", which resolves to physical bank 2.

With direct mapping:

```text
logical selector 0 -> physical bank 1
logical selector 1 -> physical bank 2
...
logical selector FE -> physical bank FF
```

The relationship is identical for standard contiguous cards.

The last bank's link is explicitly overwritten with zero, so a persistent link value of `$FF` is not required at the 255-bank limit.

## Proposed SEG.AM in-place patch

Stock runtime:

```text
D1C7  B5 00       LDA $00,X
D1C9  2D CA D0    AND $D0CA
D1CC  A8          TAY
D1CD  B9 CD D0    LDA $D0CD,Y
D1D0  8D 73 C0    STA $C073
D1D3  60          RTS
```

Replace only the three bytes at `SEG.AM` file offset `$01CD`:

```text
old: B9 CD D0    LDA $D0CD,Y
new: 98 1A EA    TYA / INC A / NOP
```

The following `STA $C073` remains unchanged.

No code movement is required.

Control-flow inspection shows the direct callers either do not rely on Y afterward or immediately replace Y, and the patch itself leaves Y unchanged anyway.

## Proposed APLWORKS.SYSTEM changes

Runtime addresses below assume the stock file load base of `$1000`.

### Copy only the masks into SEG.AM

At runtime `$320D`, retain source `$37DC` but change the move length from `$0033` to `$0002`.

Conceptually:

```text
destination = $D0CA
source      = $37DC
length      = 2
```

Only HBankMask and HBkAdrMask are required by the direct-mapped manager.

### Clear HBankMask before probing

Replace the stock `STA $C009` at `$3741` with a jump into unused/reclaimed table space at `$37F0`.

Candidate code:

```text
37F0  STZ $37DC
37F3  STA $C009
37F6  JMP $3744
```

The remainder of the reclaimed area can stay NOP-filled.

This ensures mask generation always starts from zero without needing Hugh's large relocated-table clear loop.

### Probe banks $FF down through $01

Change:

```text
LDY #$7F
...
DEY
BPL mark
```

to:

```text
LDY #$FF
...
DEY
BNE mark
```

This marks every extended bank while deliberately leaving normal Aux bank 0 untouched.

### Verify banks $01 through $FF

Keep the marker/complement validation.

Remove the bank-number table store after a valid marker is found.

Change the accepted-bank ceiling from `#$30` / Hugh's `#$60` to `#$FF`.

Change the scan termination from signed `BPL` to wrap-based `BNE` so bank numbers with bit 7 set are tested.

### Store only usable-bank count

The count can remain at the original `$37DE` working location.

No relocated `$97xx` bank table is needed.

### Link physical banks directly

Replace:

```text
LDA $37DE,X
STA $C073
```

with an equal-length sequence such as:

```text
TXA
NOP
NOP
STA $C073
```

X already runs from 1 through the usable-bank count.

### Keep the existing mask calculation

The stock/Hugh mask code is retained:

```text
DEX
TXA

loop:
    SEC
    ROL HBankMask
    LSR A
    BNE loop

LDA HBankMask
EOR #$FF
STA HBkAdrMask
```

At 255 usable extended banks it produces:

```text
HBankMask  = $FF
HBkAdrMask = $00
```

That is the expected 256-byte allocation quantum for a nearly-16-MB Aux desktop.

## Candidate patch locations

The exact byte patch is not yet frozen, but the principal stock file offsets are:

| File | Offset | Purpose |
| --- | ---: | --- |
| APLWORKS.SYSTEM | `$2214` | copied mask/table length |
| APLWORKS.SYSTEM | `$2741-$2743` | jump to mask-clear helper |
| APLWORKS.SYSTEM | `$2745` | initial probe bank: $7F -> $FF |
| APLWORKS.SYSTEM | `$2751` | probe loop BPL -> BNE |
| APLWORKS.SYSTEM | `$2766-$2769` | remove physical-bank table store |
| APLWORKS.SYSTEM | `$276B` | accepted-bank ceiling -> $FF |
| APLWORKS.SYSTEM | `$276F` | verification loop BPL -> BNE |
| APLWORKS.SYSTEM | `$278E-$2790` | direct bank select with TXA |
| APLWORKS.SYSTEM | `$27F0...` | small mask-clear helper |
| SEG.AM | `$01CD-$01CF` | table lookup -> Y+1 direct mapping |

All offsets must be guarded by SHA-256 and expected-byte verification in the eventual patcher.

## Compatibility policy

The direct mapping assumes a normal RamWorks-compatible card whose surviving unique bank numbers are contiguous from 1 through the detected capacity.

That is expected for conventional RamWorks-style decode/alias behavior, but it should be tested.

A production patcher should either:

- document contiguous bank numbering as a requirement; or
- add a startup self-test that falls back/refuses the AUX16 path if valid banks are non-contiguous.

## Test progression

The first binary experiment should not begin at 16 MB.

Suggested R0 ladder:

1. Patch direct mapping but cap at 48 banks; prove exact stock 3 MB behavior.
2. Cap at 96 banks; reproduce Hugh's 6 MB result without his table.
3. Cap at 128 banks; prove 8 MB.
4. Raise beyond $7F and test 9 MB.
5. Test 12 MB / 192 banks.
6. Test 255 extended banks on a 16 MB card/emulation.
7. Stress allocations near every bank boundary.
8. Verify loading, saving, clipboard/copy operations, database, spreadsheet, and word-processing desktops.

The 48- and 96-bank tests are critical: if direct mapping reproduces existing behavior there, the table-elimination assumption is strongly validated before crossing into new capacity.
