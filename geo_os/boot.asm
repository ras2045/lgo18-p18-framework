; P18 Geo OS — Multiboot2 boot stub
; Enters in 32-bit protected mode (per multiboot2 / GRUB), builds identity
; page tables, enables long mode, then jumps to 64-bit kernel_main.
; No Linux. No BIOS calls after boot. The lemniscate IS the OS.

MB2_MAGIC       equ 0xe85250d6
MB2_ARCH_I386   equ 0
MB2_HDR_LEN     equ (header_end - header_start)
MB2_CHECKSUM    equ -(MB2_MAGIC + MB2_ARCH_I386 + MB2_HDR_LEN)

section .multiboot_header
align 8
header_start:
    dd MB2_MAGIC
    dd MB2_ARCH_I386
    dd MB2_HDR_LEN
    dd MB2_CHECKSUM
    ; end tag
    align 8
    dw 0    ; type
    dw 0    ; flags
    dd 8    ; size
header_end:

section .bss
align 4096
p4_table:
    resb 4096
p3_table:
    resb 4096
p2_table:
    resb 4096
stack_bottom:
    resb 16384
stack_top:

section .text
bits 32
global _start
extern kernel_main

_start:
    mov esp, stack_top
    mov edi, eax        ; multiboot2 magic (arg0 -> edi for later use as 32-bit)
    mov esi, ebx         ; multiboot info physical address (arg1)

    call check_multiboot
    call check_cpuid
    call check_long_mode

    call set_up_page_tables
    call enable_paging

    lgdt [gdt64.pointer]
    jmp gdt64.code:long_mode_start

    ; should never return
    hlt

check_multiboot:
    cmp edi, 0x36d76289
    jne .no_multiboot
    ret
.no_multiboot:
    mov al, "0"
    jmp error

check_cpuid:
    pushfd
    pop eax
    mov ecx, eax
    xor eax, 1 << 21
    push eax
    popfd
    pushfd
    pop eax
    push ecx
    popfd
    cmp eax, ecx
    je .no_cpuid
    ret
.no_cpuid:
    mov al, "1"
    jmp error

check_long_mode:
    mov eax, 0x80000000
    cpuid
    cmp eax, 0x80000001
    jb .no_long_mode

    mov eax, 0x80000001
    cpuid
    test edx, 1 << 29
    jz .no_long_mode
    ret
.no_long_mode:
    mov al, "2"
    jmp error

set_up_page_tables:
    ; p4[0] -> p3_table
    mov eax, p3_table
    or eax, 0b11        ; present + writable
    mov [p4_table], eax

    ; p3[0] -> p2_table
    mov eax, p2_table
    or eax, 0b11
    mov [p3_table], eax

    ; identity map first 1GiB with 2MiB pages
    mov ecx, 0
.map_p2_table:
    mov eax, 0x200000       ; 2MiB
    mul ecx
    or eax, 0b10000011      ; present + writable + huge page
    mov [p2_table + ecx * 8], eax

    inc ecx
    cmp ecx, 512
    jne .map_p2_table

    ret

enable_paging:
    ; load P4 into cr3
    mov eax, p4_table
    mov cr3, eax

    ; enable PAE
    mov eax, cr4
    or eax, 1 << 5
    mov cr4, eax

    ; set the long mode bit in EFER MSR
    mov ecx, 0xC0000080
    rdmsr
    or eax, 1 << 8
    wrmsr

    ; enable paging
    mov eax, cr0
    or eax, 1 << 31
    mov cr0, eax

    ret

; Print "ERR: X" to VGA text buffer then halt (protected-mode error path only)
error:
    mov dword [0xb8000], 0x4f524f45
    mov dword [0xb8004], 0x4f3a4f52
    mov dword [0xb8008], 0x4f204f20
    mov byte  [0xb800a], al
    hlt

section .rodata
align 8
gdt64:
    dq 0 ; zero entry
.code: equ $ - gdt64
    dq (1<<43) | (1<<44) | (1<<47) | (1<<53) ; code segment: exec, code/data, present, long mode
.pointer:
    dw $ - gdt64 - 1
    dq gdt64

section .text
bits 64
extern kernel_main
long_mode_start:
    ; clear segment registers (flat model, segmentation unused in long mode)
    mov ax, 0
    mov ss, ax
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax

    mov rsp, stack_top

    ; kernel_main(uint32_t magic, uint64_t mbi_addr)
    ; edi already holds magic (zero-extended into rdi), esi holds mbi phys addr
    mov edi, edi        ; magic (32-bit, upper rdi bits already zero from 32-bit mov)
    mov esi, esi        ; mbi address zero-extended into rsi
    call kernel_main

    ; if kernel_main ever returns, halt forever
.hang:
    hlt
    jmp .hang
