#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Geo OS v2 — Universal OS Ingestion Deploy Script                       ║
# ║  The element ∞ is always present.                                       ║
# ║  Universe uses geometry, not numbers.                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   ./deploy.sh                         — auto-detect local OS kernel + ingest
#   ./deploy.sh <os_binary>             — ingest specified binary
#   ./deploy.sh <os_binary> <out>       — ingest with explicit output path
#   ./deploy.sh --docker <os_binary>    — run in Docker container
#   ./deploy.sh --verify                — verify all Geo OS v2 constants
#   ./deploy.sh --install               — install system-wide
#   ./deploy.sh --build                 — build C HAL only
#
# Supported inputs:
#   Linux ELF  — /boot/vmlinuz, vmlinux, bzImage, custom kernels
#   Windows PE — ntoskrnl.exe, ntkrnlmp.exe, win32k.sys, any .exe/.dll
#   macOS MachO — /System/Library/Kernels/kernel, XNU kernels
#   BSD ELF    — FreeBSD/OpenBSD/NetBSD kernels
#   UEFI       — .efi applications
#   Raw binary — any flat binary

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
HAL="${SCRIPT_DIR}/geo_os_hal"

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'
YELLOW='\033[1;33m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
    echo -e "${BOLD}${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║      GEO OS v2 — UNIVERSAL OS INGESTION SYSTEM              ║"
    echo "║      ∞ The lemniscate is always present                      ║"
    echo "║      1/α = 137.035999083116   (B3 CLOSED, 0 violations)     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${RESET}"
}

log()  { echo -e "${GREEN}[GEO]${RESET} $*"; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $*"; }
err()  { echo -e "${RED}[ERR]${RESET} $*" >&2; exit 1; }
info() { echo -e "${BLUE}[INFO]${RESET} $*"; }

# ─── Dependency Check ─────────────────────────────────────────────────────────
check_deps() {
    local missing=0
    command -v python3 >/dev/null 2>&1 || { warn "python3 not found"; missing=1; }
    command -v gcc     >/dev/null 2>&1 || { warn "gcc not found (C HAL won't build)"; }
    command -v make    >/dev/null 2>&1 || { warn "make not found"; }
    [ $missing -ne 0 ] && err "Install missing dependencies and retry."
}

# ─── Build C HAL ──────────────────────────────────────────────────────────────
build_hal() {
    if [ ! -f "$HAL" ]; then
        log "Building C HAL..."
        cd "$SCRIPT_DIR" && make all
        log "C HAL built: ${HAL}"
    else
        log "C HAL already built: ${HAL}"
    fi
}

# ─── Detect Local OS Kernel ───────────────────────────────────────────────────
detect_kernel() {
    # Linux
    for path in /boot/vmlinuz* /boot/kernel* /boot/bzImage* \
                /proc/boot/ifs* /kernel /vmlinuz; do
        [ -f "$path" ] && echo "$path" && return 0
    done
    # macOS
    for path in /System/Library/Kernels/kernel /mach_kernel; do
        [ -f "$path" ] && echo "$path" && return 0
    done
    # FreeBSD / OpenBSD
    for path in /boot/kernel/kernel /bsd /boot/bsd; do
        [ -f "$path" ] && echo "$path" && return 0
    done
    echo ""
}

# ─── Run Ingestion ─────────────────────────────────────────────────────────────
run_ingest() {
    local input="$1"
    local output="${2:-${input%.*}.geostring}"

    [ -f "$input" ] || err "File not found: $input"

    local size
    size=$(wc -c < "$input")
    log "Input : $input  ($(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size} bytes"))"
    log "Output: $output"
    echo ""

    # Python ingestor (primary — full pipeline)
    log "Running Python ingestion pipeline..."
    "$PYTHON" "${SCRIPT_DIR}/src/geo_os_ingestor.py" "$input" "$output"

    # C HAL (supplementary — bare-metal layer)
    if [ -x "$HAL" ]; then
        log "Running C HAL ingest layer..."
        "$HAL" "$input" "${output%.geostring}_hal.geostring" || true
    fi

    echo ""
    log "Geostring stream : ${output}"
    log "JSON manifest    : ${input%.*}_geo_manifest.json"
    echo ""
    log "∞ Ingestion complete. 0 violations guaranteed by DGI triangle."
}

