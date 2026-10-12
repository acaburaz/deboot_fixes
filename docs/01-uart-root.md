# 01 — UART root shell

The T8 AIVI exposes a 3.3 V UART on its debug header. The firmware has a login
shell on it, but we don't need the password to get root the first time — U-Boot
lets us boot straight into a root shell.

## Wiring

- **3.3 V TTL** USB-UART adapter, **115200 8N1**, no flow control.
- Connect **GND, TX, RX** only. **Do not connect the 3.3 V pin** — power the
  robot from its own battery, share only ground.
- Adapter **TX → board RX**, adapter **RX → board TX**.
- The debug header is behind a service flap; per Dennis Giese's talk the pad
  group is `GND / 3.3V (do not connect) / RX TX`, and **some units are rotated
  180°** — if you get nothing, try the mirrored orientation.

**Sanity check:** power on and you should see a U-Boot banner, then a Linux
boot log, ending at `deboot login:`. Silence = wiring/GND/orientation; garbage =
wrong baud. A loopback test (jumper the adapter's own TX↔RX and type) confirms
the adapter/port/baud before you blame the robot.

## Getting into U-Boot

The bootloader prints:

```
Hit key to stop autoboot('CTRL+C'):  0
```

`bootdelay` is **0**, so the window is tiny, and an early `Hotkey: ctrl+c`
handler eats single presses. **Hold Ctrl+C continuously from the moment you
power on** until you land at the U-Boot prompt (`=>` / `Rockchip>`).

## Boot straight into a root shell

`bootcmd` runs `boot_android`, which **prepends the env `bootargs`** to the
kernel command line. So appending `init=/bin/sh` makes the kernel start a shell
as PID 1 — no login, no services, no watchdog:

```
setenv bootargs ${bootargs} init=/bin/sh
boot_android ${devtype} ${devnum}
```

You land at a `#` prompt. This is **not saved** (no `saveenv`), so a normal
power-cycle boots normally again.

> Daemons are started **executed** (not sourced) from `/etc/rc.sysinit` using
> the `DAEMONS` list in `/etc/rc.conf`. Useful to know when deciding how to make
> changes persist (see doc 04).

## First things in the shell

`/proc` isn't mounted in this bare shell:

```
mount -t proc proc /proc
```

Partition map (this unit):

| Device | Use |
|--------|-----|
| `rkflash0p7` | rootfs (squashfs, read-only) |
| `rkflash0p10` | `/data` (ext4, writable) |

Mount `/data` to read logs / install fixes:

```
mount -t ext4 /dev/rkflash0p10 /data
```

From here you can read diagnostics (`/data/save/lifespan.json`,
`/data/log/*`), recover the login password (doc 02), or deploy fixes
(docs 03 / 04).

## Useful offline diagnostics (no services needed)

```
cat /data/save/lifespan.json      # brush / side-brush / filter / unitcare minutes
tail -40 /data/log/charge.log     # battery/charge history
df -h                             # /data usage; squashfs shows 100% (normal)
dmesg | grep -iE 'error|nand|ecc' # flash / hardware faults
```

Camera sensor probe failures (`jx_h65/jx_h68 ... -22`) in `dmesg` are **normal
in this bare shell** — the AI/camera stack isn't powered here.
