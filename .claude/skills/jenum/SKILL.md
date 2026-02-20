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
