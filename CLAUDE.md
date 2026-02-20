# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**JEnum** (`jenum`) — a single-file Python library implementing Dispatch Enums (`DEnum`) and Mutable Dispatch Enums (`MDEnum`) for Python. Each enum constant is a singleton instance of the enum class, enabling per-constant fields, per-constant method dispatch, and clean interface enforcement without scattered `if/elif` chains.

The library is a reference implementation for a proposed CPython PEP. Requires Python 3.11+.

## Build Commands

This project uses `bif` as its build tool.

```bash
bif do -l            # List all available build targets (numbered)
bif do <n>           # Build target n
bif do <n>/<m>       # Build multiple targets
bif test             # Run tests via pytest
bif clean            # Remove all build/artifact outputs
bif -h               # All bif commands
bif <cmd> -h         # Help for a specific command
```

The `imap.yml` Python test target runs `pytest .` from the `Test/` directory.

## Source Structure

The entire library is a **single file**: `Source/jenum.py`. There are also CLang (C) stubs in `imap.yml` for `hello.c`/`hello.o` build targets, but no C source exists yet.

## Architecture of `Source/jenum.py`

Three metaclass mechanisms work together:

**`DEnumMeta.__prepare__`** — runs before the class body. Injects a lightweight `_ForwardProxy` class into the namespace under the enum's own name. This makes `class PLUS(Operation):` work inside the `Operation` body — at parse time, `Operation` resolves to the proxy, not the not-yet-built real class.

**`_ForwardProxy.__init_subclass__`** — fires the moment each inner constant class (e.g. `PLUS`) finishes building. Stages the inner class in the module-level `_pending` dict keyed by `id(proxy)`.

**`DEnumMeta.__new__`** — runs after the full class body executes. Harvests staged inner classes from `_pending`, extracts their `args`/`ordinal`/method overrides, assigns ordinals (auto-fills gaps around explicit values), builds anonymous subclasses of the real enum class for constants that have overrides, and instantiates each constant as a singleton. Constants are frozen via `__setattr__` after `_initialized_` is set.

**`MDEnum`** (mutable variant) — overrides `__setattr__` with a two-phase strategy: during `__init__`, all assignments are recorded in `_mutable_stage_`; after construction, `_patched_meta_new` promotes that set to a frozen `_mutable_fields_` allowlist. Post-construction writes are only permitted for fields in the allowlist.

**`body()`** — a simple carrier (`_ConstantBody`) that holds args and an optional explicit ordinal. Detected by `isinstance` check in `DEnumMeta.__new__`.

**Four constant declaration styles** (freely mixable):
1. Bare tuple: `NAME = (arg1, arg2)` — auto ordinal
2. `body()`: explicit ordinal and/or args
3. Inline anonymous subclass: `class NAME(MyEnum):` inside the body — per-constant method overrides
4. `@MyEnum.override('NAME')` decorator — post-hoc method binding

## Key Design Rules

- Enum classes with constants defined are **final** — external subclassing raises `TypeError`.
- Abstract base enums (zero constants) can be freely subclassed.
- Ordinals are unique non-negative ints; duplicates raise `ValueError` at class definition time.
- Auto-assigned ordinals skip any values already claimed by explicit ordinals.
- Iteration is always in ordinal order (`_by_ordinal_` list).
- Identity equality: `==` behaves like `is` (singletons). Ordering uses ordinal values.
