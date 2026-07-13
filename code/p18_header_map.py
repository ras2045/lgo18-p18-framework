"""
P18 File Header Section Map
LGO-18 / P18 Framework — Richard Sardini

The 64-byte file header mapped through the binary translation table
gives a unique GEOMETRIC FINGERPRINT for each file type.

Key findings:
  1. Every file format has a unique 8-byte section sequence (ALL UNIQUE)
  2. The first 4 lobe bits classify the file type (4 bits = 16 classes)
  3. PE/EXE headers have the lowest section entropy (1.475) — most structured
  4. ZIP already compressed: high GROUND content, H_sec=1.223
  5. The 64-byte header IS the constant for file-type-aware compression
  
Connection to LGOFS compression:
  header section fingerprint → pre-tuned Huffman table per file type
  payload compressed with type-specific table → better ratios
  The type is readable from geostring WITHOUT decompression (zeta window)
"""

import math
from collections import Counter, defaultdict

def sieve(n):
    ip=[True]*(n+1); ip[0]=ip[1]=False
    for i in range(2,int(n**0.5)+1):
        if ip[i]:
            for j in range(i*i,n+1,i): ip[j]=False
    return [i for i in range(2,n+1) if ip[i]]

PRIMES_256 = sieve(1700)[:256]
gamma1     = 14.134725141734693
N_SEC      = 18
SPAN       = 108.0
center     = 1
DGI        = 13/800

SECTION_NAMES = {1:'CONTROL⊕',5:'LOGIC◇',7:'DATA○',
                 11:'COMPARE△',13:'ARITH◆',17:'MEMORY▽'}
SEC_CHAR = {r: list('CLDT AM')[i] if r in [1,5,7,11,13,17]
            else 'G'
            for i,r in enumerate([1,5,7,11,13,17])}
# fix the dict properly
SEC_CHAR = {1:'C',5:'L',7:'D',11:'T',13:'A',17:'M',
            0:'G',2:'G',3:'G',4:'G',6:'G',8:'G',
            9:'G',10:'G',12:'G',14:'G',15:'G',16:'G'}

def elem_x(p, r18):
    a=p/2; t=r18*math.pi/N_SEC
    s,c=math.sin(t),math.cos(t)
    return center+a*c/(1+s*s)

def fingerprint(data: bytes) -> dict:
    """
    Map a byte sequence to its P18 geometric fingerprint.
    Used to identify file type from header and
    pre-tune the compression table for the payload.
    """
    primes = [PRIMES_256[b] for b in data]
    r18s   = [p%18 for p in primes]
    lobes  = [1 if elem_x(p,r)>0 else 0 for p,r in zip(primes,r18s)]
    log_sum= sum(math.log(p) for p in primes)
    win_pos= (gamma1*log_sum) % SPAN
    sec_idx= int(win_pos/6) % N_SEC

    freq = Counter(r18s); n=len(r18s)
    H = -sum((c/n)*math.log2(c/n) for c in freq.values() if c>0) if n>0 else 0

    sec_str  = ''.join(SEC_CHAR.get(r,'?') for r in r18s)
    lobe_str = ''.join(str(l) for l in lobes)
    dom_r18  = freq.most_common(1)[0][0] if freq else 0
    dom_sec  = SECTION_NAMES.get(dom_r18, f'GND({dom_r18})')

    return dict(
        r18s=r18s, lobes=lobes, log_sum=log_sum,
        win_pos=win_pos, sec_idx=sec_idx, H_sec=H,
        sec_str=sec_str, lobe_str=lobe_str,
        dom_section=dom_sec, sec_freq=dict(freq)
    )

# Known file type classifiers (first 8 bytes → section pattern)
FILE_TYPE_SIGNATURES = {
    'ALLMDAAA': 'PNG',
    'MAMLGLCT': 'JPEG',
    'CMCGDGGG': 'PE/EXE',
    'MDTTLGGG': 'ELF',
    'LLDTCGGG': 'ZIP/DOCX/JAR',
    'CLLTCAAT': 'PDF',
    'GGGTLADL': 'MP4',
    'MATMCMDC': 'GIF',
    'TMAM????': 'LGOG (our format)',
}

def identify_file_type(header_64: bytes) -> str:
    """Identify file type from 64-byte header via section pattern."""
    fp = fingerprint(header_64[:8])
    sig = fp['sec_str'][:8]
    return FILE_TYPE_SIGNATURES.get(sig, f'UNKNOWN ({sig})')

def section_compression_gain(header_64: bytes) -> float:
    """
    Estimate compression gain from file-type-aware Huffman table.
    ratio = log2(6) / H_section  where log2(6)=2.585 is max section entropy
    """
    fp = fingerprint(header_64)
    if fp['H_sec'] > 0:
        return math.log2(6) / fp['H_sec']
    return float('inf')

if __name__ == '__main__':
    # Demo: identify file type from magic bytes
    test_headers = {
        'PNG':    bytes([0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A]),
        'JPEG':   bytes([0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46]),
        'PE/EXE': bytes([0x4D,0x5A,0x90,0x00,0x03,0x00,0x00,0x00]),
        'ELF':    bytes([0x7F,0x45,0x4C,0x46,0x02,0x01,0x01,0x00]),
        'ZIP':    bytes([0x50,0x4B,0x03,0x04,0x14,0x00,0x00,0x00]),
        'PDF':    bytes([0x25,0x50,0x44,0x46,0x2D,0x31,0x2E,0x37]),
    }

    print("P18 File Type Classifier (from 8-byte magic):")
    print(f"{'Format':<10}  {'Hex':>24}  {'Sec pattern':>12}  {'Type':>15}  H_sec")
    print("-"*75)
    for fmt, hdr in test_headers.items():
        fp = fingerprint(hdr)
        detected = identify_file_type(hdr)
        hex_str = ' '.join(f'{b:02X}' for b in hdr)
        print(f"  {fmt:<8}  {hex_str:>24}  {fp['sec_str'][:8]:>12}  "
              f"{detected:>15}  {fp['H_sec']:.3f}")
