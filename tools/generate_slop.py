#!/usr/bin/env python3
"""
Generate exactly ONE BILLION lines of technically-valid, spiritually-bankrupt code.

Design constraints that make the count defensible:

  * 25,000 files x 40,000 lines = 1,000,000,000 lines. Exactly. Not "about".
  * ZERO blank lines and ZERO comment-only lines are emitted. Every single line
    carries an actual statement. Jokes ride along as *trailing* comments, which
    every LOC counter on earth classifies as code.
    => `wc -l` and scc/cloc/tokei "code" columns agree on the same number.
  * Deterministic: same --seed reproduces every byte. Anyone can regenerate and
    diff it themselves.

Usage:
    python3 tools/generate_slop.py --out src              # the real thing
    python3 tools/generate_slop.py --out /tmp/x --files 20 --lines 1000
"""

import argparse
import bisect
import json
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

TOTAL_LINES = 1_000_000_000
NUM_FILES = 25_000
LINES_PER_FILE = TOTAL_LINES // NUM_FILES

# ---------------------------------------------------------------------------
# The memes. Trailing comments only. Keep them clean and keep them short-ish.
# ---------------------------------------------------------------------------
MEMES = [
    "works on my machine",
    "TODO: refactor this (added 2014)",
    "do not touch, nobody knows why this works",
    "temporary fix, removing it next sprint",
    "the tests pass, ship it",
    "I have no idea what this does",
    "copied from Stack Overflow, seems fine",
    "here be dragons",
    "if you remove this line the build breaks",
    "yes this is O(n^2), no I will not fix it",
    "written at 3am, reviewed by nobody",
    "this is fine",
    "legacy code, treat as radioactive",
    "PR approved in four seconds",
    "it compiles therefore it is correct",
    "sorry",
    "future me's problem",
    "load bearing whitespace",
    "we do not talk about this function",
    "management asked for more lines of code",
    "billable line",
    "this line is 1 of 1,000,000,000",
    "our CTO measures productivity in lines",
    "definitely not generated",
    "artisanal, hand-crafted, free-range code",
    "10x engineer moment",
    "an AI wrote this and I trusted it completely",
    "unit tests? in this economy?",
    "works locally, prays remotely",
    "the linter has been disabled for your safety",
    "git blame will not help you here",
    "estimated 2 points, took 3 quarters",
    "documented on a wiki page that no longer exists",
    "this used to be a one-liner",
    "microservice 47 of 3",
    "we are agile",
    "shipped on a Friday",
    "rollback is not in the budget",
    "premature optimization is the root of my paycheck",
    "clean code enthusiasts hate this one trick",
    "the architect drew this on a napkin",
    "enterprise grade",
    "synergy",
    "this abstraction has exactly one implementation",
    "deleting this is a two week project",
    "the requirements changed halfway through",
    "backwards compatible with a system we turned off",
    "please do not benchmark this",
    "scales horizontally, sideways, and emotionally",
    "the design doc says this is elegant",
    "cargo culted from a blog post",
    "works until it doesn't",
    "TODO: add error handling",
    "TODO: add the other error handling",
    "this variable name was chosen by committee",
    "refactoring this is left as an exercise for the reader",
    "six people approved this and none of them read it",
    "this is why we can't have nice things",
    "the standup said this was done",
    "measured twice, shipped once",
]

# ---------------------------------------------------------------------------
# Fake enterprise directory taxonomy, for maximum plausibility
# ---------------------------------------------------------------------------
AREAS = [
    "core", "platform", "services", "legacy", "vendor", "experiments",
    "enterprise", "cloud", "edge", "internal", "shared", "contrib",
]
DOMAINS = [
    "auth", "billing", "checkout", "inventory", "notifications", "reporting",
    "search", "sync", "telemetry", "webhooks", "accounts", "pricing",
    "shipping", "catalog", "sessions", "audit", "scheduling", "messaging",
    "onboarding", "compliance", "analytics", "provisioning", "routing",
    "settlement", "recommendations", "moderation", "fulfilment", "ledger",
]
LAYERS = [
    "handlers", "helpers", "utils", "managers", "factories", "adapters",
    "controllers", "validators", "serializers", "providers", "resolvers",
    "middleware", "strategies", "repositories", "orchestrators", "wrappers",
]
NOUNS = [
    "Widget", "Thing", "Item", "Record", "Entity", "Payload", "Context",
    "Bundle", "Token", "Session", "Request", "Response", "Envelope", "Job",
    "Task", "Event", "Message", "Node", "Chunk", "Blob", "Slot", "Ticket",
]
VERBS = [
    "process", "handle", "transform", "normalize", "validate", "resolve",
    "compute", "derive", "materialize", "reconcile", "hydrate", "flatten",
    "coerce", "sanitize", "enrich", "dispatch", "aggregate", "project",
]

