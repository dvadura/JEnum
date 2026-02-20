# bif.js5 Authoring Specification

Condensed guide for writing `bif.js5` configuration files. Defines WHAT to build.

---

## File Format

JSON5 (comments, trailing commas, unquoted keys allowed). Located at project root.

## Top-Level Structure

```json5
{
   bif_dsl_version: 1,

   // Optional: override default directories
   srcdir: './Source',
   builddir: './Build',
   artdir: './Artifacts',
   testdir: './Test',

   loggers: { /* ... */ },

   project: {
      config: { /* package identity, classification overrides, tools */ },
      artifacts: { /* filter, targets, tests */ },
   },

   deployments: { /* local, test, qa, beta, prod, pipeline */ },
   pipelines: { /* CI/CD stages */ },
}
```

---

## project.config Section

### Required Keys

| Key | Type | Description |
|-----|------|-------------|
| `pkgname` | string | Package name (e.g., `'MyApp'`) |
| `version` | string | Version string (e.g., `'1.0.0'`) |

### Optional Keys

| Key | Type | Description |
|-----|------|-------------|
| `depimap` | list | imap files to load (default: `['./imap.yml']`) |
| `flavors` | list | Additional flavor definitions `[{name, tag}]` |
| `archetypes` | list | Additional archetype definitions |
| `wrappers` | list | Additional wrapper definitions |
| `tools` | dict | Additional or override tool definitions |
| `wrappings` | dict | Override wrapping definitions |
| `*_format` | string | Override format strings |

---

## The `!` Override Operator

By default, lists in `config` **merge** with defaults. Append `!` to **replace**:

```json5
{
   // Merges with default builds [Debug] -> [Debug, Release]
   builds: [{ name: 'Release', tag: 'REL' }],

   // Replaces defaults entirely -> [Release] only
   'builds!': [{ name: 'Release', tag: 'REL' }],
}
```

Most common usage in target specs:
```json5
{
   'build!': ['Release'],     // Only Release, not Debug+Release
   'platform!': ['Linux'],    // Only Linux, not host platform
}
```

---

## project.artifacts Section

```json5
artifacts: {
   filter: ['auto'],      // or specific target names to restrict builds
   targets: [ /* target specs */ ],
   tests: { /* test configurations */ },
}
```

### Target Spec Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `archetype` | string | `'Binary'` | Artifact type name |
| `platform` | list | `['.']` | Platform names (`.` = host) |
| `architecture` | list | `['.']` | Architecture names (`.` = host) |
| `build` | list | `['Debug']` | Build type names |
| `flavor` | list | `[]` | Flavor names |
| `wrapper` | list | `[]` | Wrapper names |
| `env` | dict | `{}` | Extra environment vars |
| `macros` | dict | `{}` | Extra macro definitions |

**Values are looked up** in classification lists and replaced with tags:
`'Linux'` -> `'lnx'`, `'AMD64'` -> `'amd64'`, `'Debug'` -> `'DBG'`, etc.

---

## Wrapper Semantics

The `wrapper` field controls packaging suffixes on the target name:

| Value | Meaning | Example suffix |
|-------|---------|----------------|
| `[]` | No wrapper (unwrapped) | (none) |
| `['Tar']` | Single wrapper | `.tar` |
| `['Tar', 'Gzip']` | Two separate targets | `.tar` AND `.gz` |
| `[['Tar', 'Gzip']]` | Chained (nested list) | `.tar.gz` |
| `[[], ['Tar', 'Gzip']]` | Both unwrapped AND chained | (none) AND `.tar.gz` |

### Multiple Wrapper Example

```json5
// Produces 2 targets:
//   MyApp,1.0-osx.amd64.REL-{buildid}.bin          (unwrapped)
//   MyApp,1.0-osx.amd64.REL-{buildid}.bin.tar.gz   (tar+gzip)
wrapper: [[], ['Tar', 'Gzip']],
```

---

## Flavor Semantics

Flavors modify the package name via the `pkgflavor` wrapping (prefix `+`):

| Value | Result |
|-------|--------|
| `['CLang']` | `MyApp+cl,...` |
| `['Python']` | `MyApp+py,...` |
| `[['CLang', 'Test']]` | `MyApp+cl+tst,...` (containerized/chained) |

