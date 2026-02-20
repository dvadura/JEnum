---
name: author-imap
description: >
  Draft or modify bif.js5 and imap.yml configuration files for BIF projects.
  Encodes semantic rules for target synthesis, inference maps, and build recipes.
argument-hint: "<language> [new|modify|debug] [description]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
disable-model-invocation: true
---

# BIF Configuration Authoring Skill

You are drafting `bif.js5` and `imap.yml` files for a BIF (BuildItFast) project.
These two files work as a pair: bif.js5 defines WHAT to build (target combinations),
imap.yml defines HOW to build (inference rules and recipes).

## Arguments

Parse `$ARGUMENTS` as: `<language> [operation] [description]`

- **language**: `cpp`, `c`, `python`, `java`, `multi`, or specific language name
- **operation** (optional): `new` (default), `modify`, `debug`
- **description** (optional): free-form description of what to build

If operation is `modify` or `debug`, read the existing bif.js5 and imap.yml first.

## Workflow

1. **Gather context**: Read existing project files if modifying. Check what source files
   exist in `Source/`. Identify the project's language(s) and structure.

2. **Read reference material**: Based on the language, read the relevant reference files
   from this skill's `reference/` directory:
   - Always read `builtin-vocabulary.md` for valid classification values
   - Always read `macros-quickref.md` for macro syntax
   - Read `bif-js5-spec.md` when writing/modifying bif.js5
   - Read `imap-yml-spec.md` when writing/modifying imap.yml
   - Read `examples.md` for the matching language pattern

3. **Design the configuration**: Plan target names, dependency chains, and recipes
   before writing. Ensure bif.js5 target names match imap.yml patterns.

4. **Write the files**: Create or modify bif.js5 and imap.yml as a coordinated pair.

5. **Verify**: Run `bif do -l` to confirm target names are generated correctly.

## Critical Semantic Rules

### Rule 1: bif.js5 = WHAT, imap.yml = HOW

bif.js5 specifies target **combinations** (archetype x platform x architecture x build x
flavor x wrapper). imap.yml specifies **recipes** (how to build each target pattern).
The generated target names from bif.js5 MUST match patterns in imap.yml.

### Rule 2: Target Name Formula

The default target name is built from this chain:

```
pkgflavor = {pkgname} + flavor_wrap        -> MyApp+cl
pkgbase   = {pkgflavor},{version}          -> MyApp+cl,1.0
pfmarch   = {platform}.{architecture}      -> osx.amd64
pkgpab    = {pfmarch}.{build}              -> osx.amd64.REL
target    = {pkgbase}-{pkgpab}-{buildid}.{archetype} + wrapper_wrap
          -> MyApp+cl,1.0-osx.amd64.REL-{buildid}.bin.tar.gz
```

All values use **tags** (looked up from classification lists), not display names.

### Rule 3: The `!` Override Operator

In bif.js5, a bare key **merges** with defaults. Append `!` to **replace**:

```json5
'build!': ['Release'],     // ONLY Release
build: ['Release'],        // Debug AND Release (merged with default ['Debug'])
```

Almost always use `!` for `build`, `platform`, `architecture` to avoid surprise defaults.

### Rule 4: Wrapper Semantics

```json5
wrapper: []                    // No wrapper
wrapper: [['Tar', 'Gzip']]    // Chained: .tar.gz (one target)
wrapper: ['Tar', 'Gzip']      // Separate: .tar AND .gz (two targets!)
wrapper: [[], ['Tar', 'Gzip']] // Both unwrapped AND .tar.gz (two targets)
```

Nested list = chained. Flat list = separate targets. Common mistake: forgetting the
inner list for chained wrappers.

### Rule 5: Flavor Wrapping

Flavors wrap the package name with prefix `+` and the flavor tag:

```json5
flavor: ['CLang']              // -> MyApp+cl,...
flavor: ['Python']             // -> MyApp+py,...
flavor: [['CLang', 'Test']]   // -> MyApp+cl+tst,...  (containerized)
```

Use language-specific flavors to separate build chains in multi-language projects.

### Rule 6: imap.yml Pattern Matching

`_` wildcards in target patterns capture into `{1}`, `{2}`, etc.:

```yaml
'{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.bin':
#                                                                 ^  ^  ^
#                                                                {1}{2}{3}
# For target MyApp+cl,1.0-osx.amd64.REL-2026202_1404.bin:
#   {1}=amd64, {2}=REL, {3}=2026202_1404
```

Macros in patterns are expanded first, then `_` wildcards match against the rest.

### Rule 7: adir/bdir and `{@}` Relative Paths

- **adir**: Where the artifact lives (or will live after being built)
- **bdir**: Where the tool runs (working directory)
- **{@}**: Auto-computes `relative_path(BDIR -> ADIR) / target_name`

```yaml
_.o:
  adir: 'Build/obj'          # Artifact goes here
  bdir: 'Source'              # gcc runs here
  # {@} expands to ../Build/obj/foo.o (relative path from Source to Build/obj)
```

When adir == bdir, `{@}` is just the target filename.

### Rule 8: needs vs uses

- **needs**: Hard prerequisites. Must exist or be buildable. Scheduled in DAG.
- **uses**: Soft prerequisites. Timestamp-checked only. Not built.

Use `needs` for source files and intermediate artifacts that must be built first.
Use `uses` for headers, configs, libraries that trigger rebuilds if changed but
aren't built by this project.

