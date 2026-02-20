# PEP XXXX — DispatchEnum (DEnum) and Mutable Dispatch Enum (MDEnum)

| Field | Value |
|---|---|
| PEP | XXXX |
| Title | DispatchEnum (DEnum) and Mutable Dispatch Enum (MDEnum) |
| Author | *[your name]* |
| Status | Draft |
| Type | Standards Track |
| Requires | PEP 435 |
| Created | 2026 |
| Python-Version | 3.13 or 3.14 |
| Post-History | — |

---

## Abstract

This PEP proposes extending Python's `enum.Enum` to support **per-constant method dispatch** and **declared-field mutability**, bringing Python's enum capability to parity with Java's — arguably the most mature enum system in widespread use. The central motivation is that well-designed enums should carry behaviour, not just identity, eliminating the scattered `if`/`elif` chains that currently proliferate wherever enum values are inspected. Two new base classes are proposed: `enum.DEnum` for enums with per-constant method overrides and immutable fields, and `enum.MDEnum` for enums that additionally allow declared fields to be mutated after construction.

---

## Motivation

### The current state of Python enums

PEP 435 (accepted Python 3.4) gave Python named, typed constants with iteration and comparison. It solved the "magic number" problem effectively. What it did not solve — and what this PEP addresses — is the **behaviour problem**: the tendency for enum-inspecting code to become a sea of `if`/`elif` chains spread across a codebase.

Consider a typical Python codebase that processes orders:

```python
# order_mailer.py
def send_status_email(order):
    if order.status == OrderStatus.PENDING:
        subject  = "We received your order"
        template = "pending.html"
    elif order.status == OrderStatus.CONFIRMED:
        subject  = "Your order is confirmed"
        template = "confirmed.html"
    elif order.status == OrderStatus.SHIPPED:
        subject  = f"Tracking: {order.tracking_id}"
        template = "shipped.html"
    elif order.status == OrderStatus.CANCELLED:
        subject  = "Your order was cancelled"
        template = "cancelled.html"
    send(subject, template, order)

# inventory.py
def adjust_inventory(order):
    if order.status == OrderStatus.CONFIRMED:
        reserve(order)
    elif order.status == OrderStatus.CANCELLED:
        release(order)

# billing.py
def is_billable(order) -> bool:
    return order.status in (
        OrderStatus.CONFIRMED,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    )
```

This pattern has three serious problems:

**1. The logic is scattered.** Understanding what `CONFIRMED` means requires reading every file that branches on it. Adding a new status (`RETURNED`) requires a code-wide search to find every branch that must be updated.

**2. Omissions are silent.** If a developer adds `RETURNED` and forgets to handle it in `billing.py`, the default branch (or no branch) silently returns the wrong answer. There is no static or runtime guarantee that all cases are covered.

**3. The enum is lying about its responsibility.** `OrderStatus` defines what the statuses *are* but deliberately knows nothing about what they *mean*. Every piece of meaning lives elsewhere, duplicated and diverging.

The correct fix is to move the per-status logic onto the enum itself:

```python
class OrderStatus(DEnum):
    class CONFIRMED(OrderStatus):
        def email_subject(self, order): return "Your order is confirmed"
        def adjust_inventory(self, order): reserve(order)
        def is_billable(self): return True

    class CANCELLED(OrderStatus):
        def email_subject(self, order): return "Your order was cancelled"
        def adjust_inventory(self, order): release(order)
        def is_billable(self): return False

    # abstract interface
    def email_subject(self, order): raise NotImplementedError
    def adjust_inventory(self, order): raise NotImplementedError
    def is_billable(self) -> bool: raise NotImplementedError
```

Now every service is trivial:

```python
def send_status_email(order):
    send(order.status.email_subject(order), order)

def adjust_inventory(order):
    order.status.adjust_inventory(order)

def is_billable(order) -> bool:
    return order.status.is_billable()
```

Adding `RETURNED` is a single, contained change to `OrderStatus`. No search required. If `is_billable` is not implemented on `RETURNED`, the `NotImplementedError` fires at the call site immediately, pointing directly at the gap.

