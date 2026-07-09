#!/usr/bin/env bash
# P18 Geometric Runtime — full suite build and run (all 21 programs).
set -u
cd "$(dirname "$0")"

echo "============================================================="
echo "P18 Geometric Runtime — Full Suite"
echo "============================================================="

if grep -qm1 avx2 /proc/cpuinfo; then
    echo "[ok] AVX2 present in /proc/cpuinfo"
else
    echo "[FAIL] AVX2 not found in /proc/cpuinfo — AVX2 programs will not run correctly"
    exit 1
fi

# Generate the bytecode disassembly p18_highlevel needs, from a real script.
MAPPER_PY="../lgo18_mapper_v4.py"
DIS_FILE="/tmp/p18_dis.txt"
if [ -f "$MAPPER_PY" ]; then
    python3 -m dis "$MAPPER_PY" > "$DIS_FILE" 2>/dev/null
fi

echo
echo "-- compiling --"
BUILD_FAIL=0

build() {
    local name="$1"; shift
    echo "  $*"
    if ! "$@" 2>"build_err_$name.log"; then
        echo "  [FAIL] $name failed to compile:"
        cat "build_err_$name.log"
        BUILD_FAIL=1
    else
        if [ -s "build_err_$name.log" ]; then
            echo "  [WARN] $name compiled with warnings:"
            cat "build_err_$name.log"
        else
            echo "  [ok] $name compiled, zero warnings"
        fi
    fi
    rm -f "build_err_$name.log"
}

CC="gcc"
CFLAGS_STD="-O3 -march=native -mavx2 -Wall -Wextra"

build scalar_floor  $CC -O0 -Wall -Wextra -o p18_scalar_floor p18_scalar_floor.c -lm
build local         $CC $CFLAGS_STD -o p18_local p18_local.c -lm
build optable       $CC -O3 -march=native -Wall -Wextra -o p18_optable p18_optable.c -lm
build xxxvi         $CC -O3 -march=native -Wall -Wextra -o p18_xxxvi p18_xxxvi.c -lm
build integer       $CC $CFLAGS_STD -o p18_integer p18_integer.c -lm
build capabilities  $CC $CFLAGS_STD -o p18_capabilities p18_capabilities.c -lm
build gvm           $CC $CFLAGS_STD -o p18_gvm p18_gvm.c -lm
build exec          $CC $CFLAGS_STD -o p18_exec p18_exec.c -lm
build die           $CC $CFLAGS_STD -o p18_die p18_die.c -lm
build geo_arith     $CC $CFLAGS_STD -o p18_geo_arith p18_geo_arith.c -lm
build highlevel     $CC $CFLAGS_STD -o p18_highlevel p18_highlevel.c -lm
build alpha         $CC -O3 -march=native -Wall -Wextra -o p18_alpha p18_alpha.c -lm
build alpha_control $CC -O3 -march=native -Wall -Wextra -o p18_alpha_control p18_alpha_control.c -lm
build pipeline      $CC $CFLAGS_STD -o p18_pipeline p18_pipeline.c -lm
build geomodel      $CC $CFLAGS_STD -o p18_geomodel p18_geomodel.c -lm
build instring      $CC $CFLAGS_STD -o p18_instring p18_instring.c -lm
build pure          $CC $CFLAGS_STD -o p18_pure p18_pure.c -lm
build piece1        $CC -O3 -march=native -Wall -Wextra -o p18_piece1 p18_piece1.c -lm
build piece2        $CC -O3 -march=native -Wall -Wextra -o p18_piece2 p18_piece2.c -lm
build piece3        $CC -O3 -march=native -Wall -Wextra -o p18_piece3 p18_piece3.c -lm
build piece4        $CC -O3 -march=native -Wall -Wextra -o p18_piece4 p18_piece4.c -lm

if [ "$BUILD_FAIL" -ne 0 ]; then
    echo
    echo "[FAIL] one or more programs failed to compile — aborting"
    exit 1
fi

echo
echo "-- running --"

