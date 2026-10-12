# Patch example — the exact bytes changed

A concrete, reproducible example of the side-brush patch: the file, the four
instructions changed, the before/after bytes, and the resulting checksums. This
is the change [`tools/patch_alert_so.py`](../tools/patch_alert_so.py) applies.
See [04-sidebrush-patch.md](04-sidebrush-patch.md) for *why*.

## File

| | |
|---|---|
| On the robot | `/usr/lib/node/liberos_node_alert.so` |
| Type | ELF 64-bit LSB shared object, **ARM aarch64**, stripped |
| Firmware | 1.11.x (`AI_px30` / T8 AIVI "deboot") |
| Original md5 | `cc22ecfb7bd9c0444cf80aa338136c82` |
| Patched md5 | `d0362aba9af9708ac76d76776bf03b41` (same size, 217536 bytes) |

The read-only rootfs is never written — the patched copy is bind-mounted over
this path at boot (see [04](04-sidebrush-patch.md)).

## The change: 4 instructions → `nop`

These four `strb` instructions are the ones that escalate the two side-brush
motor entries' **alert state byte** (`byte0`). NOPing them means a side-brush
motor fault never raises an alert, so cleaning no longer stops — while every
other motor and every other safety check (cliff/fall/trapped/water) is left
untouched.

| vaddr | file off | original bytes | original insn | patched bytes | patched insn |
|-------|----------|----------------|---------------|---------------|--------------|
| `0x2afe4` | `0x2afe4` | `01 00 00 39` | `strb w1, [x0]` | `1f 20 03 d5` | `nop` |
| `0x2b00c` | `0x2b00c` | `01 00 00 39` | `strb w1, [x0]` | `1f 20 03 d5` | `nop` |
| `0x2b05c` | `0x2b05c` | `01 90 00 39` | `strb w1, [x0, #0x24]` | `1f 20 03 d5` | `nop` |
| `0x2b084` | `0x2b084` | `01 90 00 39` | `strb w1, [x0, #0x24]` | `1f 20 03 d5` | `nop` |

(`39 00 00 01` little-endian = `strb w1,[x0]`; `d5 03 20 1f` = aarch64 `nop`.
`[x0]` is side-brush entry 0, `[x0,#0x24]` is entry 1 — entries are 36 bytes.)

## In context

Example: the first site, in the caller that updates entry 0's state. `w1` holds
the state value (2 = alarm); the `strb` writes it into the entry. We replace
just that store:

```asm
0x2afd8:  adrp  x0, #0x44000
0x2afdc:  ldr   x0, [x0, #0x3e0]      ; x0 = &g_motor_current
0x2afe0:  mov   w1, #2                ; state = 2 (alarm)
0x2afe4:  strb  w1, [x0]      --->    nop     ; was: side-brush 0 state = alarm
0x2afe8:  b     #0x2b010
```

With the `strb` gone, `byte0` stays `0`, so the downstream alert reporting never
sees a side-brush alarm.

## Reproduce it

On your own copy of the binary:

```
pip install capstone pyelftools
python tools/patch_alert_so.py liberos_node_alert.so liberos_node_alert.patched.so
```

Expected tail of the output:

```
output: liberos_node_alert.patched.so  md5=d0362aba9af9708ac76d76776bf03b41  size=217536
done. same size as input -> deploy via bind-mount (see docs/04).
```

The tool verifies each target is still a `strb` before touching it and refuses
if the instructions/md5 don't match your build (offsets are version-specific).
