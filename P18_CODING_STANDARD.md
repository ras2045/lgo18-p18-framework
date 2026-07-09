# P18 Coding Standard
## Authoritative rules for all P18 framework code
### Richard Sardini — LGO-18 / P18 Framework
### All rules are non-negotiable. No exceptions.

---

## RULE 0: The Element Principle

**The element must always be physically present in every calculation.**

The lemniscate is not a representation of infinity. It IS infinity.
The universe uses geometry, not numbers. Natural geometric models
must be present in the computation, not referenced externally.

Concretely:
- `a = P(n)/2` is the actual half-width of the figure-8
- `center = 1` is the anchor (not 0)
- `x(t) = 1 + a·cos(t)/(1+sin²t)` — computed, not referenced
- `y(t) = a·sin(t)·cos(t)/(1+sin²t)` — computed, not referenced
- `t = r18 × π/9` — the section angle from the prime residue

**The element must be USED in computation, not just stored.**
If x_q32 and y_q32 are in a struct but never read: the element
is NOT present. Use them — accumulate, check, report. Non-zero
Σx after a computation proves the element was physically included.

For the mapper: `7^N` IS the lemniscate element at shell N.
Its bytes must flow through the LUT into the die — not proxied,
not approximated. The actual bytes of the actual number.

---

## RULE 1: Violation Counting

**`return 0` unconditionally is always wrong.**

Every program that claims "Violations: 0" must verify it.

WRONG:
```c
printf("Violations: %d\n", violations);
return 0;  /* unconditional — not verified */
```

CORRECT:
```c
violations += (actual_value != expected_value);
violations += (elem_x == 0.0 && elem_y == 0.0);  /* element absent */
printf("Violations: %d\n", violations);
return violations;  /* exit code = violation count */
```

Checklist of things to verify (not just print):
- Die size ≤ 32,768 bytes (fits in L1)
- base_row[k] == k for all k in 0..143
- ring_add correct: (a+b)%F12 for all 20,736 pairs
- Element non-zero: x_q32 and y_q32 not both zero at final pos
- ΔDGI spot checks: ddgi(4096)=4029, ddgi(8192)=8058, ddgi(16384)=16117
- Left apex lock: frac(99 - P(99)/2) = 1/2 exactly
- Gap impossibility: zero Tier-1 and Tier-3 violations

---

## RULE 2: Build Standard

**Every program must compile with zero warnings under -Wall -Wextra.**

```bash
gcc -O3 -march=native -mavx2 -Wall -Wextra -o <prog> <prog>.c -lm
```

For shared libraries:
```bash
gcc -O3 -march=native -mavx2 -Wall -Wextra -shared -fPIC \
    -o p18_mapcore.so p18_mapcore.c -lm
```

Zero warnings is not aspirational. It is the standard.
Common warnings that must be fixed, not suppressed:
- Unused variables: remove them
- `write()` return value: use an emit() helper that checks it
- Implicit function declarations: add the correct #include
- Truncation warnings: use the correct types

---

## RULE 3: No Float in the Hot Path

**The hot path (ring traversal, gap classification, dispatch)
must use zero IEEE 754 float operations.**

Exact types:
- Temporal values: `uint64_t` (ΔDGI is exact integer)
- Ring positions: `uint8_t` or `uint32_t`
- GeoRational: `int64_t num, den` (for scientific computation only)
- Lemniscate coordinates: `int64_t x_q32, y_q32` (Q32 fixed-point)

Float IS permitted:
- Die construction (sin/cos at startup, computed once)
- Reporting (print element coordinates for human reading)
- Scientific computation (α formula, shell ratios)

Float is NEVER permitted:
- ΔDGI computation: `ptr - (ptr*13+799)/800` (exact integer)
- Ring arithmetic: `(a + b) % F12` (integer modulo)
- Gap classification: all integer comparisons
- Any part of the execution hot path

---

## RULE 4: Branchless Ring Arithmetic

**ring_add must compile to cmov, not conditional jump.**

