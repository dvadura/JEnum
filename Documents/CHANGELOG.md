===============================================================================================
# Package rename to jenum, Dispatch Enum naming, INSTALL.md

DATE :: 2026-02-20 :: 17:10 (UTC: 01:10)

## Summary

Renamed the package from `jnum` to `jenum`, clarified the full names of `DEnum`
(Dispatch Enum) and `MDEnum` (Mutable Dispatch Enum) throughout the README, and created
`Documents/INSTALL.md` covering all installation and build paths.

### Files changed

- **`Source/jnum.py` → `Source/jenum.py`** — renamed; module import is now `from jenum import`.

- **`bif.js5`** — `pkgname: 'jnum'` → `pkgname: 'jenum'`.

- **`imap.yml`** — updated artifact name comments (`jnum-` → `jenum-`); renamed internal
  build environment variables `JNUM_*` → `JENUM_*` throughout.

- **`pyproject.toml`** — `name = "jenum"`, `py-modules = ["jenum"]`, description updated
  to "Dispatch Enums for Python", keywords updated, placeholder URLs updated.

- **`CLAUDE.md`** — project description and source file references updated.

- **`Test/test_denum.py`**, **`Test/test_mdenum.py`** — `from jnum import` →
  `from jenum import`. All 124 tests pass.

- **`README.md`** — package name updated throughout; all `from jnum import` statements
  updated; `DEnum` introduced as "Dispatch Enum" and `MDEnum` as "Mutable Dispatch Enum"
  in the title, opening paragraph, and MDEnum section heading; Installation section updated
  to show `pip install jenum` as the primary path.

- **`Documents/INSTALL.md`** — new file. Covers: install from PyPI, build with bif,
  build with standard `python3 -m build`, copy-source install, editable dev install,
  and uninstall.

===============================================================================================
# Python Package Build Configuration (bif/PyKit-style)

DATE :: 2026-02-20 :: 16:30 (UTC: 00:30)

## Summary

Configured the jnum project for Python wheel packaging using bif, mirroring the PyKit
project layout exactly. Intermediate build artefacts land in `Build/` and final
distributable artefacts land in `Artifacts/`.

### Files created / rewritten

- **`bif.js5`** — rewritten with PyKit-style project config: `pkgname: 'jnum'`,
  `force_architecture: 'None'`, `force_platform: 'Any'`, custom `pkgname_format` /
  `pkgbase_format` / `pkgpab_format` / `target_format`, `buildid` wrapping that embeds
  the flavor tag (`py3`) inside the build-number component, and a Library+Wheel target
  with `[['Python3','Test'], 'Python3']` flavor bundles.

- **`imap.yml`** — rewritten with a three-layer inference chain:
  1. Source dependency (`{PY_ART_NAME}_mod`) tracks `jnum.py`.
  2. Build target (`*.whl`) runs `python3 -m build --outdir {JNUM_BUILDDIR}` from the
     project root, yielding the intermediate wheel and source tarball in `Build/none/any/`.
  3. Artifact target (`*.lib.whl`) copies the wheel and source tarball from `Build/` into
     `Artifacts/none/any/`.
  4. Test target (`*py3,tst*.lib.whl`, virtual) runs `python3 -m pytest .` from `Test/`.

- **`pyproject.toml`** — new standard PEP 517/518 config; uses `py-modules = ["jnum"]`
  (single-file module, not a package directory) with `package-dir = {"" = "Source"}`.

- **`setup.py`** — new file with a custom `BuildCommand` that redirects distutils
  intermediate files to `Build/none/any`. Also injects `BIF_BUILD_BUILDID` as the wheel
  build number so the filename carries it.

- **`Test/pytest.ini`** — minimal `[pytest]` marker file required by the new imap.yml
  `needs: 'pytest.ini'` prerequisite check.

### Verified output

```
bif test  →  jnum-1.0-{buildid}-py3,tst-none-any.lib.whl  124 passed ✓
bif do /0 →
  Artifacts/none/any/jnum-1.0-{buildid}-py3-none-any.lib.whl   ← installable wheel
  Artifacts/none/any/jnum-1.0-{buildid}-py3-src.tar.gz          ← source distribution
  Build/none/any/jnum-1.0-{buildid}-py3-none-any.whl            ← intermediate wheel
  Build/none/any/jnum-1.0.tar.gz                                 ← intermediate sdist
```

===============================================================================================
# README Corrections Against Test Findings

DATE :: 2026-02-20 :: 16:10 (UTC: 00:10)

## Summary

Four inaccuracies in `README.md` corrected after cross-referencing against the confirmed
runtime behaviour established by the test suite.

### Changes