### Why `enum.Enum` cannot do this today

Python's `enum.Enum` supports methods on the enum class, but **not per-constant method overrides**. The following does not work:

```python
class Operation(enum.Enum):
    PLUS  = 1
    MINUS = 2

    # This applies to all constants — there is no way to make
    # PLUS.apply() and MINUS.apply() do different things.
    def apply(self, x, y):
        ...
```

The canonical workaround is a dispatch dictionary or `match`/`case` block inside the method — which is just the scattered-logic problem relocated into the enum file rather than eliminated.

Several third-party libraries have attempted partial solutions (`aenum`, `strenum`, custom metaclasses), but none has proposed a clean, PEP-level design that feels native to Python.

### Prior art

**Java** (Java 5, 2004): Java enums are classes; each constant is a singleton instance. Anonymous per-constant subclasses enable full method override per constant. Java's `Operation` enum with per-constant `apply()` is the canonical textbook example of this pattern. Twenty years of production use have validated the design.

**Kotlin**: `sealed class` achieves similar dispatch with more flexibility. Each subclass is a full class, and `when` expressions provide exhaustiveness checking.

**Swift**: `enum` with associated values and methods. Per-variant computed properties achieve similar patterns.

**Rust**: `enum` variants can be structs or tuples; `match` with exhaustiveness checking enforced by the compiler.

The common thread across all modern type systems: the community independently converged on the idea that named discriminated types should carry behaviour, not just identity.

**Previous Python enum PEPs**: PEP 354 (rejected, 2005), PEP 3144 (withdrawn, 2009), PEP 435 (accepted, 2013). None addressed per-constant behaviour.

---

## Specification

### New base classes

Two new base classes are added to the `enum` module:

```python
enum.DEnum    # immutable fields, per-constant method dispatch
enum.MDEnum   # mutable declared fields, per-constant method dispatch
```

Both inherit from `enum.Enum` and preserve all existing `Enum` semantics. They are opt-in: existing `enum.Enum` usage is completely unaffected.

---

### `enum.DEnum`

#### 1. Per-constant method dispatch via inner class syntax

A class defined inside a `DEnum` body, using the enum class itself as its base, is interpreted as a **constant definition with per-constant method overrides**:

```python
class Operation(DEnum):

    class PLUS(Operation):
        def apply(self, x, y): return x + y
        def symbol(self): return "+"

    class MINUS(Operation):
        def apply(self, x, y): return x - y
        def symbol(self): return "-"

    # Default / abstract implementations
    def apply(self, x, y): raise NotImplementedError
    def symbol(self) -> str: raise NotImplementedError
```

The inner class is not a real subclass in the MRO sense — it is syntactic sugar for a per-constant anonymous subclass instantiated once as a singleton. `isinstance(Operation.PLUS, Operation)` is `True`.

**Forward reference resolution**: Because `Operation` is not yet bound when `class PLUS(Operation):` is evaluated, the interpreter injects a forward-reference proxy into the class namespace under the enum's own name before executing the body. This is analogous to how `__prepare__` works today, but formalised as a language behaviour rather than a metaclass trick.

#### 2. Constructor arguments via `args`

If a constant needs to pass arguments to the enum's `__init__`, declare them as `args` inside the inner class:

```python
class Planet(DEnum):

    class EARTH(Planet):
        args = (5.976e+24, 6.37814e6)
        def has_known_life(self) -> bool: return True

    class MARS(Planet):
        args = (6.421e+23, 3.3972e6)
        def has_known_life(self) -> bool: return False

    def __init__(self, mass: float, radius: float):
        self.mass   = mass
        self.radius = radius

    def has_known_life(self) -> bool: raise NotImplementedError
```

For constants without method overrides, the existing tuple syntax continues to work:

```python
class Planet(DEnum):
    MERCURY = (3.303e+23, 2.4397e6)   # no overrides — tuple syntax is fine
    EARTH   = (5.976e+24, 6.37814e6)

    def __init__(self, mass, radius):
        self.mass = mass
        self.radius = radius
```

#### 3. Explicit ordinal values

