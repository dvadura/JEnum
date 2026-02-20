# BIF Macros Quick Reference

Compact reference card for macro syntax, recipe macros, functions, and expression features.

---

## Path Aliases

| Alias | Expansion | Example |
|-------|-----------|---------|
| `~` | `{BIF_PRJ_ROOTDIR}` | `~/Source` -> `/project/Source` |
| `~~` | User home dir | `~~/tools` -> `/Users/me/tools` |
| `/` | Filesystem root | `/usr/bin` |
| `//` | Network filesystem root | `//server/share` |

---

## Recipe Macros (available inside recipe options/args)

| Terse | Verbose | Description |
|-------|---------|-------------|
| `{@}` | `{TARGET}` | Relative path from BDIR to ADIR + target name |
| `{<}` | `{INPUTS}` | All prerequisites (needs + uses), relative paths |
| `{#}` | `{NEEDS}` | Hard prerequisites only, relative paths |
| `{##}` | `{USES}` | Soft prerequisites only, relative paths |
| `{^}` | `{YIELDS}` | Yields list with same path logic as `{@}` |
| `{+}` | `{BYPRODUCTS}` | Byproducts list |
| `{?}` | `{NEWER}` | Prerequisites newer than target |
| `{|}` | `{SCRIPT_FILE}` | Path to temporary script file |
| `{ADIR}` | `{ARTIFACT_DIR}` | Artifact directory (absolute or relative) |
| `{BDIR}` | `{BUILD_DIR}` | Build working directory |
| `{TOOLID}` | - | Current tool name (e.g., `gcc`, `nuitka`) |

### Capture Groups (from `_` wildcards in target patterns)

| Macro | Meaning |
|-------|---------|
| `{1}` | First capture group |
| `{2}` | Second capture group |
| `{n}` | n-th capture group |

---

## Macro Modifiers

| Syntax | Behavior when undefined |
|--------|------------------------|
| `{NAME}` | Error |
| `{?NAME}` | Empty string |
| `{NAME:-default}` | Uses `default` value |
| `{*NAME}` | Force list preservation (spread) |
| `{+NAME}` | Force space-joining into single string |
| `{{NAME}}` | Indirect (two-stage) expansion |

---

## Macro Filters (in needs/uses context)

| Syntax | Meaning |
|--------|---------|
| `{NEEDS:*.o}` | Keep only items matching `*.o` |
| `{NEEDS:!*.h}` | Exclude items matching `*.h` |

---

## Functions

### String Case

| Function | Example |
|----------|---------|
| `.lower()` | `"HELLO".lower()` -> `hello` |
| `.upper()` | `"hello".upper()` -> `HELLO` |
| `.capitalize()` | `"hELLO".capitalize()` -> `Hello` |

### Path Manipulation

| Function | Description | Example |
|----------|-------------|---------|
| `.dir()` | Directory part | `/a/b/c.txt` -> `/a/b` |
| `.file()` | Filename part | `/a/b/c.txt` -> `c.txt` |
| `.stem()` | Filename without ext | `/a/b/c.txt` -> `c` |
| `.ext()` | Extension | `/a/b/c.txt` -> `.txt` |
| `.parent()` | Parent directory | `/a/b/c` -> `/a/b` |
| `.name()` | Final component | `/a/b/c.txt` -> `c.txt` |
| `.resolve()` | To absolute path | `./file` -> `/full/path/file` |

### String Operations

| Function | Description | Example |
|----------|-------------|---------|
| `.split(sep)` | Split on separator | `"a:b:c".split(":")` -> `[a, b, c]` |
| `.split()` | Split on whitespace | `"a b c".split()` -> `[a, b, c]` |
| `.join(sep)` | Join list | `[a,b].join(":")` -> `a:b` |
| `.trim()` | Remove whitespace | `"  hi  ".trim()` -> `hi` |
| `.strip(chars)` | Remove chars | `"xxhixx".strip("x")` -> `hi` |
| `.append(s)` | Add suffix to each | `[a,b].append(".o")` -> `[a.o, b.o]` |
| `.prepend(s)` | Add prefix to each | `[a,b].prepend("x")` -> `[xa, xb]` |
| `.replace(old,new)` | Substring replace | `"hello".replace("l","L")` -> `heLLo` |
| `.map(old,new)` | Pattern replace each | `[a.c].map(".c",".o")` -> `[a.o]` |

### List Operations

| Function | Description |
|----------|-------------|
| `.filter(pat)` | Keep items matching pattern |
| `.exclude(pat)` | Remove items matching pattern |
| `.sort()` | Sort ascending |
| `.rsort()` | Sort descending |
| `.reverse()` | Reverse order |
| `.reduce()` / `.unique()` | Remove duplicates |
| `.first()` | First element |
| `.last()` | Last element |
| `.count()` | Number of elements |
| `.empty()` | True if empty |

### Slice Notation

| Syntax | Meaning |
|--------|---------|
| `[n]` | Single element (0-indexed) |
| `[n:m]` | Elements n to m-1 |
| `[n:]` | From n to end |
| `[:m]` | Start to m-1 |
| `[-n]` | n-th from end |
| `[-n:]` | Last n elements |

### Function Chaining

Functions chain left-to-right: `{FILES}.filter(".c").map(".c",".o").sort()`

---

## Cross-Product Syntax

Angle brackets create cross-product expansions:

| Expression | Result |
|------------|--------|
| `<a b c>` | `[a, b, c]` |
| `src/<main util>` | `[src/main, src/util]` |
| `<main util>.c` | `[main.c, util.c]` |
| `<a b>/<1 2>` | `[a/1, a/2, b/1, b/2]` |

---

## Dependency Prefixes (in needs/uses lists)

| Prefix | Meaning | Example |
|--------|---------|---------|
| (none) | File or target, auto-resolved | `main.o` |
| `@` | Plugin-provided dependency | `@ClangDeps({1}.d)` |
| `#` | Ref target (substitute needs list) | `#objects` |

---

## Glob Patterns (in needs/uses/yields)

| Pattern | Meaning |
|---------|---------|
| `*` | Any characters (not crossing `/`) |
| `**` | Any path (crosses `/`) |
| `?` | Single character |
| `[abc]` | Character class |
| `[!abc]` | Negated character class |