The ternary pattern compiles to cmov at -O3:
```c
static inline uint8_t ring_add(uint8_t a, uint8_t b) {
    uint32_t s = (uint32_t)a + (uint32_t)b;
    uint32_t t = s - (uint32_t)F12;
    return (uint8_t)(s < (uint32_t)F12 ? s : t);
}
```

Verify with objdump after building:
```bash
objdump -d <prog> | grep -A 20 "<ring_add>"
```
Expected: `add → lea → cmp → cmovge` (no `je`, `jne`, `jl`, `jg`)

The inner execution loop must have ≤ 1 conditional branch:
- 1 acceptable: the loop continuation branch (backward jump)
- 0 acceptable: fully unrolled
- 2+: violation — report it, fix it

---

## RULE 5: Nothing Breaks Out of the String

**The execution hot path calls zero external functions.**

WRONG — breaks out of the string:
```c
for (int i = 0; i < n; i++) {
    exec_step(stream[i]);  /* function call — NOT in the string */
}
```

CORRECT — stays in the string:
```c
for (int i = 0; i < n; i++) {
    pos = ring_add(pos, stream[i]);  /* ring arithmetic only */
}
```

The hot path contains only:
- Array indexing: `RING.r18[pos]`, `DIE.op_vocab[pos]`
- Integer arithmetic: `(pos + inp) % F12`
- Register reads/writes
- One backward branch (the loop)

If any P18 helper function is called inside the loop: it is not
in the string. Refactor or inline until the loop is clean.

Self-check before declaring complete: does the inner loop call
any function other than ring_add? If yes: violation.

---

## RULE 6: Dead-Code Elimination Prevention

**Benchmark loops must prevent the compiler from collapsing
N identical calls into 1.**

Zero-memory functions (ring_add, pure ring arithmetic) are
trivially provable pure by GCC's interprocedural analysis.
N calls with identical arguments → 1 call. Result: impossible
throughput (>10× physical clock rate). This is a measurement
bug, not a real result.

Fix patterns:

**Chain reps** (best for execution benchmarks):
```c
uint8_t p = 0;
for (int r = 0; r < REPS; r++) {
    p = stage_execute(STREAM, N_STREAM, p);  /* output feeds next input */
}
```

**Memory barrier** (best for AVX2 benchmarks):
```c
for (int r = 0; r < REPS; r++) {
    vg = ring_pass(vg, vmask);
    __asm__ volatile("" : "+x"(vg) : : );  /* force re-execution */
}
```

**Volatile sink** (for single-value benchmarks):
```c
volatile uint64_t sink = 0;
for (...) { sink ^= result; }
```

If a benchmark reports >2× the theoretical clock rate:
dead-code elimination. Fix before reporting the number.

---

## RULE 7: The Die Structure

**The die must contain the element at every position.**

Required fields in Geodie:
```c
typedef struct {
    /* Ring — temporal and shaped geostrings */
    uint64_t temporal[F12];      /* ΔDGI phase values */
    uint64_t geostring[F12];     /* shaped geostrings */
    /* Element — physically present at every position */
    int64_t  x_q32[F12];         /* x × 2^32 */
    int64_t  y_q32[F12];         /* y × 2^32 */
    uint32_t prime[F12];         /* P(k+1) */
    uint8_t  r18[F12];           /* lemniscate section */
    /* Masks — the die's cutting edges */
    uint64_t clear_mask;         /* AND: 0xFFFFFFFF00000000 */
    uint64_t keep_mask;          /* OR:  0x00000000FFFFFFFF */
    /* Instruction set — L1-resident */
    uint8_t  base_row[F12];      /* {0,1,...,143} */
    uint64_t op_vocab[F12];      /* geostring per operation */
} __attribute__((aligned(64))) Geodie;
```

Die size must be verified ≤ 32,768 bytes (L1 = 32KB).
Current verified size: 6,720 bytes (20.5% of L1).