Ordinals are auto-assigned from 0 by default. Any constant may declare an explicit ordinal, which is useful when the ordinal maps to an external protocol value (HTTP status code, Unix signal, etc.):

```python
class HttpStatus(DEnum):
    OK           = (ordinal=200)   # proposed new syntax (see Syntax section)
    NOT_FOUND    = (ordinal=404)
    INTERNAL_ERR = (ordinal=500)
```

Or inside an inner class body:

```python
class PLUS(Operation):
    ordinal = 10
    def apply(self, x, y): return x + y
```

Auto-assigned ordinals skip any values claimed by explicit declarations.

#### 4. Post-hoc method binding via `@Enum.override`

For long method bodies that would be awkward inside a compact inner class, a decorator form is provided:

```python
class Formatter(DEnum):
    UPPER = ()
    LOWER = ()

    def format(self, text: str) -> str: raise NotImplementedError

@Formatter.override('UPPER')
def format(self, text): return text.upper()

@Formatter.override('LOWER')
def format(self, text): return text.lower()
```

`override` binds the function to the named constant's anonymous subclass, not to the constant's instance directly, preserving normal method resolution behaviour.

#### 5. Immutability

All fields set during `__init__` are immutable after construction. Attempts to assign to them raise `AttributeError`. This is identical to the current behaviour of `enum.Enum` with `value`.

#### 6. Abstract base enums

A `DEnum` with no constants declared acts as a shared interface that concrete subclasses can implement. This enables a shared method contract across unrelated enum families:

```python
class Printable(DEnum):
    def to_display_string(self) -> str: raise NotImplementedError

class Color(Printable):
    RED  = ()
    BLUE = ()
    def to_display_string(self): return self.name.lower()

class Severity(Printable):
    LOW  = ()
    HIGH = ()
    def to_display_string(self): return f"[{self.name}]"
```

#### 7. Finality

A `DEnum` with constants is implicitly final — it cannot be subclassed externally. Only inner constant-body classes (which are not real subclasses) are permitted. This mirrors Java's enum finality semantics and prevents the MRO ambiguity that would arise if enum subclasses could add constants.

---

### `enum.MDEnum`

`MDEnum` extends `DEnum` with one additional capability: fields declared in `__init__` are **mutable** after construction.

Everything else — `name`, `ordinal`, the enum's class structure, and any attribute *not* set during `__init__` — remains permanently locked.

```python
class DeviceState(MDEnum):
    CONNECTED    = ("unknown",)
    DISCONNECTED = ("",)
    ERROR        = ("",)

    def __init__(self, firmware: str):
        self.firmware  = firmware    # mutable
        self.last_seen = None        # mutable

DeviceState.CONNECTED.firmware  = "2.1.4"       # OK
DeviceState.CONNECTED.last_seen = datetime.now() # OK
DeviceState.CONNECTED.ordinal   = 99             # AttributeError
DeviceState.CONNECTED.new_attr  = "x"            # AttributeError
```

The set of mutable fields is determined at construction time from the names assigned during `__init__`. This set is frozen — new fields cannot be added post-construction.

**Use case**: State machines, device registries, connection pools — anywhere you want one canonical object per state, carrying live data that updates over time.

**Thread safety**: `MDEnum` provides no synchronisation. Callers requiring concurrent mutation should use standard Python synchronisation primitives. A `threading.Lock` may itself be stored as a mutable field.

---

### Proposed syntax additions

The current `jnum` proof-of-concept uses `body(ordinal=N)` as a helper for constants that need an explicit ordinal but no method overrides. This is workable but not Pythonic. Three syntax options are presented for Steering Council consideration:

**Option A — keyword in the value tuple** (new grammar):

```python
class HttpStatus(DEnum):
    OK        = (ordinal=200)
    NOT_FOUND = (ordinal=404)
```

This requires a grammar change to allow keyword arguments in tuple literals when used as enum constant values. The parser would need to distinguish this from a regular tuple, which is ambiguous.

**Option B — decorator on the constant** (no grammar change):

```python
class HttpStatus(DEnum):
    @ordinal(200)
    OK = ()

    @ordinal(404)
    NOT_FOUND = ()
```

