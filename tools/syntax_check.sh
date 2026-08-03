#!/usr/bin/env bash
# Prove the billion lines are actually CODE, not a billion newlines.
#
#   ./tools/syntax_check.sh [files_per_language]   # default 6
#
# Every check runs a real parser from the real toolchain:
#   .js    node --check                  (parse)
#   .ts    node --check (as ESM)         (parse, strict-mode rules apply)
#   .py    compile() in-memory           (parse + bytecode compile)
#   .go    gofmt -e                      (parse)
#   .java  javac                         (parse + full semantic analysis)
#
# Nothing is ever written inside src/. Compiling in-tree would drop binary
# .pyc/.class files next to the sources, and those inflate `wc -l` with newline
# bytes that are not lines. Everything lands in a temp dir instead.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1
N=${1:-6}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

total_pass=0
total_fail=0

check_lang() {
  local ext="$1" label="$2"
  local pass=0 fail=0
  # `sort` keeps the sample deterministic so results are reproducible.
  for f in $(find src -name "*.$ext" | sort | head -"$N"); do
    local ok=1
    case "$ext" in
      js)
        node --check "$f" >/dev/null 2>&1 || ok=0 ;;
      ts)
        cp "$f" "$TMP/m.mjs"
        node --check "$TMP/m.mjs" >/dev/null 2>&1 || ok=0 ;;
      py)
        python3 -c 'import sys; compile(open(sys.argv[1]).read(), sys.argv[1], "exec")' "$f" >/dev/null 2>&1 || ok=0 ;;
      go)
        gofmt -e "$f" >/dev/null 2>&1 || ok=0 ;;
      java)
        local cls
        cls=$(grep -oE '^class Slop[A-Za-z0-9]+' "$f" | head -1 | awk '{print $2}')
        rm -rf "$TMP/j"; mkdir -p "$TMP/j"
        cp "$f" "$TMP/j/$cls.java"
        ( cd "$TMP/j" && javac -nowarn "$cls.java" ) >/dev/null 2>&1 || ok=0 ;;
    esac
    if [ "$ok" -eq 1 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "    FAIL: $f"; fi
  done
  total_pass=$((total_pass+pass))
  total_fail=$((total_fail+fail))
  printf "  %-12s %2d passed, %d failed\n" "$label" "$pass" "$fail"
}

echo "Syntax-checking $N file(s) per language with real toolchains..."
echo
check_lang js   "JavaScript"
check_lang ts   "TypeScript"
check_lang py   "Python"
check_lang go   "Go"
check_lang java "Java"
echo
if [ "$total_fail" -eq 0 ]; then
  echo "ALL $total_pass SAMPLED FILES PARSE CLEANLY."
  exit 0
fi
echo "$total_fail of $((total_pass+total_fail)) sampled files failed."
exit 1
