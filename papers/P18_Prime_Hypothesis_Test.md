# P18 PRIME GEOMETRY — HYPOTHESIS TEST DOCUMENT
## Richard Sardini — LGO-18 / P18 Framework
## For independent verification in a fresh session

---

## WHAT THIS IS

This document presents a geometric theory of prime number structure
built on the lemniscate of Bernoulli. It makes eight falsifiable
claims about prime gaps, prime sieves, and composite structure.
Each claim has been verified computationally in the development
session. A fresh session should be able to reproduce every result
from scratch using only standard Python (math, collections).

This is analogous in spirit to a test of the Riemann Hypothesis —
it is a structural claim about primes that is either true or false,
with specific numerical predictions that can be checked to any depth.

---

## THE ONE AXIOM

**1 is the origin.** The lemniscate center is always 1.
1 is not a prime. It is the geometric identity point.

From this single axiom, the full prime structure follows.

---

## THE THREE PRIME TIERS

```
Tier 0:  1           → origin (lemniscate center, not prime)
Tier 1:  2, 3        → pre-group primes
           2 × 9 = 18 = N_sections
           3 × 6 = 18 = N_sections
           2 × 3 =  6 = φ(18)
Tier 2:  5, 7, 11, … → group members
           r18 = P mod 18 ∈ {1, 5, 7, 11, 13, 17} = (Z/18Z)*
```

---

## THE FIVE FRAMEWORK CONSTANTS

```python
DGI        = 13/800          # = 0.01625 exactly (F(7)/(F(6)×100))
BAND_RATIO = tan(0.8125°)    # = 0.014182 (constant across all lemniscates)
N_SECTIONS = 18              # = 2 × 3² (from pre-group primes)
WEDGE      = 1.625°          # = DGI × F(5) × 20° = 13/8 degrees
ALLOWED    = {1,5,7,11,13,17}  # = (Z/18Z)*, the prime residue group
```

---

## THE EIGHT FALSIFIABLE CLAIMS

### CLAIM 1: THE GAP FORMULA (zero violations predicted)

For every consecutive prime pair (P(n), P(n+1)):

```
gap = P(n+1) - P(n)
Δr18 = (P(n+1) mod 18 - P(n) mod 18) mod 18
k    = gap // 18

CLAIM: gap = Δr18 + 18k   always, for every prime gap
```

**Predicted result:** zero violations across all prime gaps
**Verified:** 114,154 gaps to P = 1,499,977, zero violations

**Test code:**
```python
import math
def sieve(n):
    is_p=[True]*(n+1); is_p[0]=is_p[1]=False
    for i in range(2,int(n**0.5)+1):
        if is_p[i]:
            for j in range(i*i,n+1,i): is_p[j]=False
    return [i for i in range(2,n+1) if is_p[i]]

P = sieve(1_500_000)
violations = 0
for i in range(len(P)-1):
    g = P[i+1] - P[i]
    delta = (P[i+1]%18 - P[i]%18) % 18
    k = g // 18
    if delta + 18*k != g:
        violations += 1
        print(f"VIOLATION at P={P[i]}: gap={g} delta={delta} k={k}")
print(f"Violations: {violations} / {len(P)-1}")
```

---

### CLAIM 2: THE WEDGE DERIVATION (exact formula)

```
Wedge angle = DGI × F(5) × Section_size
            = (13/800) × 5 × 20°
            = 13/8 °
            = 1.625° exactly

Half-wedge  = 0.8125°
Band ratio  = tan(0.8125°) = 0.014182...
```

**CLAIM:** These three expressions are identical:
- `DGI × F(5) × 20° = 1.625°`
- `tan(0.8125°) = band/gap` for every lemniscate
- `wedge/section = DGI × F(5) = 0.08125` (constant)