Decorators on assignments are not currently valid Python syntax. This would require a grammar change but a clean one — `@decorator` before a name assignment is unambiguous.

**Option C — inner class only, no shorthand** (no grammar change):

```python
class HttpStatus(DEnum):
    class OK(HttpStatus):
        ordinal = 200

    class NOT_FOUND(HttpStatus):
        ordinal = 404
```

This is verbose for simple cases but requires no grammar changes and is already valid Python. It is the approach used in the `jnum` reference implementation. The Steering Council may prefer this initially, with shorthand syntax added in a later PEP if demand warrants.

**Recommendation**: Begin with Option C. It requires no grammar changes, is already demonstrably viable, and keeps the PEP focused. Syntactic sugar can be added incrementally.

---

### New API on `DEnum` and `MDEnum`

These methods extend the existing `enum.Enum` API:

| Method / Property | Description |
|---|---|
| `.name` | Declared constant name (same as `Enum.name`) |
| `.ordinal` | Integer ordinal — auto-assigned or explicit (replaces `Enum.value` for identity) |
| `MyEnum.values()` | All constants in ordinal order (Java: `MyEnum.values()`) |
| `MyEnum.value_of(name)` | Look up by name; raises `KeyError` (Java: `MyEnum.valueOf()`) |
| `MyEnum.from_ordinal(n)` | Look up by ordinal value; raises `KeyError` |
| `MyEnum.override(name)` | Decorator: post-hoc per-constant method binding |
| `MyEnum[name]` | Subscript lookup — equivalent to `value_of` |

**Relationship to `Enum.value`**: `DEnum` and `MDEnum` deliberately do not use `value`. The `value` field in `enum.Enum` conflates two concerns: identity (what distinguishes constants) and payload (constructor arguments). `DEnum` separates these cleanly — `ordinal` handles identity, `__init__` parameters handle payload, and both are explicit.

---

### Interaction with existing `enum` features

| Feature | Status |
|---|---|
| `enum.auto()` | Supported — used in place of explicit ordinals |
| `enum.unique` | Supported — validated against ordinals |
| `enum.IntEnum`, `enum.StrEnum` | Unchanged — separate hierarchy |
| `@enum.member`, `@enum.nonmember` | Respected |
| Pickling | Supported — constants are singletons, pickle by name |
| `__slots__` | `MDEnum` fields require careful interaction; recommendation is to disallow `__slots__` on `MDEnum` subclasses or to auto-generate them from `__init__` annotations |
| `dataclasses.dataclass` | Out of scope for this PEP; future PEP could address `@dataclass`-style field declarations on enums |
| `abc.abstractmethod` | Supported — methods decorated with `@abstractmethod` on the enum class should enforce that all inner constant bodies provide an implementation (interpreter enforcement, not just runtime `NotImplementedError`) |
| Type checkers (`mypy`, `pyright`) | Requires typeshed stubs and potentially new type system constructs; see *Open Issues* |

---

## Rationale

### Why not extend `enum.Enum` directly?

Extending `Enum` itself would be a breaking change. Existing code that subclasses `Enum` with tuple values would collide with the new inner-class constant syntax. New base classes (`DEnum`, `MDEnum`) are strictly additive.

### Why `ordinal` instead of `value`?

`enum.Enum.value` is overloaded — it serves as both the constant's distinguishing payload and its identity. In `DEnum`, constants can have rich constructor arguments (mass, radius, firmware version) that are fields, not identifiers. `ordinal` is a clean, separate integer identity that is always auto-assigned and unambiguous. This also makes the Java parallel explicit, which helps developers familiar with that model.

### Why is `MDEnum` separate from `DEnum`?

Immutability is the safer default and should be the first choice. `MDEnum` has genuine use cases (device state machines, connection registries, session pools) but also genuine hazards (thread safety, unexpected aliasing). Keeping `MDEnum` as a distinct opt-in class makes the programmer's intent explicit and allows documentation, linters, and type checkers to treat the two differently.

### Why inner class syntax for constants with overrides?

Several alternatives were considered:

**Lambda values**: `PLUS = lambda self, x, y: x + y` — only works for single-expression methods and cannot define multiple overrides.

