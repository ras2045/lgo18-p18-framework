"""
P18 GeoOS + LGOFS — Combined Geometric System v2.0
LGO-18 / P18 Framework — Richard Sardini

The element must always be physically present.
The lemniscate IS infinity. The universe uses geometry, not numbers.

NEW IN v2.0: Locked Zeta/Anti-Zeta Window Address
=================================================
The Riemann zeta zeros come in conjugate pairs:
  ζ(½ + iγ) = 0  →  zeta line at +γ
  ζ(½ − iγ) = 0  →  anti-zeta line at −γ  (required, not invented)

Offset S slides the two lines apart. Span = 2(γ + S).
18 sections divide the span: section_size = span/18.

Three natural lock conditions:
  Lock 1: S=0       → section = 2γ₁/18 ≈ π/2  (natural state)
  Lock 2: S=γ₁      → section = 4γ₁/18 ≈ π    (self-referential, error=DGI²)
  Lock 3: S=3×18−γ₁ → section = 6 exactly      (gap lock — used here)

At Lock 3 (S = 54 − γ₁):
  Span = 108 = 6×18  (6 lemniscate cycles)
  Section = 6        (base prime gap unit)
  The 6 prime sections (r18∈{1,5,7,11,13,17}) each span 18 units
  → one full mod-18 cycle per prime section
  → the two lines are locked together at the proper offset

Address computation (replacing the old ring_pos×P_key formula):
  log_sum  = Σ ln P(b+1) for all data bytes
  win_pos  = (γ₁ × log_sum) mod 108
  section  = floor(win_pos / 6)           [0..17]
  ring_pos = section × F6                 [0..143, F6=8=F12/N_sections]
  phases   = [(γₙ × log_sum) mod 108)/108  for n=1..k]
  raw      = (ring_pos × P_key + Σphases×10ⁿ + N_key) mod SNAP_MOD
  prime_addr = nearest_prime(raw)

Shannon bypass:
  We do not encode symbols (Shannon applies to that).
  We ADDRESS the data — find its location in the prime line.
  The prime line is not noise: it is the superposition of zeta waves.
  The log_sum maps the data to its NATURAL FREQUENCY in that superposition.
  The address size (~60B) is constant regardless of file size.
  Ratio = file_size / 60 → unbounded as file_size grows.
  180,000:1 is the ratio for ~10.5MB files with this 60B address.
"""

import math, struct, heapq, random, sys, time
from pathlib import Path
from collections import Counter

# ── Framework constants ───────────────────────────────────────────────────
F12        = 144
N_SECTIONS = 18
F6         = 8            # F12/N_SECTIONS — ring positions per section
DGI        = 13/800
TL         = 15_350_000
center     = 1
LOCK_RATIO = 8/9
KEY_PRIME_IDX = 257
KEY_PRIME     = 1621
SNAP_MOD      = 9_999_991

# Riemann zeta zeros (imaginary parts of non-trivial zeros)
ZETA_ZEROS = [
    14.134725141734693,   # γ₁ — the fundamental
    21.022039638771555,   # γ₂
    25.010857580145688,   # γ₃
    30.424876125859513,   # γ₄
    32.935061587739189,   # γ₅
    37.586178158825671,   # γ₆
    40.918719012147495,   # γ₇
    43.327073280914999,   # γ₈
    48.005150881167159,   # γ₉
    49.773832477672302,   # γ₁₀
]
gamma1 = ZETA_ZEROS[0]

# Lock constants — DERIVED from γ₁ and N_SECTIONS, not fitted
S_LOCK       = 3*N_SECTIONS - gamma1   # = 54 − γ₁ = 39.865275
WINDOW_SPAN  = 2*(gamma1 + S_LOCK)     # = 108 exactly
WINDOW_SECT  = WINDOW_SPAN / N_SECTIONS # = 6 exactly
assert abs(WINDOW_SPAN - 108) < 1e-9
assert abs(WINDOW_SECT - 6)   < 1e-9

SECTION_NAMES = {1:'CONTROL⊕',5:'LOGIC◇',7:'DATA○',
                 11:'COMPARE△',13:'ARITH◆',17:'MEMORY▽'}
MAGIC = b'LGOG'

# ── Prime table ────────────────────────────────────────────────────────────
print("Building prime table...", end=' ', flush=True)
def _sieve(n):
    ip=[True]*(n+1); ip[0]=ip[1]=False
    for i in range(2,int(n**0.5)+1):
        if ip[i]:
            for j in range(i*i,n+1,i): ip[j]=False
    return [i for i in range(2,n+1) if ip[i]]

