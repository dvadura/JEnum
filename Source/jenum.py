# jnum.py — Java-style enums for Python
#
# Reference implementation for a proposed CPython PEP.
# Proposed stdlib names: DEnum and MDEnum
# Minimum Python version: 3.11 (backport floor); 3.13/3.14 for stdlib inclusion
# Technical minimum is 3.7 (__init_subclass__ + ordered dicts), but 3.10 and
# earlier are not supported — see PEP version compatibility section.
#
# Supports:
#   - Per-constant constructor arguments
#   - Custom ordinal values (gaps and non-zero starts allowed)
#   - Default methods defined on the enum class
#   - Per-constant method overrides via inline anonymous subclasses
#   - Single-level inheritance only (enum classes are effectively final)
#   - Immutable constants (singletons)
#   - name, ordinal, values(), value_of(), from_ordinal(), iteration, comparison
#
# Constant declaration syntax (all styles may be freely mixed):
#
#   PLAIN      = ()                      # auto ordinal, no constructor args
#   FIELDED    = (3.14, "hello")         # auto ordinal, constructor args
#   CUSTOM_ORD = body(ordinal=10)        # explicit ordinal, no args
#   FULL       = body(arg, ordinal=5)    # explicit ordinal + args
#
#   # Inline anonymous subclass — use the enum class as the base.
#   # The forward reference is resolved by a proxy class injected via __prepare__:
#   class Operation(DEnum):
#       class PLUS(Operation):           # 'Operation' == proxy at this point
#           args    = ()
#           ordinal = 100               # optional
#           def apply(self, x, y): return x + y

from __future__ import annotations
import types
from typing import Any, Callable, Iterator

_SENTINEL = object()   # marks "no ordinal specified"

# Staging area: inner constant-body classes register here.
# Key: id() of the proxy class placed in the outer enum namespace.
# Value: list of (attr_name, inner_class) in declaration order.
_pending: dict[int, list[tuple[str, type]]] = {}


# ---------------------------------------------------------------------------
# _ConstantBody — carrier returned by body()
# ---------------------------------------------------------------------------

class _ConstantBody:
    def __init__(self, *args: Any, ordinal: Any = _SENTINEL):
        self._args:    tuple = args
        self._ordinal: Any   = ordinal


def body(*args: Any, ordinal: int = _SENTINEL) -> _ConstantBody:
    """
    Declare a constant with an optional explicit ordinal and/or constructor args.

        LOW    = body()                    # auto ordinal
        MEDIUM = body(ordinal=10)          # explicit ordinal
        HIGH   = body("fast", ordinal=20)  # ordinal + constructor arg

    Combine with @MyEnum.override('NAME') to add per-constant methods post-hoc.
    """
    return _ConstantBody(*args, ordinal=ordinal)


def _make_proxy(enum_name: str) -> type:
    """
    Create a fresh proxy class to stand in for the not-yet-built enum class
    during the execution of its body.

    When Python sees `class PLUS(Operation):` inside the Operation body,
    'Operation' resolves to this proxy (because __prepare__ injected it).
    The proxy's __init_subclass__ fires immediately, staging PLUS in _pending
    so the outer metaclass can harvest it later.
    """
    proxy_id_holder: list = []   # mutable cell so the closure can read proxy_id

    def _init_subclass(cls, **kwargs):
        proxy_id = proxy_id_holder[0]
        _pending.setdefault(proxy_id, []).append((cls.__name__, cls))

    proxy = type(
        f"_{enum_name}_",
        (),
        {"__init_subclass__": classmethod(_init_subclass)},
    )
    proxy_id_holder.append(id(proxy))
    return proxy


# ---------------------------------------------------------------------------
# DEnumMeta — the metaclass
# ---------------------------------------------------------------------------

