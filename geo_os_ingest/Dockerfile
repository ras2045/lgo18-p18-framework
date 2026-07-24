# Geo OS v2 — Universal OS Ingestion Container
# Ingests any OS binary (Linux ELF, Windows PE, macOS Mach-O) through
# the lemniscate ∞ kernel. The element ∞ is always present.
#
# Build:  docker build -t geo-os-ingestor:v2 .
# Usage:  docker run --rm -v /path/to/os:/data geo-os-ingestor:v2 /data/vmlinuz
#         docker run --rm -v $(pwd):/data geo-os-ingestor:v2 /data/ntoskrnl.exe /data/out.geostring

FROM python:3.12-slim

LABEL maintainer="P18 Geo OS Framework"
LABEL description="Geo OS v2 — Universal OS Ingestion via Lemniscate ∞ Kernel"
LABEL version="2.0"

# Build tools for C HAL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    make \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /geo_os

# Copy source
COPY src/geo_os_dispatch.h  src/
COPY src/geo_os_hal.c       src/
COPY src/geo_os_ingestor.py src/
COPY Makefile               .

# Build C HAL
RUN make all

# Run self-verification at build time (0 violations required)
RUN python3 src/geo_os_ingestor.py --verify

# Mount point for OS binaries
VOLUME ["/data"]

# Entrypoint: pass OS binary path as argument
# If no argument: run verification and show help
ENTRYPOINT ["/bin/sh", "-c", "\
    if [ $# -eq 0 ]; then \
        echo 'Geo OS v2 — Universal OS Ingestion Container'; \
        echo 'Usage: docker run --rm -v /path:/data geo-os-ingestor:v2 /data/<os_binary>'; \
        echo ''; \
        python3 /geo_os/src/geo_os_ingestor.py --verify; \
    elif [ \"$1\" = \"--verify\" ]; then \
        python3 /geo_os/src/geo_os_ingestor.py --verify; \
    else \
        INPUT=$1; OUTPUT=${2:-${1%.??}.geostring}; \
        echo \"Ingesting: $INPUT → $OUTPUT\"; \
        python3 /geo_os/src/geo_os_ingestor.py \"$INPUT\" \"$OUTPUT\"; \
        /geo_os/geo_os_hal \"$INPUT\" \"${OUTPUT%.geostring}_hal.geostring\" 2>/dev/null || true; \
    fi \
", "--"]
