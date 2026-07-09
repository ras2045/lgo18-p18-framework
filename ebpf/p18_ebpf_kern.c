// SPDX-License-Identifier: GPL-2.0
// P18 eBPF Connection Layer — kernel-side program.
// Fires at every syscall entry (tracepoint/raw_syscalls/sys_enter),
// runs inside the kernel, and hands (pid, syscall_nr, timestamp) to
// userspace over a lock-free ring buffer. No die logic here — the
// geometric dispatch (ring_add, element lookup) happens in userspace,
// where the die (L1-resident struct) actually lives.
//
// Compile: clang -O2 -target bpf -c p18_ebpf_kern.c -o p18_ebpf_kern.o

#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1 << 20); /* 1MB ring buffer */
} events SEC(".maps");

/* Optional target-PID filter, set by userspace before attaching.
 * key 0 -> target pid, or 0 to mean "trace everything". */
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} target_pid SEC(".maps");

struct p18_event {
    __u64 pid;
    __u64 syscall_nr;
    __u64 timestamp_ns;
};

SEC("tracepoint/raw_syscalls/sys_enter")
int p18_sys_enter(struct trace_event_raw_sys_enter *ctx) {
    __u64 pid = bpf_get_current_pid_tgid() >> 32;

    __u32 key = 0;
    __u64 *target = bpf_map_lookup_elem(&target_pid, &key);
    if (target && *target != 0 && pid != *target) return 0;

    struct p18_event *e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
    if (!e) return 0;

    e->pid          = pid;
    e->syscall_nr   = ctx->id;
    e->timestamp_ns = bpf_ktime_get_ns();

    bpf_ringbuf_submit(e, 0);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