**Dictionary of methods**: `PLUS = {"apply": lambda x, y: x + y}` — arbitrary and unhelpful for IDE support.

**Decorator-per-constant**: `@constant('PLUS') def apply(...)` — repeated decorator stacking for each method of each constant is noisy and doesn't co-locate the constant's full definition.

**Inner class using the enum as base** is the right answer because: it is already valid Python syntax (with a metaclass), it co-locates all of a constant's overrides in one block, it reads naturally ("PLUS *is a kind of* Operation"), it gives the constant a proper name in stack traces and debugging, and it scales gracefully from one override to many.

### Why finality?

Java's enum finality exists for the same reason as sealing in Kotlin and Swift: a discriminated type with a closed set of variants is far more useful than one that can be extended arbitrarily. Exhaustiveness checking (by type checkers, `match`/`case`, and linters) requires a closed set. Allowing `class MySubEnum(MyEnum)` to add new constants would break all downstream exhaustiveness guarantees.

---

---

## Relationship to `IntEnum`, `StrEnum`, and `FlagEnum`

`DEnum` and `MDEnum` are **not extensions of**, **not compatible with**, and **not replacements for** `IntEnum`, `StrEnum`, or `FlagEnum`. They exist in parallel and serve fundamentally different purposes.

### Different problems, different tools

The existing coercion enums solve an **interoperability problem**: making enum constants usable wherever a primitive type is expected, without an explicit conversion.

```python
class Color(IntEnum):
    RED   = 1
    GREEN = 2
    BLUE  = 3

# Works because Color.RED degrades to the integer 1
flags = Color.RED | Color.BLUE   # bitwise OR — works because it's an int
json.dumps({"color": Color.RED}) # serialises as 1 — works because it's an int
```

`DEnum` and `MDEnum` solve a **design problem**: keeping behaviour co-located with the constants that vary it, eliminating scattered `if`/`elif` dispatch chains.

These are orthogonal concerns. An enum that is both a rich behaviour carrier *and* transparently interchangeable with integers is pulling in two directions at once. The behaviour-first design of `DEnum` says "callers should invoke methods on me"; the coercion design of `IntEnum` says "callers can treat me as a raw integer." Combining them produces contradictory guidance about how the enum should be used.

### Mixing is explicitly not supported

Combining `DEnum` or `MDEnum` with `IntEnum`, `StrEnum`, or `FlagEnum` raises `TypeError` at class definition time:

```python
class Status(DEnum, IntEnum):   # TypeError
    ...

class Flags(MDEnum, FlagEnum):  # TypeError
    ...
```

This is intentional, not an implementation oversight. The error message directs the developer to choose the right tool for the problem at hand.

### Existing enums are completely unchanged

`IntEnum`, `StrEnum`, and `FlagEnum` are not deprecated, not modified, and not affected by this PEP in any way. Code using them continues to work exactly as before. The choice between the two families is a design decision:

| You need... | Use |
|---|---|
| Constants interoperable with `int` | `IntEnum` |
| Constants interoperable with `str` | `StrEnum` |
| Combinable bit-flag constants | `FlagEnum` |
| Constants with per-constant behaviour | `DEnum` |
| Constants with per-constant behaviour and mutable state | `MDEnum` |
| Simple named constants with no special semantics | `Enum` |

These categories rarely overlap in well-designed code. If you find yourself wanting both `IntEnum` and `DEnum` semantics, the usual answer is that the enum should be a `DEnum` with an explicit `.to_int()` method — making the conversion intentional rather than implicit.

```python
# Instead of class Status(DEnum, IntEnum) — which is rejected:
class Status(DEnum):
    class OK(Status):
        args = (200,)
        def is_success(self): return True

    class NOT_FOUND(Status):
        args = (404,)
        def is_success(self): return False

    def __init__(self, code: int):
        self.code = code

    def to_int(self) -> int:
        return self.code   # explicit, intentional conversion

    def is_success(self) -> bool:
        raise NotImplementedError
```

Explicit conversion is preferable to implicit coercion precisely because it makes the intent visible at every call site, which is consistent with the broader philosophy of `DEnum`: callers should interact with the enum through its methods, not around them.

