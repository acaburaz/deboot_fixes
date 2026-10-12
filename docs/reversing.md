# Reverse-engineering notes — the motor-current alert

Reconstructed **pseudocode** for the side-brush fault logic in
`liberos_node_alert.so` (`AI_px30` / T8 AIVI), recovered from the stripped
aarch64 binary with `capstone` + `pyelftools`. This is a hand-reconstruction for
understanding — not Ecovacs source — but it matches the disassembly 1:1 and
explains exactly what [the patch](patch-example.md) disables.

> Tooling note: you can cross-check this with a decompiler of your choice (IDA /
> Ghidra / Binary Ninja, or the REA agent decompiler — `npx rea-agents setup`,
> if it supports aarch64). Everything below was derived from the disassembly.

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
