# AUX16 R1 - 6 MB Tableless Validation

## Purpose

R1 is the first capacity increase using the new direct-mapped SEG.AM design.

It targets the same 96 extended banks / 6 MB physical Aux range as Hugh Hood's Big AuxCard patch, but does not relocate or enlarge the physical-bank-number table.

## Changes from stock

APLWORKS.SYSTEM:

- remove the store of each detected physical bank number into the old table;
- change the accepted-bank limit from $30 to $60;
- change link initialization from table lookup to direct physical bank X.

SEG.AM:

- replace LDA $D0CD,Y with TYA / INC A / NOP.

The rest of the stock AppleWorks 5.1 setup flow remains intact.

## Image hash

```text
9284f8813e049b1e7ec94d7cc4c337e71d6a16fa347e84412f6c979599775464
```

The complete 800K image differs from stock in exactly 11 bytes.

## Test

Configure GSSquared with at least 6 MB of RamWorks-compatible Aux memory.

Expected behavior:

1. AppleWorks boots normally.
2. Desktop memory increases beyond the stock 3 MB configuration.
3. Large documents can be repeatedly loaded/copied without corruption.
4. Allocation across the old stock 3 MB boundary remains stable.
5. Quit/restart is repeatable.

Useful stress test:

- load the 28K AppleWorks 3.0 Tips document several times;
- duplicate its contents repeatedly with copy/paste;
- continue until allocations clearly exceed the stock R0 case;
- save, close, reopen, and repeat.

## PASS criterion

R1 passes when it reproduces Hugh's 6 MB-class behavior without the enlarged bank-number table.

A pass validates table elimination at the largest already-proven historical capacity.

## Next step

R2 should move to 128 extended banks / 8 MB, still below the signed-bank-number crossing in the current probe loop.

R3 then changes the probe/verification loop termination so banks $80-$FF can be tested, beginning the genuinely new >8 MB territory.
