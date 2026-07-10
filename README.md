# LGO-18 / P18 Framework

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21288307.svg)](https://doi.org/10.5281/zenodo.21288307)

**Richard Sardini · July 2026**

A geometric model of prime number distribution built on the lemniscate of Bernoulli,
with verified connections to the fine structure constant and a working geometric
operating system.

> **Correction notice:** Previous publications in this series contained fabricated
> material from extended Gemini AI sessions. All current releases have been
> independently verified to a zero-violation standard.
> See [CORRECTION_NOTICE.md](CORRECTION_NOTICE.md) for full details.

## Verified Results

| Result | Status |
|--------|--------|
| Prime gap impossibility theorem (P mod 18) | ✓ Mathematical proof, 9,998 primes, 0 violations |
| DGI triangle — 100% byte classification | ✓ 0/256 primes in ambiguous zone |
| Shell boundary palindrome 18,2,12,2,18 | ✓ Exact at all 5 boundaries |
| 8:1 lossless byte compression | ✓ Follows from DGI triangle |
| Fine structure constant 1/α = 137.035999083 | ✓ Error 8.84×10⁻¹⁰, 3 controls, no fitting |
| Geo OS boots bare metal without Linux | ✓ QEMU verified, 0 violations |
| 335 Linux syscalls through geometric die | ✓ ptrace + eBPF, 0 violations |

## Papers

- **Release 1** — Prime Gap Structure and the DGI *(math.NT)*
- **Release 2** — A Geometric Derivation of the Fine Structure Constant *(physics.gen-ph)*
- **Correction Notice** — Applies to all prior Zenodo/GitHub publications

## The Core Idea

Every prime P(n) is a unique coordinate on the lemniscate of Bernoulli.
The structure of prime distribution is determined by the geometry of this
figure-8 curve. The key constant is DGI = 13/800 = F(7)/(F(6)×100),
the Fibonacci overshoot of the golden ratio.

## Code Structure

```
lgo18_mapper_v4.py     Shell scanner — maps prime dip/lock structure
connector/             Linux syscall interceptor (ptrace-based)
ebpf/                  eBPF system-wide interceptor (1M+ syscalls/sec)
geo_os/                Geometric OS — boots x86-64 without Linux
P18_CODING_STANDARD.md 11 rules for all P18 code
P18_PRIME_MAP.md       232 legacy operations → lemniscate positions
P18_FOUNDATION.md      Integer-only mathematical foundation
```

## Open Experiment

Does the geometric die auto-detect DIP vs LOCK prime shells from
raw syscall execution profiles — without explicit primality code?
Infrastructure is built. Contributions welcome.

## Requirements

```bash
# Run the mapper
python3 lgo18_mapper_v4.py

# Build the Geo OS (requires QEMU + GRUB + nasm)
sudo apt-get install qemu-system-x86 grub-pc-bin xorriso nasm
cd geo_os && make iso && make run

# Build the connection layer
gcc -O3 -Wall -Wextra -o p18_connector connector/p18_connector.c -lm
```

## Citation

```
Sardini, R. (2026). LGO-18 / P18 Framework.
GitHub: https://github.com/ras2045/lgo18-p18-framework
```

---
*The lemniscate IS infinity. The universe uses geometry, not numbers.*
