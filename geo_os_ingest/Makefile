# Geo OS v2 — Universal OS Ingestion Build System
# The element ∞ is always present. Universe uses geometry, not numbers.

CC      = gcc
CFLAGS  = -O3 -march=native -std=c11 -Wall -Wextra -pedantic \
          -fno-math-errno -fno-signed-zeros
TARGET  = geo_os_hal
SRC     = src/geo_os_hal.c
HDR     = src/geo_os_dispatch.h

.PHONY: all clean verify docker run-linux run-macos run-windows test

all: $(TARGET)

$(TARGET): $(SRC) $(HDR)
	@echo "Building Geo OS v2 HAL (Q32, no IEEE 754)..."
	$(CC) $(CFLAGS) -o $@ $(SRC)
	@echo "Built: ./$(TARGET)"

verify: all
	@echo "\nRunning Geo OS v2 self-verification..."
	python3 src/geo_os_ingestor.py --verify

# Ingest current system kernel (Linux)
run-linux: all
	@KERNEL=$$(ls /boot/vmlinuz* 2>/dev/null | head -1); \
	if [ -z "$$KERNEL" ]; then KERNEL=/boot/vmlinuz; fi; \
	if [ -f "$$KERNEL" ]; then \
	    echo "Ingesting Linux kernel: $$KERNEL"; \
	    ./$(TARGET) "$$KERNEL" kernel.geostring; \
	    python3 src/geo_os_ingestor.py "$$KERNEL"; \
	else \
	    echo "No kernel found at /boot/vmlinuz. Pass path explicitly:"; \
	    echo "  ./$(TARGET) <kernel> output.geostring"; \
	fi

# Ingest macOS kernel
run-macos: all
	@KERNEL=/System/Library/Kernels/kernel; \
	if [ -f "$$KERNEL" ]; then \
	    echo "Ingesting macOS kernel: $$KERNEL"; \
	    python3 src/geo_os_ingestor.py "$$KERNEL"; \
	else \
	    echo "macOS kernel not found at $$KERNEL"; \
	    echo "  Copy kernel to this directory and run:"; \
	    echo "  python3 src/geo_os_ingestor.py kernel output.geostring"; \
	fi

# Ingest Windows NT kernel (must be copied here)
run-windows: all
	@KERNEL=ntoskrnl.exe; \
	if [ -f "$$KERNEL" ]; then \
	    echo "Ingesting Windows kernel: $$KERNEL"; \
	    python3 src/geo_os_ingestor.py "$$KERNEL"; \
	else \
	    echo "Windows NT kernel not found. Copy ntoskrnl.exe here and run:"; \
	    echo "  python3 src/geo_os_ingestor.py ntoskrnl.exe output.geostring"; \
	fi

# Ingest any binary
ingest: all
	@if [ -z "$(INPUT)" ]; then \
	    echo "Usage: make ingest INPUT=<path_to_os_binary>"; \
	    echo "       make ingest INPUT=<path> OUTPUT=<out.geostring>"; \
	else \
	    OUT=$${OUTPUT:-$(INPUT).geostring}; \
	    echo "Ingesting: $(INPUT) → $$OUT"; \
	    python3 src/geo_os_ingestor.py "$(INPUT)" "$$OUT"; \
	fi

test: all verify
	@echo "\nRunning full test suite..."
	python3 test/geo_os_verify.py
	@echo "All tests passed — 0 violations ✓"

# Docker build
docker:
	docker build -t geo-os-ingestor:v2 .
	@echo "\nContainer built: geo-os-ingestor:v2"
	@echo "Usage: docker run --rm -v \$$(pwd):/data geo-os-ingestor:v2 /data/<kernel>"

clean:
	rm -f $(TARGET) *.geostring *_geo_manifest.json
	@echo "Cleaned."

help:
	@echo "Geo OS v2 — Universal OS Ingestion System"
	@echo ""
	@echo "Targets:"
	@echo "  make all              Build C HAL (geo_os_hal)"
	@echo "  make verify           Self-verify all Geo OS v2 constants"
	@echo "  make run-linux        Ingest detected Linux kernel"
	@echo "  make run-macos        Ingest macOS kernel"
	@echo "  make run-windows      Ingest ntoskrnl.exe (must copy here)"
	@echo "  make ingest INPUT=x   Ingest any OS binary"
	@echo "  make test             Full test suite"
	@echo "  make docker           Build Docker container"
	@echo "  make clean            Remove build artifacts"
	@echo ""
	@echo "  The element ∞ is always present."
	@echo "  1/α = 137.035999083116  (B3 CLOSED)"