class DEnumMeta(type):

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        """
        Inject a proxy class into the namespace under the enum's own name so
        that `class CONST(MyEnum):` inside the body resolves without NameError.
        """
        proxy = _make_proxy(name)
        return {name: proxy, "_jnum_proxy_": proxy}

    def __new__(mcs, name: str, bases: tuple, namespace: dict, **kwargs) -> "DEnumMeta":

        proxy = namespace.get("_jnum_proxy_")

        # ----------------------------------------------------------------
        # Guard: block external subclassing of a completed enum.
        # ----------------------------------------------------------------
        is_denum_root = (name == "DEnum" and not any(isinstance(b, DEnumMeta) for b in bases))
        if not is_denum_root:
            for base in bases:
                if isinstance(base, DEnumMeta) and getattr(base, "_members_", None):
                    raise TypeError(
                        f"Cannot subclass enum '{base.__name__}': enum classes "
                        f"are final once constants are defined. "
                        f"To add per-constant overrides, write "
                        f"'class MYCONST({base.__name__}):' inside the class body."
                    )

        # ----------------------------------------------------------------
        # Collect constant declarations
        # ----------------------------------------------------------------
        raw_constants: list[tuple[str, tuple, dict, Any]] = []
        clean: dict[str, Any] = {}

        # Inner constant-body classes staged by the proxy's __init_subclass__
        staged: dict[str, type] = {}
        if proxy is not None:
            staged = dict(_pending.pop(id(proxy), []))

        for key, value in namespace.items():
            if key in ("_jnum_proxy_", name):   # skip injected proxy entries
                continue
            if key.startswith("_"):
                clean[key] = value
                continue

            # --- inner-class constant body ---
            if key in staged:
                inner_cls    = staged[key]
                args         = getattr(inner_cls, "args", ())
                if not isinstance(args, tuple):
                    args = (args,)
                explicit_ord = getattr(inner_cls, "ordinal", _SENTINEL)
                overrides    = {
                    k: v for k, v in vars(inner_cls).items()
                    if not k.startswith("_")
                    and callable(v)
                    and k not in ("args", "ordinal")
                }
                raw_constants.append((key, args, overrides, explicit_ord))
                continue

            # --- body() carrier ---
            if isinstance(value, _ConstantBody):
                raw_constants.append((key, value._args, {}, value._ordinal))
                continue

            # --- bare tuple ---
            if isinstance(value, tuple):
                raw_constants.append((key, value, {}, _SENTINEL))
                continue

            # Real class member
            clean[key] = value

        # ----------------------------------------------------------------
        # Assign ordinals
        # ----------------------------------------------------------------
        assigned: dict[str, int] = {}
        for cname, _, __, explicit_ord in raw_constants:
            if explicit_ord is not _SENTINEL:
                if not isinstance(explicit_ord, int) or explicit_ord < 0:
                    raise ValueError(
                        f"{name}.{cname}: ordinal must be a non-negative int, "
                        f"got {explicit_ord!r}"
                    )
                if explicit_ord in assigned.values():
                    raise ValueError(f"{name}: duplicate explicit ordinal {explicit_ord}")
                assigned[cname] = explicit_ord

        used: set[int] = set(assigned.values())
        counter = 0
        final_constants: list[tuple[str, tuple, dict, int]] = []
        for cname, args, overrides, explicit_ord in raw_constants:
            if cname in assigned:
                ord_val = assigned[cname]
            else:
                while counter in used:
                    counter += 1
                ord_val = counter
                used.add(ord_val)
            counter = ord_val + 1
            final_constants.append((cname, args, overrides, ord_val))

        final_constants.sort(key=lambda t: t[3])

        # ----------------------------------------------------------------
        # Build the enum class
        # ----------------------------------------------------------------
        cls = super().__new__(mcs, name, bases, clean, **kwargs)
        cls._members_:    dict[str, "DEnum"] = {}
        cls._by_ordinal_: list["DEnum"]      = []

        # ----------------------------------------------------------------
        # Instantiate each constant
        # ----------------------------------------------------------------
        for const_name, args, overrides, ord_val in final_constants:

            if overrides:
                # Anonymous subclass carrying the per-constant overrides.
                # Built via type.__new__ (not DEnumMeta.__new__) to avoid
                # re-triggering constant collection.
                anon_cls = type.__new__(
                    mcs,
                    f"{name}.{const_name}",
                    (cls,),
                    {"__qualname__": f"{name}.{const_name}", **overrides},
                )
                instance = anon_cls.__new__(anon_cls)
            else:
                instance = cls.__new__(cls)

            object.__setattr__(instance, "_name_",    const_name)
            object.__setattr__(instance, "_ordinal_", ord_val)
            instance.__init__(*args)
            object.__setattr__(instance, "_initialized_", True)

            cls._members_[const_name] = instance
            cls._by_ordinal_.append(instance)
            setattr(cls, const_name, instance)

        return cls

    # ------------------------------------------------------------------
    # Class-level protocol
    # ------------------------------------------------------------------

    def __iter__(cls) -> Iterator["DEnum"]:
        return iter(cls._by_ordinal_)

    def __len__(cls) -> int:
        return len(cls._by_ordinal_)

    def __getitem__(cls, name: str) -> "DEnum":
        try:
            return cls._members_[name]
        except KeyError:
            raise KeyError(f"{cls.__name__} has no member {name!r}") from None

    def __contains__(cls, item: object) -> bool:
        return item in cls._members_.values()

    def __repr__(cls) -> str:
        members = ", ".join(
            f"{m}={cls._members_[m]._ordinal_}" for m in cls._members_
        )
        return f"<jenum {cls.__name__}: {members}>"


