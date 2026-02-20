# BIF Configuration Examples

Complete, annotated working examples of bif.js5 + imap.yml pairs.

---

## 1. C++ Static Library (CRUtil Pattern)

A C++ static library with unit tests, include copying, and ClangDeps integration.

### bif.js5

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
         pkgname: 'CRUtil',
         version: '1.0',
         flavors: [
            { name: 'CLang', tag: 'cl' },
         ],
      },

      artifacts: {
         filter: ['auto'],

         targets: [
            // Release library: unwrapped + tar.gz
            {
               archetype: 'Library',
               'build!': ['Release'],
               flavor: ['CLang'],
               wrapper: [[], ['Tar', 'Gzip']],
            },
            // Test target: debug only, CLang+Test flavor
            {
               archetype: 'Library',
               'build!': ['Debug'],
               flavor: [['CLang', 'Test']],
            },
         ],
      },
   },

   deployments: { local: [], prod: [] },
   pipelines: {},
}
```

**Generated targets (`bif do -l`):**
```
[0] CRUtil+cl,1.0-osx.amd64.REL-{buildid}.lib
[1] CRUtil+cl,1.0-osx.amd64.REL-{buildid}.lib.tar.gz
[2] CRUtil+cl+tst,1.0-osx.amd64.DBG-{buildid}.lib
```

### imap.yml

```yaml
# Global environment
env:
  PRJ_CLANG_SOURCEDIR: '{BIF_PRJ_SOURCEDIR}'
  # BUILD_TGTDIR uses {1},{2} resolved lazily from target's capture groups
  BUILD_TGTDIR: '{BIF_PRJ_BUILDDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}/{2}.lower()'
  CLANG_INCDIR: 'include'

# ──── TEST TARGET ────
# CRUtil+cl+tst,1.0-osx.amd64.DBG-{buildid}.lib
#                                   {1}  {2}  {3}
'{BIF_ART_NAME}+cl+tst,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.lib':
  env:
    INCDIR_LOCDIR: '{PRJ_CLANG_SOURCEDIR}'    # Tests use source includes directly
  adir: '{BIF_PRJ_TESTDIR}'
  bdir: '{BIF_PRJ_TESTDIR}'
  needs:
    - '#tests'
    - '{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}.{1}.{2}-{3}.lib'
  uses: 'include'                              # Timestamp-only, not built for tests
  virtual: true
  steps:
    - tool: g++
      options: ['-std=gnu++17', '-g', '-I< {##} >', '-o', 'test_runner']
      args: ['{#}', '-lpthread']
    - tool: bash
      options: ['-c', './test_runner -s']

# ──── RELEASE TAR.GZ TARGET ────
# CRUtil+cl,1.0-osx.amd64.REL-{buildid}.lib.tar.gz
'{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.lib.tar.gz':
  env:
    INCDIR_LOCDIR: '{ADIR}'                    # Build copies includes to artifact dir
  adir: '{BIF_PRJ_ARTIFACTDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}'
  bdir: '{BUILD_TGTDIR}'
  needs:
    - '{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}.{1}.{2}-{3}.lib'
    - '{CLANG_INCDIR}'
  tool: tar
  options: ['-czf', '{@}']
  args: ['{<}']

# ──── LIBRARY TARGET ────
# CRUtil+cl,1.0-osx.amd64.REL-{buildid}.lib
'{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.lib':
  env:
    DEPS_VARIANT: '"{BIF_BUILD_HOST_PLATFORM}_{1}_{2}".lower()'
    CLANG_OBJDIR: '{BUILD_TGTDIR}/cobj'
  adir: '{BUILD_TGTDIR}'
  bdir: '{CLANG_OBJDIR}'
  needs: ['#objects']
  steps:
    - tool: ar
      options: ['rcs', '{@}']
      args: ['{#}']

# ──── INCLUDE COPY (polymorphic via INCDIR_LOCDIR) ────
include:
  adir: '{INCDIR_LOCDIR}'
  bdir: '{PRJ_CLANG_SOURCEDIR}'
  tool: bash
  options: ['-c', '/bin/cp -rp {CLANG_INCDIR} {ADIR}']

# ──── REF TARGETS (dependency sets) ────
objects:
  adir: '{CLANG_OBJDIR}'
  needs:
    - 'crstring.o'
    # Add more object files here as project grows

