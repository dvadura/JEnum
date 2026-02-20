# imap.yml Authoring Specification

Condensed guide for writing `imap.yml` inference map files. Defines HOW to build.

---

## File Format

YAML. Use **single quotes** for strings with `{MACRO}` expressions (prevents YAML
interpolation). Located at project root (or as specified by `depimap` in bif.js5).

## Document Structure

```yaml
# Global environment (available to all targets)
env:
  VAR_NAME: 'value'
  ANOTHER: '{BIF_PRJ_SOURCEDIR}/subdir'

# Optional: compile commands config
cocmds:
  enabled: true
  cocmdsfile: 'compile_commands.json'
  cocmdspath: '{BIF_PRJ_SOURCEDIR}'

# Target definitions (one or more)
'target_pattern':
  # recipe properties...

'another_pattern':
  # recipe properties...
```

---

## Target Pattern Matching

### Underscore Wildcards

`_` in target patterns matches any character sequence (greedy, including dots):

| Pattern | Matches | Captures |
|---------|---------|----------|
| `_.o` | `foo.o`, `bar.o` | `{1}` = `foo`, `bar` |
| `_._` | `a.b` | `{1}` = `a`, `{2}` = `b` |
| `_._._.bin` | `osx.amd64.REL.bin` | `{1}`=`osx`, `{2}`=`amd64`, `{3}`=`REL` |
| `__` | Literal `_` | No capture (escape) |

### Macros in Patterns

Macros in patterns are expanded before matching:

```yaml
'{BIF_ART_NAME}+cl-_._._.bin':
  # After expansion: 'MyApp+cl-_._._.bin'
  # Matches: MyApp+cl-osx.amd64.REL.bin
  # {1}=osx, {2}=amd64, {3}=REL
```

### Pattern Priority

1. Exact literal matches win first
2. More literal characters (higher weight) win
3. Fewer wildcards win
4. First-defined wins ties

---

## Recipe Forms

### Simple Recipe (single step, inline)

```yaml
'target_pattern':
  adir: '{BIF_PRJ_BUILDDIR}'
  bdir: '{BIF_PRJ_SOURCEDIR}'
  needs: ['{1}.c']
  tool: gcc
  options: ['-c', '-o', '{@}']
  args: ['{<}']
```

### Multi-Step Recipe

```yaml
'target_pattern':
  adir: '{BIF_PRJ_BUILDDIR}'
  needs: ['main.o', 'util.o']
  steps:
    - tool: echo
      args: ['Linking...']
    - tool: gcc
      options: ['-o', '{@}']
      args: ['{<}']
```

### Multi-Try Recipe (declarative polymorphism)

```yaml
'target_pattern':
  try:
    # First try: preferred path
    - adir: '{BIF_PRJ_BUILDDIR}'
      needs: ['optimized_main.o']
      tool: gcc
      options: ['-o', '{@}']
      args: ['{<}']

    # Second try: fallback path
    - adir: '{BIF_PRJ_BUILDDIR}'
      needs: ['main.c']
      tool: gcc
      options: ['-o', '{@}']
      args: ['{<}']
```

**Try evaluation:** At inference time, tries are checked in order. First try whose
`needs` can be satisfied (via existing files or other imap rules) wins. Selection is
irreversible.

---

## Recipe Properties

### Directory Semantics

| Property | Default | Description |
|----------|---------|-------------|
| `adir` | `{BIF_PRJ_SOURCEDIR}` | Where artifact lives (or will live) |
| `bdir` | `{ADIR}` | Working directory when executing recipe |

**`{@}` computation:** `{@}` = `relative_path(BDIR -> ADIR) / target_name`

When ADIR and BDIR differ, `{@}` automatically computes the relative path. Tools run
from BDIR but write artifacts to ADIR.

### Dependency Properties

| Property | Default | Description |
|----------|---------|-------------|
| `needs` | `[]` | Hard prerequisites. Must exist or be buildable. Built if missing. |
| `uses` | `[]` | Soft prerequisites. Timestamp-checked only. Not built. |
| `yields` | `['<target>']` | Output artifacts. Glob-expanded post-build. |
| `byproducts` | `[]` | Secondary outputs. Cleaned by `bif clean`. |

**needs vs uses:**
- `needs` = "must build this first" (scheduled in DAG)
- `uses` = "rebuild me if this changes" (timestamp-checked, not built)

### Environment and Exports

| Property | Default | Description |
|----------|---------|-------------|
| `env` | `{}` | Environment variables for this scope |
| `exports` | `[]` | Variable names to export to child processes |

### Execution Control

| Property | Default | Description |
|----------|---------|-------------|
| `virtual` | `false` | No filesystem artifact produced |
| `ignore` | `false` | Ignore errors |
| `timeout` | `0` | Timeout in seconds (0 = none) |
| `log` | `null` | Custom log message format |

### Step Properties

