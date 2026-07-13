"""
P18 Index-Delta Geo Vector Pack v2.0
LGO-18 / P18 Framework — Richard Sardini

CORRECTED: P(1)=1 (Richard's model — geometrically correct)

Byte table: {1, 2, 3, 5, 7, 11, ..., 1613}  (256 entries)
  byte 0x00 → value 1  → window pos = 0.000000 EXACTLY (the origin)
  byte 0x01 → value 2  → window pos = γ₁×log(2) = 9.797
  byte 0xFF → value 1613 → window pos = 104.397
  
Key prime: 1619 (first prime > 1613, r18=17 MEMORY▽)
  Unique residues mod 1619: 256/256 ✓

CORRECTED SCALE CONSTANTS:
  C_bit    = DGI × 5π/18              = 0.01418080
  C_byte   = γ₁ × log(P_R(256)) / 255 = 0.40939990
  C_header = F6² × C_byte              = 26.201594
  SPAN     = 108 (= 6×18, locked window)
  P_R(1)=1 → window pos = 0 (the padding origin, exact)

The 0x00 byte IS the geometric center: log(1)=0 → window=0.
Null padding contributes ZERO to the log_sum — geometrically exact.
All other bytes have strictly positive window positions.

THREE VALUES TO UNPACK:
  1. start_byte — first byte (0x00 → the origin)
  2. delta stream — Huffman-coded byte differences
  3. win_sec — zeta window section (file type, readable w/o decode)

RECONSTRUCTION: b_i = (b_{i-1} + delta_i) mod 256  (integer addition only)
"""

import math, struct, heapq, sys
from pathlib import Path
from collections import Counter

# ── Framework constants ───────────────────────────────────────────────────
gamma1   = 14.134725141734693
DGI      = 13/800
phi      = (1+math.sqrt(5))/2
N_SEC    = 18
F6       = 8
F12      = 144
SPAN     = 108.0

# Scale constants — lemniscate fixed points, computed once
C_BIT    = DGI * 5*math.pi/18
C_BYTE   = gamma1 * math.log(1613) / 255   # Richard's model: log(P_R(256))/255
C_HEADER = F6**2 * C_BYTE
KEY_PRIME = 1619   # first prime > 1613, r18=17

MAGIC = b'LGI2'

# ── Build Richard's prime table ────────────────────────────────────────────
print("Building prime table (Richard's model: P(1)=1)...", end=' ', flush=True)

def _sieve(n):
    ip=[True]*(n+1); ip[0]=ip[1]=False
    for i in range(2,int(n**0.5)+1):
        if ip[i]:
            for j in range(i*i,n+1,i): ip[j]=False
    return [i for i in range(2,n+1) if ip[i]]

_PRIMES_STD = _sieve(1700)
PRIMES_R    = [1] + _PRIMES_STD[:255]   # {1,2,3,5,...,1613}
PRIME_TO_BYTE_R = {p:b for b,p in enumerate(PRIMES_R)}

# Verify key properties
assert len(PRIMES_R) == 256
assert PRIMES_R[0] == 1
assert PRIMES_R[-1] == 1613
assert len(set(p % KEY_PRIME for p in PRIMES_R)) == 256, "Residue collision!"
print(f"done. {len(PRIMES_R)} entries. Key prime={KEY_PRIME} ✓")

# ── Lemniscate element ────────────────────────────────────────────────────
def _elem_coords(p, r18):
    if p <= 0: return 1.0, 0.0, 0.0
    a=p/2; t=r18*math.pi/N_SEC
    s,c=math.sin(t),math.cos(t); d=1+s*s
    return 1+a*c/d, a*s*c/d, a

# DGI triangle — 0 ambiguous (skip p=1 which is the center)
_TAN_DGI = math.tan(math.radians(DGI*100/2))
for _b in range(1, 256):  # skip b=0 (p=1, center)
    _p=PRIMES_R[_b]; _r=_p%18
    _x,_y,_a=_elem_coords(_p,_r)
    _cx=1+_a/2 if _x>0 else 1-_a/2
    _dx=abs(_x-_cx); _dy=abs(_y)
    assert not(_dx>0 and _dy/_dx<_TAN_DGI), f"byte {_b} in DGI triangle!"
print(f"DGI triangle: 0/255 non-anchor bytes ambiguous ✓")

# ── Window section LUT ────────────────────────────────────────────────────
def _win_sec(b: int) -> int:
    """Zeta window section. 0x00 → section 0 exactly (the origin)."""
    p = PRIMES_R[b]
    if p <= 1: return 0   # log(1)=0 → window pos 0 → section 0
    return int((gamma1 * math.log(p)) % SPAN / 6) % N_SEC