tests:
  adir: '{BIF_PRJ_TESTDIR}'
  needs:
    - 'test_main.cpp'
    - 'test_ainteger.cpp'

# ──── OBJECT FILE RECIPE ────
_.o:
  adir: '{CLANG_OBJDIR}'
  bdir: '{BIF_PRJ_SOURCEDIR}'
  env:
    CFLAGS: '-std=gnu++17'
  needs: ['{1}.cpp']
  uses: ['@ClangDeps({1}_{DEPS_VARIANT}.d)']
  steps:
    - tool: echo
      args: ['Compiling: {#}']
    - tool: gcc
      options: ['{CFLAGS}', '-I', 'include', '-c', '-o', '{@}']
      args: ['{#}']

# ──── DEPENDENCY FILE RECIPE ────
_.d:
  adir: '{BIF_PRJ_SOURCEDIR}/.deps'
  bdir: '{BIF_PRJ_SOURCEDIR}'
  needs: ['{1}.split("_")[0].append(".cpp")']
  steps:
    - tool: echo
      args: ['Generating dependencies for: {<}']
    - tool: gitkeep
      args: ['{ADIR}']
    - tool: gcc
      options: ['-MM', '-MG', '-I', 'include', '-o', '{@}']
      args: ['{<}']

# ──── SOURCE LEAVES ────
_.cpp:
  adir: '{BIF_PRJ_SOURCEDIR}'

_.c:
  adir: '{BIF_PRJ_SOURCEDIR}'

test___.cpp:
  adir: '{BIF_PRJ_TESTDIR}'
```

---

## 2. Python Binary (Nuitka Standalone)

Python application compiled to a standalone binary using Nuitka.

### bif.js5

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
         pkgname: 'MyApp',
         version: '1.0.0',
         flavors: [
            { name: 'Python', tag: 'py' },
         ],
      },

      artifacts: {
         filter: ['auto'],
         targets: [
            {
               archetype: 'Binary',
               'build!': ['Release'],
               flavor: ['Python'],
               wrapper: [['Tar', 'Gzip']],
            },
         ],
      },
   },

   deployments: { local: [] },
   pipelines: {},
}
```

**Generated targets:**
```
[0] MyApp+py,1.0.0-osx.amd64.REL-{buildid}.bin.tar.gz
```

### imap.yml

```yaml
env:
  BIF_LOC_BUILDDIR: '{BIF_PRJ_BUILDDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}/{2}.lower()'

# ──── TAR.GZ ROOT TARGET ────
'{BIF_ART_NAME}+py,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.bin.tar.gz':
  adir: '{BIF_PRJ_ARTIFACTDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}'
  bdir: '{BIF_LOC_BUILDDIR}'
  needs:
    - '{BIF_ART_NAME}+py,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}.{1}.{2}-{3}.bin'
  tool: tar
  options: ['-czf', '{@}']
  args: ['{<}']

# ──── NUITKA BINARY TARGET ────
'{BIF_ART_NAME}+py,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.bin':
  adir: '{BIF_LOC_BUILDDIR}'
  bdir: '{BIF_PRJ_SOURCEDIR}'
  byproducts: ['{BIF_ART_NAME}.lower().build', '{BIF_ART_NAME}.lower().dist']
  needs:
    - '#app_modules'
    - '#app_main'
  env:
    PY_MAIN: 'main.py'
  exports: ['PY_MAIN']
  tool: nuitka
  options:
    - '--onefile'
    - '--standalone'
    - '--no-progressbar'
    - '--assume-yes-for-downloads'
    - '--product-name={BIF_ART_NAME}'
    - '--product-version={BIF_ART_VERSION}'
    - '--output-dir={ADIR}'
    - '--output-filename={@}.file()'
  args: ['{PY_MAIN}']

# ──── REF TARGETS ────
app_modules:
  adir: '~/Source'
  needs:
    - 'myapp/**/*.py'

app_main:
  adir: '~/Source'
  needs:
    - 'main.py'
```

---

## 3. C++ Executable (Minimal Starter)

Minimal C++ project producing a single executable.

