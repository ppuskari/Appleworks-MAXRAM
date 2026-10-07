# AUX16 Initial Design Notes

Status: research hypothesis based on Hugh Hood's Big AuxCard AppleWorks 5.1 patch.

## Goal

Extend AppleWorks 5.1 RamWorks-compatible auxiliary-memory support beyond Hugh Hood's 6 MB implementation toward the complete 8-bit $C073 bank namespace.

The first engineering target is 16 MB physical Aux RAM recognition. Actual usable AppleWorks Desktop size must be measured separately.

## Proven baseline

Hugh's Big AuxCard patch:

- probes only bank numbers $00-$7F;
- caps accepted extended banks at $60 (96 banks / 6 MB);
- relocates and enlarges the HBank table;
- copies that table into SEG.AM at $D0CA;
- keeps one-byte physical bank numbers.

These are explicit software limits and are therefore candidates for extension.

## Candidate 16 MB probe

A 16 MB RamWorks-compatible card exposes 256 64K bank numbers, $00-$FF.

Normal Aux bank $00 is treated specially by Hugh's code, leaving up to 255 extended banks.

The current mark loop:

```text
LDY #$7F
...
DEY
BPL loop
```

cannot reach banks $80-$FF because BPL uses bit 7 of Y as a termination condition.

A full-range implementation can instead iterate $FF down through $01 and terminate when Y becomes zero.

Conceptually:

```text
LDY #$FF
mark:
    STY $C073
    STY $00
    TYA
    EOR #$FF
    STA $01
    DEY
    BNE mark
```

This intentionally does not overwrite normal Aux bank $00.

The verification loop can similarly start at $01, increment through $FF, and terminate when INY wraps to $00.

This is a design sketch, not yet a patch.

## Candidate table geometry

Hugh's relocated table begins with:

```text
+0 HBankMask
+1 HBkAdrMask
+2 HBankTab count
+3 physical bank numbers...
```

For 255 extended bank entries, a straightforward table requires:

```text
3 + 255 = 258 bytes
```

This cannot be initialized with Hugh's single descending 8-bit X loop.

More importantly, it may not fit at the current SEG.AM destination $D0CA.

Do not choose a new table location until SEG.AM has been inspected.

## Bank-count representation

Hugh's code uses X as an 8-bit count and stores the accepted bank count in one byte.

A maximum of 255 extended banks is representable as $FF, so the count itself may not require widening.

However, code that distinguishes zero from 256 total physical banks must be reviewed carefully because:

- bank 0 is special;
- $FF represents 255 extended banks;
- total physical capacity becomes 256 banks / 16 MB.

## HBankMask and HBkAdrMask

Hugh calculates HBankMask from usable-bank-count minus one using repeated shifts/rotates, then stores its complement as HBkAdrMask.

The values appear to describe logical Desktop address geometry.

For >128 accepted banks, this algorithm can produce an $FF mask and $00 complement.

Whether that is valid depends entirely on SEG.AM consumers.

This is the highest-priority code path to trace after obtaining SEG.AM.

## LockOutBanks

The setup subtracts the byte at $11B6 (LockOutBanks) from detected banks before building the usable-memory links.

Questions:

1. What initializes LockOutBanks?
2. Is its unit a 64K Aux bank?
3. Is it constant across AppleWorks 5.1 configurations?
4. Does any later arithmetic assume the post-lockout count is <= $60?

## Required SEG.AM analysis

We need to identify every access to the copied table at/near $D0CA and answer:

- table start/end;
- code/data immediately following it;
- HBankMask use;
- HBkAdrMask use;
- HBankTab/count use;
- physical bank lookup;
- VM pointer to bank/offset conversion;
- Get/Put/Move entry points used by AppleWorks;
- assumptions about maximum table index.

Only after this is known should AUX16 patch bytes be designed.

## Incremental test ladder

Do not jump directly from 6 MB to 16 MB.

Suggested progression:

1. Reproduce Hugh 6 MB baseline exactly.
2. Raise ceiling to 7 MB.
3. Raise ceiling to 8 MB.
4. Cross sign-bit boundary: 9 MB / bank numbers >= $80.
5. Test 12 MB.
6. Test 15 MB.
7. Test full 16 MB hardware population.
8. Record actual AppleWorks Desktop size at every step.

The $7F->$80 crossing deserves its own milestone because Hugh's existing loops deliberately depend on signed BPL termination.

## Emulator target

Use AppleWin's large RamWorks configuration for rapid regression testing where possible, followed by verification on physical hardware.

## Success criteria for AUX16 Phase 1

Phase 1 succeeds when:

- all physical banks through $FF are correctly detected without alias false-positives;
- AppleWorks starts and remains stable;
- Desktop allocation does not corrupt normal Aux memory or AppleWorks resident data;
- load/save/copy operations survive allocations across the old 6 MB boundary;
- allocations survive bank numbers with bit 7 set;
- maximum reported and actually usable Desktop size is measured and documented.

The measured logical Desktop ceiling may be lower than the physical 16 MB card size. That result would identify the next AppleWorks allocator limit rather than make AUX16 detection a failure.
