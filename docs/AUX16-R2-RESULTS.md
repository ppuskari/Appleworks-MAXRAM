# AUX16 R2 8 MB Test Results

Status: **PASS**

## Configuration

R2 retained the tableless/direct `SEG.AM` mapping proven in R0/R1 and opened the complete original AppleWorks bank-probe range `$01-$7F`.

Observed startup Desktop:

```text
approximately 5827K available
```

## Stress test

The test used large AppleWorks word-processing documents to force real Desktop allocations.

Observed behavior:

- seven large documents loaded simultaneously;
- approximately 656K remained after the seventh document;
- loading the eighth document drove Desktop memory to zero at roughly three-quarters of the file;
- files resident at different points in the Desktop retained independent data;
- edits remained unique to the intended document;
- switching repeatedly among resident files did not reveal corruption or cross-file aliasing;
- no bank-selection or allocation failures were observed.

## Result

R2 successfully exercised essentially the complete available Desktop associated with the 8 MB-class RamWorks configuration.

Together with R1, this validates the tableless/direct physical-bank mapping across the original AppleWorks bank-number range.

## Next boundary

R3 intentionally changes two things that R0-R2 never changed:

1. the destructive bank-marker probe will scan physical banks `$80-$FF`;
2. the verification scan will accept bank numbers with bit 7 set.

R3 will run on a 16 MB emulated RamWorks card but cap the accepted expansion at `$90` banks (144 extended banks / 9 MB). This is deliberately just beyond the historical `$7F` boundary so failures can be attributed to the sign-bit crossing and 256-byte VM allocation geometry rather than to the full 16 MB endpoint.
