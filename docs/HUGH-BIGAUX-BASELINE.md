# Hugh Hood Big AuxCard Baseline

## Purpose

This document records the first reproducible baseline for Appleworks-MaxRAM.

The source material is Hugh Hood's AppleWorks 5.1 Big AuxCard distribution:

- `appleworksauxmemmod.pdf` - annotated BrkDown disassembly of the AppleWorks 5.1 `APLWORKS.SYSTEM` changes.
- `bigauxapwks.shk` - NuFX/ShrinkIt distribution archive containing the modified AppleWorks system files.

Original AppleWorks binaries are intentionally not committed to this repository.

## Source hashes

| Artifact | SHA-256 |
| --- | --- |
| appleworksauxmemmod.pdf | `48fa2b04de14e63c337eece8bc8fdb6b20b5737d76518ffe638fac9767fedcd0` |
| bigauxapwks.shk | `f1bddce80deee8586fde14a823179e3e0ff749face2c95b9e4af4049883556d4` |

## SHK inventory

The archive contains two AppleWorks 5.1 `APLWORKS.SYSTEM` payloads:

| Variant | Size | SHA-256 |
| --- | ---: | --- |
| `BREDONY2KVRSION:APLWORKS.SYSTEM` | 21,924 bytes | `5932188599e5230f9ec2a4f5c28006f0cd06ef2328c672a1e65788dcdc38c60b` |
| `STANDARDVERSION:APLWORKS.SYSTEM` | 21,924 bytes | `f69a2b2d873d5e236da808881716758b6e33af918e4f69367ed5690a98c33a79` |

The two payloads differ at only two file offsets:

| File offset | Bredon/Y2K | Standard |
| --- | ---: | ---: |
| `$2CD3` | `$64` | `$3C` |
| `$2CD4` | `$90` | `$B0` |

All bytes implementing the Big AuxCard memory modification are identical between the two variants.

The two-byte difference appears outside the Big AuxCard routines documented by Hugh and should be treated as an independent variant difference until its purpose is proven.

## Hugh's 3 MB -> 6 MB modification

The PDF identifies the project as modifications to AppleWorks 5.1 `APLWORKS.SYSTEM` to increase AuxSlot/RamWorks Desktop memory support from 3 MB to 6 MB.

### 1. Bank table relocation

At file offset `$220D` / runtime `$320D`, Hugh changes the table move to:

- source: `$97DC` instead of `$37DC`
- destination: `$D0CA` in `SEG.AM`
- size: `$0063` instead of `$0033`

This is a major architectural clue. The original table area was too small for the larger bank list, so Hugh created a larger table elsewhere and copied it into the memory-manager segment.

### 2. Probe ceiling

At runtime `$3744`, the modified code starts with:

```text
LDY #$7F
```

It writes a bank-number marker and its complement into each candidate bank and uses:

```text
DEY
BPL
```

to iterate downward.

This explicitly limits probing to bank numbers `$00-$7F`, independent of the 8-bit `$C073` bank register's full `$00-$FF` namespace.

### 3. Usable-bank count ceiling

During verification, valid banks are appended to the relocated table at `$97DE,X`.

Hugh changes:

```text
CPX #$30
```

to:

```text
CPX #$60
```

The source comment identifies `$60` as the 6 MB maximum.

Thus the 6 MB limit is explicitly enforced by software.

### 4. Lock-out banks

After probing, the number of detected banks is compared with and reduced by `LockOutBanks` at `$11B6`.

The resulting usable-bank count is stored at `$97DE`.

The meaning and normal value of `LockOutBanks` must be mapped before changing capacity calculations.

### 5. Per-bank links

AppleWorks stores four link bytes at `$0800` in every selected auxiliary bank.

The low byte of the link contains the bank's position in the bank table.

This linked-bank representation is part of the interface that must remain valid at higher capacities.

### 6. HBankMask / HBkAdrMask

After the usable bank list is built, the setup code derives:

- `HBankMask` at `$97DC`
- `HBkAdrMask` at `$97DD`

The routine repeatedly rotates the mask while shifting `bank_count - 1`.

We need to trace how `SEG.AM` consumes these two values before assuming a 256-bank geometry is safe.

### 7. Reclaimed code/table space

The original table at `$37DC` is no longer used as the active bank table.

Hugh uses part of that reclaimed area for new setup code at `$37F0`:

```text
LDX #$63
STZ $97DC,X
DEX
BPL ...
STA $C009
JMP $3744
```

This initializes the relocated table and rejoins the original setup flow.

## Binary verification

Both extracted SHK payloads were checked directly at the documented offsets.

They contain the instructions and constants shown in Hugh's PDF, including:

- `$220D`: relocated table move
- `$2741`: jump to new code at `$37F0`
- `$2744`: `LDY #$7F`
- `$276A`: `CPX #$60`
- `$2788`: store count at `$97DE`
- `$27AF`: HBankMask setup
- `$27F0`: new table-clear/setup routine

The PDF and shipped binaries therefore form a matched baseline.

## Initial AUX16 implications

A 16 MB RamWorks-style implementation requires support for the complete 8-bit bank namespace.

The most obvious 6 MB restrictions are not fundamental hardware restrictions:

1. The probe loop stops at `$7F`.
2. The valid-bank list stops at `$60`.
3. The allocated bank table is sized only for Hugh's 6 MB implementation.

A candidate 16 MB implementation will need to probe banks `$01-$FF` and represent up to 255 extended banks in addition to normal bank 0.

The existing one-byte bank number and one-byte bank count are potentially sufficient for 255 extended banks, but the table itself would require approximately 258 bytes:

- HBankMask
- HBkAdrMask
- bank count
- up to 255 bank-number entries

That is larger than Hugh's current relocated table and larger than a single 8-bit-indexed clear loop.

## Critical unknowns before patching

### SEG.AM destination space

Hugh copies the table to `$D0CA` in `SEG.AM`.

Before enlarging the table, we must obtain and inspect the actual AppleWorks 5.1 `SEG.AM` used with this `APLWORKS.SYSTEM` and determine:

- what resides after the current copied table;
- whether a ~258-byte table fits at `$D0CA`;
- whether `SEG.AM` code assumes the existing table length;
- how HBankMask and HBkAdrMask are used;
- how logical Desktop pointers are converted into table index + bank offset.

### Desktop allocator geometry

Physical bank detection is only one half of the problem.

We must also map:

- AppleWorks Desktop pointer representation;
- allocation quantum;
- maximum logical Desktop size;
- size calculations and display calculations;
- any 8-bit or 16-bit arithmetic that saturates before 16 MB.

### Stock comparison

The SHK contains the two modified AppleWorks system variants, not an unmodified stock AppleWorks 5.1 system.

A byte-accurate stock-vs-Hugh diff still requires the exact AppleWorks 5.1 baseline `APLWORKS.SYSTEM`.

## Next required inputs

For the next reverse-engineering pass, obtain from the same AppleWorks 5.1 installation:

- stock `APLWORKS.SYSTEM`
- `SEG.AM`
- `SEG.XM`

With those files we can turn this baseline into an annotated call/interface map and determine whether AUX16 can remain an `APLWORKS.SYSTEM`-only modification or requires a modified `SEG.AM`.
