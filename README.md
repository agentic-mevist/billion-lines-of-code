# billion-lines-of-code

```
   1,000,000,000 lines
      25,000 files
           0 blank lines
           0 comment-only lines
           0 useful features
```

This repository contains **exactly one billion lines of code**. Not "about a
billion." Not "over a billion." Exactly `1,000,000,000` — verified by `wc -l`
and independently by [`scc`](https://github.com/boyter/scc), which agree on the
number to the line.

It exists to settle a discussion about whose project has the most lines of
code, though probably not in the way anyone wanted.

---

## Verify it yourself

Don't take our word for it. That's the entire point.

```bash
./tools/verify.sh        # counts every line with wc(1), then cross-checks with scc
./tools/syntax_check.sh  # proves the lines are real code, using real compilers
```

Or skip our scripts entirely and count it the hard way:

```bash
find src -type f -print0 | xargs -0 cat | wc -l
# 1000000000
```

## The count

```
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
```

Note the **0 / 0** in the Blanks and Comments columns. That is deliberate, and
it is the detail that makes the number bulletproof. Every joke in this
repository rides along as a *trailing* comment on a line that already contains a
real statement, so there is not a single line here that a counter could dismiss
as padding. `wc -l` and `scc`'s Code column report the same figure:

```
wc -l  ....... 1,000,000,000
scc Code ..... 1,000,000,000
```

## It is real code

A billion newlines would be cheating. Files parse with the actual toolchain for
their language:

| Language   | Checked with          | What that proves            |
|------------|-----------------------|-----------------------------|
| JavaScript | `node --check`        | parses                      |
| TypeScript | `node --check` (ESM)  | parses under strict-mode    |
| Python     | `compile()`           | parses **and** compiles     |
| Go         | `gofmt -e`            | parses                      |
| Java       | `javac`               | parses, resolves, **compiles to bytecode** |

A 40,000-line generated Java file compiles to a `.class` file. Cleanly.

## What's actually in it

Load-bearing enterprise software:

```js
function acc6618(a) {
 let r = a;
 r += 1;
 r -= 1;
 r *= 1;
 r |= 0;
 r += 1; // the architect drew this on a napkin
 r -= 1;
 return r;
}
```

```python
def identity_7679(x): # measured twice, shipped once
 t = [x]
 u = t[:]
 w = u + [] # please do not benchmark this
 return w[0] # we do not talk about this function
```

Also included: recursive `isEven` implementations that subtract two until they
hit zero, boolean laundering functions that turn `true` into `true`, retry loops
that `continue` on failure until they run out of attempts and return `null`,
and roughly 90 million trailing comments drawn from a curated list of things
developers actually say.

Everything lives under a directory tree (`src/<area>/<domain>/<layer>/`) that
looks exactly like a real monorepo, because that is funnier.

## How it was built

`tools/generate_slop.py` writes the whole thing in **66 seconds** on 4 cores.

It is fully deterministic — the same `--seed` reproduces all 14,655,393,160
bytes byte-for-byte. You can regenerate the repository and `diff` it against
what's committed:

```bash
python3 tools/generate_slop.py --out /tmp/regen   # ~66s
diff -r src /tmp/regen && echo "identical"
```

The trick to hitting the number exactly is a three-phase fill: bulk-fill with
large pre-rendered blocks, pack the remainder with progressively smaller blocks
chosen by binary search, then land on the target precisely with single-line
statements. Blocks are sampled without replacement so no identifier is ever
declared twice in the same file — which matters, because redeclaring a `class`
or `const` is a hard `SyntaxError` in JavaScript.

## The actual point

This repository took **66 seconds** to write and does **nothing**.

Lines of code measure typing, not value. A metric you can saturate in about a
minute with a 700-line script is not a metric — and if a billion lines of
working, compiling, honestly-counted code is worthless, then so is any smaller
number used as a scoreboard.

The most valuable commit most of us will ever push is the one that deletes code.

---

See [`PROOF.md`](PROOF.md) for the raw, unedited verification output.

<sub>Every line here was generated by a script. That is disclosed everywhere in
this repo on purpose — the joke only works if it's honest.</sub>