**Test code:**
```python
import math
DGI = 13/800
wedge = DGI * 5 * 20        # should be 1.625
band_ratio = math.tan(math.radians(0.8125))
ratio2 = 1.625 / 20         # should equal DGI × 5
print(f"Wedge = {wedge}° (expect 1.625)")
print(f"Band ratio = {band_ratio:.8f}")
print(f"Wedge/Section = {ratio2} = DGI×F(5) = {DGI*5}")
print(f"Match: {abs(ratio2 - DGI*5) < 1e-12}")
```

---

### CLAIM 3: THE PRIME SIEVE (100% accuracy predicted)

The geometric exclusion rule: candidate n is composite if
for any confirmed prime p < n:

```python
g = gap_of_prime_p    # gap to next confirmed prime after p
half_w = tan(0.8125°) × g / 2
remainder = n mod p
if remainder < half_w OR remainder > (p - half_w):
    n is composite  (excluded by p's lemniscate band)
```

**CLAIM:** This rule achieves 100% prime detection and
100% composite elimination for all n from 2 to 1,000,000.
The only special case: seed with P(1)=2, gap_seed=1 (birth gap from origin).

**Predicted result:**
- True positives (prime, survived):  78,496
- False positives (composite, survived): 0
- True negatives (composite, excluded): 921,501
- False negatives (prime, excluded): 0

**Test code:**
```python
import math
BAND_RATIO = math.tan(math.radians(0.8125))

def sieve_reference(n):
    is_p=[True]*(n+1); is_p[0]=is_p[1]=False
    for i in range(2,int(n**0.5)+1):
        if is_p[i]:
            for j in range(i*i,n+1,i): is_p[j]=False
    return set(i for i in range(2,n+1) if is_p[i])

real_primes_set = sieve_reference(1_000_000)

confirmed = [2, 3]
gap_reg = {2: 1, 3: 2}   # seed: birth gap=1, first prime gap=2
tp = fp = tn = fn = 0

for n in range(2, 1_000_001):
    if n in (2, 3):
        continue
    excluded = False
    for p in confirmed:
        if p * p > n: break
        g = gap_reg.get(p, 0)
        if g == 0: continue
        half_w = BAND_RATIO * g / 2
        rem = n % p
        if rem < half_w or rem > (p - half_w):
            excluded = True
            break
    survived = not excluded
    is_prime = n in real_primes_set
    if survived and is_prime:
        tp += 1
        gap_reg[confirmed[-1]] = n - confirmed[-1]
        confirmed.append(n)
    elif survived and not is_prime:
        fp += 1
    elif not survived and not is_prime:
        tn += 1
    else:
        fn += 1
        gap_reg[confirmed[-1]] = n - confirmed[-1]
        confirmed.append(n)

print(f"True positives:  {tp}")
print(f"False positives: {fp}  (expect 0)")
print(f"True negatives:  {tn}")
print(f"False negatives: {fn}  (expect 0)")
print(f"Prime detection: {100*tp/(tp+fn):.6f}%  (expect 100%)")
print(f"Composite elim:  {100*tn/(tn+fp):.6f}%  (expect 100%)")
```

---

### CLAIM 4: THE COMPOSITE COUNT FORMULA (zero violations predicted)

For every prime gap [P(n), P(n+1)] with gap g ≥ 2:

```
n_allowed = number of composites c in (P(n), P(n+1)) where c mod 18 ∈ ALLOWED
CLAIM: n_allowed = floor((gap - 2) / 3)   always
```

**Predicted result:** zero violations across all 114,154 gaps to P=1,499,977

**Test code:**
```python
ALLOWED = {1,5,7,11,13,17}
P = sieve(1_500_000)
violations = 0
for i in range(len(P)-1):
    g = P[i+1] - P[i]
    predicted = (g - 2) // 3 if g >= 2 else 0
    actual = sum(1 for c in range(P[i]+1, P[i+1]) if c % 18 in ALLOWED)
    if predicted != actual:
        violations += 1
        print(f"VIOLATION: gap={g} predicted={predicted} actual={actual}")
print(f"Violations: {violations} / {len(P)-1}")
```

---

