#!/usr/bin/env python3
"""Ecovacs UART root-password calculator (offline).

Reproduces the `eco_passwd` algorithm from Dennis Giese / braelynn's
DEF CON 32 talk "Reverse engineering and hacking Ecovacs robots":

    password = base64( sha256sum_stdout( model + SALT + sn + "\n" ) )

where sha256sum_stdout is the textual "<hexdigest>  -\n" line that coreutils
`sha256sum` prints when hashing stdin.

- `model` is the `product` value from /etc/fw.manifest on the robot. For the
  Deebot T8 AIVI ("deboot") it is "AI_px30" (verified working at the UART
  login). It is NOT the firmware image name, the SoC, or the robotinfo codename.
- `sn` is the LAST 8 characters of the sticker serial
  (e.g. serial E0B7XXXXXXXXABCD1234 -> sn = ABCD1234).

Usage:
    python ecopass.py <SERIAL_OR_LAST8>            # all known model strings
    python ecopass.py <SERIAL_OR_LAST8> -m AI_px30 # just the T8 AIVI value
    python ecopass.py E0B7XXXXXXXXABCD1234         # full serial also accepted
"""
import argparse
import base64
import hashlib

SALT = "d4:3d:7e:fa:12:5d:C8:02:8F:0A:E2:F5"

# The hash prefix is the `product` string from /etc/fw.manifest. AI_px30 is the
# confirmed T8 AIVI value; the others are generic guesses for related platforms.
KNOWN_MODELS = [
    "AI_px30",   # Deebot T8 AIVI ("deboot") -- CONFIRMED
    "px30-ai",
    "px30-sl",
    "rk3326-ai",
    "rk3326-sl",
    "rv1126",
]


def eco_password(model: str, sn: str) -> str:
    line = f"{model}{SALT}{sn}\n"
    hexdigest = hashlib.sha256(line.encode()).hexdigest()
    # match `sha256sum` stdin output: "<hex><SP><SP>-\n"
    sha256sum_stdout = f"{hexdigest}  -\n"
    return base64.b64encode(sha256sum_stdout.encode()).decode()


def normalize_sn(raw: str) -> str:
    raw = raw.strip()
    return raw[-8:] if len(raw) > 8 else raw


def main() -> None:
    ap = argparse.ArgumentParser(description="Ecovacs UART root password calculator (offline)")
    ap.add_argument("serial", help="Serial from sticker, or just the last-8 tail")
    ap.add_argument("-m", "--model", help="Single model string (default: print all known)")
    args = ap.parse_args()

    sn = normalize_sn(args.serial)
    models = [args.model] if args.model else KNOWN_MODELS

    print(f"SN tail: {sn}\n")
    for model in models:
        print(f"{model:12} {eco_password(model, sn)}")
    print("\nLog in as root at the UART `login:` prompt with the password for the")
    print("model string that matches your board (AI_px30 for the T8 AIVI).")


if __name__ == "__main__":
    main()