### Rule 9: Ref Targets (`#name`)

Targets without a `tool` are ref targets (non-buildable dependency sets):

```yaml
objects:
  adir: '{OBJDIR}'
  needs: ['main.o', 'util.o']

# Usage:
needs: ['#objects']  # Substitutes the needs list with adir from 'objects'
```

Items from a ref target inherit the **ref target's adir**, NOT the referencing
target's adir. This is critical for correct path resolution.

### Rule 10: Environment Scoping

Variables cascade: global -> target -> recipe -> step. Later overrides earlier.

Macros like `{1}`, `{2}` in global env are resolved **lazily** from the active
target's capture groups.

The INCDIR pattern uses env-driven polymorphism: different parent targets set
different env values, making shared recipes behave differently.

### Rule 11: Try Blocks

Try blocks select recipes at **inference time** (not build time):

```yaml
'output.bin':
  try:
    - needs: ['optimized.o']    # Preferred: use if buildable
      tool: gcc
      ...
    - needs: ['main.c']         # Fallback: build from source
      tool: gcc
      ...
```

First try whose `needs` can be satisfied wins. Selection is irreversible.

### Rule 12: Source Leaf Nodes

Targets with `adir` but no `tool` and no `needs` are source leaves:

```yaml
_.cpp:
  adir: '{BIF_PRJ_SOURCEDIR}'
```

Inference terminates at these nodes. They declare where existing files live.

## Language-Specific Patterns

### C/C++ Library

```
bif.js5: archetype='Library', flavor=['CLang'], wrapper=[[], ['Tar','Gzip']]
imap.yml chain: .lib.tar.gz -> .lib -> #objects -> _.o -> _.cpp (leaf)
Key techniques: ar for archiving, #objects ref, ClangDeps for headers,
  INCDIR pattern for polymorphic include handling
Compile step: gcc with -c -o {@ } for objects, ar rcs {@} for library
```

### C/C++ Executable

```
bif.js5: archetype='Executable', flavor=['CLang']
imap.yml chain: .exe -> #objects -> _.o -> _.c (leaf)
Key techniques: gcc link step, #objects ref, byproducts for obj dir
Link step: gcc -o {@} {<}
```

### Python Binary (Nuitka)

```
bif.js5: archetype='Binary', flavor=['Python'], wrapper=[['Tar','Gzip']]
imap.yml chain: .bin.tar.gz -> .bin (nuitka) -> #modules + #main
Key techniques: #module refs with **/*.py globs, nuitka options,
  --output-dir={ADIR} --output-filename={@}.file()
Ref targets group py sources: adir='~/Source', needs=['app/**/*.py']
```

### Python Wheel

```
bif.js5: archetype='Library', platform=['Any'], architecture=['Universal'],
  wrapper=['Wheel'], custom format overrides for PEP-427 naming
imap.yml: custom build script, #sources + #metadata refs
Format overrides: pkgname_format='{pkgname}.lower()', custom target_format
```

### Multi-Language

```
bif.js5: separate targets with different flavors (CLang + Python)
imap.yml: independent chains sharing env definitions
Key: PRJ_CLANG_SOURCEDIR and PRJ_PYTHON_SOURCEDIR for separate source trees,
  language-specific leaf patterns (_.cpp vs *.py globs)
```

### Test Targets

```
bif.js5: flavor=[['CLang','Test']], build=['Debug']
imap.yml: virtual=true target that depends on the non-test artifact
  and #tests ref target, runs test framework
Pattern: {PKG}+cl+tst,...  depends on {PKG}+cl,...
```

## Verification Checklist

After writing the configuration, verify:

- [ ] `bif do -l` lists expected targets with correct names
- [ ] Target names from bif.js5 match patterns in imap.yml
- [ ] Every imap pattern that should match a RAT uses `{BIF_ART_NAME}` and
      `{BIF_ART_VERSION}` (not hardcoded package names)
- [ ] Flavor tags in target names match the `flavors` classification list
- [ ] Wrapper suffixes match the `wrappers` classification list
- [ ] `!` override used on build/platform/architecture where defaults should not merge
- [ ] Every buildable recipe has a `tool` specification
- [ ] Ref targets have `adir` and `needs` but NO `tool`
- [ ] Source leaf nodes have `adir` but no `tool` and no `needs`
- [ ] adir/bdir are set correctly for each recipe
- [ ] `{@}` is used for tool output paths (auto-computes relative path)
- [ ] `{<}` or `{#}` used for input arguments (auto-computes relative paths)
- [ ] Capture groups `{1}`, `{2}` in recipes match the underscore positions in pattern
- [ ] needs vs uses distinction is correct for each dependency
- [ ] Single quotes used for YAML strings containing `{MACRO}` expressions
- [ ] Chained wrappers use nested lists `[['Tar','Gzip']]` not flat `['Tar','Gzip']`

## Reference Files

Read these reference files from `reference/` as needed:

| File | When to Read |
|------|-------------|
| `builtin-vocabulary.md` | Always — valid tags, tools, macros, formats |
| `macros-quickref.md` | Always — macro syntax, functions, recipe macros |
| `bif-js5-spec.md` | When writing or modifying bif.js5 |
| `imap-yml-spec.md` | When writing or modifying imap.yml |
| `examples.md` | For complete working examples by language |
