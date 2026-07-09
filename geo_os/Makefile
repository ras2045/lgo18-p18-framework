# P18 Geo OS — build, ISO, run
# No Linux. The lemniscate IS the OS.

CC      = gcc
NASM    = nasm
FREESTANDING_INC = $(shell $(CC) -print-file-name=include)
CFLAGS  = -O2 -ffreestanding -fno-stack-protector -fno-pic \
          -mno-red-zone -mno-mmx -mno-sse -mno-sse2 \
          -Wall -Wextra -nostdinc -isystem $(FREESTANDING_INC) \
          -nostdlib -march=x86-64 -c
LDFLAGS = -n -T linker.ld -nostdlib

ISO_DIR = isodir
KERNEL  = kernel.bin
ISO     = p18_geo_os.iso

all: $(KERNEL)

boot.o: boot.asm
	$(NASM) -f elf64 boot.asm -o boot.o

kernel.o: kernel.c
	$(CC) $(CFLAGS) kernel.c -o kernel.o

$(KERNEL): boot.o kernel.o linker.ld
	ld $(LDFLAGS) -o $(KERNEL) boot.o kernel.o

iso: $(KERNEL) grub.cfg
	rm -rf $(ISO_DIR)
	mkdir -p $(ISO_DIR)/boot/grub
	cp $(KERNEL) $(ISO_DIR)/boot/kernel.bin
	cp grub.cfg $(ISO_DIR)/boot/grub/grub.cfg
	grub-mkrescue -o $(ISO) $(ISO_DIR)

run: iso
	qemu-system-x86_64 -cdrom $(ISO) -m 64M -serial stdio -display none -no-reboot

clean:
	rm -rf *.o $(KERNEL) $(ISO) $(ISO_DIR)

.PHONY: all iso run clean
