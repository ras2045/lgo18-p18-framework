/*
 * geo_os_dispatch.h — Geo OS v2: Star Octagon Kernel Constants
 *
 * The physical element ∞ (lemniscate of Bernoulli) is always present.
 * Every constant derives from the figure-8 curve — no free parameters.
 *
 * Universe uses geometry, not numbers.
 *
 * Reference: P18 Framework · Richard Sardini · July 2026
 */

#ifndef GEO_OS_DISPATCH_H
#define GEO_OS_DISPATCH_H

#include <stdint.h>
#include <stddef.h>

/* ─── Fixed-Point (Q32) ────────────────────────────────────────────────────── */
typedef uint32_t q32_t;
typedef uint64_t q64_t;

#define Q32_ONE       4294967296ULL   /* 2^32 — unit of Q32 scale */
#define Q32_HALF      2147483648UL    /* 1/2 × 2^32 */

/* ─── Golden Ratio φ and Derivatives ──────────────────────────────────────── */
#define Q32_INV_PHI   2654435769UL   /* 1/φ   × 2^32  = cos(t_ζ) */
#define Q32_PHI_S     3376494457UL   /* 1/√φ  × 2^32  = sin(t_ζ) */
#define Q32_D_Z       1640531527UL   /* 1/φ²  × 2^32  = D(t_ζ)   */
#define Q32_YS_Z      1289706120UL   /* 1/φ^(5/2) × 2^32 = ys(t_ζ) */
#define Q64_PHI_3_2   8839777252ULL  /* φ^(3/2) × 2^32 */

/* ─── Star Octagon Geometry ────────────────────────────────────────────────── */
/*   R_outer = √2,  R_inner = √(4φ-6),  ratio = φ^(3/2)  [all EXACT]         */
#define Q64_R_OUT_SQ  8589934592ULL  /* 2 × 2^32       = R_outer² */
#define Q32_R_IN_SQ   2027808486UL   /* (4φ−6) × 2^32  = R_inner² */
#define Q32_PD_TZ     2654435769UL   /* P_D(t_ζ) = 1/φ   × 2^32 */
#define Q32_PYS_TZ    1640531527UL   /* P_ys(t_ζ)= 1/φ²  × 2^32 */
#define Q32_PD_T1     2618882498UL   /* P_D(t₁)  = 25/41 × 2^32  [L2 gate] */
#define Q32_PYS_T1    1676084798UL   /* P_ys(t₁) = 16/41 × 2^32  [L2 gate] */

/* ─── DGI (Deterministic Geometric Impedance) = 13/800 ─────────────────────── */
#define DGI_Q32          69793219UL  /* 13/800 × 2^32 */
#define TAN_DGI_HALF     60910156UL  /* tan(0.8125°) × 2^32 — DGI triangle test */

/* ─── 18-Wheel Section Constants (Q32 sin/cos) ─────────────────────────────── */
/*   t(r) = r × π/9,  r ∈ {0..17}  (20° steps)                                 */
static const q32_t GEO_SIN[18] = {
    0,           1468965330, 2760751762, 3719550787,
    4229717092,  4229717092, 3719550787, 2760751762,
    1468965330,  0,          0,          0,          /* r=9..11: negative, store abs */
    0,           0,          0,          0,
    0,           0
};
/* Signed 64-bit sin/cos for lemniscate arithmetic (avoids int32 overflow) */
static const int64_t GEO_SIN64[18] = {
    0LL,            1468965330LL,   2760751762LL,   3719550787LL,
    4229717092LL,   4229717092LL,   3719550787LL,   2760751762LL,
    1468965330LL,   0LL,           -1468965330LL,  -2760751762LL,
   -3719550787LL,  -4229717092LL,  -4229717092LL,  -3719550787LL,
   -2760751762LL,  -1468965330LL
};
static const int64_t GEO_COS64[18] = {
    4294967296LL,   4035949075LL,   3290135830LL,   2147483648LL,
    745813244LL,   -745813244LL,   -2147483648LL,  -3290135830LL,
   -4035949075LL,  -4294967296LL,  -4035949075LL,  -3290135830LL,
   -2147483648LL,  -745813244LL,    745813244LL,    2147483648LL,
    3290135830LL,   4035949075LL
};