### bif.js5

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
         pkgname: 'Hello',
         version: '0.1',
         flavors: [
            { name: 'CLang', tag: 'cl' },
         ],
      },

      artifacts: {
         filter: ['auto'],
         targets: [
            {
               archetype: 'Executable',
               flavor: ['CLang'],
            },
         ],
      },
   },

   deployments: {},
   pipelines: {},
}
```

**Generated targets:**
```
[0] Hello+cl,0.1-osx.amd64.DBG-{buildid}.exe
```

### imap.yml

```yaml
env:
  BIF_LOC_BUILDDIR: '{BIF_PRJ_BUILDDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}/{2}.lower()'
  OBJDIR: '{BIF_LOC_BUILDDIR}/obj'

# ──── EXECUTABLE TARGET ────
'{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.exe':
  adir: '{BIF_LOC_BUILDDIR}'
  bdir: '{OBJDIR}'
  needs: ['#objects']
  byproducts: ['{OBJDIR}']
  tool: gcc
  options: ['-o', '{@}']
  args: ['{<}']

# ──── REF TARGET ────
objects:
  adir: '{OBJDIR}'
  needs:
    - 'main.o'

# ──── COMPILE RECIPE ────
_.o:
  adir: '{OBJDIR}'
  bdir: '{BIF_PRJ_SOURCEDIR}'
  needs: ['{1}.c']
  tool: gcc
  options: ['-c', '-o', '{@}']
  args: ['{<}']

# ──── SOURCE LEAF ────
_.c:
  adir: '{BIF_PRJ_SOURCEDIR}'
```

---

## 4. Python Wheel (PyKit Pattern)

Python package with custom format overrides for PEP-427 wheel naming.

### bif.js5

```json5
{
   bif_dsl_version: 1,

   project: {
      config: {
         pkgname: 'PyKit',
         version: '1.0.0',

         flavors: [
            { name: 'Python3', tag: 'py3' },
         ],

         // Override formats for Python-standard naming
         pkgname_format: '{pkgname}.lower()',
         pkgbase_format: '{pkgname}-{pkgversion}',
         pfmarch_format: '{architecture}-{platform}',
         pkgpab_format: '{pfmarch}',
         target_format: '{pkgbase}-{buildid}-{pkgpab}.{archetype}',

         // Override wrappings for PEP-427 naming
         wrappings: {
            buildid: {
               prefix: ',',
               template: '{prefix}{material}',
               material: 'flavor',
               values: 'flavors',
               bundle: null,
            },
         },
      },

      artifacts: {
         targets: [
            {
               archetype: 'Library',
               'platform!': ['Any'],
               'architecture!': ['Universal'],
               'build!': ['Release'],
               flavor: ['Python3'],
               wrapper: ['Wheel'],
            },
         ],
      },
   },

   deployments: {},
   pipelines: {},
}
```

**Generated targets:**
```
[0] pykit-1.0.0-py3-uni-any.lib.whl
```

### imap.yml

```yaml
env:
  PYSRC: '{BIF_PRJ_SOURCEDIR}'

# ──── WHEEL TARGET ────
# pykit-1.0.0-py3-uni-any.lib.whl
#                   {1} {2}
'{BIF_ART_NAME},{BIF_ART_VERSION}-_-_.lib.whl':
  adir: '{BIF_PRJ_ARTIFACTDIR}'
  bdir: '{PYSRC}'
  needs:
    - '#pkg_sources'
    - '#pkg_metadata'
  tool: python3
  script: |
    import zipfile, os
    # Build wheel from source and metadata
    # ... wheel building logic ...
  args: ['{|}']

# ──── REF TARGETS ────
pkg_sources:
  adir: '{PYSRC}'
  needs:
    - 'pykit/**/*.py'

pkg_metadata:
  adir: '~'
  needs:
    - 'setup.py'
    - 'pyproject.toml'