# ---------------------------------------------------------------------------
# DEnum — base class
# ---------------------------------------------------------------------------

class DEnum(metaclass=DEnumMeta):
    """
    Base class for Java-style enums.

    Constant declaration styles (freely mixable):

        # 1. Bare tuple — auto ordinal, optional constructor args
        MERCURY = (3.303e+23, 2.4397e6)

        # 2. body() — explicit ordinal and/or constructor args
        LOW    = body()
        MEDIUM = body(ordinal=10)
        HIGH   = body("fast", ordinal=20)

        # 3. Inline anonymous subclass — use the enum class as base:
        class Operation(DEnum):
            class PLUS(Operation):      # <-- the enum being defined
                args    = ()            # constructor args (default: ())
                ordinal = 100           # optional explicit ordinal
                def apply(self, x, y): return x + y

        # 4. Post-hoc override decorator
        @MyEnum.override('NAME')
        def some_method(self): ...

    Rules:
        - Enum classes with constants defined are final (no external subclassing).
        - 'class CONST(MyEnum):' inside the body is the exception — the forward
          reference resolves via a proxy class injected by __prepare__, and the
          inner class is harvested as a constant definition.
        - Ordinals must be unique non-negative integers.
        - Auto-assigned ordinals skip any explicitly reserved values.
        - Constants are immutable after construction.
        - Iteration is in ordinal order.
    """

    _name_:        str
    _ordinal_:     int
    _members_:     dict[str, "DEnum"]
    _by_ordinal_:  list["DEnum"]
    _initialized_: bool

    def __init__(self, *args):
        """Override to receive per-constant constructor args."""

    # ------------------------------------------------------------------
    # Core properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Declared name of the constant  (Java: .name())"""
        return self._name_

    @property
    def ordinal(self) -> int:
        """Ordinal value — auto-assigned or explicitly set  (Java: .ordinal())"""
        return self._ordinal_

    # ------------------------------------------------------------------
    # Class-level helpers
    # ------------------------------------------------------------------

    @classmethod
    def values(cls) -> list["DEnum"]:
        """All constants in ordinal order  (Java: MyEnum.values())"""
        return list(cls._by_ordinal_)

    @classmethod
    def value_of(cls, name: str) -> "DEnum":
        """Look up constant by name  (Java: MyEnum.valueOf(name))"""
        return cls[name]

    @classmethod
    def from_ordinal(cls, ordinal: int) -> "DEnum":
        """Look up constant by ordinal value."""
        for member in cls._by_ordinal_:
            if member._ordinal_ == ordinal:
                return member
        raise KeyError(f"{cls.__name__} has no member with ordinal {ordinal}")

    # ------------------------------------------------------------------
    # Post-hoc per-constant override decorator
    # ------------------------------------------------------------------

    @classmethod
    def override(cls, constant_name: str):
        """
        Decorator: bind a method to a single constant after class definition.

            @Operation.override('PLUS')
            def apply(self, x, y):
                return x + y
        """
        def decorator(fn: Callable) -> Callable:
            instance = cls._members_[constant_name]
            inst_cls = type(instance)
            if inst_cls is not cls:
                setattr(inst_cls, fn.__name__, fn)
            else:
                object.__setattr__(
                    instance,
                    fn.__name__,
                    types.MethodType(fn, instance),
                )
            return fn
        return decorator

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------

    def __setattr__(self, key: str, value: Any) -> None:
        if getattr(self, "_initialized_", False):
            raise AttributeError(
                f"{type(self).__name__}.{self._name_} is immutable: "
                f"cannot set {key!r} after construction"
            )
        super().__setattr__(key, value)

    # ------------------------------------------------------------------
    # Dunder niceties
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"{type(self).__name__.split('.')[0]}.{self._name_}"

    def __str__(self) -> str:
        return self._name_

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._name_))

    def __eq__(self, other: object) -> bool:
        return self is other

    def __lt__(self, other: "DEnum") -> bool:
        if not isinstance(other, DEnum):
            return NotImplemented
        return self._ordinal_ < other._ordinal_

    def __le__(self, other: "DEnum") -> bool:
        if not isinstance(other, DEnum):
            return NotImplemented
        return self._ordinal_ <= other._ordinal_

    def __gt__(self, other: "DEnum") -> bool:
        if not isinstance(other, DEnum):
            return NotImplemented
        return self._ordinal_ > other._ordinal_

    def __ge__(self, other: "DEnum") -> bool:
        if not isinstance(other, DEnum):
            return NotImplemented
        return self._ordinal_ >= other._ordinal_



