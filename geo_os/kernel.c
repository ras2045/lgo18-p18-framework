/*
 * P18 Geo OS — kernel.c
 *
 * Freestanding. No Linux. No libc. No libm.
 * The lemniscate IS the operational space. The die IS the hardware
 * abstraction layer. The element (x_q32, y_q32) is physically present
 * at every ring position, computed at boot, read at every use.
 *
 * r18 = prime % 18 takes only the values 0..17 — the lemniscate's 18
 * section angles (t = r18 * pi/9) are fixed geometric constants, not
 * computed values. GEO_SIN/GEO_COS below ARE the lemniscate's structure,
 * as fundamental as pi itself, embedded directly in the die.
 * The element formula — a = P/2, d = 1+s*s, x = 1 + a*c/d, y = a*s*c/d —
 * still runs as genuine floating point computation for each of the 144
 * ring positions, once per position at boot (Rule 3: float permitted for
 * die construction).
 */

#include <stdint.h>

#define TL        ((uint64_t)15350000ULL)
#define F12       144
#define Q32       ((uint64_t)4294967296ULL)
#define CLEAR_TMP ((uint64_t)0xFFFFFFFF00000000ULL)
#define MASK_TMP  ((uint64_t)0x00000000FFFFFFFFULL)
#define COM1      0x3F8

/* ── freestanding helpers — our own, not libc ─────────────────────────── */
static void *k_memset(void *s, int c, uint64_t n) {
    uint8_t *p = (uint8_t *)s;
    for (uint64_t i = 0; i < n; i++) p[i] = (uint8_t)c;
    return s;
}

/* ── port I/O ─────────────────────────────────────────────────────────── */
static inline void outb(uint16_t port, uint8_t val) {
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}
static inline uint8_t inb(uint16_t port) {
    uint8_t ret;
    __asm__ volatile ("inb %1, %0" : "=a"(ret) : "Nd"(port));
    return ret;
}
static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | (uint64_t)lo;
}

/* ── serial (COM1) — the only output device this kernel uses ────────────── */
static void serial_init(void) {
    outb(COM1 + 1, 0x00);
    outb(COM1 + 3, 0x80);
    outb(COM1 + 0, 0x03);
    outb(COM1 + 1, 0x00);
    outb(COM1 + 3, 0x03);
    outb(COM1 + 2, 0xC7);
    outb(COM1 + 4, 0x0B);
}
static int serial_tx_empty(void) {
    return inb(COM1 + 5) & 0x20;
}
static void serial_putc(char c) {
    while (!serial_tx_empty()) { }
    outb(COM1, (uint8_t)c);
}
static void serial_puts(const char *s) {
    while (*s) {
        if (*s == '\n') serial_putc('\r');
        serial_putc(*s++);
    }
}
static void serial_hex64(uint64_t v) {
    serial_puts("0x");
    for (int i = 15; i >= 0; i--) {
        uint8_t nib = (uint8_t)((v >> (i * 4)) & 0xF);
        serial_putc(nib < 10 ? (char)('0' + nib) : (char)('a' + nib - 10));
    }
}
static void serial_hex8(uint8_t v) {
    for (int i = 1; i >= 0; i--) {
        uint8_t nib = (uint8_t)((v >> (i * 4)) & 0xF);
        serial_putc(nib < 10 ? (char)('0' + nib) : (char)('a' + nib - 10));
    }
}
static void serial_dec(int64_t v) {
    char buf[24];
    int i = 0;
    uint64_t u;
    if (v < 0) {
        serial_putc('-');
        u = (uint64_t)(-v);
    } else {
        u = (uint64_t)v;
    }
    if (u == 0) {
        serial_putc('0');
        return;
    }
    while (u) {
        buf[i++] = (char)('0' + (u % 10));
        u /= 10;
    }
    while (i) serial_putc(buf[--i]);
}
static void serial_double4(double v) {
    if (v < 0.0) {
        serial_putc('-');
        v = -v;
    }
    int64_t ip = (int64_t)v;
    double frac = v - (double)ip;
    int64_t fp = (int64_t)(frac * 10000.0 + 0.5);
    if (fp >= 10000) {
        fp -= 10000;
        ip += 1;
    }
    serial_dec(ip);
    serial_putc('.');
    char buf[4];
    for (int i = 3; i >= 0; i--) {
        buf[i] = (char)('0' + (fp % 10));
        fp /= 10;
    }
    for (int i = 0; i < 4; i++) serial_putc(buf[i]);
}