```

---

## 5. Multi-Language Project (C++ + Python)

Project with both C++ and Python build chains coexisting.

### bif.js5

```json5
{
   bif_dsl_version: 1,

   project: {
      config: {
         pkgname: 'HybridApp',
         version: '2.0',
         flavors: [
            { name: 'CLang', tag: 'cl' },
            { name: 'Python', tag: 'py' },
         ],
      },

      artifacts: {
         filter: ['auto'],
         targets: [
            // C++ library
            {
               archetype: 'Library',
               'build!': ['Release'],
               flavor: ['CLang'],
               wrapper: [[], ['Tar', 'Gzip']],
            },
            // Python binary
            {
               archetype: 'Binary',
               'build!': ['Release'],
               flavor: ['Python'],
               wrapper: [['Tar', 'Gzip']],
            },
         ],
      },
   },

   deployments: {},
   pipelines: {},
}
```

**Generated targets:**
```
[0] HybridApp+cl,2.0-osx.amd64.REL-{buildid}.lib
[1] HybridApp+cl,2.0-osx.amd64.REL-{buildid}.lib.tar.gz
[2] HybridApp+py,2.0-osx.amd64.REL-{buildid}.bin.tar.gz
```

### imap.yml

```yaml
env:
  PRJ_CLANG_SOURCEDIR: '{BIF_PRJ_SOURCEDIR}/clang'
  PRJ_PYTHON_SOURCEDIR: '{BIF_PRJ_SOURCEDIR}/python'
  BIF_LOC_BUILDDIR: '{BIF_PRJ_BUILDDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}/{2}.lower()'

# ==============================
# C++ CHAIN
# ==============================

# C++ library tar.gz
'{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.lib.tar.gz':
  adir: '{BIF_PRJ_ARTIFACTDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}'
  bdir: '{BIF_LOC_BUILDDIR}'
  needs:
    - '{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}.{1}.{2}-{3}.lib'
  tool: tar
  options: ['-czf', '{@}']
  args: ['{<}']

# C++ library (static archive)
'{BIF_ART_NAME}+cl,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.lib':
  env:
    CLANG_OBJDIR: '{BIF_LOC_BUILDDIR}/cobj'
  adir: '{BIF_LOC_BUILDDIR}'
  bdir: '{CLANG_OBJDIR}'
  needs: ['#cl_objects']
  steps:
    - tool: ar
      options: ['rcs', '{@}']
      args: ['{#}']

cl_objects:
  adir: '{CLANG_OBJDIR}'
  needs:
    - 'core.o'
    - 'utils.o'

_.o:
  adir: '{CLANG_OBJDIR}'
  bdir: '{PRJ_CLANG_SOURCEDIR}'
  needs: ['{1}.cpp']
  tool: gcc
  options: ['-std=gnu++17', '-c', '-o', '{@}']
  args: ['{<}']

_.cpp:
  adir: '{PRJ_CLANG_SOURCEDIR}'

# ==============================
# PYTHON CHAIN
# ==============================

# Python binary tar.gz
'{BIF_ART_NAME}+py,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.bin.tar.gz':
  adir: '{BIF_PRJ_ARTIFACTDIR}/{BIF_BUILD_HOST_PLATFORM}/{1}'
  bdir: '{BIF_LOC_BUILDDIR}'
  needs:
    - '{BIF_ART_NAME}+py,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}.{1}.{2}-{3}.bin'
  tool: tar
  options: ['-czf', '{@}']
  args: ['{<}']

# Python binary via Nuitka
'{BIF_ART_NAME}+py,{BIF_ART_VERSION}-{BIF_BUILD_HOST_PLATFORM}._._-_.bin':
  adir: '{BIF_LOC_BUILDDIR}'
  bdir: '{PRJ_PYTHON_SOURCEDIR}'
  needs:
    - '#py_modules'
    - '#py_main'
  env:
    PY_MAIN: 'main.py'
  exports: ['PY_MAIN']
  tool: nuitka
  options:
    - '--onefile'
    - '--standalone'
    - '--no-progressbar'
    - '--product-name={BIF_ART_NAME}'
    - '--product-version={BIF_ART_VERSION}'
    - '--output-dir={ADIR}'
    - '--output-filename={@}.file()'
  args: ['{PY_MAIN}']

py_modules:
  adir: '{PRJ_PYTHON_SOURCEDIR}'
  needs:
    - 'hybridapp/**/*.py'

py_main:
  adir: '{PRJ_PYTHON_SOURCEDIR}'
  needs:
    - 'main.py'
```

---

## Pattern Catalog Summary

| Pattern | Flavor | Archetype | Key Techniques |
|---------|--------|-----------|----------------|
| C++ Library | CLang | Library | ar, #objects ref, ClangDeps, INCDIR pattern |
| C++ Executable | CLang | Executable | gcc link, #objects ref |
| Python Binary | Python | Binary | nuitka, #module refs, **/*.py globs |
| Python Wheel | Python3 | Library | Custom wrappings, format overrides |
| Multi-Language | CLang+Python | Mixed | Separate source dirs, independent chains |
