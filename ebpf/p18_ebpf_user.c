/*
 * P18 eBPF Connection Layer — Userspace Consumer (system-wide)
 * Reads syscall events from the BPF ring buffer, routes them through
 * the geometric die. The element IS present at every ring position —
 * read from the die, not computed per event.
 *
 * gcc -O3 -march=native -mavx2 -Wall -Wextra \
 *     -o p18_ebpf_user p18_ebpf_user.c -lbpf -lelf -lz -lm
 *
 * Requires root (or CAP_BPF+CAP_PERFMON) to load/attach the BPF
 * program — it traces every syscall on the system while it runs.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <math.h>
#include <bpf/libbpf.h>
#include <bpf/bpf.h>
#include <inttypes.h>
#include <sys/resource.h>

#include "p18_syscall_map.h" /* 335 entries, from p18_connector */

#define F12 144
#define Q32 UINT64_C(4294967296)
#define TL  UINT64_C(15350000)

static inline uint32_t ddgi(uint32_t p) { return p - (p * 13u + 799u) / 800u; }
static inline uint64_t pack_g(uint64_t Fc, uint64_t mu, uint64_t d) {
    return (((Fc << 48) ^ (mu << 32) ^ d) ^ TL) + 1ULL;
}
static inline uint8_t ring_add(uint8_t a, uint8_t b) {
    uint32_t s = (uint32_t)a + (uint32_t)b;
    uint32_t t = s - (uint32_t)F12;
    return (uint8_t)(s < (uint32_t)F12 ? s : t);
}

/* Primes — same trial-division sieve as p18_connector.c */
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

/* The Die — identical to p18_connector.c. Genuine libm sin/cos,
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
static volatile sig_atomic_t running = 1;
static long syscall_count = 0;
static int violations = 0;

struct p18_event {
    uint64_t pid;
    uint64_t syscall_nr;
    uint64_t timestamp_ns;
};

static int handle_event(void *ctx, void *data, size_t size) {
    (void)ctx; (void)size;
    const struct p18_event *e = data;
    long nr = (long)e->syscall_nr;

    if (nr < 0 || nr >= N_SYSCALLS) return 0;

    const SyscallEntry *entry = &SYSCALL_MAP[nr];

    die_pos = ring_add(die_pos, entry->ring_pos);
    syscall_count++;

    int64_t ex = DIE.x_q32[die_pos];
    int64_t ey = DIE.y_q32[die_pos];

    if (ex == 0 && ey == 0) {
        violations++;
        fprintf(stderr, "VIOLATION: element zero at pos=%u\n", die_pos);
    }

    if (syscall_count <= 50 || syscall_count % 100 == 0) {
        printf("  [%5ld] pid=%-6lu %-20s nr=%-4ld "
               "prime=%-6u r18=%2u "
               "elem(x=%+.4f y=%+.4f)\n",
               syscall_count,
               (unsigned long)e->pid,
               entry->name, nr,
               entry->prime, entry->r18,
               (double)ex / (double)Q32,
               (double)ey / (double)Q32);
    }

    return 0;
}

static void sig_handler(int sig) { (void)sig; running = 0; }

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    struct bpf_object *obj = NULL;
    struct bpf_program *prog = NULL;
    struct bpf_link *link = NULL;
    struct ring_buffer *rb = NULL;
    int map_fd, err;

    struct rlimit rl = { RLIM_INFINITY, RLIM_INFINITY };
    setrlimit(RLIMIT_MEMLOCK, &rl);

    build_primes();
    build_die();

    int ra_ok = 1;
    for (int a = 0; a < F12 && ra_ok; a++)
        for (int b = 0; b < F12 && ra_ok; b++)
            if (ring_add((uint8_t)a, (uint8_t)b) != (uint8_t)((a + b) % F12)) ra_ok = 0;
    if (!ra_ok) { violations++; fprintf(stderr, "VIOLATION: ring_add incorrect\n"); }

    if (sizeof(DIE) != 6720) {
        violations++;
        fprintf(stderr, "VIOLATION: die size %zu != 6720\n", sizeof(DIE));
    }

    printf("P18 eBPF Connection Layer\n");
    printf("Die: %zu bytes  ring_add \xe2\x86\x92 cmov  element present \xe2\x9c\x93\n", sizeof(DIE));
    printf("Monitoring ALL syscalls (Ctrl-C to stop)\n\n");

    obj = bpf_object__open_file("p18_ebpf_kern.o", NULL);
    if (libbpf_get_error(obj)) {
        fprintf(stderr, "Failed to open BPF object\n");
        return 1;
    }

    err = bpf_object__load(obj);
    if (err) {
        fprintf(stderr, "Failed to load BPF object: %d\n", err);
        goto cleanup;
    }

    prog = bpf_object__find_program_by_name(obj, "p18_sys_enter");
    if (!prog) {
        fprintf(stderr, "Failed to find BPF program\n");
        goto cleanup;
    }

    link = bpf_program__attach(prog);
    if (libbpf_get_error(link)) {
        fprintf(stderr, "Failed to attach BPF program\n");
        goto cleanup;
    }

    map_fd = bpf_object__find_map_fd_by_name(obj, "events");
    rb = ring_buffer__new(map_fd, handle_event, NULL, NULL);
    if (!rb) {
        fprintf(stderr, "Failed to open ring buffer\n");
        goto cleanup;
    }

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    printf("Attached. Intercepting syscalls system-wide...\n\n");

    while (running) {
        ring_buffer__poll(rb, 100);
    }

    printf("\n=== eBPF Connection Layer Summary ===\n");
    printf("Syscalls intercepted: %ld\n", syscall_count);
    printf("Final die position:   %u\n", die_pos);
    printf("Final element: prime=%-6u r18=%u x=%.4f y=%.4f\n",
           DIE.prime[die_pos], DIE.r18[die_pos],
           (double)DIE.x_q32[die_pos] / (double)Q32,
           (double)DIE.y_q32[die_pos] / (double)Q32);
    printf("Violations: %d\n", violations);

cleanup:
    ring_buffer__free(rb);
    bpf_link__destroy(link);
    bpf_object__close(obj);
    return violations;
}