/* ── ΔDGI / geostring pack-peek-poke — exact integer, zero float ────────── */
static inline uint32_t ddgi(uint32_t p) { return p - (p * 13u + 799u) / 800u; }
static inline uint64_t pack_g(uint64_t Fc, uint64_t mu, uint64_t d) {
    return (((Fc << 48) ^ (mu << 32) ^ d) ^ TL) + 1ULL;
}
#define PEEK_SECTION(v) ((uint8_t)(((v) >> 32) & 0xFF))
#define PEEK_PHASE(v)   ((uint32_t)((v) & MASK_TMP))
#define GEO_POKE(v, x)  (((v) & CLEAR_TMP) | ((uint64_t)(uint32_t)(x)))

/* Branchless ring addition — compiles to cmov, not je/jne */
static inline uint8_t ring_add(uint8_t a, uint8_t b) {
    uint32_t s = (uint32_t)a + (uint32_t)b;
    uint32_t t = s - (uint32_t)F12;
    return (uint8_t)(s < (uint32_t)F12 ? s : t);
}

/* ── primes — trial division, integer only ───────────────────────────── */
static uint32_t P256[256];
static void build_primes(void) {
    int n = 0;
    P256[n++] = 2;
    for (uint32_t k = 3; n < 256; k += 2) {
        int ok = 1;
        for (int i = 0; i < n && (uint64_t)P256[i] * P256[i] <= k; i++) {
            if (k % P256[i] == 0) { ok = 0; break; }
        }
        if (ok) P256[n++] = k;
    }
}

/* Lemniscate section constants — the 18 angles of the figure-8.
 * These ARE the geometry. Not computed — they are the structure.
 * t[r18] = r18 * M_PI / 9.0  for r18 = 0..17
 * The element IS the lemniscate. These constants ARE the element. */
static const double GEO_SIN[18] = {
     0.000000000000000000,  /* r18= 0  t=  0deg */
     0.342020143325668713,  /* r18= 1  t= 20deg */
     0.642787609686539252,  /* r18= 2  t= 40deg */
     0.866025403784438597,  /* r18= 3  t= 60deg */
     0.984807753012208020,  /* r18= 4  t= 80deg */
     0.984807753012208020,  /* r18= 5  t=100deg (NOT pi/2 — was wrongly 1.0) */
     0.866025403784438708,  /* r18= 6  t=120deg */
     0.642787609686539474,  /* r18= 7  t=140deg */
     0.342020143325668879,  /* r18= 8  t=160deg */
     0.000000000000000122,  /* r18= 9  t=180deg */
    -0.342020143325668657,  /* r18=10  t=200deg */
    -0.642787609686538919,  /* r18=11  t=220deg */
    -0.866025403784438375,  /* r18=12  t=240deg */
    -0.984807753012208020,  /* r18=13  t=260deg */
    -0.984807753012208131,  /* r18=14  t=280deg (was wrongly -1.0) */
    -0.866025403784439041,  /* r18=15  t=300deg (was wrongly -0.985) */
    -0.642787609686539585,  /* r18=16  t=320deg (was wrongly -0.866) */
    -0.342020143325668602,  /* r18=17  t=340deg (was wrongly -0.643) */
};