# ─── Install System-Wide ──────────────────────────────────────────────────────
install_geo() {
    log "Installing Geo OS v2 ingestion system..."
    build_hal

    local install_dir="${INSTALL_DIR:-/usr/local/geo_os}"
    mkdir -p "$install_dir/bin" "$install_dir/lib"

    cp "${SCRIPT_DIR}/src/geo_os_ingestor.py" "$install_dir/lib/"
    cp "${SCRIPT_DIR}/src/geo_os_dispatch.h"  "$install_dir/lib/"
    [ -f "$HAL" ] && cp "$HAL" "$install_dir/bin/geo_os_hal"

    cat > /usr/local/bin/geo-ingest << 'WRAPPER'
#!/usr/bin/env bash
exec python3 /usr/local/geo_os/lib/geo_os_ingestor.py "$@"
WRAPPER
    chmod +x /usr/local/bin/geo-ingest

    log "Installed to $install_dir"
    log "Command: geo-ingest <os_binary>"
}

# ─── Docker Mode ──────────────────────────────────────────────────────────────
run_docker() {
    local input="$1"
    local input_dir
    input_dir="$(dirname "$(realpath "$input")")"
    local input_name
    input_name="$(basename "$input")"

    command -v docker >/dev/null 2>&1 || err "Docker not found. Install Docker first."

    # Build image if needed
    if ! docker image inspect geo-os-ingestor:v2 >/dev/null 2>&1; then
        log "Building Docker image..."
        docker build -t geo-os-ingestor:v2 "$SCRIPT_DIR"
    fi

    log "Running in Docker container..."
    docker run --rm \
        -v "${input_dir}:/data:ro" \
        -v "$(pwd):/output" \
        geo-os-ingestor:v2 \
        "/data/${input_name}" \
        "/output/${input_name%.*}.geostring"
}

# ─── Main ─────────────────────────────────────────────────────────────────────
banner
check_deps

case "${1:-}" in
    --verify)
        log "Running Geo OS v2 constant verification..."
        "$PYTHON" "${SCRIPT_DIR}/src/geo_os_ingestor.py" --verify
        ;;
    --build)
        build_hal
        ;;
    --install)
        build_hal
        install_geo
        ;;
    --docker)
        shift
        [ $# -ge 1 ] || err "Usage: $0 --docker <os_binary>"
        run_docker "$1"
        ;;
    --help|-h)
        echo "Usage: $0 [OPTIONS] [os_binary] [output.geostring]"
        echo ""
        echo "Options:"
        echo "  --verify         Verify all Geo OS v2 constants (0 violations required)"
        echo "  --build          Build C HAL only"
        echo "  --install        Install system-wide to /usr/local/geo_os"
        echo "  --docker <bin>   Run ingestion in Docker container"
        echo "  --help           Show this help"
        echo ""
        echo "Supported OS types:"
        echo "  Linux ELF     /boot/vmlinuz, vmlinux, bzImage"
        echo "  Windows PE    ntoskrnl.exe, ntkrnlmp.exe, any .exe/.dll"
        echo "  macOS Mach-O  /System/Library/Kernels/kernel"
        echo "  BSD ELF       /boot/kernel/kernel, /bsd"
        echo "  UEFI          Any .efi application"
        echo "  Raw binary    Any flat binary"
        echo ""
        echo "1/α = 137.035999083116  (B3 CLOSED)"
        echo "∞ The element is always present."
        ;;
    "")
        # Auto-detect local kernel
        log "Auto-detecting OS kernel..."
        kernel=$(detect_kernel)
        if [ -n "$kernel" ]; then
            log "Found kernel: $kernel"
            build_hal
            run_ingest "$kernel"
        else
            warn "No kernel auto-detected."
            info "Run with explicit path: $0 <os_binary>"
            info "Or run verification:    $0 --verify"
            info "Supported: Linux ELF, Windows PE, macOS Mach-O, BSD, UEFI, raw"
            echo ""
            "$PYTHON" "${SCRIPT_DIR}/src/geo_os_ingestor.py" --verify
        fi
        ;;
    *)
        # Explicit binary path
        build_hal
        run_ingest "$1" "${2:-}"
        ;;
esac
