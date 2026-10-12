# deboot_fixes

Notes, tools, and repair fixes for the **Ecovacs Deebot OZMO T8 AIVI** robot
vacuum (internal name **"deboot"**, firmware product `AI_px30`, platform
`px30` — Rockchip PX30 + RK1608 AI/CV board, Linux 4.4 + ROS Melodic).

These are **right-to-repair / local-control notes for a device you own.** The
goal is to get root on your *own* robot to diagnose it, cut its cloud
dependency for privacy, and repair fault behaviour the vendor won't let you fix
in software — e.g. a dead side-brush motor **driver** that bricks cleaning even
though everything else works.

Everything here is reconstructed from a single unit and from public research
(see [Credits](#credits)). Your mileage may vary across firmware versions.

## ⚠️ Read first

- **Your own device only.** Opening it may void warranty. You are responsible
  for what you do to your hardware.
- **No vendor binaries are distributed here.** Ecovacs' firmware and `.so`
  files are proprietary. This repo contains only *our own* scripts/tools and
  the *recipe* to patch a binary you already have on your own robot.
- **No secrets.** Don't commit your serial, root password, Wi-Fi SSID, MAC, or
  the cloud IoT credentials from `mdsctl` — they're unique to your device.
- **3.3 V logic.** The UART is 3.3 V TTL. A 5 V adapter can damage the board.
- **Keep the safety checks.** The side-brush patch intentionally leaves
  cliff/fall, trapped, and water detection fully active. Don't disable those.
- **Don't let it auto-update.** A firmware OTA can strip root and revert fixes.

## Contents

| Doc | What |
|-----|------|
| [docs/01-uart-root.md](docs/01-uart-root.md) | Wiring + getting a root shell via U-Boot `init=/bin/sh` |
| [docs/02-root-password.md](docs/02-root-password.md) | How the UART `root` login password is derived (`eco_passwd`) |
| [docs/03-decloud.md](docs/03-decloud.md) | Blocking the cloud while keeping the LAN (no iptables) |
| [docs/04-sidebrush-patch.md](docs/04-sidebrush-patch.md) | Reverse-engineering + patching the "side brush stuck" stop |
| [docs/05-file-transfer.md](docs/05-file-transfer.md) | Moving files on/off the robot over LAN |

Tools (ours, MIT):
- [tools/ecopass.py](tools/ecopass.py) — offline root-password calculator
- [tools/patch_alert_so.py](tools/patch_alert_so.py) — patch *your* `liberos_node_alert.so`

Deploy scripts (ours):
- [autostart/90-brushpatch.sh](autostart/90-brushpatch.sh) — persistent side-brush patch
- [autostart/00-decloud.sh](autostart/00-decloud.sh) — persistent cloud block

## Device facts

- SoC: Rockchip **PX30** + **RK1608** AI/CV co-processor
- Kernel: Linux **4.4.185**, console `ttyFIQ0`, U-Boot 2017.09
- Rootfs: squashfs (read-only) on `rkflash0p7`; writable `/data` ext4 on `rkflash0p10`
- Model string (`/etc/fw.manifest` → `product`): **`AI_px30`**
- robotinfo.dev id `ecovacs.x5d34r`, codename ZJ1913

## Support

If these notes saved your robot (or a repair bill), you can buy me a coffee ☕

[![Buy me a coffee](https://img.shields.io/badge/Buy_me_a_coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://donate.stripe.com/dRm4gzd6Ufx49uBfo76g800)

## Credits

- Dennis Giese & braelynn — *Reverse engineering and hacking Ecovacs robots*,
  DEF CON 32. The `eco_passwd` algorithm and UART approach come from this work.
  <https://dontvacuum.me/>
- `itsjfx/ecovacs-hacking` — the `plat=`/model-string insight.
- Password calculator reference: <https://builder.dontvacuum.me/ecopassword.php>

## License

Our scripts, tools, and docs: MIT (see [LICENSE](LICENSE)). Vendor material is
not included and remains the property of its owner.