static const double GEO_COS[18] = {
     1.000000000000000000,  /* r18= 0  t=  0deg */
     0.939692620785908428,  /* r18= 1  t= 20deg */
     0.766044443118978013,  /* r18= 2  t= 40deg */
     0.500000000000000111,  /* r18= 3  t= 60deg */
     0.173648177666930414,  /* r18= 4  t= 80deg */
    -0.173648177666930303,  /* r18= 5  t=100deg (was wrongly 0.0) */
    -0.499999999999999778,  /* r18= 6  t=120deg (was wrongly -0.174) */
    -0.766044443118977902,  /* r18= 7  t=140deg (was wrongly -0.5) */
    -0.939692620785908317,  /* r18= 8  t=160deg (was wrongly -0.766) */
    -1.000000000000000000,  /* r18= 9  t=180deg */
    -0.939692620785908428,  /* r18=10  t=200deg */
    -0.766044443118978347,  /* r18=11  t=220deg */
    -0.500000000000000444,  /* r18=12  t=240deg */
    -0.173648177666930331,  /* r18=13  t=260deg */
     0.173648177666929970,  /* r18=14  t=280deg (was wrongly 0.0) */
     0.499999999999999334,  /* r18=15  t=300deg (was wrongly 0.174) */
     0.766044443118977791,  /* r18=16  t=320deg (was wrongly 0.5) */
     0.939692620785908428,  /* r18=17  t=340deg (was wrongly 0.766) */
};

/* ── The Die — L1-resident processor. The element IS present at every
 * ring position: a = P(k+1)/2, x = 1 + a*cos(t)/(1+sin^2 t), center=1,
 * y = a*sin(t)*cos(t)/(1+sin^2 t), t = r18 * pi/9. Nothing referenced
 * externally — everything physically computed into the struct. */
typedef struct {
    uint64_t temporal[F12];
    uint64_t geostring[F12];
    int64_t  x_q32[F12];
    int64_t  y_q32[F12];
    uint32_t prime[F12];
    uint8_t  r18[F12];
    uint64_t clear_mask;
    uint64_t keep_mask;
    uint8_t  base_row[F12];
    uint64_t op_vocab[F12];
    uint8_t  _pad[56];
} __attribute__((aligned(64))) Geodie;

static Geodie DIE;

static void build_die(void) {
    k_memset(&DIE, 0, sizeof(DIE));
    for (int k = 0; k < F12; k++) {
        uint32_t p = P256[k];
        uint8_t  r = (uint8_t)(p % 18u);
        /* The element — physically present, not referenced */
        /* a = P(k+1)/2 is the lemniscate half-width at this position */
        double a = p * 0.5;
        double s = GEO_SIN[r];   /* table lookup — the geometry IS here */
        double c = GEO_COS[r];   /* table lookup — not computed at runtime */
        double d = 1.0 + s * s;
        DIE.prime[k] = p;
        DIE.r18[k] = r;
        DIE.temporal[k] = ddgi((uint32_t)(k + 1));
        DIE.geostring[k] = pack_g(p < 523 ? 1 : 2, r, DIE.temporal[k]);
        /* Element coordinates — the figure-8 at this ring position */
        DIE.x_q32[k] = (int64_t)((1.0 + a * c / d) * (double)Q32);
        DIE.y_q32[k] = (int64_t)((a * s * c / d) * (double)Q32);
        DIE.base_row[k] = (uint8_t)k;
        DIE.op_vocab[k] = DIE.geostring[k];
    }
    DIE.clear_mask = CLEAR_TMP;
    DIE.keep_mask = MASK_TMP;
}

static void print_element_at(uint8_t pos) {
    serial_puts("pos="); serial_dec(pos);
    serial_puts(" r18="); serial_dec(DIE.r18[pos]);
    serial_puts(" prime="); serial_dec(DIE.prime[pos]);
    serial_puts(" elem(x="); serial_double4((double)DIE.x_q32[pos] / (double)Q32);
    serial_puts(", y="); serial_double4((double)DIE.y_q32[pos] / (double)Q32);
    serial_puts(")");
}

