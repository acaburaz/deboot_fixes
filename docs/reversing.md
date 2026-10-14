# Reverse-engineering notes — the motor-current alert

Reconstructed **pseudocode** for the side-brush fault logic in
`liberos_node_alert.so` (`AI_px30` / T8 AIVI), recovered from the stripped
aarch64 binary with `capstone` + `pyelftools`. This is a hand-reconstruction for
understanding — not Ecovacs source — but it matches the disassembly 1:1 and
explains exactly what [the patch](patch-example.md) disables.

> Tooling note: the pseudocode below was first reconstructed from the
> `capstone` disassembly, then **verified against Ghidra 12.1.4's decompiler**
> (headless) — the raw Ghidra output is in the [appendix](#appendix-raw-ghidra-decompiler-output).
> The [REA](https://github.com/morluto/rea) agent decompiler uses the same
> engine, but its **Windows** build only accepts PE targets ("Windows Ghidra P0
> accepts native PE … only"), so for this aarch64 ELF we drove Ghidra headless
> directly (REA would work on Linux/WSL).

## The data: `g_motor_current`

A global array of **6 entries × 36 bytes**, filled by
`MotorCurrentCheckParameterInit`. Reconstructed layout:

```c
typedef struct {            // 36 bytes
    uint8_t  state;         // +0x00  alert state: 0 ok, 1 warn, 2 alarm
    uint8_t  flag;          // +0x01  latched "fault" flag
    uint8_t  _pad[2];
    int32_t  limit;         // +0x04  current threshold being compared
    int32_t  low;           // +0x08  (set, but unused by the check)
    int32_t  ctr_a;         // +0x0c  debounce counter A
    int32_t  n_a;           // +0x10  A target
    int32_t  ctr_b;         // +0x14  debounce counter B
    int32_t  n_b;           // +0x18  B target
    int32_t  ctr_lo;        // +0x1c  recovery counter
    int32_t  n_lo;          // +0x20  recovery target
} motor_entry_t;

motor_entry_t g_motor_current[6];
```

Values programmed by `MotorCurrentCheckParameterInit` (limit / low / n_a / n_b / n_lo):

| idx | limit | low | n_a | n_b | n_lo | motor |
|-----|-------|-----|-----|-----|------|-------|
| 0 | 280 | 100 | 4 | 12 | 50 | **side brush** |
| 1 | 280 | 100 | 4 | 12 | 50 | **side brush** |
| 2 | 1100 | 300 | 2 | 12 | 50 | main brush |
| 3 | 700 | 300 | 3 | 6 | 50 | wheel |
| 4 | 700 | 300 | 3 | 6 | 50 | wheel |
| 5 | 600 | 300 | 2 | 3 | 50 | fan |

## The per-motor check (`sub_0x2abe0`)

```c
// returns 1 while a sample is "over threshold" and being counted, else 0
static int motor_current_check(int current, int idx, uint8_t mode) {
    motor_entry_t *g = &g_motor_current[idx];
    int limit = g->limit;                 // entry+4 (mode only selects source; here always +4)

    if (current >= limit) {               // over-current branch
        g->ctr_lo = 0;
        if (++g->ctr_a < g->n_a) return 0;        // need n_a consecutive
        g->ctr_a = 0;
        if (++g->ctr_b >= g->n_b) {               // sustained long enough...
            g->flag = 1;                          // entry+1: latch fault
            g->ctr_b = 0;
        }
        return 1;
    } else {                              // under-threshold (normal, or dead motor)
        g->ctr_a = 0;
        if (g->ctr_b != 0) {
            if (++g->ctr_lo >= g->n_lo)           // recovered for n_lo samples
                g->ctr_b = 0;
        }
        return 0;
    }
}
```

## The caller (`sub_0x2af8c`) — and what the patch removes

Runs the check for all six motors and escalates each entry's `state` byte. The
**four marked writes** (two per side brush, entries 0 and 1) are exactly the
`strb` instructions the patch replaces with `nop`:

```c
void motor_current_check_all(current_report_t *r) {
    for (int i = 0; i < 6; i++) {
        motor_entry_t *g = &g_motor_current[i];
        int ret = motor_current_check(r->current[i], i, g->state);
        if (ret != 0) {
            if (g->flag != 0)
                g->state = 2;     // ALARM    <-- idx 0: 0x2afe4 | idx 1: 0x2b05c  ==> nop
            else if (g->state != 2)
                g->state = 1;     // WARNING  <-- idx 0: 0x2b00c | idx 1: 0x2b084  ==> nop
        }
    }
}
```

Downstream alert reporting reads `g->state`. After the patch, side-brush entries
(0 and 1) can never leave `state == 0`, so no side-brush alarm is ever raised —
every other motor and the cliff/fall/trapped/water checks are untouched.

## Why a *dead* side brush trips this

With the driver output dead the MCU reports an abnormal current for that motor;
once it crosses `limit` for the debounce window (`n_a` then `n_b` samples), the
caller sets `state = 2` and cleaning halts with "side brush stuck." NOPing the
two side-brush `state` writes short-circuits that escalation.

(If a future unit instead faults via `libDeebot.so`'s navigation stuck
framework — `rbot_stuck_det` / `RobotStuckWarning` with `STUCK *_side_brush` —
the same reconstruct-then-NOP approach applies there.)

## Appendix: raw Ghidra decompiler output

Ground truth, straight from Ghidra 12.1.4 headless (image base `0x00100000`, so
`FUN_0012abe0` = file vaddr `0x2abe0`). `PTR_g_motor_current_001443e0` is the
pointer to `g_motor_current`; `* 0x24` = 36-byte stride. This confirms the
reconstruction above 1:1.

### Per-motor check — `FUN_0012abe0`

```c
undefined8 FUN_0012abe0(uint param_1,uint param_2,char param_3)   // (current, idx, mode)
{
  uint local_4;
  // all three mode branches read the same field (+4 = limit):
  if (param_3 == '\x01')      local_4 = *(uint *)(g + param_2*0x24 + 4);
  else if (param_3 == '\x02') local_4 = *(uint *)(g + param_2*0x24 + 4);
  else                        local_4 = *(uint *)(g + param_2*0x24 + 4);

  if (param_1 < local_4) {                              // under threshold
    *(u32*)(g + param_2*0x24 + 0xc) = 0;                // ctr_a = 0
    if (*(int*)(g + param_2*0x24 + 0x14) != 0 &&
        (++*(int*)(g + param_2*0x24 + 0x1c),
         *(uint*)(g + param_2*0x24 + 0x20) <= *(uint*)(g + param_2*0x24 + 0x1c)))
      *(u32*)(g + param_2*0x24 + 0x14) = 0;             // recovered -> clear ctr_b
  } else {                                              // >= threshold
    *(u32*)(g + param_2*0x24 + 0x1c) = 0;
    ++*(int*)(g + param_2*0x24 + 0xc);
    if (*(uint*)(g + param_2*0x24 + 0x10) <= *(uint*)(g + param_2*0x24 + 0xc)) {
      *(u32*)(g + param_2*0x24 + 0xc) = 0;
      ++*(int*)(g + param_2*0x24 + 0x14);
      if (*(uint*)(g + param_2*0x24 + 0x18) <= *(uint*)(g + param_2*0x24 + 0x14)) {
        g[param_2*0x24 + 1] = 1;                        // latch fault flag (+1)
        *(u32*)(g + param_2*0x24 + 0x14) = 0;
      }
      return 1;
    }
  }
  return 0;
}
```

### Caller — `FUN_0012af8c` (← the four patched lines)

```c
void FUN_0012af8c(undefined1 *param_1)   // param_1 = per-motor current report
{
  char cVar1;
  cVar1 = FUN_0012abe0(*(u32*)(param_1 + 0x30),0,*param_1);   // motor 0  (SIDE BRUSH)
  if (cVar1 != '\0') {
    if (g[1] == '\0') { if (*g != '\x02') *g = 1; }           // 0x2b00c  --> nop
    else              *g = 2;                                 // 0x2afe4  --> nop
  }
  cVar1 = FUN_0012abe0(*(u32*)(param_1 + 0x34),1,*param_1);   // motor 1  (SIDE BRUSH)
  if (cVar1 != '\0') {
    if (g[0x25] == '\0') { if (g[0x24] != '\x02') g[0x24] = 1; } // 0x2b084 --> nop
    else                 g[0x24] = 2;                            // 0x2b05c --> nop
  }
  // motors 2..5 (main brush / wheels / fan) left untouched:
  cVar1 = FUN_0012abe0(*(u32*)(param_1 + 0x38),2,*param_1); if (cVar1) { if (g[0x49]=='\0'){if(g[0x48]!='\x02')g[0x48]=1;} else g[0x48]=2; }
  cVar1 = FUN_0012abe0(*(u32*)(param_1 + 0x3c),3,*param_1); if (cVar1) { if (g[0x6d]=='\0'){if(g[0x6c]!='\x02')g[0x6c]=1;} else g[0x6c]=2; }
  cVar1 = FUN_0012abe0(*(u32*)(param_1 + 0x40),4,*param_1); if (cVar1) { if (g[0x91]=='\0'){if(g[0x90]!='\x02')g[0x90]=1;} else g[0x90]=2; }
  cVar1 = FUN_0012abe0(*(u32*)(param_1 + 0x44),5,*param_1); if (cVar1) { if (g[0xb5]=='\0'){if(g[0xb4]!='\x02')g[0xb4]=1;} else g[0xb4]=2; }
}
```

The four `*g = 2 / 1` and `g[0x24] = 2 / 1` stores (motors 0 and 1) are exactly
the `strb` instructions replaced with `nop` — see [patch-example.md](patch-example.md).

### `MotorCurrentCheckParameterInit`

```c
void MotorCurrentCheckParameterInit(void)
{
  FUN_0012aa94(g + 0x48, 0x44c, 300, 2, 0xc, 0x32);  // idx 2 main brush (1100/300)
  FUN_0012aa94(g,        0x118, 100, 4, 0xc, 0x32);  // idx 0 SIDE BRUSH (280/100)
  FUN_0012aa94(g + 0x24, 0x118, 100, 4, 0xc, 0x32);  // idx 1 SIDE BRUSH (280/100)
  FUN_0012aa94(g + 0x6c, 700, 300, 3, 6, 0x32);      // idx 3 wheel
  FUN_0012aa94(g + 0x90, 700, 300, 3, 6, 0x32);      // idx 4 wheel
  FUN_0012aa94(g + 0xb4, 600, 300, 2, 3, 0x32);      // idx 5 fan
}
```

> Reproduce: `GHIDRA_INSTALL_DIR=<ghidra-12.1.x> support/analyzeHeadless <proj>
> p -import liberos_node_alert.so -postScript DecompileAt.java` with a small
> GhidraScript that decompiles `imageBase + {0x2abe0,0x2af8c,0x2aaf8}`.