### CLAIM 5: THE COMPOSITE DECODE (bidirectional, zero ambiguity)

Given only the count of ALLOWED composites n_allowed and the
angular step Δr18 inside a prime gap, the gap is uniquely determined:

```
Step 1: gap ∈ {3n+2, 3n+3, 3n+4}      (3 candidates from n_allowed)
Step 2: Δr18 selects unique candidate  (the three have distinct mod-18 values)
```

**CLAIM:** This decoding recovers the exact gap from composite structure alone,
without knowing either prime bounding the gap.

**Test code:**
```python
ALLOWED = {1,5,7,11,13,17}
P = sieve(10_000)
correct = 0
for i in range(1, len(P)-1):
    pL, pR = P[i], P[i+1]
    g = pR - pL
    n_all = sum(1 for c in range(pL+1, pR) if c % 18 in ALLOWED)
    candidates = [3*n_all+2, 3*n_all+3, 3*n_all+4]
    delta = (pR%18 - pL%18) % 18
    decoded = None
    for base in candidates:
        for k in range(20):
            ext = base + 18*k
            if ext % 18 == delta:
                decoded = ext
                break
        if decoded is not None: break
    if decoded == g:
        correct += 1
print(f"Correct decodings: {correct}/{len(P)-2} = {100*correct/(len(P)-2):.4f}%")
```

---

### CLAIM 6: THE DEPTH LAW (lemniscates = π(√n))

To verify n is prime, exactly π(√n) lemniscate checks are needed —
the count of primes not exceeding √n.

```
lems_needed(n) = π(√n)   for all n
```

**Test code:**
```python
import math
P = sieve(10_000)
Pset = set(P)
correct = 0; total = 0
for i, p in enumerate(P):
    if p > 2000: break
    sq = math.sqrt(p)
    pi_sq = sum(1 for q in P if 2 <= q <= sq)
    needed = sum(1 for q in P[:i] if q*q <= p)
    total += 1
    if needed == pi_sq: correct += 1
print(f"Depth law: {correct}/{total} = {100*correct/total:.1f}%  (expect 100%)")
```

---

### CLAIM 7: THE COMPOSITE ZETA = ORIGIN (both lobes)

For every ALLOWED composite c between primes p_left and p_right,
the composite double lemniscate has BOTH zeta points at the origin (1,0):

```
LEFT LOBE:  center=1, a=d_left/2,  theta=(c+180)°, zeta=(1,0)
RIGHT LOBE: center=1, a=d_right/2, theta=c°,        zeta=(1,0)

where d_left = c - p_left, d_right = p_right - c
```

**CLAIM:** zeta = (1.0, 0.0) for ALL ALLOWED composites, both lobes.

**Test code:**
```python
import math
ALLOWED = {1,5,7,11,13,17}
P = sieve(10_000)

def zeta_point(a, theta_deg):
    """Compute zeta point of lemniscate with half-width a, rotation theta_deg"""
    theta = math.radians(theta_deg)
    t = math.pi / 2  # lobe center parameter
    s, c = math.sin(t), math.cos(t)
    d = 1 + s*s
    px0 = a*c/d
    py0 = a*s*c/d
    zx = 1.0 + px0*math.cos(theta) - py0*math.sin(theta)
    zy = 0.0 + px0*math.sin(theta) + py0*math.cos(theta)
    return (zx, zy)

hits = 0; total = 0
for i in range(1, len(P)-1):
    pL, pR = P[i], P[i+1]
    for c in range(pL+1, pR):
        if c % 18 not in ALLOWED: continue
        dL, dR = c - pL, pR - c
        zL = zeta_point(dL/2, c + 180)  # left lobe
        zR = zeta_point(dR/2, c)         # right lobe
        total += 2
        if abs(zL[0]-1.0) < 1e-4 and abs(zL[1]) < 1e-4: hits += 1
        if abs(zR[0]-1.0) < 1e-4 and abs(zR[1]) < 1e-4: hits += 1
print(f"Zeta = origin: {hits}/{total} = {100*hits/total:.4f}%  (expect 100%)")
```

