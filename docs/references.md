# References

Primary sources this work is based on. These are **external, authoritative
links** — the PDFs/pages are the authors' own copyrighted material and are not
copied into this repo. Open them at the source.

## Debug-header pinout (what you likely came here for)

- **Reverse engineering and hacking Ecovacs robots** — Dennis Giese & braelynn,
  DEF CON 32 (2024). PDF:
  <https://dontvacuum.me/talks/DEFCON32/DEFCON32_reveng_hacking_ecovacs_robots.pdf>
  - **Debug ports** overview: slides ~37–38 (UART / 3.3V / SWD / USB; "same for
    all models since 2019").
  - **UART pinout diagram:** the **final slide (p. 87)** — `GND`,
    `3.3V (do not connect)`, `RX TX`, with the warning that **some units are
    rotated 180°**. See also [docs/01-uart-root.md](01-uart-root.md) for the
    text version.
  - **Root shell / `eco_passwd`:** slide ~75 (algorithm + salt).

## Other sources

- **dontvacuum.me** — Dennis Giese's site; index of talks and research:
  <https://dontvacuum.me/>
- **Ecovacs root password calculator** (reference implementation of
  `eco_passwd`): <https://builder.dontvacuum.me/ecopassword.php>
- **robotinfo.dev** — hardware/firmware/rootability database. The T8 AIVI:
  <https://robotinfo.dev/detail_ecovacs.x5d34r_0.html>
- **itsjfx/ecovacs-hacking** — community notes; source of the "model string is
  the platform `product` value" insight:
  <https://github.com/itsjfx/ecovacs-hacking>

> If any link rots, search for "Dennis Giese Ecovacs DEF CON" / "dontvacuum
> ecovacs" — the talks are mirrored in several places.
