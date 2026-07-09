/*
 * P18 Connection Layer — Linux Syscall Interceptor
 *
 * COMPILE:
 * gcc -O3 -march=native -mavx2 -Wall -Wextra -o p18_connector p18_connector.c -lm
 *
 * Every Linux syscall a traced child makes IS a position on the
 * lemniscate. SYSCALL_MAP[nr] gives the syscall's prime address
 * (idx = nr + 184, prime = P(idx)); die_pos = ring_add(die_pos,
 * ring_pos) advances the element through the ring on every syscall.
 * The element (x_q32, y_q32) is read from the die, not computed per
 * dispatch — it is physically present at every ring position because
 * build_die() put it there once, at startup (Rule 3).
 *
 * The fork+exec approach traces only its own child, so no yama
 * ptrace_scope relaxation or root is required.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/user.h>
#include <sys/types.h>
#include <signal.h>
#include <math.h>
#include <inttypes.h>
#include <errno.h>

#define F12    144
#define Q32    UINT64_C(4294967296)
#define TL     UINT64_C(15350000)
#define O      61
#define LAYER_SYSCALL_OFFSET  183  /* 3 x O */

#include "p18_syscall_map.h"

static inline uint32_t ddgi(uint32_t p) { return p - (p * 13u + 799u) / 800u; }
static inline uint64_t pack_g(uint64_t Fc, uint64_t mu, uint64_t d) {
    return (((Fc << 48) ^ (mu << 32) ^ d) ^ TL) + 1ULL;
}

/* Branchless ring addition — compiles to cmov, not je/jne */
static inline uint8_t ring_add(uint8_t a, uint8_t b) {
    uint32_t s = (uint32_t)a + (uint32_t)b;
    uint32_t t = s - (uint32_t)F12;
    return (uint8_t)(s < (uint32_t)F12 ? s : t);
}

/* Primes — same trial-division sieve as p18_singlepass.c */
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

/* The Die — copied exactly from p18_singlepass.c. The element IS
 * present at every ring position: a = P(k+1)/2, x = 1 + a*cos(t)/(1+sin^2 t),
 * y = a*sin(t)*cos(t)/(1+sin^2 t), t = r18 * pi/9. Genuine libm sin/cos,
 * computed once at startup (Rule 3). */
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
    for (int k = 0; k < F12; k++) {
        uint32_t p = P256[k];
        uint8_t r = (uint8_t)(p % 18u);
        double a = p * 0.5, t = r * (M_PI / 9.0), s = sin(t), c = cos(t), d = 1.0 + s * s;
        DIE.prime[k] = p;
        DIE.r18[k] = r;
        DIE.temporal[k] = ddgi((uint32_t)(k + 1));
        DIE.geostring[k] = pack_g(p < 523 ? 1 : 2, r, DIE.temporal[k]);
        DIE.x_q32[k] = (int64_t)round((1.0 + a * c / d) * (double)Q32);
        DIE.y_q32[k] = (int64_t)round((a * s * c / d) * (double)Q32);
        DIE.base_row[k] = (uint8_t)k;
        DIE.op_vocab[k] = DIE.geostring[k];
    }
    DIE.clear_mask = UINT64_C(0xFFFFFFFF00000000);
    DIE.keep_mask  = UINT64_C(0x00000000FFFFFFFF);
}

static uint8_t die_pos = 0;
static int violations = 0;

static void geo_dispatch_syscall(long syscall_nr, int is_entry) {
    if (syscall_nr < 0 || syscall_nr >= N_SYSCALLS) {
        violations++;
        fprintf(stderr, "VIOLATION: syscall nr=%ld not found in SYSCALL_MAP\n", syscall_nr);
        return;
    }

    const SyscallEntry *e = &SYSCALL_MAP[syscall_nr];

    /* Advance die — element moves through the lemniscate */
    die_pos = ring_add(die_pos, e->ring_pos);

    /* The element IS present — read from die, not computed */
    int64_t  ex = DIE.x_q32[die_pos];
    int64_t  ey = DIE.y_q32[die_pos];

    if (ex == 0 && ey == 0) {
        violations++;
        fprintf(stderr, "VIOLATION: element zero at pos=%u\n", die_pos);
    }

    if (is_entry) {
        printf("  \xe2\x86\x92 syscall %-20s nr=%-4ld "
               "prime=%-6u r18=%2u ring_pos=%3u "
               "elem(x=%+.4f y=%+.4f)\n",
               e->name, syscall_nr,
               e->prime, e->r18, e->ring_pos,
               (double)ex / (double)Q32,
               (double)ey / (double)Q32);
    }
}

int p18_connector_run(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: p18_connector <program> [args...]\n");
        return 1;
    }

    build_primes();
    build_die();

    int ra_ok = 1;
    for (int a = 0; a < F12 && ra_ok; a++) {
        for (int b = 0; b < F12 && ra_ok; b++) {
            if (ring_add((uint8_t)a, (uint8_t)b) != (uint8_t)((a + b) % F12)) ra_ok = 0;
        }
    }
    if (!ra_ok) { violations++; fprintf(stderr, "VIOLATION: ring_add incorrect\n"); }

    if (sizeof(DIE) != 6720) {
        violations++;
        fprintf(stderr, "VIOLATION: die size %zu != 6720\n", sizeof(DIE));
    }

    if (DIE.x_q32[0] == 0 && DIE.y_q32[0] == 0) {
        fprintf(stderr, "VIOLATION: die element zero at pos 0\n");
        return 1;
    }

    printf("P18 Connection Layer\n");
    printf("Die: %zu bytes  ring_pos=0  element present \xe2\x9c\x93\n", sizeof(DIE));
    printf("Intercepting: %s\n\n", argv[1]);

    pid_t child = fork();
    if (child == 0) {
        ptrace(PTRACE_TRACEME, 0, NULL, NULL);
        raise(SIGSTOP);
        execvp(argv[1], argv + 1);
        perror("execvp");
        _exit(1);
    }

    int status;
    waitpid(child, &status, 0);
    ptrace(PTRACE_SETOPTIONS, child, 0, PTRACE_O_TRACESYSGOOD);

    long syscall_count = 0;
    int in_syscall = 0;

    while (1) {
        ptrace(PTRACE_SYSCALL, child, NULL, NULL);
        waitpid(child, &status, 0);

        if (WIFEXITED(status)) break;
        if (WIFSIGNALED(status)) break;
        if (!WIFSTOPPED(status)) continue;
        if ((WSTOPSIG(status) & 0x80) == 0) {
            /* Not a syscall-stop (e.g. real signal) — forward it and continue */
            continue;
        }

        struct user_regs_struct regs;
        if (ptrace(PTRACE_GETREGS, child, NULL, &regs) == -1) continue;

        if (!in_syscall) {
            long nr = (long)regs.orig_rax;
            geo_dispatch_syscall(nr, 1);
            syscall_count++;
            in_syscall = 1;
        } else {
            in_syscall = 0;
        }
    }

    printf("\n=== Connection layer summary ===\n");
    printf("Syscalls intercepted: %ld\n", syscall_count);
    printf("Final die position:   %u\n", die_pos);
    printf("Final element: prime=%u r18=%u x=%.4f y=%.4f\n",
           DIE.prime[die_pos], DIE.r18[die_pos],
           (double)DIE.x_q32[die_pos] / (double)Q32,
           (double)DIE.y_q32[die_pos] / (double)Q32);
    printf("Violations: %d\n", violations);
    return violations;
}

int main(int argc, char **argv) {
    return p18_connector_run(argc, argv);
}