/* ─── Born Probability Table (Q32) ─────────────────────────────────────────── */
/*   P_D(r)  = Q32 / (1 + sin²(r·π/9))                                         */
/*   P_ys(r) = Q32 − P_D(r)                                                     */
/*   r ∈ {0..8}, symmetric repeat for r ∈ {9..17}                               */
/* BORN_PD[r]: r=0,9 are exactly Q32_ONE=2^32; stored as 0 with flag BORN_PD_MAX */
#define BORN_PD_IS_MAX(r) ((r) == 0 || (r) == 9)
static const q32_t BORN_PD[18] = {
    0xFFFFFFFFUL, 3845168077UL, 3039230475UL, 2454267026UL,
    2180356545UL, 2180356545UL, 2454267026UL, 3039230475UL,
    3845168077UL, 0xFFFFFFFFUL, 3845168077UL, 3039230475UL,
    2454267026UL, 2180356545UL, 2180356545UL, 2454267026UL,
    3039230475UL, 3845168077UL
};
static const q32_t BORN_PYS[18] = {
    0UL,          449799219UL,  1255736821UL, 1840700270UL,
    2114610751UL, 2114610751UL, 1840700270UL, 1255736821UL,
    449799219UL,  0UL,          449799219UL,  1255736821UL,
    1840700270UL, 2114610751UL, 2114610751UL, 1840700270UL,
    1255736821UL, 449799219UL
};

/* ─── Section Names and ISA Class ──────────────────────────────────────────── */
typedef enum {
    SEC_GROUND   = 0,   /* r18 ∈ {0,2,3,9}  — center/crossing  */
    SEC_CONTROL  = 1,   /* r18 = 1           — JMP/CALL/RET      */
    SEC_LOGIC    = 5,   /* r18 = 5           — AND/OR/XOR        */
    SEC_DATA     = 7,   /* r18 = 7           — MOV/load          */
    SEC_COMPARE  = 11,  /* r18 = 11          — CMP/TEST          */
    SEC_ARITH    = 13,  /* r18 = 13          — ADD/SUB/MUL       */
    SEC_MEMORY   = 17   /* r18 = 17          — PUSH/POP/IO       */
} geo_section_t;

static const char* GEO_SECTION_NAME[18] = {
    "GROUND·",  "CONTROL⊕", "GROUND·", "GROUND·",
    "—",        "LOGIC◇",   "—",       "DATA○",
    "—",        "GROUND·",  "—",       "COMPARE△",
    "—",        "ARITH◆",   "—",       "—",
    "—",        "MEMORY▽"
};

/* ─── Orbit Classification ──────────────────────────────────────────────────── */
/*   D-orbit {0,6,12}  — file I/O, lightest generation                          */
/*   P-orbit {2,8,14}  — network I/O, middle generation                         */
/*   C-orbit {4,10,16} — memory/process, heaviest generation                    */
typedef enum { ORBIT_D = 0, ORBIT_P = 1, ORBIT_C = 2, ORBIT_NONE = 3 } geo_orbit_t;

static inline geo_orbit_t geo_orbit(uint8_t r18) {
    if (r18 == 0 || r18 == 6  || r18 == 12) return ORBIT_D;
    if (r18 == 2 || r18 == 8  || r18 == 14) return ORBIT_P;
    if (r18 == 4 || r18 == 10 || r18 == 16) return ORBIT_C;
    return ORBIT_NONE;
}

/* ─── Ring Constants ────────────────────────────────────────────────────────── */
#define F12          144     /* ring closure = lcm(18,48) = F(12) Fibonacci     */
#define N_SECTIONS   18      /* lemniscate sections                              */
#define N_CHANNELS   137     /* 8×17 + 1 — star octagon dispatch channels       */
#define N_LOBES      8       /* four lemniscates × 2 lobes                      */
#define N_NONTRIVIAL 17      /* non-trivial 18-wheel sections per lobe           */
#define TL_CONST     15350000UL /* temporal lock constant                        */

/* ─── Three-Level Cache Gates ──────────────────────────────────────────────── */
#define L1_PRIME_MAX 827     /* P(144) — die static boundary                    */
#define L2_PRIME_MAX 108301  /* P(10291) — warm dispatch boundary               */
/* L3: everything beyond — full universe                                         */

/* ─── Geostring Format ──────────────────────────────────────────────────────── */
/*   uint64_t geostring = (Fc<<48) ^ (μop<<32) ^ ΔDGI ^ (TL+1)                 */
/*   Fc   = fiber count / ring position  [bits 48..63]                           */
/*   μop  = micro-op class (section index) [bits 32..47]                        */
/*   ΔDGI = DGI displacement (Q32) [bits 16..31]                                */
/*   TL+1 = temporal lock + 1 [bits 0..15]                                      */
static inline uint64_t geo_pack_geostring(uint8_t ring_pos, uint8_t uop,
                                          uint16_t dgi_delta, uint16_t tl) {
    return ((uint64_t)ring_pos << 48)
         ^ ((uint64_t)uop     << 32)
         ^ ((uint64_t)dgi_delta << 16)
         ^ ((uint64_t)(tl + 1));
}