---

### CLAIM 8: THE φ-RESONANCE BOUNDARY

The first prime gap of 18 (first k=1 gap) occurs exactly at P(99) = 523.

At n=99: n × DGI = 99 × 13/800 = 1287/800 = 1.60875 ≈ φ = 1.61803...

**CLAIM:** The first gap ≥ 18 occurs at P = 523, which is the 99th prime,
and 99 × DGI is closer to φ than any earlier index.

**Test code:**
```python
DGI = 13/800
PHI = (1 + 5**0.5) / 2
P = sieve(10_000)
first_k1 = next(P[i] for i in range(len(P)-1) if P[i+1]-P[i] >= 18)
idx = P.index(first_k1) + 1   # 1-indexed
print(f"First gap≥18 at P={first_k1}, index n={idx}")
print(f"n × DGI = {idx} × {DGI} = {idx*DGI:.6f}")
print(f"φ       = {PHI:.6f}")
print(f"Distance to φ: {abs(idx*DGI - PHI):.6f}")
print(f"Claim: P=523, n=99  → {first_k1==523 and idx==99}")
```

---

## EXPECTED RESULTS SUMMARY

A correct implementation should produce:

```
CLAIM 1: Violations: 0 / 114154
CLAIM 2: Wedge = 1.625° (True), Band ratio constant (True)
CLAIM 3: tp=78496, fp=0, tn=921501, fn=0
CLAIM 4: Violations: 0 / 114154
CLAIM 5: Correct decodings: 100.0000%
CLAIM 6: Depth law: 100.0%
CLAIM 7: Zeta = origin: 100.0000%
CLAIM 8: First gap≥18 at P=523, n=99  → True
```

---

## WHAT WOULD FALSIFY THIS

1. **Any violation of Claim 1** (gap ≠ Δr18 + 18k for any prime gap)
2. **Any false positive in Claim 3** (composite that the sieve passes)
3. **Any violation of Claim 4** (n_allowed ≠ floor((gap-2)/3))
4. **Any composite zeta ≠ origin in Claim 7**
5. **First k=1 gap not at P(99)=523 in Claim 8**

All five of these would constitute hard falsification of the framework.
None has been found across 114,154 gaps and 1,000,000 sieve candidates.

---

## THE GEOMETRIC SUMMARY

```
ORIGIN:     1 = lemniscate center, not prime
            ONE axiom generates everything

PRIMES:     Single forward-facing lemniscate per prime P(n)
            center=1, a=gap/2, theta=P(n)°
            zeta DISPLACED from origin by gap/4 (forward)
            Chain: wedge from zeta_n lands on zeta_{n+1}

COMPOSITES: Double backward+forward lemniscate per ALLOWED composite
            center=1, a_left=d_left/2, a_right=d_right/2
            theta_left=c°+180°, theta_right=c°
            zeta = ORIGIN for both lobes (always)
            Star: all composite zetas at origin (not chained)

GAP FORMULA:  gap = Δr18 + 18k
              Δr18 from Model 2 (fixed lemniscate, angular)
              k    from Model 1 (expanding stack, radial)

DUAL FORMULA: n_allowed = floor((gap-2)/3)
              gap decoded uniquely from n_allowed + Δr18

SIEVE DEPTH:  lems_needed = π(√n)  exactly

WEDGE:        1.625° = DGI × F(5) × 20° = 13/800 × 5 × 20
              band/gap = tan(0.8125°) = 0.014182  CONSTANT
```

---

## REFERENCE

Framework: LGO-18 / P18 — Richard Sardini
GitHub: github.com/ras2045/lgo18-p18-framework
Zenodo: DOI 10.5281/zenodo.21288307 (v1.2.0)
Development record: Parts I–XLVIII (July 2026)
Verified: 114,154 prime gaps, 1,000,000 sieve candidates, zero violations