# ---------------------------------------------------------------------------
# MDEnum — Java-style Mutable Enum
#
# Identical to DEnum in every respect except that fields declared in
# __init__ remain mutable after construction.  The enum's identity is
# still fully locked:
#
#   LOCKED forever  : _name_, _ordinal_, _initialized_, _mutable_fields_,
#                     any attribute NOT set during __init__, methods,
#                     and the enum class structure itself.
#
#   MUTABLE         : any instance attribute first assigned inside __init__.
#
# Typical use-case: carrying live device/session state alongside a state
# enum, where the state constant itself is stable but its payload changes.
# ---------------------------------------------------------------------------

class MDEnum(DEnum):
    """
    Mutable variant of DEnum.

    Fields set in __init__ are freely mutable after construction.
    Everything else — name, ordinal, identity, methods, and any attribute
    NOT established during __init__ — is permanently locked.

    Use this when constants need to carry live state (device data, session
    info, counters) that changes over the object's lifetime, while keeping
    the enum's structural identity immutable.

    Declaration syntax is identical to DEnum — all four styles work the
    same way.  Just inherit from MDEnum instead of DEnum.

    Example:

        class DeviceState(MDEnum):
            CONNECTED    = ("unknown",)
            DISCONNECTED = ("",)
            ERROR        = ("",)

            def __init__(self, firmware: str):
                self.firmware  = firmware   # mutable after construction
                self.last_seen = None       # mutable after construction

        DeviceState.CONNECTED.firmware  = "2.1.4"      # OK
        DeviceState.CONNECTED.last_seen = datetime.now()  # OK
        DeviceState.CONNECTED.ordinal   = 99            # AttributeError — locked
        DeviceState.CONNECTED.new_field = "x"           # AttributeError — not in __init__
    """

    _mutable_fields_: frozenset   # names set during __init__ — the allowlist

    def __setattr__(self, key: str, value: Any) -> None:
        # ── Phase 1: during construction (before _initialized_ is set) ────
        # The metaclass uses object.__setattr__ directly for _name_ and
        # _ordinal_, so those never reach us here.  Everything that does
        # reach us during __init__ is a user field — record and set it.
        if not getattr(self, "_initialized_", False):
            # Accumulate field names in a staging set on the instance.
            try:
                stage = object.__getattribute__(self, "_mutable_stage_")
            except AttributeError:
                stage = set()
                object.__setattr__(self, "_mutable_stage_", stage)

            stage.add(key)
            object.__setattr__(self, key, value)   # bypass DEnum's lock
            return

        # ── Phase 2: post-construction — enforce the allowlist ────────────
        _identity_ = frozenset({
            "_name_", "_ordinal_", "_initialized_",
            "_mutable_fields_", "_mutable_stage_",
        })
        if key in _identity_:
            raise AttributeError(
                f"{type(self).__name__}.{self._name_}: "
                f"{key!r} is part of the enum's identity and cannot be changed"
            )

        try:
            mutable = object.__getattribute__(self, "_mutable_fields_")
        except AttributeError:
            mutable = frozenset()

        if key not in mutable:
            raise AttributeError(
                f"{type(self).__name__}.{self._name_}: "
                f"cannot set {key!r} — only fields declared in __init__ "
                f"are mutable: {sorted(mutable)}"
            )

        object.__setattr__(self, key, value)   # allowed mutation