def _lobe(b: int) -> int:
    p = PRIMES_R[b]; r18 = p % 18
    if p <= 1: return 1   # center: x=1 > 0 → right lobe
    x,_,_ = _elem_coords(p, r18)
    return 1 if x > 0 else 0

WIN_SEC = [_win_sec(b) for b in range(256)]
LOBE    = [_lobe(b)    for b in range(256)]

# Verify 0x00 → window section 0 exactly
assert WIN_SEC[0] == 0, f"0x00 window section should be 0, got {WIN_SEC[0]}"
print(f"0x00 → window section 0 (exact origin) ✓")
print(f"Scale constants: C_bit={C_BIT:.6f}  C_byte={C_BYTE:.6f}  "
      f"C_header={C_HEADER:.4f}")
print()

# ── Huffman ────────────────────────────────────────────────────────────────
def _huff_build(freq):
    if len(freq)==1:
        s=list(freq)[0]; return {s:'0'},{'0':s}
    h=[[w,[s,'']] for s,w in freq.items()]; heapq.heapify(h)
    while len(h)>1:
        lo=heapq.heappop(h); hi=heapq.heappop(h)
        for p in lo[1:]: p[1]='0'+p[1]
        for p in hi[1:]: p[1]='1'+p[1]
        heapq.heappush(h,[lo[0]+hi[0]]+lo[1:]+hi[1:])
    enc={s:c for s,c in h[0][1:]}
    return enc,{c:s for s,c in enc.items()}

def _bits_pack(bs):
    pad=(8-len(bs)%8)%8; bs+='0'*pad
    return bytes(int(bs[i:i+8],2) for i in range(0,len(bs),8)), pad

def _bits_unpack(d, pad):
    bits=''.join(f'{b:08b}' for b in d)
    return bits[:-pad] if pad else bits

# ── Ring traversal ────────────────────────────────────────────────────────
def _ring_step(pos, b):
    """Ring traversal using Richard's prime values."""
    return (pos + PRIMES_R[b] % F12) % F12

# ── PACK ──────────────────────────────────────────────────────────────────
def pack(data: bytes, verbose=False) -> bytes:
    """
    Pack data as index-delta geo vector stream.
    
    The 0x00 byte IS the origin — contributes 0 to log_sum.
    Null padding is invisible to the window position computation.
    Three values reconstruct everything:
      start_byte + delta_sequence + win_sec_sequence
    """
    if not data:
        return MAGIC + struct.pack('<I', 0)

    # Delta sequence (byte differences, mod 256)
    deltas   = [(data[i] - data[i-1]) & 0xFF for i in range(1, len(data))]
    win_secs = [WIN_SEC[b] for b in data[1:]]
    lobes    = [LOBE[b]    for b in data[1:]]

    # Huffman on deltas
    freq = Counter(deltas) if deltas else {0:1}
    enc, _dec = _huff_build(freq)

    # Encode
    bitstr  = ''.join(enc[d] for d in deltas)
    encoded, pad = _bits_pack(bitstr)

    # Ring traversal for address (element physically present)
    ring_pos = 0
    for b in data:
        ring_pos = _ring_step(ring_pos, b)

    # Locked window address
    log_sum = sum(math.log(max(PRIMES_R[b], 1)) for b in data)
    win_pos = (gamma1 * log_sum) % SPAN
    win_sec_file = int(win_pos / 6) % N_SEC

    # Serialize Huffman table
    table = bytearray()
    table += struct.pack('<H', len(enc))
    for sym, code in sorted(enc.items()):
        cl=len(code); cb=max(1,math.ceil(cl/8))
        table += struct.pack('<BB', sym, cl)
        table += int(code,2).to_bytes(cb,'big')

    # Win_sec stream (1 byte each — could be 5-bit packed)
    win_stream = bytes(win_secs)

    # Header
    b0 = data[0]
    header = (MAGIC
              + struct.pack('<I', len(data))
              + struct.pack('<B', b0)
              + struct.pack('<B', (WIN_SEC[b0]&0x1F)<<3|(LOBE[b0]&1)<<2)
              + struct.pack('<B', win_sec_file)
              + struct.pack('<B', ring_pos)
              + struct.pack('<B', pad)
              + struct.pack('<H', len(bytes(table)))
              + struct.pack('<H', len(win_stream)))

    packed = header + bytes(table) + encoded + win_stream

    if verbose:
        H = (-sum((c/len(deltas))*math.log2(c/len(deltas))
                  for c in freq.values() if c>0)
             if deltas else 0)
        ratio = len(data)/len(packed)
        print(f"  start=0x{b0:02X}(P_R={PRIMES_R[b0]}) "
              f"win_sec_file={win_sec_file} "
              f"ring_pos={ring_pos}")
        print(f"  H_delta={H:.3f}  {len(data):,}B→{len(packed):,}B "
              f"({ratio:.3f}:1)")

    return packed