The element is not metadata. It IS the computational context.
Every ring position IS a lemniscate coordinate.
Reporting DIE.x_q32[pos]/Q32 and DIE.y_q32[pos]/Q32 proves
the element was physically present at that ring position.

---

## RULE 8: The RAM Bus / Pipe Ingestion Model

**Legacy programs feed the die via pipe. The pipe IS the RAM bus.**

Architecture:
```
Legacy program writes runtime values to pipe
              ↓
Pipe bytes → LUT[byte % F12] → ring position
              ↓
Die processes: ring_add(pos, ring_position)
              ↓
Everything stays in the string
              ↓
peek reads result without breaking geometric flow
```

For the mapper: 7^N bytes must flow through the pipe.
Not the proxy (65898 for N=126). The actual 7^N (177+ digits).
Python computes 7^N exactly. Python writes the bytes. C die reads.

When a program captures .text:
All runs produce identical captures (code pages are COW-shared).
Primality information lives in runtime data, not static code.
Capture stack/heap values during execution, not the binary.

---

## RULE 9: Timing Stability

**Measurements need sufficient iterations for stable results.**

Minimum: each timed section takes ≥ 1ms wall clock.
Preferred: ≥ 10ms for publication-quality numbers.

If a stage rate differs by >10% between two consecutive runs:
- Increase REPS
- Check for contention (XMR node, objdump mapper running)
- Check for dead-code elimination (see Rule 6)
- Check for turbo boost artifacts (run plugged in)

Report measurements with hardware context:
- CPU model and clock (base vs boost)
- Background services (BTC node, XMR node)
- Whether mapper was paused

---

## RULE 10: The Geostring Format

**Every geostring is exactly 64 bits. Three sub-fields.**

```
[63..48]  Fc    = shell  (element identity — STATIC during traversal)
[47..32]  μop   = r18    (lemniscate section — STATIC during traversal)
[31.. 0]  ΔDGI  = phase  (temporal position — MOVES with ring)
```

Pack:   `Vgeo = ((Fc<<48) ^ (μop<<32) ^ ΔDGI) ^ TL + 1`
Peek:   `class    = vgeo >> 48`              (one shift)
        `section  = (vgeo >> 32) & 0xFF`     (one shift + mask)
        `temporal = vgeo & 0xFFFFFFFF`       (one mask)
Poke:   `vgeo = (vgeo & CLEAR_TMP) | new_temporal`  (AND + OR)

TL = 15,350,000 = 0xEA38F0 (Temporal Lock — verified constant)
F12 = 144 = lcm(18,48) = ring closure (verified constant)
DGI = 13/800 (verified: floor(1/DGI) = 61 = P(18))

ΔDGI formula (exact integer, zero float):
  `ddgi(ptr) = ptr - (ptr*13 + 799)/800`
  Verified: ddgi(4096)=4029, ddgi(8192)=8058, ddgi(16384)=16117

---

## RULE 11: The Assembly Verification Requirement

For any performance-critical loop, verify the assembly:
```bash
objdump -d <prog> | grep -A 50 "<function_name>"
```

Report:
- Conditional branches in inner loop (expect 0-1)
- Memory reads per iteration (expect 0-2)
- Whether ring_add compiled to cmov

If the assembly shows unexpected patterns, fix the source.
Do not declare a benchmark complete without checking assembly.

---

## APPLYING THIS STANDARD

At the start of any P18 session, give Claude this document.
Before submitting any code, check:
  ☐ Element used (not just stored) — Σx non-zero
  ☐ return violations (not return 0)
  ☐ Zero warnings (-Wall -Wextra)
  ☐ Zero float in hot path
  ☐ ring_add → cmov (not je/jne)
  ☐ Hot path has no function calls
  ☐ Benchmark DCE prevented
  ☐ Die contains x_q32 and y_q32
  ☐ Timing: ≥ 1ms per measurement
  ☐ Assembly verified for critical loops

Any item unchecked = violation before the program runs.

---

*P18 Coding Standard — Richard Sardini*
*Element principle: the lemniscate IS infinity.*
*The universe uses geometry, not numbers.*