## Backwards Compatibility

This PEP is fully backwards compatible. No existing code is changed. `enum.Enum`, `enum.IntEnum`, `enum.StrEnum`, and all other existing enum classes are unmodified. `DEnum` and `MDEnum` are new classes in the `enum` module.

The only potential compatibility concern is if existing code uses `from enum import *` — the two new names would be added to `enum.__all__`. This is standard practice for new additions to the `enum` module and is not considered a breaking change.

### Composition through containment is supported and encouraged

While mixing `DEnum` with the coercion enums via inheritance is rejected, **using `IntEnum`, `StrEnum`, or `FlagEnum` values as fields inside a `DEnum` or `MDEnum` is natural and fully supported**. The two families compose cleanly through containment.

This pattern is useful when a `DEnum` constant needs to carry a field whose valid values are themselves a closed, typed set:

```python
from enum import IntFlag

class Permission(IntFlag):
    NONE    = 0x00
    READ    = 0x01
    WRITE   = 0x02
    EXECUTE = 0x04

class DeviceMode(DEnum):

    class LOCKED(DeviceMode):
        args = (Permission.NONE,)
        def request_access(self, user): raise PermissionError("device is locked")

    class READONLY(DeviceMode):
        args = (Permission.READ,)
        def request_access(self, user): return authenticate(user, Permission.READ)

    class OPERATIONAL(DeviceMode):
        args = (Permission.READ | Permission.WRITE,)
        def request_access(self, user): return authenticate(user, self.permissions)

    class MAINTENANCE(DeviceMode):
        args = (Permission.READ | Permission.WRITE | Permission.EXECUTE,)
        def request_access(self, user): return authenticate(user, Permission.EXECUTE)

    def __init__(self, permissions: Permission):
        self.permissions = permissions   # IntFlag field — typed, constrained

    def request_access(self, user): raise NotImplementedError

    def has_permission(self, perm: Permission) -> bool:
        return bool(self.permissions & perm)   # IntFlag bitwise ops work normally
```

```python
DeviceMode.READONLY.has_permission(Permission.READ)    # True
DeviceMode.READONLY.has_permission(Permission.WRITE)   # False
DeviceMode.READONLY.permissions                        # Permission.READ (typed)
```

Similarly, a `MDEnum` can hold `StrEnum` or `IntEnum` values as mutable fields, providing a constrained vocabulary for live state:

```python
class ConnectionQuality(StrEnum):
    EXCELLENT = "excellent"
    GOOD      = "good"
    POOR      = "poor"
    NONE      = "none"

class DeviceState(MDEnum):
    CONNECTED    = ()
    DISCONNECTED = ()

    def __init__(self):
        self.quality: ConnectionQuality = ConnectionQuality.NONE   # constrained mutable field

DeviceState.CONNECTED.quality = ConnectionQuality.GOOD   # OK
DeviceState.CONNECTED.quality = "invalid"                # runtime: works (StrEnum is a str)
                                                          # static:  type checker flags it
```

The separation of concerns is clean: `DEnum` and `MDEnum` own the **behaviour and identity**; `IntEnum`, `StrEnum`, and `FlagEnum` own the **type-safe value sets** that fields may be drawn from. Inheritance conflates these two responsibilities; containment composes them correctly.

---

## Security Implications

None. This PEP adds no security-relevant functionality.

---

## How to Teach This

The canonical teaching example — used in Java for twenty years — is `Operation`:

```python
class Operation(DEnum):
    class PLUS(Operation):
        def apply(self, x, y): return x + y

    class MINUS(Operation):
        def apply(self, x, y): return x - y

    def apply(self, x, y): raise NotImplementedError

result = Operation.PLUS.apply(6, 2)   # 8
```

The key insight to teach:

> If you find yourself writing `if x == MyEnum.SOMETHING`, ask whether that logic belongs on the enum. If different constants should behave differently, they should *implement* that behaviour, not be *inspected* for it.

This should be presented as a progression:

