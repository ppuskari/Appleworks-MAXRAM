# AUX16 R0 Validation Build

## Purpose

R0 validates one architectural change only:

> Replace SEG.AM's physical-bank table lookup with direct contiguous
> RamWorks bank mapping.

R0 does **not** increase AppleWorks' memory limit.

`APLWORKS.SYSTEM` is byte-for-byte stock AppleWorks 5.1, so the normal
3 MB extended-Aux ceiling remains in force.

If R0 behaves exactly like stock AppleWorks under the same emulator
memory configuration, the physical-bank table can be removed safely
before capacity work begins.

## Patch

Stock `SEG.AM` at file offset `$01CD`:

```text
B9 CD D0    LDA $D0CD,Y
```

R0:

```text
98          TYA
1A          INC A
EA          NOP
```

The existing following instruction remains:

```text
8D 73 C0    STA $C073
```

Thus logical bank selector 0 maps to RamWorks bank 1, selector 1 to
bank 2, and so on.

## Known baseline hashes

Stock Program image:

```text
76c569b26800b721f691e9a4019413606cf760574a8f2b28a25bbfff9d53a808
```

Stock SEG.AM:

```text
371d3a93e9ee4b5c42383fd4d2f3050a5c82e6b97bf87f40e3bf720dcf07d25f
```

R0 SEG.AM:

```text
255253463f57c90b744523be4d04877d22eb3269e6fcf560994636e508a579ed
```

R0 Program image:

```text
00e2f1e0af3efdaf49ecf57697bac39be7b8eb7e21f8d2402e8cabbe65212747
```

The complete 800K disk image differs from stock in exactly **three
bytes**.

## Building locally

After pulling the research branch:

```powershell
python tools\build_aux16_r0.py "AppleWorks 5.1 Program.po"
```

This creates:

```text
AppleWorks-MaxRAM-AUX16-R0-3MB.po
```

The builder refuses any input whose SHA-256 does not match the known
stock AppleWorks 5.1 Program disk.

## GSSquared test

Use the same emulator configuration for stock and R0.

A large Aux-memory configuration is useful, but R0 is intentionally
still limited by stock `APLWORKS.SYSTEM` to the normal AppleWorks 5.1
maximum.

### Test A - startup

1. Start AppleWorks from the R0 image.
2. Verify normal startup with no hang/crash.
3. Record the reported/available Desktop memory.
4. Compare it with the untouched Program image under the identical
   emulator memory configuration.

Expected: the values should match.

### Test B - basic Desktop use

Exercise all three main applications:

- word processor;
- spreadsheet;
- database.

Create/open documents and make enough edits to allocate Desktop memory.

Expected: normal operation and no corruption.

### Test C - memory pressure

Open or create enough documents to consume a substantial portion of
the available Desktop.

Exercise:

- New/Open;
- copy/paste;
- switching files;
- saving;
- closing/reopening;
- printing preview or other operations that allocate temporary Desktop
  structures where practical.

Expected: behavior identical to stock AppleWorks.

### Test D - repeatability

Quit AppleWorks cleanly and start it again.

Expected: repeatable normal startup.

## Pass criterion

R0 passes when its behavior is indistinguishable from stock AppleWorks
5.1 while using the same emulator configuration.

A pass proves that normal contiguous RamWorks hardware does not need
the explicit physical-bank-number table for the existing 3 MB range.

## Next build after PASS

R1 will preserve the direct-mapped SEG.AM change while modifying
`APLWORKS.SYSTEM` to reproduce Hugh Hood's 96-bank / 6 MB capacity
**without** Hugh's relocated physical-bank table.

That gives us a second known-good comparison point before we cross the
historical 6 MB ceiling.