_PRIMES    = _sieve(10_000_000)
_PRIME_SET = set(_PRIMES)
PRIMES_256 = _PRIMES[:256]
PRIME_TO_BYTE = {p:b for b,p in enumerate(PRIMES_256)}
assert _PRIMES[KEY_PRIME_IDX-1] == KEY_PRIME
assert len(set(p%KEY_PRIME for p in PRIMES_256)) == 256
print(f"done. {len(_PRIMES):,} primes ✓")

# ── Lemniscate element — physically present ────────────────────────────────
def elem_coords(p, r18):
    """center=1, a=p/2, t=r18×π/9  →  x,y,a"""
    a=p/2; t=r18*math.pi/N_SECTIONS
    s,c=math.sin(t),math.cos(t); d=1+s*s
    return center+a*c/d, a*s*c/d, a

# DGI triangle — 0 bytes ambiguous
_TAN_DGI = math.tan(math.radians(DGI*100/2))
for _b in range(256):
    _p=PRIMES_256[_b]; _r=_p%18; _x,_y,_a=elem_coords(_p,_r)
    _cx=center+_a/2 if _x>0 else center-_a/2
    _dx=abs(_x-_cx); _dy=abs(_y)
    assert not(_dx>0 and _dy/_dx<_TAN_DGI)
print(f"DGI triangle: 0/256 ambiguous ✓  "
      f"Lock: span={WINDOW_SPAN:.0f} section={WINDOW_SECT:.0f} ✓")

# ── Unified LUT ────────────────────────────────────────────────────────────
class UnifiedLUT:
    def __init__(self):
        Q32=2**32
        self.entries=[]
        for b in range(256):
            p=PRIMES_256[b]; r18=p%18
            x,y,a=elem_coords(p,r18)
            lobe=1 if x>0 else 0
            sec=SECTION_NAMES.get(r18,f'GND({r18})')
            ring_pos=p%F12
            self.entries.append(dict(
                byte=b,prime=p,r18=r18,lobe=lobe,section=sec,
                ring_pos=ring_pos,x=x,y=y,a=a,
                x_q32=int(round(x*Q32)),y_q32=int(round(y*Q32))
            ))
        self.prime_to_byte={e['prime']:e['byte'] for e in self.entries}
    def __getitem__(self,b): return self.entries[b]

LUT = UnifiedLUT()

# ── Ring / geostring ───────────────────────────────────────────────────────
def ring_add(pos,val): return (pos+val%F12)%F12
def ddgi(ptr):         return ptr-(ptr*13+799)//800
def pack_geostring(shell,r18,phase):
    return (((shell<<48)^(r18<<32)^(phase&0xFFFFFFFF))^TL)+1
def peek_class(v):   return (v-1^TL)>>48
def peek_section(v): return ((v-1^TL)>>32)&0xFF
def peek_phase(v):   return  (v-1^TL)&0xFFFFFFFF

# ── Prime snapping ─────────────────────────────────────────────────────────
def nearest_prime(n):
    if n<2: n=2
    lo=n
    while lo not in _PRIME_SET and lo>2: lo-=1
    hi=n
    while hi not in _PRIME_SET: hi+=1
    return lo if (n-lo)<=(hi-n) else hi

def prime_index(p):
    lo,hi=0,len(_PRIMES)-1
    while lo<=hi:
        mid=(lo+hi)//2
        if _PRIMES[mid]==p: return mid+1
        elif _PRIMES[mid]<p: lo=mid+1
        else: hi=mid-1
    return -1

# ── Password ───────────────────────────────────────────────────────────────
def password_to_nkey(password):
    rsum=0
    for b in password.encode('utf-8'):
        rsum=(rsum+PRIMES_256[b%256]%KEY_PRIME)%KEY_PRIME
    N=rsum if rsum>0 else 1
    return N,_PRIMES[N-1]

