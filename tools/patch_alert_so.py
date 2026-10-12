#!/usr/bin/env python3
"""patch_alert_so.py — disable the side-brush motor-current alert escalation in
an Ecovacs "deboot" (AI_px30 / T8 AIVI) liberos_node_alert.so.

This patches YOUR OWN copy of the vendor binary — no vendor binary is shipped
with this repo. It NOPs the four `strb` instructions that escalate the two
side-brush motor entries' alert state byte, leaving every other motor and every
other safety check (cliff/fall/trapped/water) untouched.

See docs/04-sidebrush-patch.md for the full reverse-engineering writeup.

Requirements:  pip install capstone pyelftools

Usage:
    python patch_alert_so.py liberos_node_alert.so liberos_node_alert.patched.so

Offsets below are for firmware 1.11.x (original md5 cc22ecfb...). On another
build they will differ — re-locate them with a disassembler and update
TARGETS / EXPECT_ORIG_MD5.
"""
import hashlib
import shutil
import sys

try:
    from elftools.elf.elffile import ELFFile
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
except ImportError:
    sys.exit("Need: pip install capstone pyelftools")

# Known-good reference for the build these offsets were derived from.
EXPECT_ORIG_MD5 = "cc22ecfb7bd9c0444cf80aa338136c82"
EXPECT_PATCHED_MD5 = "d0362aba9af9708ac76d76776bf03b41"

# vaddr -> human label. Each MUST currently be a `strb` (side-brush state write).
TARGETS = {
    0x2afe4: "side-brush entry 0, state = 2",
    0x2b00c: "side-brush entry 0, state = 1",
    0x2b05c: "side-brush entry 1, state = 2",
    0x2b084: "side-brush entry 1, state = 1",
}
NOP = b"\x1f\x20\x03\xd5"  # aarch64 nop


def vaddr_to_offset(elf, vaddr):
    for seg in elf.iter_segments():
        if seg["p_type"] != "PT_LOAD":
            continue
        va, off, sz = seg["p_vaddr"], seg["p_offset"], seg["p_filesz"]
        if va <= vaddr < va + sz:
            return off + (vaddr - va)
    raise ValueError(f"vaddr {vaddr:#x} not in any PT_LOAD segment")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]

    orig = open(src, "rb").read()
    md5 = hashlib.md5(orig).hexdigest()
    print(f"input : {src}  md5={md5}  size={len(orig)}")
    if md5 != EXPECT_ORIG_MD5:
        print(f"  WARNING: md5 != known original ({EXPECT_ORIG_MD5}).")
        print("  Offsets may not match this build. Verify the disassembly below.")

    elf = ELFFile(open(src, "rb"))
    if elf.get_machine_arch() != "AArch64":
        sys.exit("Not an AArch64 ELF.")
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    buf = bytearray(orig)
    ok = True
    for vaddr, label in TARGETS.items():
        off = vaddr_to_offset(elf, vaddr)
        ins = next(md.disasm(bytes(buf[off:off + 4]), vaddr))
        print(f"  {vaddr:#010x}  {label:32}  {ins.mnemonic} {ins.op_str}")
        if ins.mnemonic != "strb":
            print("    !! expected 'strb' here — refusing to patch this offset")
            ok = False
            continue
        buf[off:off + 4] = NOP

    if not ok:
        sys.exit("Aborted: one or more targets were not the expected instruction.")

    shutil.copyfile(src, dst)  # preserve perms/metadata, then overwrite bytes
    open(dst, "wb").write(bytes(buf))

    out_md5 = hashlib.md5(bytes(buf)).hexdigest()
    print(f"output: {dst}  md5={out_md5}  size={len(buf)}")
    if md5 == EXPECT_ORIG_MD5 and out_md5 != EXPECT_PATCHED_MD5:
        sys.exit(f"ERROR: patched md5 {out_md5} != expected {EXPECT_PATCHED_MD5}")
    print("done. same size as input -> deploy via bind-mount (see docs/04).")


if __name__ == "__main__":
    main()