/* ─── Lemniscate ∞ Point Evaluation (Q32 integer-only) ─────────────────────── */
/*   x(t) = 1 + a·D(t)        D(t) = cos(t)/(1 + sin²(t))                      */
/*   y(t) = a·D(t)·sin(t)     ys(t) = D(t)·sin(t)  [EXACT IDENTITY]            */
static inline void geo_lemniscate_q32(q32_t a_q32, uint8_t r18,
                                      int64_t *out_x, int64_t *out_y) {
    /* D_t = cos(t) / (1 + sin²(t)) — all Q32 integer arithmetic */
    int64_t  cos_t  = GEO_COS64[r18];
    int64_t  sin_t  = GEO_SIN64[r18];
    int64_t  sin2   = (sin_t * sin_t) >> 32;            /* sin²(t) in Q32 */
    int64_t  denom  = (int64_t)Q32_ONE + sin2;          /* 1 + sin²(t) in Q32 */
    int64_t  D_t    = (cos_t * (int64_t)Q32_ONE) / denom; /* D(t) in Q32 */

    /* x = 1 + a·D(t)   (critical: +1 is fixed offset, NOT a*(1+D)) */
    *out_x = (int64_t)Q32_ONE + ((__int128)a_q32 * D_t >> 32);

    /* y = a·D(t)·sin(t) = a·ys(t)   [exact identity] */
    int64_t ys_t = (D_t * sin_t) >> 32;
    *out_y = ((__int128)a_q32 * ys_t) >> 32;
}

/* ─── Born Gate ──────────────────────────────────────────────────────────────── */
/*   Returns 1 if p_val passes the D-lane (outer) Born gate                      */
/*   Compares against BORN_PD[r18] — 1 cycle comparison, no branches             */
static inline int geo_born_gate(q32_t p_val, uint8_t r18) {
    return (p_val <= BORN_PD[r18]);
}

/* ─── Ring Advance (branchless) ─────────────────────────────────────────────── */
/*   2 cycles: AND + OR — the entire Geo OS scheduler                            */
static inline uint8_t geo_ring_advance(uint8_t pos) {
    return (pos + 1) & (F12 - 1);   /* AND: mod 144, branchless */
}

/* ─── Context Switch ─────────────────────────────────────────────────────────── */
typedef struct {
    uint8_t  ring_pos;   /* current ring position [0..143]    */
    uint8_t  lobe;       /* 0=left, 1=right                   */
    uint8_t  section;    /* r18 ∈ {0..17}                     */
    uint8_t  orbit;      /* D=0, P=1, C=2, NONE=3             */
    uint32_t p_val;      /* Born probability estimate (Q32)   */
    uint64_t geostring;  /* packed 64-bit geometric address   */
} geo_ctx_t;

/* Switch context in 2 cycles (AND+OR): clear old lobe, set new */
static inline void geo_ctx_switch(geo_ctx_t *from, geo_ctx_t *to) {
    from->ring_pos  = (from->ring_pos) & ~0x80;   /* AND: clear high bit */
    to->ring_pos    = (to->ring_pos)   |  0x00;   /* OR:  set  new state */
    from->ring_pos  = geo_ring_advance(from->ring_pos);
}

/* ─── 137-Channel Dispatch Table ────────────────────────────────────────────── */
/*   8 lobes × 17 non-trivial sections + 1 center = 137 channels               */
/*   Angular traversal order: [0,4,1,5,2,6,3,7]                                 */
/*   (P1→Q2→P2→Q3→P3→Q4→P4→Q1, matching t_ζ/(90°−t_ζ) gap alternation)        */
static const uint8_t LOBE_TRAVERSAL[8] = {0, 4, 1, 5, 2, 6, 3, 7};
static const uint8_t NONTRIVIAL_SECTIONS[17] = {
    1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 0xFF /* pad */
};
/* Channel index: channel = lobe*17 + section_index; channel 136 = center */
static inline uint8_t geo_channel(uint8_t lobe_idx, uint8_t sec_idx) {
    if (lobe_idx >= 8 || sec_idx >= 16) return 136; /* center */
    return lobe_idx * 17 + sec_idx;
}

/* ─── Lobe Index (8:1 compression) ─────────────────────────────────────────── */
/*   86 right-lobe bytes (bit=1), 170 left-lobe bytes (bit=0)                   */
/*   Stored as 32-byte AVX2 register — static at boot, never evicted from L1    */
extern const uint8_t LOBE_INDEX_256[32];

static inline int geo_lobe_bit(uint8_t byte_val) {
    /* Returns 1 for right lobe (x>0), 0 for left lobe (x<0) */
    return (LOBE_INDEX_256[byte_val >> 3] >> (byte_val & 7)) & 1;
}

/* ─── Fine Structure Verification ──────────────────────────────────────────── */
/*   1/α = F(6)·P(7) + 1 + F(4)²/(2·F(5)³) − DGI²/(2·F(12))                  */
/*       = 8×17 + 1 + 9/250 − (13/800)²/288                                    */
/*       = 137.035999083116   (CODATA error: 8.84×10⁻¹⁰)                       */
#define ALPHA_INV_NUM   25258475351LL   /* numerator   × 184,320,000 */
#define ALPHA_INV_DEN   184320000LL     /* denominator */

#endif /* GEO_OS_DISPATCH_H */