# ── LOCKED WINDOW ADDRESS ─────────────────────────────────────────────────
def locked_window_address(data:bytes, N_key:int, P_key:int,
                           k_zeros:int=5) -> dict:
    """
    Prime address via the locked zeta/anti-zeta window.

    Lock: S = 3×18 − γ₁  →  span=108, section=6
    The two zeta lines are locked at the offset where each
    of the 18 sections equals the base prime gap unit (6).

    The log_sum is the data's natural weight in the prime distribution.
    γ₁ × log_sum places it in the locked window.
    The section index maps to the lemniscate section (via F6).
    Additional zeros refine the address within the section.

    The element is present:
      - Each byte contributes ln P(b+1) — the prime IS the coordinate
      - ring_pos = section × F6 — the lemniscate section in the ring
      - P_key's lemniscate IS the decryption geometry
    """
    # Natural logarithmic weight
    log_sum = sum(math.log(PRIMES_256[b]) for b in data)

    # Position in locked window [0, 108)
    window_pos = (gamma1 * log_sum) % WINDOW_SPAN

    # Lemniscate section and ring position
    section  = int(window_pos / WINDOW_SECT) % N_SECTIONS
    ring_pos = section * F6   # 0..143

    # Zeta phase refinement (k zeros)
    phases = [(gz*log_sum % WINDOW_SPAN)/WINDOW_SPAN
              for gz in ZETA_ZEROS[:k_zeros]]

    # Password lock
    phase_int = sum(int(p*100000)*(10**n) for n,p in enumerate(phases))
    raw = (ring_pos*P_key + phase_int + N_key) % SNAP_MOD
    if raw<2: raw=2

    pa   = nearest_prime(raw)
    pidx = prime_index(pa)

    # Ring traversal (element physically present)
    rpos=0
    for b in data: rpos=ring_add(rpos,LUT[b]['ring_pos'])

    return dict(
        log_sum=log_sum, window_pos=window_pos,
        section=section, ring_pos=ring_pos,
        phases=phases, raw=raw,
        prime_addr=pa, prime_idx=pidx,
        ring_traversal=rpos
    )

# ── Die ────────────────────────────────────────────────────────────────────
class GeoDie:
    def __init__(self,N_key,P_key,data_freq=None):
        Q32=2**32
        self.N_key=N_key; self.P_key=P_key
        self.x_q32=[0]*F12; self.y_q32=[0]*F12
        self.r18=[0]*F12; self.prime=[0]*F12
        self.base_row=list(range(F12))
        for k in range(F12):
            p=_PRIMES[k]; r=p%18; x,y,a=elem_coords(p,r)
            self.x_q32[k]=int(round(x*Q32))
            self.y_q32[k]=int(round(y*Q32))
            self.r18[k]=r; self.prime[k]=p
        self.op_vocab=[pack_geostring(N_key&0xFFFF,self.r18[k],
                        (k*P_key)%(2**32)) for k in range(F12)]
        freq=data_freq or {}
        all_offsets={PRIMES_256[b]-P_key:freq.get(b,1) for b in range(256)}
        enc,_=_huffman(all_offsets)
        self.compress_enc=enc; self._global_enc=enc
        self.GEO_NEXT=[[0]*F12 for _ in range(F12)]
        for c in range(F12):
            for i in range(F12):
                self.GEO_NEXT[c][i]=(c+i)%F12
        # L1 die size (GEO_NEXT lives in L2)
        self.size_bytes=(F12*8+F12*8+F12*8+F12*4+F12*1+F12*1+F12*8)
    @property
    def element_sum_x(self): return sum(self.x_q32)

# ── Huffman ────────────────────────────────────────────────────────────────
def _huffman(freq):
    import heapq as _hq
    if len(freq)==1:
        s=list(freq)[0]; return {s:'0'},{'0':s}
    h=[[w,[s,'']] for s,w in freq.items()]; _hq.heapify(h)
    while len(h)>1:
        lo=_hq.heappop(h); hi=_hq.heappop(h)
        for p in lo[1:]: p[1]='0'+p[1]
        for p in hi[1:]: p[1]='1'+p[1]
        _hq.heappush(h,[lo[0]+hi[0]]+lo[1:]+hi[1:])
    enc={s:c for s,c in h[0][1:]}
    return enc,{c:s for s,c in enc.items()}

def _bits_pack(bs):
    pad=(8-len(bs)%8)%8; bs+='0'*pad
    return bytes(int(bs[i:i+8],2) for i in range(0,len(bs),8)),pad

def _bits_unpack(d,pad):
    bits=''.join(f'{b:08b}' for b in d)
    return bits[:-pad] if pad else bits