# ---------------------------------------------------------------------------
# Post-construction: seal _mutable_fields_ on MDEnum instances.
#
# After DEnumMeta.__new__ calls instance.__init__(), the _mutable_stage_
# set is complete.  We wrap DEnumMeta.__new__ to promote it to the
# immutable _mutable_fields_ frozenset on every MDEnum constant.
# ---------------------------------------------------------------------------

_original_meta_new = DEnumMeta.__new__

def _patched_meta_new(mcs, name, bases, namespace, **kwargs):
    cls = _original_meta_new(mcs, name, bases, namespace, **kwargs)

    # Only process classes that are concrete MDEnum subclasses
    if any(b is MDEnum for b in cls.__mro__[1:]) and cls is not MDEnum:
        for instance in cls._members_.values():
            # Promote staging set → frozen allowlist
            try:
                stage = object.__getattribute__(instance, "_mutable_stage_")
            except AttributeError:
                stage = set()
            object.__setattr__(instance, "_mutable_fields_", frozenset(stage))
            try:
                object.__delattr__(instance, "_mutable_stage_")
            except AttributeError:
                pass

    return cls

DEnumMeta.__new__ = staticmethod(_patched_meta_new)


# ---------------------------------------------------------------------------
# Claude Code skill — embedded so jenum is self-contained as a single file
# ---------------------------------------------------------------------------

