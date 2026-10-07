# AUX16 R1 6 MB Validation Results

Status: PASS on GSSquared emulator.

## Configuration

R1 retains the tableless/direct-bank SEG.AM mapping proven by R0 and raises the accepted extended-bank ceiling to 96 banks (6 MB physical Aux expansion).

## Observed result

AppleWorks 5.1 reported approximately 4290K available Desktop memory with the 6 MB option.

The test loaded a roughly 475K word-processing file repeatedly until only about 45K of Desktop remained.

Multiple resident copies were independently modified at different points in the allocation pool. Returning to each document showed its unique edits preserved correctly.

This exercises far more than startup detection:

- allocation across the expanded Desktop;
- access beyond the stock 3 MB range;
- bank selection and retrieval;
- independent mutable documents resident simultaneously;
- repeated switching between allocations;
- Desktop exhaustion to approximately 45K free.

## Conclusion

R1 passes.

The tableless direct mapping reproduces Hugh Hood's 6 MB-class Desktop capacity without Hugh's relocated physical-bank-number table.

This validates the architectural change required to scale beyond the 6 MB implementation.

## Next step

R2 allows the complete stock probe range, banks $01-$7F, corresponding to 127 extended 64K banks on an 8 MB RamWorks-compatible card.

R2 remains below the $80 physical-bank boundary. Crossing that boundary is reserved for the following build so the signed-loop changes can be tested separately.