| Property | Default | Description |
|----------|---------|-------------|
| `tool` | (required for buildable) | Tool to execute |
| `script` | `null` | Inline script content |
| `options` | `[]` | Command-line options |
| `args` | `[]` | Command-line arguments |
| `silent` | `false` | Suppress output |
| `hidden` | `false` | Suppress command echo |
| `cocmd` | `false` | Include in compile_commands.json |

---

## Ref Targets (`#name`)

Ref targets are **non-buildable dependency sets** (no `tool`). They group `needs`
with an associated `adir`.

### Defining a Ref Target

```yaml
objects:
  adir: '{CLANG_OBJDIR}'
  needs:
    - 'main.o'
    - 'util.o'
    - 'parser.o'
```

### Using a Ref Target

```yaml
'MyApp-_._._.bin':
  needs:
    - '#objects'       # Substitutes ['main.o', 'util.o', 'parser.o']
    - '#test_sources'  # Another ref target
    - 'extra.o'        # Direct dependency
```

### ADIR Propagation

Items from a ref target inherit **the ref target's ADIR**, not the referencing
target's ADIR:

```yaml
# Referencing target:
'MyApp.lib':
  adir: '{BUILD_DIR}'       # Library lives here
  bdir: '{OBJ_DIR}'         # Build runs here
  needs: ['#objects']        # Ref expansion

# Ref target:
objects:
  adir: '{OBJ_DIR}'         # Object files live HERE
  needs: ['main.o']         # main.o gets adir={OBJ_DIR}, not {BUILD_DIR}
```

---

## Source Leaf Nodes

Targets with `adir` but no `tool` and no `needs` are source leaves. They declare
where existing files live. Inference terminates at these nodes.

```yaml
_.cpp:
  adir: '{BIF_PRJ_SOURCEDIR}'

_.c:
  adir: '{BIF_PRJ_SOURCEDIR}'
```

---

## Environment Scoping

Variables cascade through four levels, each overriding the previous:

```
1. Built-in BIF_* variables
2. Global env: section (top of imap.yml)
3. Target env: section
4. Recipe/try env: section
5. Step env: section
```

### Lazy Evaluation

Macros like `{1}`, `{2}` in global env definitions are resolved lazily when expanded
in the context of a specific target's capture groups.

```yaml
env:
  # {1} and {2} are NOT known here — resolved when expanded in a target context
  BUILD_DIR: '{BIF_PRJ_BUILDDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}/{2}.lower()'
```

### Environment-Driven Polymorphism (INCDIR Pattern)

Use different env values to make the same recipe behave differently:

```yaml
# Build path: copy includes to artifact dir
'MyApp.lib.tar.gz':
  env:
    INCDIR_LOCDIR: '{ADIR}'           # Artifacts/osx/amd64

# Test path: use includes from source
'MyApp+tst.lib':
  env:
    INCDIR_LOCDIR: '{BIF_PRJ_SOURCEDIR}'  # Source

# Shared recipe adapts via env
include:
  adir: '{INCDIR_LOCDIR}'            # Polymorphic based on caller
  bdir: '{BIF_PRJ_SOURCEDIR}'
  tool: bash
  options: ['-c', '/bin/cp -rp include {ADIR}']
```

---

## @Plugin Dependencies

Invoke a plugin during inference to generate dependency lists:

```yaml
uses: ['@ClangDeps({1}_{DEPS_VARIANT}.d)']
```

The plugin reads the `.d` file and returns a list of header paths as `uses` dependencies.

Built-in plugins: `@ClangDeps(file.d)`, `@MakeDeps(file.d)`.

---

## Try Blocks: When and Why

Try blocks enable **declarative polymorphism at inference time**:

- Select different recipes based on which `needs` can be satisfied
- First viable try wins (checked in definition order)
- Selection is irreversible (no fallback at build time)

**Good use cases:**
- Platform-specific recipes (different tools/flags per platform)
- Optional optimization paths (use optimized variant if available)

**Not for:** Cache-then-build patterns (use timestamp checking instead).

---

## Script Execution

Embed scripts for complex operations:

```yaml
'complex_target':
  tool: bash
  script: |
    echo "Building..."
    mkdir -p output
    for f in *.c; do
      gcc -c "$f"
    done
  args: ['{|}']         # {|} expands to temp script file path
```

---

## Key Rules

1. **imap.yml defines HOW** (recipes), **bif.js5 defines WHAT** (target combinations)
2. Target patterns in imap MUST match names generated by bif.js5
3. Use single quotes for YAML strings containing `{MACRO}` expressions
4. `_` wildcards are greedy and capture into `{1}`, `{2}`, etc.
5. `{@}` auto-computes relative path from BDIR to ADIR/target
6. A target without `tool` is a ref target (non-buildable dependency set)
7. `needs` = built if missing; `uses` = timestamp-only, not built
8. Ref target items inherit the ref's ADIR, not the referencing target's ADIR
9. `try` blocks select at inference time; first satisfiable wins
10. Environment cascades: global -> target -> recipe -> step