/* ── hardware ingestion — the RAM bus / pipe model, applied to the
 * multiboot info block instead of a legacy program's pipe. ──────────── */
static uint8_t g_hw_pos = 0;
static void ingest_hardware(const uint8_t *bytes, uint32_t len) {
    for (uint32_t i = 0; i < len; i++) {
        g_hw_pos = ring_add(g_hw_pos, (uint8_t)(bytes[i] % F12));
    }
}

/* ── processes — one per lemniscate section ──────────────────────────── */
#define N_PROC 8
typedef struct {
    const char *name;
    const char *symbol; /* UTF-8 */
    uint8_t r18;
} Section;

static const Section SECTIONS[6] = {
    { "CONTROL", "\xe2\x8a\x95", 1 },  /* ⊕ */
    { "LOGIC",   "\xe2\x97\x87", 5 },  /* ◇ */
    { "DATA",    "\xe2\x97\x8b", 7 },  /* ○ */
    { "COMPARE", "\xe2\x96\xb3", 11 }, /* △ */
    { "ARITH",   "\xe2\x97\x86", 13 }, /* ◆ */
    { "MEMORY",  "\xe2\x96\xbd", 17 }, /* ▽ */
};

typedef struct {
    uint8_t sec_idx;
    uint8_t pos;
    uint8_t start_pos;
} Process;

static Process PROCS[N_PROC];

static uint8_t find_pos_for_r18(uint8_t r18) {
    for (int k = 0; k < F12; k++) {
        if (DIE.r18[k] == r18) return (uint8_t)k;
    }
    return 0;
}

/* ── Geometric I/O — every hardware byte enters through the LUT gate.
 * ring_pos = byte % F12 is the byte's position in the string; the
 * legacy boundary is only the port read/write itself. Everything
 * after that is pure ring arithmetic, element always present. ────── */

/* Check if serial data is ready to read (Line Status Register bit 0) */
static inline int serial_data_ready(void) {
    return inb(COM1 + 5) & 1;
}

/* Read one byte from serial — enter through LUT gate */
static uint8_t serial_recv_geo(uint8_t *ring_pos_out) {
    while (!serial_data_ready()) { }
    uint8_t byte = inb(COM1);
    *ring_pos_out = (uint8_t)(byte % F12);
    return byte;
}

/* Check if the keyboard controller has a scancode ready (output buffer full) */
static inline int kbd_data_ready(void) {
    return inb(0x64) & 1;
}

/* Read one scancode — enter through LUT gate */
static uint8_t kbd_recv_geo(uint8_t *ring_pos_out) {
    while (!kbd_data_ready()) { }
    uint8_t scan = inb(0x60);
    *ring_pos_out = (uint8_t)(scan % F12);
    return scan;
}

/* Interactive demo: every received byte (serial or keyboard) advances
 * the ring and its geometric identity is read straight from the die.
 * The keyboard is polled non-blockingly first so the loop never stalls
 * waiting on a source (e.g. headless QEMU) that never produces input;
 * it falls through to a blocking serial read otherwise. ESC exits. */