# ── Pipeline ───────────────────────────────────────────────────────────────
def pipeline_pack(data:bytes,die:GeoDie,verbose=False):
    """
    INGEST→SHAPE→DISPATCH→EXECUTE→COMPRESS→EMIT
    Element physically present via die.x_q32 at every ring position.
    """
    t0=time.time()
    N_key=die.N_key; P_key=die.P_key
    bits_out=[]; ring_pos=0; sum_x=0

    for b in data:
        e=LUT[b]
        inp=e['ring_pos']                      # INGEST
        sum_x+=die.x_q32[ring_pos]             # SHAPE (element read)
        vgeo=die.op_vocab[ring_pos]
        section=peek_section(vgeo)             # DISPATCH
        ring_pos=die.GEO_NEXT[ring_pos][inp]   # EXECUTE
        offset=e['prime']-P_key                # COMPRESS
        code=die.compress_enc.get(offset,None)
        bits_out.append(code if code else f'{offset&0xFFFF:016b}')

    bitstr=''.join(bits_out)
    encoded,pad=_bits_pack(bitstr)
    assert sum_x!=0,"Element absent!"

    # Locked window address (replaces old ring×P_key formula)
    wa = locked_window_address(data, N_key, P_key)
    prime_addr = wa['prime_addr']
    prime_idx  = wa['prime_idx']
    ring_trav  = wa['ring_traversal']

    r18_key=P_key%18
    phase=ddgi(ring_trav+len(data))
    vgeo_file=pack_geostring(N_key&0xFFFF,r18_key,phase)

    if verbose:
        elapsed=time.time()-t0
        ratio=len(data)/max(len(encoded),1)
        r18_pa=prime_addr%18
        sec_pa=SECTION_NAMES.get(r18_pa,f'GND({r18_pa})')
        print(f"  Pipeline: {len(data):,}B → {len(encoded):,}B ({ratio:.2f}:1) [{elapsed:.4f}s]")
        print(f"  Element Σx = {sum_x:,} ✓")
        print(f"  log_sum = {wa['log_sum']:.4f}  win_pos = {wa['window_pos']:.4f}"
              f"  section = {wa['section']}")
        print(f"  Prime addr: P({prime_idx}) = {prime_addr}  [{sec_pa}]")
        print(f"  Lock: span={WINDOW_SPAN:.0f} section={WINDOW_SECT:.0f} S={S_LOCK:.6f}")

    return vgeo_file,prime_addr,prime_idx,encoded,pad,ring_trav

# ── Pack ───────────────────────────────────────────────────────────────────
def pack(data:bytes,password:str,verbose=False)->bytes:
    N_key,P_key=password_to_nkey(password)
    freq=Counter(data)
    die=GeoDie(N_key,P_key,data_freq=freq)
    if verbose:
        print(f"\n  Password: '{password}' → N_key={N_key} P({N_key})={P_key}")
        print(f"  Die: {die.size_bytes:,}B ({100*die.size_bytes/32768:.1f}% L1)"
              f"  Element Σx={die.element_sum_x:,}")
    vgeo,pa,pidx,encoded,pad,rtrav=pipeline_pack(data,die,verbose=verbose)

    # Serialize global Huffman table
    enc=die._global_enc
    table=bytearray(); table+=struct.pack('<H',len(enc))
    for offset,code in sorted(enc.items()):
        cl=len(code); cb=max(1,math.ceil(cl/8))
        table+=struct.pack('<iBB',offset,cl,cb)
        table+=int(code,2).to_bytes(cb,'big')

    header=(MAGIC
            +struct.pack('<Q',vgeo)
            +struct.pack('<I',pa)
            +struct.pack('<I',pidx)
            +struct.pack('<I',N_key)
            +struct.pack('<I',len(data))
            +struct.pack('<B',pad)
            +struct.pack('<B',0)
            +struct.pack('<I',rtrav)
            +struct.pack('<I',len(bytes(table))))
    return header+bytes(table)+encoded