# Files are distributed across languages with these weights.
LANG_MIX = [("js", 34), ("py", 26), ("ts", 16), ("java", 14), ("go", 10)]
EXT = {"js": ".js", "ts": ".ts", "py": ".py", "java": ".java", "go": ".go"}
COMMENT = {"js": "//", "ts": "//", "py": "#", "java": "//", "go": "//"}


def _lang_for(idx):
    """Deterministic language pick, stable across runs."""
    total = sum(w for _, w in LANG_MIX)
    pos = (idx * 7919) % total
    acc = 0
    for lang, w in LANG_MIX:
        acc += w
        if pos < acc:
            return lang
    return LANG_MIX[-1][0]


# ---------------------------------------------------------------------------
# Chunk templates. Each returns a list of lines (no trailing newline).
# Every line is a real statement. No blanks. No comment-only lines.
# ---------------------------------------------------------------------------

# How many copies of the "ritual" chunk to stuff into each pack. Higher = more
# very-short lines = fewer bytes per line. Set from CLI, read at pool-build time.
_RUN_WEIGHT = 6


def _ritual(head, init, ops, tail, n):
    """A long run of pointless one-token statements. The cheapest line there is."""
    k = n % 17 + 12
    return [head, init] + [ops[i % len(ops)] for i in range(k)] + tail


def _js_chunks(n, noun, verb):
    """Curly-brace family: JS, TS, Java bodies, Go bodies all borrow shapes."""
    base = [
        # The world's most defensive increment
        ["function %s%s%d(a) {" % (verb, noun, n),
         " let r = a;",
         " r += %d;" % (n % 7 + 1),
         " r -= %d;" % (n % 7 + 1),
         " r += 1;",
         " r -= 1;",
         " r += 1;",
         " return r;",
         "}"],
        # Recursive parity, because modulo is for cowards
        ["function isEven%d(n) {" % n,
         " if (n === 0) return true;",
         " if (n === 1) return false;",
         " if (n < 0) return isEven%d(-n);" % n,
         " return isEven%d(n - 2);" % n,
         "}"],
        # Boolean laundering
        ["function toBool%d(v) {" % n,
         " if (v) {",
         "  return true;",
         " } else {",
         "  return false;",
         " }",
         "}"],
        # FizzBuzz, enterprise edition
        ["function fizz%d(i) {" % n,
         " let s = \"\";",
         " if (i % 3 === 0) s += \"Fizz\";",
         " if (i % 5 === 0) s += \"Buzz\";",
         " if (s === \"\") s = String(i);",
         " return s;",
         "}"],
        # Getter, setter, and a getter for the setter
        ["class %s%dConfig {" % (noun, n),
         " constructor() {",
         "  this.v = %d;" % n,
         " }",
         " get() {",
         "  return this.v;",
         " }",
         " set(v) {",
         "  this.v = v;",
         "  return this;",
         " }",
         " reset() {",
         "  this.v = %d;" % n,
         "  return this;",
         " }",
         "}"],
        # Retry loop that retries nothing
        ["function retry%d(f) {" % n,
         " for (let i = 0; i < 3; i++) {",
         "  try {",
         "   return f();",
         "  } catch (e) {",
         "   continue;",
         "  }",
         " }",
         " return null;",
         "}"],
        # A staircase
        ["function depth%d(x) {" % n,
         " if (x > 0) {",
         "  if (x > 1) {",
         "   if (x > 2) {",
         "    if (x > 3) {",
         "     return 4;",
         "    }",
         "    return 3;",
         "   }",
         "   return 2;",
         "  }",
         "  return 1;",
         " }",
         " return 0;",
         "}"],
        # Identity function with extra steps
        ["function %s%d(x) {" % (verb, n),
         " const t = [x];",
         " const u = t.slice(0);",
         " const w = u.concat([]);",
         " return w[0];",
         "}"],
        # Manual array sum, in the year of our lord
        ["function total%d(xs) {" % n,
         " let s = 0;",
         " for (let i = 0; i < xs.length; i++) {",
         "  s = s + xs[i];",
         " }",
         " return s;",
         "}"],
        # Stringly typed everything
        ["function name%d(k) {" % n,
         " switch (k) {",
         "  case 0: return \"zero\";",
         "  case 1: return \"one\";",
         "  case 2: return \"two\";",
         "  case 3: return \"three\";",
         "  default: return \"many\";",
         " }",
         "}"],
        # Small ones, for exact tail packing
        ["const %s%dFlag = true;" % (verb, n)],
        ["let %s%dCounter = 0;" % (verb, n)],
        ["const %s%dLimit = %d;" % (noun.lower(), n, n * 3 + 1)],
    ]
    run = _ritual("function acc%d(a) {" % n, " let r = a;",
                  (" r += 1;", " r -= 1;", " r *= 1;", " r |= 0;"),
                  [" return r;", "}"], n)
    return base + [run] * _RUN_WEIGHT


