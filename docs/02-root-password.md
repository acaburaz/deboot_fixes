# 02 — UART `root` login password

Once you've booted normally (not `init=/bin/sh`), the UART prompt is
`deboot login:` with user **`root`**. The password is **unique per device**,
generated at boot by the `eco_passwd` program. You can compute it offline.

## How it works

From `/etc/conf/eco_passwd.conf` on the robot:

```json
{
  "product_file": "/etc/fw.manifest",
  "product_key": "product",
  "sn_info": {
    "prefix": ["E"],
    "file": "/dev/block/bootdevice/by-name/sys",
    "offset": 1048576
  }
}
```

And the boot flow (`/etc/rc.d/pre_boot.sh`) copies a template passwd file into a
writable location, then runs `eco_passwd -f /etc/conf/eco_passwd.conf`, which
rewrites root's hash with the computed password. (`/etc/passwd` is a symlink to
that writable copy, which is why it looks "missing" in a bare `init=/bin/sh`
shell — the target only exists after a normal boot.)

So the two inputs are:

- **model string** = the `product` value in `/etc/fw.manifest` → **`AI_px30`**
  on the T8 AIVI. (It is *not* the firmware image name, the SoC, or the
  robotinfo codename — those were all dead ends.)
- **serial** = the sticker serial; the algorithm uses the **last 8 characters**.

## The algorithm

Published in Dennis Giese's DEF CON 32 talk:

```
password = base64( sha256sum_line( product + SALT + last8(serial) + "\n" ) )
```

where:
- `SALT` = `d4:3d:7e:fa:12:5d:C8:02:8F:0A:E2:F5` (the fixed constant; it is
  obfuscated inside the `eco_passwd` binary, but the DEF CON value is correct),
- `sha256sum_line` is the textual line GNU `sha256sum` prints for stdin:
  `"<hexdigest>  -\n"` (two spaces, a dash, a newline),
- the whole line is then base64-encoded.

Equivalent shell one-liner:

```sh
printf '%s\n' "AI_px30d4:3d:7e:fa:12:5d:C8:02:8F:0A:E2:F5<LAST8>" | sha256sum | base64 -w0
```

## Use the tool

[`tools/ecopass.py`](../tools/ecopass.py) — offline, no network:

```
python ecopass.py <YOUR_SERIAL_OR_LAST8>            # prints all known models
python ecopass.py <YOUR_SERIAL_OR_LAST8> -m AI_px30 # just the T8 AIVI value
```

It accepts the full sticker serial or just the last 8 characters, and takes the
last 8 internally. The printed base64 string **is** the password — type/paste
the whole thing at the `deboot login:` prompt (it won't echo).

## Reading the real serial

If the sticker is unreadable, read it from the shell once you're root
(it's at offset 2048 of the `sys` partition for the factory tool, and the live
value is also available via):

```
mdsctl sys0 '{"pid_get":"get_all"}'   # shows "sn" and "mach_pwd" (= product)
```

> **Do not publish your serial or the resulting password.** They identify and
> unlock *your* specific robot.

## Troubleshooting

- **"Login incorrect" on a long paste:** characters can drop over UART. Paste
  slowly / use a terminal with a paste delay. The value ends in `=`.
- **Still wrong:** confirm `product` really is `AI_px30`
  (`cat /etc/fw.manifest`) and re-check the serial characters (`0`↔`O`, `B`↔`8`).
- **Can't get in at all:** fall back to the U-Boot `init=/bin/sh` method
  (doc 01) — it needs no password.