1. Enums as identity (current `enum.Enum`) — good for constants that don't vary in behaviour
2. Enums as data carriers (`__init__` with fields) — good for constants with associated values
3. Enums as dispatch (`DEnum`) — good for constants that differ in what they *do*
4. Enums as state (`MDEnum`) — good for constants that carry live-changing data

Python documentation should include a worked example of the order-status refactor (the "before/after" from the Motivation section) as the primary motivation for `DEnum`.

---

## Reference Implementation

A complete, working proof-of-concept is available at `jnum.py`. It implements all semantics described in this PEP using Python's existing metaclass machinery (`__prepare__`, `__init_subclass__`, `type.__new__`), with no CPython modifications required. The implementation has been tested on Python 3.7–3.13.

The production implementation in CPython would integrate these mechanisms into `Lib/enum.py` rather than using a separate metaclass, which would also allow tighter integration with `enum.auto()`, pickling, and the type annotation system.

### Version compatibility

This PEP targets **Python 3.13 or 3.14** for stdlib inclusion.

The implementation can be backported to **Python 3.11** as the minimum supported version. Python 3.10 and earlier are not supported by the backport. The rationale for each boundary:

**Why 3.13/3.14 as the stdlib target**

New stdlib additions are conventionally targeted at the current or next development release. At the time of writing (2026), 3.13 is the current stable release and 3.14 is in active development. The Steering Council will determine the appropriate target version during PEP review.

**Why 3.11 as the backport floor**

Three factors make 3.11 the natural minimum for the `jnum` backport package:

| Factor | Detail |
|---|---|
| `StrEnum` in stdlib | Added in 3.11 (PEP 663) — used in composition examples throughout this PEP |
| `enum` module overhaul | 3.11 brought significant improvements to `enum` internals and error messages |
| Security support | As of 2026, 3.11 is the oldest CPython version still receiving security fixes. Supporting anything older would mean targeting unsupported runtimes. |

**Why not 3.10 or earlier**

Python 3.10 introduced `match`/`case` (PEP 634), which this PEP references as a usage pattern. More importantly, the 3.11 `enum` overhaul changed internal details that the implementation interacts with. Supporting 3.10 would require maintaining separate code paths for old and new `enum` internals — complexity that is not justified given 3.10's approaching end-of-life (October 2026).

**Feature dependency summary**

The core implementation technique relies on three language features, all available since well before 3.11:

| Feature | Introduced | PEP | Required for |
|---|---|---|---|
| `__prepare__` on metaclass | 3.0 | PEP 3115 | Forward-reference proxy injection |
| `__init_subclass__` | 3.6 | PEP 487 | Capturing inner constant-body classes |
| Guaranteed `dict` ordering | 3.7 | PEP 468 | Preserving constant declaration order |

The 3.11 floor is a policy decision, not a technical one. The mechanics work on 3.7+. The backport chooses 3.11 because that is the oldest version worth supporting in 2026.

Key implementation notes from the proof-of-concept:

- **Forward reference resolution** is achieved by injecting a proxy class into the namespace via `__prepare__` under the enum's own name. The proxy's `__init_subclass__` captures inner classes as they are defined and stages them for the metaclass.
- **Mutable field tracking** for `MDEnum` uses a two-phase `__setattr__`: during `__init__`, field names are accumulated into a staging set; after construction, the set is frozen into a `_mutable_fields_` frozenset that serves as the permanent allowlist.
- **Anonymous subclass creation** for constants with overrides is performed via `type.__new__` directly, bypassing the enum metaclass's constant-collection logic, to avoid recursive processing.

---

## Open Issues

### 1. Type checker support

`mypy` and `pyright` would need updates to understand that:

- `Operation.PLUS` is both an instance of `Operation` and has a distinct implementation of `apply()`
- Iteration over `DEnum` yields instances of the enum type
- `from_ordinal()` returns the enum type (not `object`)
- `MDEnum` fields are mutable (overriding the usual assumption that enum attributes are immutable)

This likely requires new `typing` constructs or Protocol extensions. Coordination with the typing working group is needed before this PEP can be finalised.

### 2. Exhaustiveness checking