def _py_chunks(n, noun, verb):
    base = [
        ["def %s_%s_%d(a):" % (verb, noun.lower(), n),
         " r = a",
         " r += %d" % (n % 7 + 1),
         " r -= %d" % (n % 7 + 1),
         " r += 1",
         " r -= 1",
         " return r"],
        ["def is_even_%d(n):" % n,
         " if n == 0:",
         "  return True",
         " if n == 1:",
         "  return False",
         " if n < 0:",
         "  return is_even_%d(-n)" % n,
         " return is_even_%d(n - 2)" % n],
        ["def to_bool_%d(v):" % n,
         " if v:",
         "  return True",
         " else:",
         "  return False"],
        ["def fizz_%d(i):" % n,
         " s = \"\"",
         " if i % 3 == 0:",
         "  s += \"Fizz\"",
         " if i % 5 == 0:",
         "  s += \"Buzz\"",
         " if s == \"\":",
         "  s = str(i)",
         " return s"],
        ["class %s%dConfig:" % (noun, n),
         " def __init__(self):",
         "  self.v = %d" % n,
         " def get(self):",
         "  return self.v",
         " def set(self, v):",
         "  self.v = v",
         "  return self",
         " def reset(self):",
         "  self.v = %d" % n,
         "  return self"],
        ["def retry_%d(f):" % n,
         " for _ in range(3):",
         "  try:",
         "   return f()",
         "  except Exception:",
         "   continue",
         " return None"],
        ["def depth_%d(x):" % n,
         " if x > 0:",
         "  if x > 1:",
         "   if x > 2:",
         "    if x > 3:",
         "     return 4",
         "    return 3",
         "   return 2",
         "  return 1",
         " return 0"],
        ["def total_%d(xs):" % n,
         " s = 0",
         " for i in range(len(xs)):",
         "  s = s + xs[i]",
         " return s"],
        ["def name_%d(k):" % n,
         " if k == 0:",
         "  return \"zero\"",
         " if k == 1:",
         "  return \"one\"",
         " if k == 2:",
         "  return \"two\"",
         " return \"many\""],
        ["def identity_%d(x):" % n,
         " t = [x]",
         " u = t[:]",
         " w = u + []",
         " return w[0]"],
        ["%s_%d_FLAG = True" % (verb.upper(), n)],
        ["%s_%d_LIMIT = %d" % (noun.upper(), n, n * 3 + 1)],
    ]
    run = _ritual("def acc_%d(a):" % n, " r = a",
                  (" r += 1", " r -= 1", " r *= 1", " r //= 1"),
                  [" return r"], n)
    return base + [run] * _RUN_WEIGHT