Flavors can produce **multiple target variants**: `flavor: ['CLang', 'Python']` generates
both `+cl` and `+py` targets.

---

## Target Name Construction

The name is built from a chain of format strings:

```
1. pkgflavor_format  = '{pkgname}'          -> MyApp
     + flavor wrap   = '+{tag}'             -> MyApp+cl
2. pkgversion_format = '{version}'          -> 1.0
3. pkgbase_format    = '{pkgflavor},{pkgversion}'  -> MyApp+cl,1.0
4. pfmarch_format    = '{platform}.{architecture}' -> osx.amd64
5. pkgpab_format     = '{pfmarch}.{build}'         -> osx.amd64.REL
6. buildid           = (computed at build time)     -> 2026202_1404
7. target_format     = '{pkgbase}-{pkgpab}-{buildid}.{archetype}'
                     -> MyApp+cl,1.0-osx.amd64.REL-{buildid}.bin
     + wrapper wrap  = '.{tag}'             -> .tar.gz
```

`{buildid}` stays literal in the target name until build time.

### Overriding Format Strings

Override in `project.config` for custom naming:

```json5
// PyKit example: Python-standard naming
pkgname_format: '{pkgname}.lower()',
pkgbase_format: '{pkgname}-{pkgversion}',
pkgpab_format: '{architecture}-{platform}',
target_format: '{pkgbase}-{buildid}-{pkgpab}.{archetype}',
```

---

## Host Platform Defaults

The special value `.` (dot) uses the current host's value:

```json5
{
   platform: ['.'],      // host platform (Darwin, Linux, etc.)
   architecture: ['.'],  // host architecture (AMD64, ARM64, etc.)
}
```

Use explicit values for cross-platform builds:
```json5
{
   'platform!': ['Linux', 'Darwin', 'Windows'],
   'architecture!': ['AMD64', 'ARM64'],
}
```

---

## Cartesian Product Expansion

A single target spec expands into the cartesian product of all list fields:

```json5
{
   archetype: 'Executable',
   'platform!': ['Linux', 'Darwin'],
   'architecture!': ['AMD64', 'ARM64'],
   'build!': ['Debug', 'Release'],
}
// Produces 2 x 2 x 2 = 8 targets
```

---

## Complete Annotated Template

```json5
{
   bif_dsl_version: 1,

   loggers: {
      default: 'build',
      build: [{
         enabled: true,
         name: 'console',
         facility: 'stream',
         channel: 'stderr',
         level: 'info',
      }],
   },

   project: {
      config: {
         pkgname: 'MyProject',
         version: '1.0.0',

         // Add custom flavors (merged with defaults)
         flavors: [
            { name: 'Enterprise', tag: 'ent' },
         ],

         // Add custom tools
         tools: {
            mycompiler: {
               path: ['{BIF_TOOLBOX_PATH}'],
               devops: ['Build'],
            },
         },
      },

      artifacts: {
         // 'auto' builds all, or list specific target names
         filter: ['auto'],

         targets: [
            // Minimal: host-platform debug binary
            {
               archetype: 'Binary',
            },

            // Release executable for two platforms, with tar.gz
            {
               archetype: 'Executable',
               'platform!': ['Linux', 'Darwin'],
               'build!': ['Release'],
               wrapper: [['Tar', 'Gzip']],
            },

            // Flavored library
            {
               archetype: 'Library',
               'build!': ['Release'],
               flavor: ['CLang'],
               wrapper: [[], ['Tar', 'Gzip']],
            },
         ],
      },
   },

   deployments: {
      local: [],
      prod: [],
   },

   pipelines: {},
}
```

---

## Key Rules

1. **bif.js5 defines WHAT** (target combinations), **imap.yml defines HOW** (build recipes)
2. Target names from bif.js5 must match patterns in imap.yml
3. Use `!` suffix to replace defaults, bare keys to merge
4. `.` in platform/architecture means "host system"
5. Nested wrapper lists `[[]]` chain suffixes; flat lists produce separate targets
6. `filter: ['auto']` builds everything; list specific names to restrict
7. Run `bif do -l` to see all generated target names