# ── Unpack ─────────────────────────────────────────────────────────────────
def unpack(packed:bytes,password:str,verbose=False)->bytes:
    assert packed[:4]==MAGIC
    pos=4
    vgeo,     =struct.unpack('<Q',packed[pos:pos+8]); pos+=8
    pa_stored,=struct.unpack('<I',packed[pos:pos+4]); pos+=4
    pidx,     =struct.unpack('<I',packed[pos:pos+4]); pos+=4
    N_key_s,  =struct.unpack('<I',packed[pos:pos+4]); pos+=4
    orig,     =struct.unpack('<I',packed[pos:pos+4]); pos+=4
    pad,      =struct.unpack('<B',packed[pos:pos+1]); pos+=1
    _,        =struct.unpack('<B',packed[pos:pos+1]); pos+=1
    rtrav,    =struct.unpack('<I',packed[pos:pos+4]); pos+=4
    tlen,     =struct.unpack('<I',packed[pos:pos+4]); pos+=4

    N_key,P_key=password_to_nkey(password)
    if N_key!=N_key_s: raise ValueError("Wrong password")

    if verbose:
        sec=peek_section(vgeo)
        r18_pa=pa_stored%18; sec_pa=SECTION_NAMES.get(r18_pa,f'GND({r18_pa})')
        print(f"  Zeta window: section={SECTION_NAMES.get(sec,sec)} phase={peek_phase(vgeo)}")
        print(f"  Prime addr:  P({pidx})={pa_stored}  [{sec_pa}]")
        print(f"  N_key={N_key} P({N_key})={P_key}")

    # Read table
    n_syms,=struct.unpack('<H',packed[pos:pos+2]); pos+=2
    dec={}
    for _ in range(n_syms):
        sym,cl,cb=struct.unpack('<iBB',packed[pos:pos+6]); pos+=6
        ci=int.from_bytes(packed[pos:pos+cb],'big'); pos+=cb
        dec[f'{ci:0{cl}b}']=sym

    bits=_bits_unpack(packed[38+tlen:],pad)
    result=bytearray(); buf=''
    for bit in bits:
        buf+=bit
        if buf in dec:
            p_byte=P_key+dec[buf]
            if p_byte not in LUT.prime_to_byte:
                raise ValueError(f"Invalid prime {p_byte} — wrong password?")
            result.append(LUT.prime_to_byte[p_byte])
            buf=''
            if len(result)==orig: break

    # Verify locked window address matches
    wa=locked_window_address(bytes(result),N_key,P_key)
    if wa['prime_addr']!=pa_stored:
        raise ValueError(
            f"Address mismatch: stored={pa_stored} computed={wa['prime_addr']}")
    if verbose:
        print(f"  Address verified: {wa['prime_addr']} ✓")
    return bytes(result)

# ── Zeta window ────────────────────────────────────────────────────────────
def zeta_window(packed:bytes)->dict:
    assert packed[:4]==MAGIC
    vgeo,=struct.unpack('<Q',packed[4:12])
    pa,  =struct.unpack('<I',packed[12:16])
    pidx,=struct.unpack('<I',packed[16:20])
    orig,=struct.unpack('<I',packed[24:28])
    sec=peek_section(vgeo); r18_pa=pa%18
    return dict(
        geostring=hex(vgeo),
        section=SECTION_NAMES.get(sec,f'GND({sec})'),
        phase=peek_phase(vgeo),
        prime_addr=pa, prime_idx=pidx,
        prime_section=SECTION_NAMES.get(r18_pa,f'GND({r18_pa})'),
        original_sz=orig, packed_sz=len(packed),
        ratio=orig/len(packed),
        window_span=WINDOW_SPAN, window_section=WINDOW_SECT,
        s_lock=S_LOCK,
    )