def _java_chunks(n, noun, verb):
    base = [
        [" static int %s%s%d(int a) {" % (verb, noun, n),
         "  int r = a;",
         "  r += %d;" % (n % 7 + 1),
         "  r -= %d;" % (n % 7 + 1),
         "  r += 1;",
         "  r -= 1;",
         "  return r;",
         " }"],
        [" static boolean isEven%d(int n) {" % n,
         "  if (n == 0) return true;",
         "  if (n == 1) return false;",
         "  if (n < 0) return isEven%d(-n);" % n,
         "  return isEven%d(n - 2);" % n,
         " }"],
        [" static boolean toBool%d(boolean v) {" % n,
         "  if (v) {",
         "   return true;",
         "  } else {",
         "   return false;",
         "  }",
         " }"],
        [" static String fizz%d(int i) {" % n,
         "  String s = \"\";",
         "  if (i % 3 == 0) s += \"Fizz\";",
         "  if (i % 5 == 0) s += \"Buzz\";",
         "  if (s.equals(\"\")) s = String.valueOf(i);",
         "  return s;",
         " }"],
        [" static int depth%d(int x) {" % n,
         "  if (x > 0) {",
         "   if (x > 1) {",
         "    if (x > 2) {",
         "     return 3;",
         "    }",
         "    return 2;",
         "   }",
         "   return 1;",
         "  }",
         "  return 0;",
         " }"],
        [" static int total%d(int[] xs) {" % n,
         "  int s = 0;",
         "  for (int i = 0; i < xs.length; i++) {",
         "   s = s + xs[i];",
         "  }",
         "  return s;",
         " }"],
        [" static String name%d(int k) {" % n,
         "  switch (k) {",
         "   case 0: return \"zero\";",
         "   case 1: return \"one\";",
         "   case 2: return \"two\";",
         "   default: return \"many\";",
         "  }",
         " }"],
        [" static int identity%d(int x) {" % n,
         "  int t = x;",
         "  int u = t;",
         "  int w = u;",
         "  return w;",
         " }"],
        [" static final boolean %s_%d_FLAG = true;" % (verb.upper(), n)],
        [" static final int %s_%d_LIMIT = %d;" % (noun.upper(), n, n * 3 + 1)],
    ]
    run = _ritual(" static int acc%d(int a) {" % n, "  int r = a;",
                  ("  r += 1;", "  r -= 1;", "  r *= 1;", "  r |= 0;"),
                  ["  return r;", " }"], n)
    return base + [run] * _RUN_WEIGHT


def _go_chunks(n, noun, verb):
    base = [
        ["func %s%s%d(a int) int {" % (verb.title(), noun, n),
         " r := a",
         " r += %d" % (n % 7 + 1),
         " r -= %d" % (n % 7 + 1),
         " r += 1",
         " r -= 1",
         " return r",
         "}"],
        ["func IsEven%d(n int) bool {" % n,
         " if n == 0 {",
         "  return true",
         " }",
         " if n == 1 {",
         "  return false",
         " }",
         " return IsEven%d(n - 2)" % n,
         "}"],
        ["func ToBool%d(v bool) bool {" % n,
         " if v {",
         "  return true",
         " }",
         " return false",
         "}"],
        ["func Fizz%d(i int) string {" % n,
         " s := \"\"",
         " if i%3 == 0 {",
         "  s += \"Fizz\"",
         " }",
         " if i%5 == 0 {",
         "  s += \"Buzz\"",
         " }",
         " return s",
         "}"],
        ["func Depth%d(x int) int {" % n,
         " if x > 0 {",
         "  if x > 1 {",
         "   if x > 2 {",
         "    return 3",
         "   }",
         "   return 2",
         "  }",
         "  return 1",
         " }",
         " return 0",
         "}"],
        ["func Total%d(xs []int) int {" % n,
         " s := 0",
         " for i := 0; i < len(xs); i++ {",
         "  s = s + xs[i]",
         " }",
         " return s",
         "}"],
        ["func Name%d(k int) string {" % n,
         " switch k {",
         " case 0:",
         "  return \"zero\"",
         " case 1:",
         "  return \"one\"",
         " }",
         " return \"many\"",
         "}"],
        ["var %s%dFlag = true" % (verb.title(), n)],
        ["var %s%dLimit = %d" % (noun.title(), n, n * 3 + 1)],
    ]
    run = _ritual("func Acc%d(a int) int {" % n, " r := a",
                  (" r += 1", " r -= 1", " r *= 1", " r |= 0"),
                  [" return r", "}"], n)
    return base + [run] * _RUN_WEIGHT


CHUNKS = {"js": _js_chunks, "ts": _js_chunks, "py": _py_chunks,
          "java": _java_chunks, "go": _go_chunks}


