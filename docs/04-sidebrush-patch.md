# 04 — Patching the "side brush stuck" stop

## The problem

Symptom: the robot cleans for a bit, then stops and reports **side brush stuck**.

Diagnosis on this unit: the **right side-brush motor is fine** (it spins on a
bench 3.3 V supply), but the **motor-driver output on the mainboard is dead** —
no drive reaches that motor. So the measured motor current is abnormal, the
firmware flags "side brush stuck," and halts.

Because the motor itself is healthy, a mechanical fix or a load-spoof doesn't
help — there's no drive output to put a load on. The fix is a **binary patch**
that stops the firmware from escalating the side-brush motor-current alert,
while leaving every other safety check untouched.

## How the firmware decides "stuck"

Three ROS nodes (`dlopen`-ed from `/usr/lib/node/*.so`) are involved:

- `liberos_node_hardware_platform.so` — reads per-motor current from the MCU and
  publishes `motor/MotorCurrentValue` (motor types: `MAINBRUSH=0`,
  `LEFT_SIDEBRUSH=1`, `RIGHT_SIDEBRUSH=2`).
- **`liberos_node_alert.so`** — the safety monitor. Runs `MotorCurrentCheck`
  (plus `FallCheck`, `TrappedCheck`, `WaterCheck`, `DirtCheck`) and raises
  `alert/Alerts`.
- `libDeebot.so` — reacts to alerts / its own stuck framework and stops cleaning.

Inside `liberos_node_alert.so`, `MotorCurrentCheckParameterInit` fills a global
`g_motor_current`: **6 entries × 36 bytes**, each
`{ +4: high limit, +8: low limit, +0x10/+0x18/+0x20: debounce counts }`. The
identical pairs reveal the mapping:

| entry index | high | low | motor |
|---|---|---|---|
| 0 | 280 | 100 | side brush |
| 1 | 280 | 100 | side brush |
| 2 | 1100 | 300 | main brush |
| 3 | 700 | 300 | wheel |
| 4 | 700 | 300 | wheel |
| 5 | 600 | 300 | fan |

A per-motor check (`sub_0x2abe0`) runs the current through a debounce state
machine and, when the fault persists, sets the entry's **state byte (`byte0`)**
0 → 1 → 2. That escalated state is what surfaces as the alert that stops
cleaning. The caller (`sub_0x2af8c`) runs it for all six motors (side brushes
are indices **0 and 1**).

## The patch

Disable **only** the side-brush entries' state escalation: NOP the four `strb`
instructions that write `byte0` for entries 0 and 1. Every other motor and every
other safety check (cliff/fall/trapped/water) is left intact.

Offsets in `liberos_node_alert.so` (firmware **1.11.x**, original
`md5 cc22ecfb7bd9c0444cf80aa338136c82`):

| vaddr | original | → |
|---|---|---|
| `0x2afe4` | `strb w1,[x0]`       (side-brush 0, state=2) | `nop` |
| `0x2b00c` | `strb w1,[x0]`       (side-brush 0, state=1) | `nop` |
| `0x2b05c` | `strb w1,[x0,#0x24]` (side-brush 1, state=2) | `nop` |
| `0x2b084` | `strb w1,[x0,#0x24]` (side-brush 1, state=1) | `nop` |

aarch64 `nop` = `1f 20 03 d5`. Patched `md5 d0362aba9af9708ac76d76776bf03b41`,
**same size** (so it bind-mounts cleanly over the original).

Reproduce on **your own** copy with [`tools/patch_alert_so.py`](../tools/patch_alert_so.py):

```
python patch_alert_so.py /path/to/liberos_node_alert.so liberos_node_alert.patched.so
```

It verifies each target is a `strb` before patching and refuses if the md5 /
instructions don't match your build.

> **Offsets are version-specific.** They're valid for the firmware above. On a
> different build, re-locate `MotorCurrentCheckParameterInit` / the caller with
> your own disassembler (capstone + pyelftools — see the tool) and find the
> side-brush `strb byte0` writes.

## Deploying it (persistent, safe)

The rootfs is read-only squashfs, so we can't overwrite the `.so`. Instead we
**bind-mount** the patched copy over it and reload deebot so it re-`dlopen`s it.

Key gotchas learned the hard way:

- **`pidof`, not `ps`** — busybox `ps`/`ps w` is unreliable here; use
  `pidof deebot` / `pidof medusa` to check state.
- **Don't name your autostart file `deebot.sh`.** The stock
  `/etc/rc.d/deebot.sh` *exits* if `/data/autostart/deebot.sh` exists (an
  override hook), and replicating its launch loop is fragile — it wedged the
  whole stack in testing. Use a differently-named autostart script that leaves
  the stock launcher (and its restart loop) alone.
- **`deebot` and `medusa` restart-couple each other** (each kills the other on
  its own reload). A single `killall deebot` recovers via the stock loop within
  a few seconds — verify with `pidof`.

Steps:

```
mkdir -p /data/patch
# 1. back up the stock binary (see doc 05 for how to copy it off/around)
cp /usr/lib/node/liberos_node_alert.so /data/patch/liberos_node_alert.so.orig
# 2. put your PATCHED binary at:
#    /data/patch/liberos_node_alert.so
# 3. install the persistent hook:
#    /data/autostart/90-brushpatch.sh   (from this repo)
chmod +x /data/autostart/90-brushpatch.sh
```

[`autostart/90-brushpatch.sh`](../autostart/90-brushpatch.sh) waits for the
system to settle, bind-mounts the patched node, then `killall deebot` so the
stock loop reloads it with the patch. All backgrounded so it can never wedge
boot.

### Test without rebooting

```
mount --bind /data/patch/liberos_node_alert.so /usr/lib/node/liberos_node_alert.so
killall deebot
sleep 15; echo "deebot=$(pidof deebot) medusa=$(pidof medusa)"; mount | grep liberos_node_alert
```

Both PIDs present + the bind-mount line = patch is live. Then run a clean and
confirm it no longer stops on the side brush.

### Verify persistence

After installing `90-brushpatch.sh`, reboot, wait ~40 s, and check:

```
sleep 40; echo "deebot=$(pidof deebot) medusa=$(pidof medusa)"; mount | grep liberos_node_alert
```

## Rollback

```
rm /data/autostart/90-brushpatch.sh
reboot
```

(or live: `umount /usr/lib/node/liberos_node_alert.so; killall deebot`)

## If it still stops

Then the stop originates in `libDeebot.so`'s navigation stuck framework
(`rbot_stuck_det` → `rbotStuckHandler` → `RobotStuckWarning`, with
`STUCK right_side_brush`/`left_side_brush`) rather than the alert node. Pull
`libDeebot.so` and apply the same technique: locate the side-brush stuck escalation
and NOP it.