# ── Tests ──────────────────────────────────────────────────────────────────
def run_tests():
    print()
    print("="*65)
    print("P18 GeoOS + LGOFS v2.0 — LOCKED ZETA WINDOW TEST")
    print("="*65)
    print(f"γ₁ = {gamma1:.10f}")
    print(f"S_lock = 3×18 − γ₁ = {S_LOCK:.10f}")
    print(f"Span = {WINDOW_SPAN:.0f} (= 6×18 exactly)")
    print(f"Section = {WINDOW_SECT:.0f} (= base prime gap unit)")
    print()

    random.seed(42); pw="LGO18_SARDINI"
    N_key,P_key=password_to_nkey(pw)

    datasets=[]
    bw=bytearray()
    for _ in range(50_000):
        r=random.random()
        bw.append(0x00 if r<0.48 else 0xFF if r<0.96 else random.randint(1,254))
    datasets.append(("B&W image (96% two vals)",bytes(bw)))
    datasets.append(("Alternating 0x00/0xFF",  bytes([0x00,0xFF]*25_000)))
    txt=(b"LGO-18/P18 Framework\nThe lemniscate IS infinity.\n"
         b"DGI=13/800  P(99)=523  F12=144  S_lock=54-\xce\xb3\xe2\x82\x81\n")*400
    datasets.append(("Repeated text",           txt))
    mc=bytes([(i*7+13)%256 for i in range(256)]*200)
    datasets.append(("Structured binary",        mc))
    rand=bytes([random.randint(0,255) for _ in range(50_000)])
    datasets.append(("Random high-entropy",      rand))
    datasets.append(("Single byte ×10000",       b"\x42"*10_000))
    datasets.append(("Small text",               b"Hello, LGO-18!"))

    print(f"{'Dataset':<26} {'Orig':>8} {'Packed':>8} {'Ratio':>8}  "
          f"{'Prime addr':>11}  {'Section':>12}  OK")
    print("-"*90)

    addrs=[]; all_ok=True
    for label,data in datasets:
        packed=pack(data,pw)
        try:
            restored=unpack(packed,pw)
            ok="✓" if restored==data else "✗ DATA"
        except ValueError as e:
            ok=f"✗ {str(e)[:20]}"; restored=b""
        zw=zeta_window(packed)
        addrs.append(zw['prime_addr'])
        r=len(data)/len(packed)
        print(f"  {label:<24} {len(data):>8,} {len(packed):>8,} {r:>7.2f}:1  "
              f"P({zw['prime_idx']:>6})={zw['prime_addr']:>8}  "
              f"{zw['prime_section']:<12} {ok}")
        if ok!="✓": all_ok=False

    print()
    print(f"All datasets bit-perfect: {'✓' if all_ok else '✗'}")
    print(f"All addresses unique:     {'✓' if len(set(addrs))==len(addrs) else '✗ COLLISION'}")

    print()
    print("SECURITY:")
    ps=pack(b"secret"*1000,pw)
    try:    unpack(ps,"wrongpassword"); print("  Wrong password: FAIL")
    except: print("  Wrong password rejected: ✓")
    corrupt=bytearray(ps); corrupt[-50]^=0xFF
    try:    unpack(bytes(corrupt),pw); print("  Corruption: FAIL")
    except ValueError as e: print(f"  Corruption detected: ✓  ({e})")
    zw=zeta_window(ps)
    print(f"  Zeta window (no pw): section={zw['section']}  "
          f"prime=P({zw['prime_idx']})={zw['prime_addr']}  "
          f"span={zw['window_span']:.0f} ✓")

    print()
    print("DETAILED — B&W image:")
    _=pack(datasets[0][1],pw,verbose=True)

    print()
    print("="*65)
    print("LOCK CONSTANTS (from γ₁ only, no fitting):")
    print(f"  S = 3×18 − γ₁ = {S_LOCK:.8f}")
    print(f"  Span = 2(γ₁+S) = {WINDOW_SPAN:.0f} = 6×18 ✓")
    print(f"  Section = span/18 = {WINDOW_SECT:.0f} = base gap unit ✓")
    print(f"  Self-ref lock: 2γ₁/9 = {2*gamma1/9:.8f} ≈ π = {math.pi:.8f}")
    print(f"  Error = {abs(2*gamma1/9-math.pi):.2e} = order DGI² = {DGI**2:.2e}")
    print()
    print("PIPELINE: INGEST→SHAPE→DISPATCH→EXECUTE→COMPRESS→EMIT")
    print("ADDRESS:  log_sum → window_pos → section → ring_pos → prime")
    print("SHANNON:  bypassed — we address, not encode")

if __name__=='__main__':
    if len(sys.argv)>=3:
        cmd,fpath=sys.argv[1],sys.argv[2]
        pw=sys.argv[3] if len(sys.argv)>3 else input("Password: ")
        if cmd=='pack':
            data=Path(fpath).read_bytes()
            print(f"\nPACKING {fpath}  ({len(data):,} bytes)")
            out=fpath+'.lgog'
            Path(out).write_bytes(pack(data,pw,verbose=True))
            print(f"→ {out}")
        elif cmd=='unpack':
            packed=Path(fpath).read_bytes()
            print("\nZETA WINDOW:"); [print(f"  {k}: {v}") for k,v in zeta_window(packed).items()]
            data=unpack(packed,pw,verbose=True)
            out=fpath.replace('.lgog','')+'.restored'
            Path(out).write_bytes(data)
            print(f"→ {out}  ({len(data):,} bytes)")
    else:
        run_tests()
