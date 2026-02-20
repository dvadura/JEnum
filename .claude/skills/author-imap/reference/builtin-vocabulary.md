# BIF Built-in Vocabulary Reference

Quick-lookup tables for all classification lists, format strings, wrappings, tools, and
built-in macros defined in `defaults.js5`. Use this when constructing target names or
referencing valid values in `bif.js5` target specs.

---

## Architectures

| Name | Tag |
|------|-----|
| AMD32 | i386 |
| AMD64 | amd64 |
| ARMV7L | armv7 |
| ARM64 | aarch64 |
| I386 | i386 |
| IBMZ | s390x |
| PPC64LE | ppc64le |
| RISC-V | riscv64 |
| Universal | uni |
| X86_64 | amd64 |
| X86_32 | i386 |

## Platforms

| Name | Tag |
|------|-----|
| Any | any |
| Android | and |
| Darwin | osx |
| iOS | ios |
| Linux | lnx |
| MacOS | osx |
| OSX | osx |
| Windows | win |
| FreeBSD | fbd |
| Solaris | sol |
| zOS | zos |
| zTPF | tpf |

## Archetypes

| Name | Tag | Use |
|------|-----|-----|
| BifBundle | bbn | Bundle package |
| Binary | bin | General binary artifact |
| Documentation | doc | Documentation package |
| Executable | exe | Standalone executable |
| Library | lib | Linkable library |
| Resources | res | Resource bundle |
| Source | src | Source distribution |

## Build Types

| Name | Tag |
|------|-----|
| Debug | DBG |
| Internal | INT |
| Release | REL |

## Wrappers

| Name | Tag | Common Use |
|------|-----|------------|
| BZip2 | bz2 | Compression |
| Gzip | gz | Compression |
| Tar | tar | Archive |
| Zip | zip | Archive + compression |
| Wheel | whl | Python package |
| Dmg | dmg | macOS disk image |
| DebPkg | dpk | Debian package |
| Rpm | rpm | RPM package |
| Jar | jar | Java archive |
| Encrypted | enc | Encryption layer |
| Iso9660 | iso | ISO image |
| Shar | sh | Shell archive |
| Package | pkg | Generic package |

## Flavors

| Name | Tag | Use |
|------|-----|-----|
| Keyed | key | Licensed with external key |
| Keyless | kls | Explicitly keyless |
| Test | tst | Test artifact |
| Python | py | Python language variant |
| CLang | cl | C/C++ language variant |
| Go | go | Go language variant |
| Rust | ru | Rust language variant |
| Java | jav | Java language variant |

---

## Default Format Strings

These control how artifact names are assembled. Override in `project.config`:

| Format Key | Default | Produces |
|------------|---------|----------|
| `pkgflavor_format` | `{pkgname}` | `MyApp` |
| `pkgversion_format` | `{version}` | `1.0` |
| `pkgbase_format` | `{pkgflavor},{pkgversion}` | `MyApp+cl,1.0` |
| `pfmarch_format` | `{platform}.{architecture}` | `osx.amd64` |
| `pkgpab_format` | `{pfmarch}.{build}` | `osx.amd64.REL` |
| `buildid_format` | `{builddate}_{buildtime}` | `2026202_1404` |
| `target_format` | `{pkgbase}-{pkgpab}-{buildid}.{archetype}` | `MyApp+cl,1.0-osx.amd64.REL-{buildid}.bin` |

**Processing order:** pkgname -> pkgflavor (wrap) -> pkgversion -> pkgbase -> pfmarch -> pkgpab -> buildid -> target (wrap)

---

## Default Wrappings

| Wrapping ID | Prefix | Material Attribute | Lookup List | Bundle Key |
|-------------|--------|--------------------|-------------|------------|
| `pkgflavor` | `+` | `flavor` | `flavors` | null |
| `target` | `.` | `wrapper` | `wrappers` | `Bundle` |

**Template:** `{prefix}{material}` for both.

---

## Built-in Tools

### Plugin Tools (built-in, no external binary)

| Tool | Hidden | Silent | Description |
|------|--------|--------|-------------|
| echo | yes | no | Print arguments |
| gitkeep | yes | - | Create .gitkeep in directory |
| touch | yes | - | Update timestamp / create file |
| copy | yes | - | Copy files or directories |
| bundle | yes | - | Create BIF bundle package |
| pytest | no | - | Run Python tests |

### External Tools (require system binary)

| Tool | Command | Default Options | DevOps Phase |
|------|---------|-----------------|--------------|
| bash | bash | - | * |
| python3 | python3 | - | * |
| make | make | verbose: `-v`, debug: `-d` | Build |
| cmake | cmake | verbose: `-v`, debug: `-d` | * |
| gcc | gcc | - | * |
| g++ | g++ | - | * |
| clang | clang | - | * |
| clang++ | clang++ | - | * |
| tar | tar | - | * |
| javac | javac | verbose: `-v`, debug: `-d` | Build |
| jar | jar | verbose: `-v`, debug: `-d` | Build |
| gradle | gradle | verbose: `-v`, debug: `-d` | Build |
| nuitka | python3 -m nuitka | - | Build |

---

## Built-in BIF_* Macros

### Project Directory Macros

| Macro | Expansion |
|-------|-----------|
| `{BIF_PRJ_ROOTDIR}` | Project root directory |
| `{BIF_PRJ_SOURCEDIR}` | `{ROOT}/Source` |
| `{BIF_PRJ_BUILDDIR}` | `{ROOT}/Build` |
| `{BIF_PRJ_ARTIFACTDIR}` | `{ROOT}/Artifacts` |
| `{BIF_PRJ_TESTDIR}` | `{ROOT}/Test` |
| `{BIF_PRJ_CONFIGDIR}` | `{ROOT}/Config` |
| `{BIF_PRJ_DOCDIR}` | `{ROOT}/Documents` |

### Build Context Macros

| Macro | Example |
|-------|---------|
| `{BIF_BUILD_HOST_PLATFORM}` | `osx.amd64` |
| `{BIF_BUILD_DATE}` | `20260203` |
| `{BIF_BUILD_TIME}` | `1423` |
| `{BIF_BUILD_ID}` | `20260203_1423` |

### Package Identity Macros

| Macro | Example |
|-------|---------|
| `{BIF_ART_PACKAGE_NAME}` | `MyApp` (from `pkgname`) |
| `{BIF_ART_PACKAGE_VERSION}` | `1.0` (from `version`) |
| `{BIF_ART_PACKAGE_BASE}` | `MyApp,1.0` |
| `{BIF_ART_NAME}` | `MyApp` (alias for package name) |
| `{BIF_ART_VERSION}` | `1.0` (alias for package version) |

### Tool Macros

| Macro | Description |
|-------|-------------|
| `{BIF_TOOLBOX_PATH}` | System PATH for tool resolution |
| `{TOOLID}` | Current tool identifier (e.g., `nuitka`) |