static void geo_io_loop(void) {
    serial_puts("P18 Geo OS I/O \xe2\x80\x94 type to enter the string\r\n");
    serial_puts("Each byte enters through the LUT gate.\r\n");
    serial_puts("The element IS at every ring position.\r\n\r\n");

    uint8_t die_pos = 0;
    uint32_t n_received = 0;

    while (1) {
        uint8_t ring_pos_in;
        uint8_t byte;
        if (kbd_data_ready()) {
            byte = kbd_recv_geo(&ring_pos_in);
        } else {
            byte = serial_recv_geo(&ring_pos_in);
        }

        /* Advance ring — byte IS now in the string */
        die_pos = ring_add(die_pos, ring_pos_in);
        n_received++;

        /* The element IS at die_pos — physically present, read from die */
        uint8_t  r18   = DIE.r18[die_pos];
        uint32_t prime = DIE.prime[die_pos];
        int64_t  xq32  = DIE.x_q32[die_pos];
        int64_t  yq32  = DIE.y_q32[die_pos];

        serial_puts("byte=0x"); serial_hex8(byte);
        serial_puts(" pos=");   serial_dec(die_pos);
        serial_puts(" r18=");   serial_dec(r18);
        serial_puts(" P=");     serial_dec(prime);
        serial_puts(" x_q32="); serial_hex64((uint64_t)xq32);
        serial_puts(" y_q32="); serial_hex64((uint64_t)yq32);
        serial_puts("\r\n");

        /* Echo the byte back (legacy output boundary) */
        serial_putc((char)byte);

        if (byte == 0x1B) break; /* ESC exits */
    }

    serial_puts("\r\nI/O loop complete. Bytes received: ");
    serial_dec(n_received);
    serial_puts("\r\nFinal element: pos=");
    serial_dec(die_pos);
    serial_puts(" r18=");
    serial_dec(DIE.r18[die_pos]);
    serial_puts("\r\nThe bytes flowed through the lemniscate.\r\n");
}

