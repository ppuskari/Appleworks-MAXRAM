# SLINKY16 Initial Design Notes

Status: research based on stock AppleWorks 5.1 `APLWORKS.SYSTEM` and `SEG.XM`.

## Goal

Extend AppleWorks 5.1 RamFactor/Slinky Desktop-memory support beyond the historical approximately-2-MB limit toward a 16 MB Slinky-compatible card.

## Proven manager architecture

`SEG.XM` does not use a 16-bit physical address.

It takes AppleWorks' two-byte logical pointer and shifts it left by the startup-selected scale value in `$0FD6`, producing a three-byte physical Slinky address.

The result is written to the slot-relative address registers:

```text
$BFF8,X  low
$BFF9,X  middle
$BFFA,X  high
```

and data transfers use the Slinky auto-increment data port at `$BFFB,X`.

This means the manager is already architected for 24-bit physical addressing.

## Current 2 MB limit: one ProDOS bitmap block

AppleWorks reserves Slinky RAM by creating a ProDOS tree file named `SYS.DESKTOP`.

The relevant startup allocator:

1. reads volume directory block 2;
2. obtains the volume bitmap block number;
3. reads one bitmap block into `$0800`;
4. copies exactly 512 bytes to a work buffer at `$BD00`;
5. allocates blocks by scanning and clearing bits in that single buffer;
6. copies `$BD00` back to `$0800`;
7. writes the same bitmap block back to the volume.

The scanner's bitmap base is statically `$BD00`.

One ProDOS bitmap block describes 4096 disk blocks:

```text
4096 * 512 = 2,097,152 bytes
```

Therefore the familiar 2 MB ceiling comes directly from bitmap traversal, not from `SEG.XM`.

## The SYS.DESKTOP file structure is already a tree file

The embedded directory template at `$368D` has storage type 3 and name `SYS.DESKTOP`.

The allocator creates:

- data blocks;
- sapling index blocks;
- a tree/master index block;
- the directory entry.

Its internal index-block arrays are substantially larger than would be required for a 2 MB-only implementation.

This is encouraging: extending the allocator across multiple bitmap blocks should not require inventing a new file format.

## Required multi-bitmap change

A 16 MB ProDOS volume has 32,768 512-byte blocks.

That requires eight 512-byte volume bitmap blocks.

The block allocator must therefore track:

```text
bitmap_index = candidate_block / 4096
bit_index    = candidate_block % 4096
```

When `bitmap_index` changes, the allocator must:

1. flush the currently modified bitmap block;
2. load the next bitmap block;
3. continue allocation using a zero-based bit offset inside that bitmap;
4. flush the final bitmap before completion.

A simpler first experiment is 4 MB, requiring two bitmap blocks.

## Startup scale variables

Two startup variables are shared with `SEG.XM`:

```text
$0FD5  power-of-two scale companion
$0FD6  shift count
```

`SEG.XM` directly consumes `$0FD6` when converting 16-bit logical pointers to 24-bit Slinky addresses.

Stock startup derives these from the ProDOS volume size.

The current code uses a 16-bit doubled block count and an 8-bit power-of-two accumulator.

That creates large-volume edge cases:

### 8 MB

8 MB is 16,384 ProDOS blocks.

The normalization loop requires eight shifts.

The one-byte `$0FD5` value shifts from 1 through 128 and then wraps to 0.

All consumers of `$0FD5` must be checked before declaring 8 MB safe.

### 16 MB

16 MB is 32,768 blocks (`$8000`).

The current code first doubles the 16-bit block count.

```text
$8000 << 1 = $0000 with carry
```

The carry is discarded, so the normalization input becomes zero.

Thus 16 MB definitely requires a change to startup scale calculation.

## Candidate strategy

Do not widen AppleWorks' logical pointer.

Instead preserve the existing 16-bit logical-pointer ABI and calculate the required physical scale explicitly.

For each supported Slinky volume size, derive a shift count that keeps the logical Desktop address inside AppleWorks' existing pointer range.

A patched startup routine can use a small size/shift table or a carry-aware 24-bit normalization routine.

A table-driven approach may be preferable because the supported physical range is small and discrete:

```text
2 MB
4 MB
8 MB
16 MB
```

The exact `$0FD5` semantics must be completely mapped before selecting this design.

## Incremental test ladder

1. Reproduce stock ~2 MB Slinky Desktop.
2. Teach SYS.DESKTOP allocator to use two bitmap blocks.
3. Test 4 MB.
4. Map all consumers of $0FD5.
5. Test 8 MB and resolve the 8-bit scale-wrap boundary.
6. Add carry-aware or table-driven scale calculation.
7. Test 16 MB.
8. Stress Desktop allocations across every 2 MB bitmap boundary.

## Combined MaxRAM implications

The important commonality between `SEG.AM` and `SEG.XM` is that both accept AppleWorks' existing logical Desktop pointer and privately translate it to hardware-specific addressing.

That keeps a future hybrid manager realistic.

A MaxRAM manager could reserve a logical range for Aux memory and route higher logical ranges through the Slinky converter without requiring every AppleWorks caller to understand 24-bit addresses.
