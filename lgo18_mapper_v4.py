"""
LGO-18 Geometric Mapper v4 — Parallel (4 cores × HT = 8 workers)
Richard Sardini, July 2026

The element itself: 7^N is the lemniscate at shell N.
The geometry IS the calculation — not a representation of it.
Each worker computes primality for a sub-range of the window
centered on the element 7^N.

Speedup: ~4-6× over single-process (arithmetic-heavy, HT partial benefit)

Parallelism strategy:
  - Split each candidate window into N_WORKERS sub-ranges
  - Pool workers scan sub-ranges independently (no shared state)
  - Main process merges, computes gap stats, writes results
  - All 3 sets (A, B, C) for ★ shells scanned in parallel batches

Same tier system as v3:
  ★ full:  mod-21 AND 7-smooth         — adaptive half, 3 sets
  ★ ext:   N=42p for prime p           — adaptive half, 3 sets
  · mid:   mod-21 only                 — adaptive half, 2 sets
  quick:   everything else             — quick half,    1 set
"""

import math, time, json, os, signal
from multiprocessing import Pool, cpu_count

# ── Configuration
N_WORKERS = min(8, (cpu_count() or 4))   # 4 cores × HT → 8; auto-detects
LOCK      = 8/9
LN7       = math.log(7)

print(f"LGO-18 Mapper v4  |  {N_WORKERS} workers (4-core + HT)")

# ── Primality (module-level for pickling)
_SP = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,
       73,79,83,89,97,101,103,107,109,113,127,131,137,139,149,151,
       157,163,167,173,179,181,191,193,197,199]
_MW = [2,3,5,7,11,13,17,19,23,29,31,37]

def _mr(n):
    if n < 2: return False
    for p in _SP:
        if n == p: return True
        if n % p == 0: return False
    r, d = 0, n - 1
    while d % 2 == 0: r += 1; d //= 2
    for a in _MW:
        if a >= n: continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1: continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1: break
        else: return False
    return True

def _scan_subrange(args):
    """
    Worker function: scan one sub-range of a window for primes.
    Must be module-level for multiprocessing pickling.
    The element (center) is baked into start/end — the lemniscate
    position 7^N is included in the calculation through the range.
    """
    start, end = args
    n = start if start % 2 == 1 else start + 1
    ps = []
    while n <= end:
        skip = False
        for p in _SP[1:]:          # 2 already excluded (n is odd)
            if p * p > n: break
            if n % p == 0: skip = True; break
        if not skip and _mr(n):
            ps.append(n)
        n += 2
    return ps

def _is_prime_s(n):
    """Simple primality for small n (tier classification only)."""
    if n < 2: return False
    if n < 4: return True
    if n%2==0 or n%3==0: return False
    i = 5
    while i*i <= n:
        if n%i==0 or n%(i+2)==0: return False
        i += 6
    return True