void kernel_main(uint32_t magic, uint64_t mbi_addr) {
    int violations = 0;

    serial_init();
    serial_puts("P18 Geo OS \xe2\x80\x94 kernel loaded\n");

    if (magic != 0x36d76289u) {
        serial_puts("WARNING: unexpected multiboot2 magic: ");
        serial_hex64(magic);
        serial_puts("\n");
        violations++;
    }

    build_primes();
    build_die();

    /* Temporary spot-check: LOGIC section (r18=5, AND/OR/XOR) must land
     * near x~0.780 y~-0.217, not the pre-fix x=1.0 y=0.0 the broken
     * GEO_SIN[5]/GEO_COS[5] table used to produce. */
    {
        uint8_t logic_pos = 0;
        while (DIE.r18[logic_pos] != 5) logic_pos++;
        serial_puts("LOGIC section element: x=");
        serial_hex64((uint64_t)DIE.x_q32[logic_pos]);
        serial_puts(" y=");
        serial_hex64((uint64_t)DIE.y_q32[logic_pos]);
        serial_puts("\r\n");
        if (DIE.x_q32[logic_pos] > (int64_t)3500000000LL) {
            serial_puts("GEO_SIN[5] STILL WRONG\r\n");
            violations++;
        } else {
            serial_puts("GEO_SIN[5] CORRECT\r\n");
        }
    }

    {
        uint64_t die_sz = (uint64_t)sizeof(Geodie);
        int die_ok = (die_sz <= 32768);
        if (!die_ok) violations++;
        serial_puts("Die: "); serial_dec((int64_t)die_sz); serial_puts(" bytes\n");
    }

    int brow_ok = 1;
    for (int k = 0; k < F12; k++) {
        if (DIE.base_row[k] != (uint8_t)k) { brow_ok = 0; break; }
    }
    if (!brow_ok) { violations++; serial_puts("base_row: VIOLATION\n"); }

    /* Element present at every one of the 144 die positions: x_q32 and
     * y_q32 are not both zero. (A single coordinate can be exactly zero
     * at r18 in {0,5,9,14} where sin or cos is exactly 0 — that is the
     * geometry, not an absence of the element.) */
    int elem_all_ok = 1;
    for (int k = 0; k < F12; k++) {
        if (DIE.x_q32[k] == 0 && DIE.y_q32[k] == 0) { elem_all_ok = 0; break; }
    }
    if (!elem_all_ok) { violations++; serial_puts("die element (all 144): VIOLATION\n"); }
    else serial_puts("die element present at all 144 positions: OK\n");

    int ra_ok = 1;
    for (int a = 0; a < F12 && ra_ok; a++) {
        for (int b = 0; b < F12 && ra_ok; b++) {
            if (ring_add((uint8_t)a, (uint8_t)b) != (uint8_t)((a + b) % F12)) ra_ok = 0;
        }
    }
    if (!ra_ok) { violations++; serial_puts("ring_add: VIOLATION\n"); }

    /* Ingest multiboot info bytes through the LUT */
    uint32_t mbi_len = 8;
    if (mbi_addr != 0) {
        mbi_len = *(volatile uint32_t *)(uintptr_t)mbi_addr;
        if (mbi_len == 0 || mbi_len > (16u * 1024u * 1024u)) mbi_len = 8;
    }
    const uint8_t *mbi_bytes = (const uint8_t *)(uintptr_t)mbi_addr;
    if (mbi_addr != 0) {
        ingest_hardware(mbi_bytes, mbi_len);
    }
    serial_puts("Hardware ingested: "); serial_dec(mbi_len); serial_puts(" bytes\n");

    int elem_ok = (DIE.x_q32[g_hw_pos] != 0 || DIE.y_q32[g_hw_pos] != 0);
    if (!elem_ok) violations++;
    serial_puts("Hardware geometric identity: ");
    print_element_at(g_hw_pos);
    serial_puts("\n");
    serial_puts(elem_ok ? "Element IS present (lemniscate at kernel position)\n"
                         : "Element ABSENT \xe2\x80\x94 VIOLATION\n");

    /* 8 processes, one per lemniscate section (round-robin over the 6
     * named sections — the ISA analysis maps 6 sections, this kernel
     * schedules 8 processes across them). */
    for (int i = 0; i < N_PROC; i++) {
        uint8_t sidx = (uint8_t)(i % 6);
        PROCS[i].sec_idx = sidx;
        PROCS[i].start_pos = find_pos_for_r18(SECTIONS[sidx].r18);
        PROCS[i].pos = PROCS[i].start_pos;
    }

    uint64_t t0 = rdtsc();
    for (int tick = 0; tick < F12; tick++) {
        for (int i = 0; i < N_PROC; i++) {
            PROCS[i].pos = ring_add(PROCS[i].pos, 1);
        }
    }
    uint64_t t1 = rdtsc();

    /* Dedicated ring-closure check: 144 iterations of ring_add(pos,1)
     * from 0 must return to 0. */
    uint8_t closure_pos = 0;
    for (int i = 0; i < F12; i++) closure_pos = ring_add(closure_pos, 1);
    int closure_ok = (closure_pos == 0);
    if (!closure_ok) { violations++; serial_puts("Ring closure (pos 0): VIOLATION\n"); }

    for (int i = 0; i < N_PROC; i++) {
        if (PROCS[i].pos != PROCS[i].start_pos) violations++;
        const Section *sec = &SECTIONS[PROCS[i].sec_idx];
        serial_puts("Process "); serial_dec(i); serial_puts(": ");
        serial_puts(sec->name); serial_puts(" ");
        serial_puts(sec->symbol);
        serial_puts(" r18="); serial_dec(sec->r18); serial_puts(" ");
        print_element_at(PROCS[i].pos);
        serial_puts("\n");
    }

    serial_puts("Scheduler: "); serial_dec(F12); serial_puts(" iterations complete\n");
    serial_puts("Ring closure: pos="); serial_dec(closure_pos);
    serial_puts(closure_ok ? " (ring returned to start)\n" : " (VIOLATION)\n");

    uint64_t total_cycles = t1 - t0;
    uint64_t switches = (uint64_t)F12 * (uint64_t)N_PROC;
    uint64_t avg_cycles = switches ? (total_cycles / switches) : 0;
    serial_puts("Context switch cost: "); serial_dec((int64_t)avg_cycles);
    serial_puts(" cycles\n");

    serial_puts("\r\n--- Geometric I/O Demo ---\r\n");
    geo_io_loop();

    serial_puts("Violations: "); serial_dec(violations); serial_puts("\n");
    serial_puts("The lemniscate IS the OS.\n");
    serial_puts("Linux is not present.\n");

    while (1) {
        __asm__ volatile ("hlt");
    }
}