run() {
    local label="$1" bin="$2"; shift 2
    echo
    echo "===== $label ====="
    ./"$bin" "$@"
    local rc=$?
    echo "----- $label: return code (violations) = $rc -----"
    return $rc
}

# For programs that read a piped bytecode stream (python3 -m dis | ./prog)
# rather than a file argument.
run_piped() {
    local label="$1" bin="$2"
    echo
    echo "===== $label ====="
    python3 -m dis ../lgo18_mapper_v4.py | ./"$bin"
    local rc=$?
    echo "----- $label: return code (violations) = $rc -----"
    return $rc
}

declare -A RC
run "1/21  p18_scalar_floor  (-O0 scalar baseline)"          p18_scalar_floor;        RC[scalar_floor]=$?
run "2/21  p18_local         (-O3 -mavx2 ring buffer)"       p18_local;               RC[local]=$?
run "3/21  p18_optable       (operation translation table)"  p18_optable;             RC[optable]=$?
run "4/21  p18_xxxvi         (x86-64 -> geostring mapping)"  p18_xxxvi;               RC[xxxvi]=$?
run "5/21  p18_integer       (zero-float integer runtime)"   p18_integer;             RC[integer]=$?
run "6/21  p18_capabilities  (7-subsystem test suite)"       p18_capabilities;        RC[capabilities]=$?
run "7/21  p18_gvm           (GVM ingestion layer)"          p18_gvm ./p18_gvm;       RC[gvm]=$?
run "8/21  p18_exec          (execution layer)"              p18_exec;               RC[exec]=$?
run "9/21  p18_die           (L1-cached die extrusion)"      p18_die;                 RC[die]=$?
run "10/21 p18_geo_arith     (geometric arithmetic)"         p18_geo_arith;           RC[geo_arith]=$?
run "11/21 p18_highlevel     (Python bytecode ingestion)"    p18_highlevel "$DIS_FILE"; RC[highlevel]=$?
run "12/21 p18_alpha         (fine structure constant)"      p18_alpha;               RC[alpha]=$?
run "13/21 p18_alpha_control (random-control test)"          p18_alpha_control;       RC[alpha_control]=$?
run "14/21 p18_pipeline      (GVM -> exec pipeline)"          p18_pipeline ./p18_pipeline; RC[pipeline]=$?
run "15/21 p18_geomodel      (geometric addressing model)"    p18_geomodel;            RC[geomodel]=$?
run "16/21 p18_instring     (in-string ring execution)"       p18_instring ../lgo18_mapper_v4.py; RC[instring]=$?
run "17/21 p18_pure         (pure in-string engine)"      p18_pure ../lgo18_mapper_v4.py; RC[pure]=$?
run "18/21 p18_piece1      (state transition table)"      p18_piece1;              RC[piece1]=$?
run_piped "19/21 p18_piece2      (branchless execution engine)"  p18_piece2; RC[piece2]=$?
run_piped "20/21 p18_piece3      (complete pipeline)"             p18_piece3; RC[piece3]=$?
run_piped "21/21 p18_piece4      (L1-resident instruction set)"  p18_piece4; RC[piece4]=$?

TOTAL=0
for k in "${!RC[@]}"; do TOTAL=$((TOTAL + RC[$k])); done

echo
echo "============================================================="
echo "FINAL SUMMARY"
echo "============================================================="
for name in scalar_floor local optable xxxvi integer capabilities gvm exec die geo_arith highlevel alpha alpha_control pipeline geomodel instring pure piece1 piece2 piece3 piece4; do
    rc=${RC[$name]}
    printf "  %-16s %s\n" "$name" "$([ "$rc" -eq 0 ] && echo PASS || echo "FAIL ($rc violations)")"
done
echo
echo "  Total violations across all 21 programs: $TOTAL"
if [ "$TOTAL" -eq 0 ]; then
    echo "  ALL PASS — zero violations"
else
    echo "  FAILED — see program output above"
fi
echo "============================================================="

exit "$TOTAL"