# ── UNPACK ────────────────────────────────────────────────────────────────
def unpack(packed: bytes, verbose=False) -> bytes:
    assert packed[:4] == MAGIC, "Not LGI2 data"

    pos = 4
    n,  = struct.unpack('<I', packed[pos:pos+4]); pos+=4
    if n == 0: return b''
    b0, = struct.unpack('<B', packed[pos:pos+1]); pos+=1
    sl, = struct.unpack('<B', packed[pos:pos+1]); pos+=1  # win_sec|lobe
    wf, = struct.unpack('<B', packed[pos:pos+1]); pos+=1  # win_sec_file
    rp, = struct.unpack('<B', packed[pos:pos+1]); pos+=1  # ring_pos
    pd, = struct.unpack('<B', packed[pos:pos+1]); pos+=1  # pad
    tl, = struct.unpack('<H', packed[pos:pos+2]); pos+=2  # table len
    wl, = struct.unpack('<H', packed[pos:pos+2]); pos+=2  # win stream len

    if verbose:
        ws0 = (sl>>3)&0x1F; lb0 = (sl>>2)&1
        print(f"  Zeta window: start=0x{b0:02X} win_sec={ws0} lobe={lb0} "
              f"file_sec={wf} ring={rp}")

    # Decode Huffman table
    n_syms,=struct.unpack('<H',packed[pos:pos+2]); pos+=2
    dec={}
    for _ in range(n_syms):
        sym,cl=struct.unpack('<BB',packed[pos:pos+2]); pos+=2
        cb=max(1,math.ceil(cl/8))
        ci=int.from_bytes(packed[pos:pos+cb],'big'); pos+=cb
        dec[f'{ci:0{cl}b}']=sym

    # Decode bits
    encoded = packed[pos:pos+(len(packed)-pos-wl)]
    bits = _bits_unpack(encoded, pd)

    # Reconstruct
    result = bytearray([b0])
    buf=''; prev=b0
    for bit in bits:
        buf+=bit
        if buf in dec:
            b = (prev + dec[buf]) & 0xFF
            result.append(b); prev=b; buf=''
            if len(result)==n: break

    return bytes(result)

# ── ZETA WINDOW ───────────────────────────────────────────────────────────
def zeta_window(packed: bytes) -> dict:
    """Read metadata without decoding. 13-byte header read only."""
    assert packed[:4] == MAGIC
    pos=4
    n,  =struct.unpack('<I',packed[pos:pos+4]); pos+=4
    b0, =struct.unpack('<B',packed[pos:pos+1]); pos+=1
    sl, =struct.unpack('<B',packed[pos:pos+1]); pos+=1
    wf, =struct.unpack('<B',packed[pos:pos+1]); pos+=1
    rp, =struct.unpack('<B',packed[pos:pos+1])
    ws0=(sl>>3)&0x1F; lb0=(sl>>2)&1
    SNAMES={1:'CONTROL⊕',5:'LOGIC◇',7:'DATA○',
            11:'COMPARE△',13:'ARITH◆',17:'MEMORY▽'}
    r18_b0 = PRIMES_R[b0] % 18
    return dict(
        start_byte    = b0,
        start_prime   = PRIMES_R[b0],
        start_win_sec = ws0,
        start_lobe    = lb0,
        file_win_sec  = wf,
        file_section  = SNAMES.get(wf,f'GND({wf})'),
        ring_pos      = rp,
        n_bytes       = n,
        packed_sz     = len(packed),
        ratio         = n/len(packed),
        is_padding    = (b0==0),      # 0x00 IS the origin
        C_byte        = C_BYTE,
        C_header      = C_HEADER,
        key_prime     = KEY_PRIME,
    )