# ---------------------------------------------------------------------------
# Pool construction
# ---------------------------------------------------------------------------

class Block(object):
    __slots__ = ("text", "n")

    def __init__(self, text, n):
        self.text = text
        self.n = n


def _decorate(lines, rng, marker, prob):
    """Attach trailing meme comments. Never adds or removes a line."""
    out = []
    for ln in lines:
        if rng.random() < prob:
            out.append("%s %s %s" % (ln, marker, rng.choice(MEMES)))
        else:
            out.append(ln)
    return out


def _build_pools(lang, seed, meme_prob):
    """Superblocks for bulk fill, tail blocks for exact packing."""
    # zlib.crc32 rather than hash(): builtin hash() of str is salted per process
    # by PYTHONHASHSEED, which would silently break --seed reproducibility.
    rng = random.Random(seed * 6364136223846793005 + zlib.crc32(lang.encode()))
    marker = COMMENT[lang]
    maker = CHUNKS[lang]

    # Every chunk in the pool gets a globally unique id. Combined with
    # sampling-without-replacement per file (see _write_one), this guarantees no
    # duplicate identifiers inside any single file -- which matters, because
    # redeclaring a `class` or `const` is a hard SyntaxError in JS, and ESM
    # rejects duplicate `function` declarations too.
    counter = [0]

    def uid():
        counter[0] += 1
        return counter[0]

    supers, tails = [], []
    for b in range(900):
        lines = []
        target = rng.randint(300, 700)
        while len(lines) < target:
            pack = maker(uid(), rng.choice(NOUNS), rng.choice(VERBS))
            lines.extend(_decorate(rng.choice(pack), rng, marker, meme_prob))
        supers.append(Block("\n".join(lines) + "\n", len(lines)))

    for b in range(1200):
        pack = maker(uid(), rng.choice(NOUNS), rng.choice(VERBS))
        lines = _decorate(rng.choice(pack), rng, marker, meme_prob)
        tails.append(Block("\n".join(lines) + "\n", len(lines)))

    tails.sort(key=lambda b: b.n)
    return supers, tails, [b.n for b in tails]


_POOLS = {}
_CFG = {}


def _pools(lang):
    if lang not in _POOLS:
        _POOLS[lang] = _build_pools(lang, _CFG["seed"], _CFG["meme_prob"])
    return _POOLS[lang]


# ---------------------------------------------------------------------------
# Per-language file scaffolding. Header/footer lines are CODE, never comments,
# so they don't pollute the code/comment ratio.
# ---------------------------------------------------------------------------

def _scaffold(lang, idx, relpath):
    """Return (header_lines, footer_lines, filler_fn)."""
    stem = "M%05d" % idx
    if lang in ("js", "ts"):
        head = ["const __MODULE__ = \"%s\";" % relpath]
        foot = ["module.exports = { __MODULE__ };"] if lang == "js" else \
               ["export default __MODULE__;"]
        fill = lambda k: ["const _p%s_%d = %d;" % (stem, i, i) for i in range(k)]
    elif lang == "py":
        head = ["__MODULE__ = \"%s\"" % relpath]
        foot = ["__all__ = [\"__MODULE__\"]"]
        fill = lambda k: ["_p%s_%d = %d" % (stem, i, i) for i in range(k)]
    elif lang == "java":
        head = ["class Slop%s {" % stem,
                " static final String MODULE = \"%s\";" % relpath]
        foot = ["}"]
        fill = lambda k: [" static final int P%d = %d;" % (i, i) for i in range(k)]
    else:  # go
        head = ["package slop", "var module%s = \"%s\"" % (stem, relpath)]
        foot = ["var built%s = true" % stem]
        fill = lambda k: ["var p%s_%d = %d" % (stem, i, i) for i in range(k)]
    return head, foot, fill


