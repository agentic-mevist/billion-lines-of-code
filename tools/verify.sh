#!/usr/bin/env bash
# Independently verify the line count. Run it yourself. That is the whole point.
#
#   ./tools/verify.sh
#
# Deliberately uses boring, universally available tools so nobody has to take
# our word for anything. If `scc` is installed it gets consulted too, because a
# third-party counter that splits code from comments is harder to argue with.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

TARGET=1000000000
SRC=src

if [ ! -d "$SRC" ]; then
  echo "No $SRC/ directory. Generate it first:"
  echo "  python3 tools/generate_slop.py --out src"
  exit 1
fi

echo "=============================================================="
echo " BILLION LINES OF CODE :: VERIFICATION"
echo "=============================================================="
echo

# --- Guard: src/ must contain source files only. -----------------------------
# A stray binary (a .pyc from compiling in-tree, say) would inflate `wc -l` with
# newline bytes that are not lines. We caught exactly that during development,
# so now we refuse to count anything that is not a known source extension.
STRAY=$(find "$SRC" -type f ! \( -name '*.js' -o -name '*.ts' -o -name '*.py' \
        -o -name '*.java' -o -name '*.go' \) | head -20)
if [ -n "$STRAY" ]; then
  echo "REFUSING TO COUNT: non-source files found under $SRC/:"
  echo "$STRAY"
  exit 1
fi
echo "[1/5] Source-purity check ............ OK (no non-source files in $SRC/)"

# --- Files -------------------------------------------------------------------
FILES=$(find "$SRC" -type f | wc -l)
printf "[2/5] Files .......................... %'d\n" "$FILES"

# --- The number ---------------------------------------------------------------
echo "[3/5] Counting lines with wc(1) ...... (reading every byte, please wait)"
LINES=$(find "$SRC" -type f -print0 | xargs -0 cat | wc -l)
printf "      wc -l total .................... %'d\n" "$LINES"

BYTES=$(find "$SRC" -type f -printf '%s\n' | awk '{s+=$1} END{print s}')
printf "[4/5] Bytes on disk .................. %'d (%.2f GiB)\n" \
       "$BYTES" "$(awk -v b="$BYTES" 'BEGIN{print b/1073741824}')"

# --- Third-party opinion -----------------------------------------------------
if command -v scc >/dev/null 2>&1; then
  echo "[5/5] Third-party counter (scc) ......"
  scc --no-cocomo "$SRC"
else
  echo "[5/5] scc not installed - skipping third-party cross-check."
  echo "      go install github.com/boyter/scc/v3@latest"
fi

echo
echo "=============================================================="
if [ "$LINES" -eq "$TARGET" ]; then
  printf " RESULT: EXACTLY %'d LINES. \xf0\x9f\x8e\x89\n" "$TARGET"
  echo "=============================================================="
  exit 0
else
  printf " RESULT: %'d lines (target %'d, off by %'d)\n" \
         "$LINES" "$TARGET" "$((LINES - TARGET))"
  echo "=============================================================="
  exit 1
fi