`match`/`case` with `DEnum` should ideally support exhaustiveness warnings when not all constants are covered, as with `Literal` types. This requires either:
- A new `@final_enum` or `@sealed` type annotation
- Native support in the `match` statement for closed enum types
- Cooperation with type checkers via `__final__` or similar

This is a separate concern and could be deferred to a follow-up PEP.

### 3. `abstractmethod` enforcement

The current proposal uses `raise NotImplementedError` as a convention for abstract methods on the base enum. Proper `@abstractmethod` enforcement — where the interpreter verifies at class construction time that all inner constant bodies implement all abstract methods — would require deeper integration with `abc.ABCMeta`. The interaction between `ABCMeta` and the enum metaclass needs careful design.

### 4. `__slots__` interaction with `MDEnum`

`MDEnum` instances need to store mutable fields on the instance `__dict__`. This conflicts with `__slots__`, which is sometimes used on `Enum` subclasses for memory efficiency. Options:
- Disallow `__slots__` on `MDEnum` subclasses (simple, slightly limiting)
- Auto-generate `__slots__` from `__init__` parameter annotations (elegant, requires annotation-based field declaration)
- Document the incompatibility and leave it to users

### 5. `args` as a reserved name

Inside inner constant-body classes, `args` is used as a reserved attribute to specify constructor arguments. This is a minor but real naming conflict for enums that happen to have a field or method named `args`. The PEP should specify that `args` inside a constant body class is consumed by the enum machinery and cannot be used as a user field name.

Alternative: use a dunder `__args__` to avoid the collision entirely.

### 6. Serialisation and `__reduce__`

`DEnum` constants should pickle by name (the same as `Enum`), since they are singletons. `MDEnum` constants carry mutable state that is not part of their identity — the question of whether mutable field values should be pickled alongside the constant name is unresolved. Recommendation: document that `MDEnum` pickles by name only (restoring to the default field values), with users responsible for serialising live state separately if needed.

---

## Rejected Alternatives

### "Just use a class hierarchy with `@classmethod`s"

A base class with subclasses achieves per-subclass dispatch but loses enum semantics entirely: no `values()`, no ordinals, no iteration, no singleton guarantee, no `match`/`case` integration, no finality. Enums and class hierarchies solve fundamentally different problems.

### "Use a dispatch dictionary"

```python
_apply = {Operation.PLUS: lambda x, y: x + y, Operation.MINUS: lambda x, y: x - y}

def apply(op, x, y):
    return _apply[op](x, y)
```

This is the most common current workaround. Problems: the dictionary lives outside the enum, is not enforced to be complete, duplicates the constant list, does not support inheritance, and still scatters logic across files when there are multiple such dictionaries for different aspects of the enum.

### "Add `functools.singledispatch` integration"

`singledispatch` dispatches on type, not enum value. Since all constants of an enum share the same type, `singledispatch` cannot distinguish `Operation.PLUS` from `Operation.MINUS`.

### "Extend `enum.Enum` with a `dispatch` decorator"

```python
class Operation(enum.Enum):
    PLUS  = 1
    MINUS = 2

    @Operation.PLUS.implements
    def apply(self, x, y): return x + y
```

This syntax is explored in several third-party libraries. Problems: `Operation.PLUS` doesn't exist yet when the decorator is being applied (same forward reference problem this PEP solves), the syntax is unusual, and it doesn't co-locate all of a constant's methods.

### "Use `match`/`case` everywhere instead of per-constant dispatch"

`match`/`case` is an improvement over `if`/`elif` but does not eliminate the scattered-logic problem — it just makes each branch cleaner. Logic still lives in callers. Adding a new constant still requires a codebase search. `match` exhaustiveness checking helps catch omissions but does not reorganise where logic lives.

---

## Acknowledgements

This proposal draws heavily on Java's enum design (JLS Chapter 8.9), Josh Bloch's *Effective Java* (Items 34 and 36), and the Python `enum` module's existing design as specified in PEP 435. The proof-of-concept implementation (`jnum.py`) informed the specification, particularly the forward-reference resolution mechanism and the two-phase `MDEnum` field tracking.

---

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal licence, whichever is more permissive.