_JENUM_SKILL = """\
---
name: jenum
description: >
  Work with jenum DEnum and MDEnum classes — Java-style dispatch enums for Python.
  Use when creating, modifying, or reading code that imports from jenum.
argument-hint: "[describe what you want to build or fix]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# JEnum Skill — DEnum and MDEnum

This skill teaches you how to create and use `DEnum` and `MDEnum` classes from the
`jenum` library.  Use it whenever you work with code that does `from jenum import`.

## Quick Import

```python
from jenum import DEnum, MDEnum, body
```

## DEnum — Dispatch Enum

Each constant is an immutable singleton instance of the enum class.  Define one class,
get back a set of frozen, identifiable, orderable constants that can each carry their
own data and override any method.

### Constant Declaration Styles (freely mixable)

```python
from jenum import DEnum, body

class Planet(DEnum):
    # Style 1 — bare tuple: auto ordinal, constructor args forwarded to __init__
    MERCURY = (3.303e+23, 2.4397e6)
    VENUS   = (4.869e+24, 6.0518e6)
    EARTH   = (5.976e+24, 6.37814e6)

    # Style 2 — body(): explicit ordinal and/or args
    MARS    = body(6.421e+23, 3.3972e6, ordinal=10)

    def __init__(self, mass: float, radius: float):
        self.mass   = mass
        self.radius = radius

    def surface_gravity(self) -> float:
        G = 6.67300e-11
        return G * self.mass / self.radius ** 2
```

```python
from jenum import DEnum, body

class Operation(DEnum):
    # Style 3 — inline anonymous subclass: per-constant method overrides
    class PLUS(Operation):
        args = ()           # constructor args (default empty)
        ordinal = 0         # optional explicit ordinal
        def apply(self, x, y): return x + y

    class MINUS(Operation):
        args = ()
        def apply(self, x, y): return x - y

    class TIMES(Operation):
        args = ()
        def apply(self, x, y): return x * y

    def apply(self, x, y):
        raise NotImplementedError(f"{self.name} has no apply()")
```

```python
# Style 4 — post-hoc override decorator (after class body)
@Operation.override('PLUS')
def describe(self) -> str:
    return "addition"
```

### body() — Explicit Ordinal / Args Carrier

```python
LOW    = body()                    # auto ordinal, no args
MEDIUM = body(ordinal=10)          # explicit ordinal, no args
HIGH   = body("fast", ordinal=20)  # explicit ordinal + constructor arg
```

### Core Instance API

| Attribute/Method          | Description                                   |
|---------------------------|-----------------------------------------------|
| `.name`                   | Declared constant name (str)                  |
| `.ordinal`                | Ordinal value (int)                           |
| `MyEnum.values()`         | All constants in ordinal order                |
| `MyEnum.value_of(name)`   | Look up by name string                        |
| `MyEnum.from_ordinal(n)`  | Look up by ordinal int                        |
| `MyEnum['NAME']`          | Subscript lookup by name                      |
| `NAME in MyEnum`          | Membership test                               |
| `len(MyEnum)`             | Number of constants                           |
| `for c in MyEnum:`        | Iterate in ordinal order                      |

### Immutability

Constants are frozen after `__init__` returns.  Any post-construction assignment
raises `AttributeError`.

```python
Planet.EARTH.mass = 0       # AttributeError — immutable
```

### Identity Equality

`==` is `is`.  Use `is` or `==` interchangeably for identity checks:

```python
Planet.EARTH is Planet.EARTH    # True
Planet.EARTH == Planet.EARTH    # True
Planet.EARTH == Planet.MARS     # False
```

### Ordering

Comparison operators (`<`, `<=`, `>`, `>=`) compare by ordinal:

```python
Planet.MERCURY < Planet.EARTH   # True (ordinal 0 < 2)
```

### Final Classes

Once a `DEnum` subclass defines at least one constant, it is **final** — you cannot
subclass it further.  Abstract base enums (zero constants) can be subclassed freely.

```python
class Color(DEnum): pass        # abstract — OK to subclass

class RGB(Color):               # OK — Color has no constants
    RED   = ()
    GREEN = ()
    BLUE  = ()

class Bad(RGB): pass            # TypeError — RGB has constants
```

---

## MDEnum — Mutable Dispatch Enum

Identical to `DEnum` except that fields assigned in `__init__` remain mutable after
construction.  The constant's identity (name, ordinal, methods, class structure) is
still permanently locked.

### Use Case

Carry live, changing state alongside a stable enum identity:

```python
from jenum import MDEnum

class DeviceState(MDEnum):
    CONNECTED    = ("unknown",)
    DISCONNECTED = ("",)
    ERROR        = ("",)

    def __init__(self, firmware: str):
        self.firmware  = firmware   # mutable — declared in __init__
        self.last_seen = None       # mutable — declared in __init__

DeviceState.CONNECTED.firmware  = "2.1.4"          # OK
DeviceState.CONNECTED.last_seen = "2026-01-01"      # OK
DeviceState.CONNECTED.ordinal   = 99                # AttributeError — identity locked
DeviceState.CONNECTED.new_field = "x"               # AttributeError — not in __init__
```

### Mutability Rules

| Attribute                      | Mutable? |
|-------------------------------|----------|
| `_name_`, `_ordinal_`         | No — identity |
| Any field set in `__init__`   | Yes       |
| Any field NOT set in `__init__`| No       |
| Methods                       | No        |

---

## Common Patterns

### Dispatch Without if/elif

```python
class Shape(DEnum):
    class CIRCLE(Shape):
        def area(self, r): return 3.14159 * r * r

    class SQUARE(Shape):
        def area(self, r): return r * r

    def area(self, r):
        raise NotImplementedError

# Dispatch: no if/elif needed
result = Shape.CIRCLE.area(5)
```

### Enum with Constructor Arguments

```python
class HttpMethod(DEnum):
    GET    = ("GET",    False)
    POST   = ("POST",   True)
    PUT    = ("PUT",    True)
    DELETE = ("DELETE", False)

    def __init__(self, verb: str, has_body: bool):
        self.verb     = verb
        self.has_body = has_body

# Usage
if HttpMethod.POST.has_body:
    ...
```

### Mixed Ordinals (Gaps Allowed)

```python
class Priority(DEnum):
    LOW    = body(ordinal=10)
    NORMAL = body(ordinal=20)
    HIGH   = body(ordinal=30)
    URGENT = body(ordinal=100)

Priority.URGENT.ordinal   # 100
list(Priority)            # [LOW, NORMAL, HIGH, URGENT] — ordinal order
```

### State Machine with MDEnum

```python
class ConnState(MDEnum):
    IDLE        = ()
    CONNECTING  = ()
    CONNECTED   = ()
    ERROR       = ()

    def __init__(self):
        self.retries = 0
        self.detail  = ""

# Each constant tracks its own live state
ConnState.CONNECTING.retries += 1
ConnState.ERROR.detail = "timeout"
```

---

## Error Reference

| Situation | Exception |
|-----------|-----------|
| Subclass a final enum | `TypeError` |
| Duplicate explicit ordinal | `ValueError` |
| Non-integer or negative ordinal | `ValueError` |
| Write to immutable DEnum constant | `AttributeError` |
| Write to MDEnum identity field | `AttributeError` |
| Write undeclared field to MDEnum | `AttributeError` |
| `value_of` unknown name | `KeyError` |
| `from_ordinal` unknown ordinal | `KeyError` |

---

## Installing This Skill

Run once from Python to install the skill into your project:

```python
import jenum
jenum.claude_init()   # installs .claude/skills/jenum/SKILL.md
```
"""


