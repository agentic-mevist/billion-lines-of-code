# PROOF

Raw, unedited output from `./tools/verify.sh` and `./tools/syntax_check.sh`.
Nothing below is retyped or reformatted.

**Run date:** 2026-08-03 08:45 UTC

## The headline

| Metric | Value |
|---|---|
| **Total lines** | **1,000,000,000** |
| Files | 25,000 |
| Blank lines | 0 |
| Comment-only lines | 0 |
| Lines classified as *code* by `scc` | **1,000,000,000** |
| Bytes on disk | 14,655,393,160 (13.65 GiB) |
| Mean bytes per line | 14.655 |
| Cyclomatic complexity (`scc`) | 78,588,322 |
| Wall-clock time to generate | 66.0 seconds |

Two independent counters agree exactly:

```
wc -l  ....... 1000000000
scc Code ..... 1000000000
```

They agree because the generator emits **zero** blank lines and **zero**
comment-only lines. There is no category of line here that a skeptic can
discount. Every joke is a trailing comment on a line that already does work.

## Verbatim output

```
==============================================================
 BILLION LINES OF CODE :: VERIFICATION
==============================================================

[1/5] Source-purity check ............ OK (no non-source files in src/)
[2/5] Files .......................... 25000
[3/5] Counting lines with wc(1) ...... (reading every byte, please wait)
      wc -l total .................... 1000000000
[4/5] Bytes on disk .................. 14655393160 (13.65 GiB)
[5/5] Third-party counter (scc) ......
───────────────────────────────────────────────────────────────────────────────
Language            Files       Lines    Blanks  Comments       Code Complexity
───────────────────────────────────────────────────────────────────────────────
JavaScript          8,500 340,000,000         0         0 340,000,000 21,380,550
Python              6,500 260,000,000         0         0 260,000,000 22,669,468
TypeScript          4,000 160,000,000         0         0 160,000,000 16,261,397
Java                3,500 140,000,000         0         0 140,000,000 11,430,886
Go                  2,500 100,000,000         0         0 100,000,000  6,846,021
───────────────────────────────────────────────────────────────────────────────
Total              25,000 1,000,000,000         0         0 1,000,000,000 78,588,322
───────────────────────────────────────────────────────────────────────────────
Processed 14655393160 bytes, 14655.393 megabytes (SI)
───────────────────────────────────────────────────────────────────────────────

==============================================================
 RESULT: EXACTLY 1000000000 LINES. 🎉
==============================================================

### syntax_check.sh ###
Syntax-checking 6 file(s) per language with real toolchains...

  JavaScript    6 passed, 0 failed
  TypeScript    6 passed, 0 failed
  Python        6 passed, 0 failed
  Go            6 passed, 0 failed
  Java          6 passed, 0 failed

ALL 30 SAMPLED FILES PARSE CLEANLY.
```

The 30 sampled files above total 1,200,000 lines. They were checked with
`node --check`, in-memory `compile()`, `gofmt -e`, and `javac`. The Java check
is the strongest of the five: `javac` performs full semantic analysis and
emitted a real `.class` file from a 40,000-line source file.

## Environment

| | |
|---|---|
| OS | Linux 6.18.5 x86_64 |
| Python | 3.11.15 |
| Node | v22.22.2 |
| Go | go1.24.7 |
| javac | 21.0.10 |
| scc | 3.7.0 |

## Reproduce it from scratch

The generator is deterministic. The same seed reproduces all 14,655,393,160
bytes exactly:

```bash
python3 tools/generate_slop.py --out /tmp/regen    # ~66 seconds
diff -r src /tmp/regen && echo "byte-for-byte identical"
```

Determinism was itself a bug we had to fix. The first version seeded its
template pool with Python's builtin `hash()` of the language name — and `hash()`
for `str` is salted per-process by `PYTHONHASHSEED`, so two runs with the same
`--seed` produced different bytes. It now uses `zlib.crc32`, which is stable
across processes and platforms.

## Things that could make this number a lie, and why they don't

An honest proof should state its own attack surface.

**"You counted binary files."** We did, once, by accident — and it is the
reason `verify.sh` opens with a source-purity check. Running `python3 -m
py_compile` during development dropped 8 binary `.pyc` files into the tree, and
`cat`ing them into `wc -l` added **73,846 phantom lines** out of nowhere. The
newline byte `0x0A` appears in binary data and `wc -l` counts it. `verify.sh`
now refuses to count if anything under `src/` is not a `.js`, `.ts`, `.py`,
`.java`, or `.go` file, and `syntax_check.sh` compiles only into a temp
directory. `.gitignore` blocks `*.pyc` and `*.class` as a third line of defence.

**"Trailing newlines inflate the count."** Every file ends with exactly one
newline, so `wc -l` equals the true line count rather than overcounting or
undercounting by one. The generator asserts a per-file newline count of exactly
40,000 and aborts the whole run if any file disagrees.

**"It's a billion blank lines."** Zero blank lines exist. `scc` confirms it
independently in the Blanks column.

**"It's a billion comments."** Zero comment-only lines exist. `scc` confirms it
in the Comments column.

**"It doesn't parse."** See above: five languages, real toolchains, and Java
compiles all the way to bytecode.

**"The files are duplicates of each other."** They are not identical — each is
assembled from a distinct sample of template blocks, drawn without replacement.
They are, however, deeply repetitive by design, and git's delta compression
squeezes 13.65 GiB down to a fraction of that. This is a joke repository, not
an argument that the content is *original*.

## What this proves

That one billion lines of compiling, honestly-counted, zero-padding code can be
produced in 66 seconds by a 700-line script.

Which is the point. Lines of code measure typing, not value.