# ── Parallel window scanner — the heart of v4
def scan_parallel(center, half, pool):
    """
    Scan [center-half, center+half] using the shared pool.
    Splits the odd-number range into N_WORKERS sub-ranges.
    Includes the element (center = 7^N) by centering the window on it.
    """
    lo = max(3, center - half)
    hi = center + half
    if lo % 2 == 0: lo += 1

    # Split into N_WORKERS equal sub-ranges of odd numbers
    total_odds = (hi - lo) // 2 + 1
    chunk = max(1, (total_odds + N_WORKERS - 1) // N_WORKERS)

    ranges = []
    pos = lo
    for _ in range(N_WORKERS):
        if pos > hi: break
        end = min(pos + chunk * 2 - 2, hi)
        ranges.append((pos, end))
        pos = end + 2

    # Parallel scan — each worker handles its sub-range independently
    results = pool.map(_scan_subrange, ranges)

    # Merge (already sorted within each sub-range; merge in order)
    primes = []
    for sublist in results:
        primes.extend(sublist)
    return primes

def gap_stats(ps):
    if len(ps) < 2: return None
    r0 = r6 = r12 = other = 0
    for i in range(len(ps) - 1):
        g = ps[i+1] - ps[i]
        rv = g % 18
        if rv == 0:   r0   += 1
        elif rv == 6:  r6   += 1
        elif rv == 12: r12  += 1
        else:          other += 1
    total = r0 + r6 + r12 + other
    return {
        'n': len(ps), 'r0': r0, 'r6': r6, 'r12': r12,
        'other': other, 'total': total,
        'ratio': r0/r12 if r12 > 0 else None
    }

# ── Geometry helpers
def is_7smooth(N):
    n = N
    for p in [2,3,5,7]:
        while n % p == 0: n //= p
    return n == 1

def is_star(N):     return N%21==0 and is_7smooth(N)
def is_starx(N):
    if N%42!=0: return False
    p = N//42
    return _is_prime_s(p)
def ext_prime(N):
    if N%42!=0: return None
    p = N//42
    return p if _is_prime_s(p) else None

def elem_geo(N):
    r18 = pow(7, N, 18)   # THE ELEMENT: 7^N mod 18 = lemniscate position
    geo = {1:'crossing⊕', 7:'lobe-mid○', 13:'F7-apex◆'}[r18]
    return r18, geo

def factor_str(N):
    fs={}; n=N; d=2
    while d*d<=n:
        while n%d==0: fs[d]=fs.get(d,0)+1; n//=d
        d+=1
    if n>1: fs[n]=fs.get(n,0)+1
    return '×'.join(f'{p}^{e}' if e>1 else str(p) for p,e in sorted(fs.items()))

def predict_ext(p):
    if p==3: return 'DIP'
    return 'LOCK' if p%6==5 else 'DIP'

def adaptive_half(N): return max(80_000, int(400 * N * LN7))
def quick_half(N):    return max(30_000, int(100 * N * LN7))

# ── Files
MAP_JSON = 'lgo18_map_v4.json'
MAP_TXT  = 'lgo18_map_v4.txt'

results = json.load(open(MAP_JSON)) if os.path.exists(MAP_JSON) else {}
done = {int(k) for k in results}

if not os.path.exists(MAP_TXT):
    with open(MAP_TXT, 'w') as f:
        f.write(f"LGO-18 Mapper v4 — {N_WORKERS} workers (4-core + HT)\n")
        f.write(f"Lock={LOCK:.8f}  DGI=13/800  element=7^N\n")
        f.write(f"★=mod21+7sm  ✦=42×prime  ·=mod21  _=quick\n")
        f.write(f"{'N':>5}  {'factored':>18}  {'r18':>4}  {'tier':>6}  "
                f"{'ratio':>8}  {'Δlock':>9}  note\n")
        f.write("─"*95+"\n")

N = 126
while N in done: N += 1

running = True
def _stop(s, f):
    global running; running = False
    print("\n  Stopping after current shell...")
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

print(f"Resuming from shell {N}")
print(f"Lock = {LOCK:.6f}  |  DGI = 13/800 = {13/800}")
print(f"Element at each shell: 7^N (lemniscate center)\n")

# ── Main loop — create pool once, reuse across all shells
with Pool(processes=N_WORKERS) as pool:
    while running:
        if N in done: N += 1; continue

        star  = is_star(N)
        starx = is_starx(N) and not star
        d21   = N % 21 == 0
        r18, geo = elem_geo(N)
        fs    = factor_str(N)
        digits = len(str(7**N))
        ext_p = ext_prime(N)

        # Tier selection
        if star:
            half=adaptive_half(N); n_sets=3; tier='★full '
            offsets=[0, 3*half, -(3*half)]
        elif starx:
            half=adaptive_half(N); n_sets=3; tier='✦ext  '
            offsets=[0, 3*half, -(3*half)]
        elif d21:
            half=adaptive_half(N); n_sets=2; tier='·mid  '
            offsets=[0, -(3*half)]
        else:
            half=quick_half(N); n_sets=1; tier='quick '
            offsets=[0]

        # THE ELEMENT: 7^N is the lemniscate at shell N
        # All window centers are derived from this element
        center = 7 ** N

        t0 = time.time()
        sets = {}
        for i, off in enumerate(offsets):
            ps = scan_parallel(center + off, half, pool)
            s  = gap_stats(ps)
            if s: sets['ABC'[i]] = s
        elapsed = time.time() - t0

        ratios = [sets[s]['ratio'] for s in sets if sets[s]['ratio']]
        mean   = sum(ratios)/len(ratios) if ratios else None
        n_p    = sum(sets[s]['n'] for s in sets)

        results[str(N)] = {
            'N':N,'digits':digits,'half':half,'tier':tier,
            'r18':r18,'geo':geo,'d21':d21,'sm7':is_7smooth(N),
            'factor':fs,'ext_prime':ext_p,'mean_ratio':mean,
            'delta_lock':round(mean-LOCK,6) if mean else None,
            'is_dip':mean<LOCK if mean else False,
            'n_primes':n_p,'elapsed':round(elapsed,1),**sets
        }
        with open(MAP_JSON,'w') as f: json.dump(results,f)

        ratio_s = f'{mean:.5f}' if mean else '    --- '
        delta_s = f'{mean-LOCK:+.5f}' if mean else '       '
        tag     = '▼DIP' if (mean and mean<LOCK) else '↑   '
        note    = ''
        if star:  note = '★'
        if starx and ext_p: note = f'✦ p={ext_p}→{predict_ext(ext_p)}'
        mark = '★' if star else ('✦' if starx else ('·' if d21 else ' '))

        with open(MAP_TXT,'a') as f:
            f.write(f"{N:5d}  {fs:>18}  {r18:4d}  {tier}  "
                    f"{ratio_s}  {delta_s}  {note}\n")

        print(f"  {mark}{N:4d}  {fs:>16}  {geo:>10}  [{tier}]  "
              f"{ratio_s}  {delta_s}  {tag}  "
              f"({digits}d {n_p:,}p {elapsed:.0f}s)")

        done.add(N); N += 1

print(f"\nStopped. Results in {MAP_JSON}")