def claude_skill() -> str:
    """Return the jenum Claude Code skill content as a markdown string.

    The skill teaches Claude how to create and use DEnum and MDEnum classes.
    Install it into your project with :func:`claude_init`.

    Example::

        import jenum
        print(jenum.claude_skill()[:80])
    """
    return _JENUM_SKILL


def install_claude_skills(project_dir=None, force: bool = False):
    """Install the jenum Claude Code skill into a project's .claude/skills/ directory.

    Writes the skill to ``<project_dir>/.claude/skills/jenum/SKILL.md``,
    namespaced under ``jenum/`` to avoid conflicts with other skills.

    Args:
        project_dir: Project root directory.  Defaults to ``Path.cwd()``.
        force: Overwrite existing skill file if True; skip if False (default).

    Returns:
        List of :class:`~pathlib.Path` objects for every file written.

    Example::

        import jenum
        jenum.install_claude_skills()
    """
    from pathlib import Path

    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    target_dir = project_dir / ".claude" / "skills" / "jenum"
    target_dir.mkdir(parents=True, exist_ok=True)

    target_file = target_dir / "SKILL.md"
    if target_file.exists() and not force:
        print(f"Skipping {target_file} (already exists, use force=True to overwrite)")
        return []

    target_file.write_text(_JENUM_SKILL, encoding="utf-8")
    print(f"Installed: {target_file}")
    print(f"\nInstalled 1 skill to {target_dir}")
    return [target_file]


def claude_init(project_dir=None, force: bool = False):
    """Initialize Claude Code support for jenum in your project.

    Installs the jenum skill into ``<project_dir>/.claude/skills/jenum/SKILL.md``
    so that Claude Code can load it and understand how to work with DEnum and
    MDEnum classes.

    Args:
        project_dir: Project root directory.  Defaults to ``Path.cwd()``.
        force: Overwrite existing files if True; skip if False (default).

    Returns:
        Dict with key ``'skills'`` mapping to a list of installed
        :class:`~pathlib.Path` objects.

    Example::

        import jenum
        jenum.claude_init()

        # Force overwrite an existing installation
        jenum.claude_init(force=True)
    """
    from pathlib import Path

    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    result = {"skills": install_claude_skills(project_dir, force)}

    total = len(result["skills"])
    if total == 0:
        print("\n✓ No new files installed (everything already exists)")
    else:
        print(f"\n✓ Claude Code initialization complete! Installed {total} file(s)")

    return result


# ---------------------------------------------------------------------------
# Re-export the public surface
# ---------------------------------------------------------------------------

# Overwrite the earlier __all__ with the complete set
__all__ = ["DEnum", "MDEnum", "body", "claude_skill", "install_claude_skills", "claude_init"]