def _path_for(idx):
    area = AREAS[idx % len(AREAS)]
    domain = DOMAINS[(idx // len(AREAS)) % len(DOMAINS)]
    layer = LAYERS[(idx // (len(AREAS) * len(DOMAINS))) % len(LAYERS)]
    lang = _lang_for(idx)
    name = "%s_%s_%05d%s" % (
        VERBS[idx % len(VERBS)], NOUNS[idx % len(NOUNS)].lower(), idx, EXT[lang])
    return os.path.join(area, domain, layer, name), lang


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def _write_one(idx):
    out_root = _CFG["out"]
    lines_per_file = _CFG["lines"]
    relpath, lang = _path_for(idx)
    full = os.path.join(out_root, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)

    head, foot, fill = _scaffold(lang, idx, relpath)
    supers, tails, tail_sizes = _pools(lang)
    rng = random.Random(_CFG["seed"] * 1000003 + idx)

    budget = lines_per_file - len(head) - len(foot)
    if budget < 0:
        raise ValueError("lines-per-file too small for scaffolding")

    parts = ["\n".join(head) + "\n"] if head else []
    used = 0
    biggest_super = max(b.n for b in supers)
    smallest_super = min(b.n for b in supers)

    # Phase 1: bulk fill with big pre-rendered superblocks (cheap, few RNG calls).
    # Sampled WITHOUT replacement so no block -- and therefore no identifier --
    # appears twice in the same file.
    want = min(len(supers), max(8, budget // max(smallest_super, 1) + 8))
    for si in rng.sample(range(len(supers)), want):
        if budget - used <= biggest_super:
            break
        b = supers[si]
        parts.append(b.text)
        used += b.n

    # Phase 2: pack the tail with whatever still fits, also without replacement
    seen = set()
    while True:
        rem = budget - used
        if rem <= 0:
            break
        cut = bisect.bisect_right(tail_sizes, rem)
        if cut == 0:
            break
        pick = -1
        for _ in range(24):
            cand = rng.randrange(cut)
            if cand not in seen:
                pick = cand
                break
        if pick < 0:
            break
        seen.add(pick)
        b = tails[pick]
        parts.append(b.text)
        used += b.n

    # Phase 3: land on the number exactly, with one-line statements
    rem = budget - used
    if rem > 0:
        parts.append("\n".join(fill(rem)) + "\n")
        used += rem

    if foot:
        parts.append("\n".join(foot) + "\n")

    blob = "".join(parts)
    with open(full, "w", buffering=1 << 20) as fh:
        fh.write(blob)

    n = blob.count("\n")
    if n != lines_per_file:
        raise AssertionError("%s: got %d lines, wanted %d" % (relpath, n, lines_per_file))
    return n, len(blob)


def _init(cfg):
    global _RUN_WEIGHT
    _CFG.update(cfg)
    _RUN_WEIGHT = cfg["run_weight"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--files", type=int, default=NUM_FILES)
    ap.add_argument("--lines", type=int, default=LINES_PER_FILE)
    ap.add_argument("--seed", type=int, default=1_000_000_000)
    ap.add_argument("--meme-prob", type=float, default=0.09)
    ap.add_argument("--run-weight", type=int, default=6)
    ap.add_argument("--procs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--manifest", default=None)
    args = ap.parse_args()

    cfg = {"out": args.out, "lines": args.lines, "seed": args.seed,
           "meme_prob": args.meme_prob, "run_weight": args.run_weight}

    t0 = time.time()
    total_lines = 0
    total_bytes = 0
    done = 0
    with Pool(args.procs, initializer=_init, initargs=(cfg,)) as pool:
        for n, b in pool.imap_unordered(_write_one, range(args.files), chunksize=16):
            total_lines += n
            total_bytes += b
            done += 1
            if done % 500 == 0 or done == args.files:
                el = time.time() - t0
                sys.stderr.write(
                    "\r%6d/%d files  %14d lines  %7.2f GiB  %5.0fs" %
                    (done, args.files, total_lines, total_bytes / 2**30, el))
                sys.stderr.flush()
    sys.stderr.write("\n")

    summary = {
        "files": args.files,
        "lines_per_file": args.lines,
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "bytes_per_line": round(total_bytes / max(total_lines, 1), 3),
        "seed": args.seed,
        "meme_prob": args.meme_prob,
        "run_weight": args.run_weight,
        "seconds": round(time.time() - t0, 1),
    }
    print(json.dumps(summary, indent=2))
    if args.manifest:
        with open(args.manifest, "w") as fh:
            json.dump(summary, fh, indent=2)

    expected = args.files * args.lines
    if total_lines != expected:
        sys.stderr.write("FATAL: expected %d lines, wrote %d\n" % (expected, total_lines))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