# ── TEST SUITE ────────────────────────────────────────────────────────────
def run_tests():
    import random; random.seed(42)

    print("="*65)
    print("P18 INDEX-DELTA PACK v2.0 — RICHARD'S MODEL (P(1)=1)")
    print("="*65)
    print()
    print(f"Byte table: {{1,2,3,5,...,1613}}  (P_R(1)=1 = origin)")
    print(f"Key prime: {KEY_PRIME}  (first prime > 1613, r18=17)")
    print(f"0x00 → window section 0 = exact origin ✓")
    print()

    datasets = [
        ("All zeros (padding)",     bytes(256)),
        ("All 0xFF",                bytes([0xFF]*256)),
        ("PNG header+pad",          bytes([0x89,0x50,0x4E,0x47,
                                           0x0D,0x0A,0x1A,0x0A]+[0]*56)),
        ("JPEG header+pad",         bytes([0xFF,0xD8,0xFF,0xE0,
                                           0x00,0x10,0x4A,0x46]+[0]*56)),
        ("PE/EXE header+pad",       bytes([0x4D,0x5A,0x90,0x00,
                                           0x03,0x00,0x00,0x00]+[0]*56)),
        ("B&W blocks",              bytes([0x00]*500+[0xFF]*500)),
        ("Alternating 0x00/0xFF",   bytes([0x00,0xFF]*500)),
        ("Repeated text",           b"LGO-18 Framework\n"*56+b"LGO-"),
        ("Sequential 0x00..0xFF",   bytes(range(256))),
        ("Single byte 0x00",        bytes(1000)),
        ("Random",                  bytes([random.randint(0,255)
                                           for _ in range(1000)])),
    ]

    print(f"{'Dataset':<26} {'Orig':>6} {'Packed':>8} {'Ratio':>8}  "
          f"{'win_sec':>8}  {'is_pad':>6}  Match")
    print("-"*75)

    all_ok = True
    for label, data in datasets:
        packed   = pack(data)
        restored = unpack(packed)
        zw       = zeta_window(packed)
        ok = "✓" if restored==data else "✗"
        if restored!=data: all_ok=False
        ratio = len(data)/len(packed)
        print(f"  {label:<24} {len(data):>6,} {len(packed):>8,} "
              f"{ratio:>7.3f}:1  ws={zw['file_win_sec']:>2}  "
              f"  {'YES' if zw['is_padding'] else 'no':>6}  {ok}")

    print()
    print(f"All bit-perfect: {'✓' if all_ok else '✗'}")

    # Key verification: 0x00 window section
    print()
    print("KEY VERIFICATIONS:")
    zw0 = zeta_window(pack(bytes(64)))
    print(f"  0x00 padding → win_sec={zw0['start_win_sec']} "
          f"(should be 0) {'✓' if zw0['start_win_sec']==0 else '✗'}")
    print(f"  0x00 is_padding={zw0['is_padding']} ✓")

    # Show fixed points
    print()
    print("FIXED POINTS (lemniscate constants, stored once globally):")
    print(f"  C_bit    = DGI×5π/18              = {C_BIT:.10f}")
    print(f"  C_byte   = γ₁×log(P_R(256))/255   = {C_BYTE:.10f}")
    print(f"  C_header = F6²×C_byte              = {C_HEADER:.8f}")
    print(f"  SPAN     = {SPAN} (locked window)")
    print(f"  P_R(1)=1 → window pos = 0.000000 (exact origin)")
    print()

    # Scale ratios
    r1 = C_BYTE/C_BIT
    r2 = C_HEADER/C_BYTE
    print(f"Scale ratios:")
    print(f"  C_byte/C_bit    = {r1:.4f}  ≈ γ₁×φ×18/(5π) = "
          f"{gamma1*phi*18/(5*math.pi):.4f}")
    print(f"  C_header/C_byte = {r2:.0f}  = F6² = 64 (exact)")
    print()

    # Detailed view
    print("DETAILED — PNG header:")
    png = bytes([0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A]+[0]*56)
    pack(png, verbose=True)
    print()
    print("ZETA WINDOW — PNG (no decode):")
    zw = zeta_window(pack(png))
    for k,v in zw.items():
        print(f"  {k:<16}: {v}")

    print()
    print("DELTA ENTROPY BY FILE TYPE:")
    for label, data in datasets[:9]:
        packed = pack(data)
        # extract deltas
        n = len(data)
        if n < 2: continue
        d_stream = [((data[i]-data[i-1])&0xFF) for i in range(1,n)]
        freq = Counter(d_stream)
        H = (-sum((c/len(d_stream))*math.log2(c/len(d_stream))
                  for c in freq.values() if c>0)
             if d_stream else 0)
        dominant = freq.most_common(1)[0] if freq else (0,0)
        print(f"  {label:<26} H_delta={H:.3f}  "
              f"dom Δ={dominant[0]:3d}×{dominant[1]}")

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        cmd, fpath = sys.argv[1], sys.argv[2]
        if cmd == 'pack':
            data = Path(fpath).read_bytes()
            out  = fpath + '.lgi2'
            Path(out).write_bytes(pack(data, verbose=True))
            print(f"→ {out}")
        elif cmd == 'unpack':
            packed = Path(fpath).read_bytes()
            print("Zeta window:")
            for k,v in zeta_window(packed).items():
                print(f"  {k}: {v}")
            data = unpack(packed, verbose=True)
            out  = fpath.replace('.lgi2','') + '.restored'
            Path(out).write_bytes(data)
            print(f"→ {out}  ({len(data):,} bytes)")
    else:
        run_tests()