1. **Broken ToC anchor** (`line 219`): `#jmenum--mutable-enum-fields` →
   `#mdenum--mutable-enum-fields`. The auto-generated anchor for the heading
   `## MDEnum — Mutable Enum Fields` is `mdenum-…`, not `jmenum-…`.

2. **Wrong metaclass name** (`line 927`, "How it works internally"): `JEnumMeta.__new__`
   → `DEnumMeta.__new__`. The actual metaclass in `jnum.py` is `DEnumMeta`.

3. **Wrong error message for `MDEnum.ordinal` mutation** (`lines 1155–1156`): The README
   showed `'ordinal' is part of the enum's identity and cannot be changed`, but tests
   confirmed the actual message is `cannot set 'ordinal' — only fields declared in
   __init__ are mutable: ['firmware', 'last_seen']`. The "identity" wording only appears
   when the private backing attribute `._ordinal_` is set directly; the public `.ordinal`
   property alias falls through to the mutable-fields allowlist check.

4. **Redundant comparison-table cell text** (two rows, `vs enum.Enum` and `vs Java`
   tables): `MDEnum / proposed MDEnum` → `MDEnum`. The phrase "proposed MDEnum" was a
   copy-paste artefact that repeated the class name confusingly.

===============================================================================================
# Comprehensive Test Suite for jnum

DATE :: 2026-02-20 :: 15:41 (UTC: 23:41)

## Summary

Added a full pytest test suite covering `DEnum`, `MDEnum`, and `body()`.

### Files created

- `Test/conftest.py` — sys.path fixup so `import jnum` resolves from the `Source/` tree.
- `Test/test_denum.py` — 83 tests across 9 test classes for `DEnum`.
- `Test/test_mdenum.py` — 41 tests across 8 test classes for `MDEnum`.

**Total: 124 tests, all passing (`bif test`).**

### Coverage

**test_denum.py**
- `TestDeclarationStyles` — all four constant declaration styles (bare tuple, `body()`,
  inline anonymous subclass, `@override` decorator), mixed usage, edge cases for
  omitted/non-tuple `args` in inline subclasses.
- `TestOrdinals` — auto-start at 0, skipping of explicitly reserved slots, out-of-order
  explicit ordinals, duplicate/negative/float ordinal errors.
- `TestAPI` — `.name`, `.ordinal`, `values()`, `value_of()`, `from_ordinal()`, subscript
  `[]`, `in` containment, `len()`, iteration order, `list(enum) == values()`.
- `TestStringRepresentation` — `str()`, `repr()` on instances and on the class itself,
  anonymous-subclass suffix stripping in `repr`.
- `TestEqualityAndHashing` — identity equality, cross-type inequality, hash stability,
  dict key and set deduplication usage.
- `TestComparison` — `<`, `<=`, `>`, `>=` by ordinal; `TypeError` for non-DEnum operands;
  `min()`, `max()`, `sorted()`, `sorted(reverse=True)`.
- `TestImmutability` — cannot set init fields, `.name`, `.ordinal`, or new attributes
  after construction; inline-subclass constants also locked.
- `TestInheritance` — finality, abstract base subclassing, zero-constant base, multiple
  independent concrete subclasses.
- `TestMethodOverrides` — per-constant inline dispatch, `NotImplementedError` default,
  `@override` on plain and inline-subclass constants, multiple overrides on one constant,
  decorator return value.
- `TestEdgeCases` — single-constant enum, empty enum, `values()` returns new list,
  forward-reference resolution, dict/set usage, repeated iteration, `match`/`case`.

**test_mdenum.py**
- `TestMDEnumMutability` — init fields are mutable post-construction; `None` fields,
  repeated reassignment, per-constant independence; state reset via `setup_method`.
- `TestMDEnumIdentityImmutable` — private identity attrs (`_name_`, `_ordinal_`,
  `_initialized_`, `_mutable_fields_`) raise "identity"; public property aliases
  raise "only fields declared in __init__".
- `TestMDEnumNewAttributeRejected` — undeclared field raises correct error; error
  message enumerates the actual allowed field names.
- `TestMDEnumSingleton` — mutation through one reference is visible through all
  (`[]`, `value_of()`, `from_ordinal()`); all are `is`-identical.
- `TestMDEnumDeclarationStyles` — bare tuple, `body(ordinal=…)`, inline subclass,
  `@override` with field mutation.
- `TestMDEnumOverrideMutation` — per-constant and base `calibrate()` modify `value`;
  shared `increment()` mutates `count`; mutations are per-constant.
- `TestMDEnumInheritedBehaviors` — full DEnum API surface, str/repr, equality, hash,
  finality, comparison operators.
- `TestMDEnumInternalState` — `_mutable_fields_` is a `frozenset` with exactly the
  names set in `__init__`; `_mutable_stage_` is absent after construction.
