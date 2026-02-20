# jenum — Dispatch Enums for Python

`jenum` brings **Dispatch Enums** to Python. `DEnum` (Dispatch Enum) treats each constant as a **singleton instance of the enum class** — giving you per-constant fields and per-constant method dispatch, so behaviour lives with the enum rather than scattered across caller `if/elif` chains. `MDEnum` (Mutable Dispatch Enum) is identical but allows fields declared in `__init__` to be updated after construction.

```python
from jenum import DEnum, body

class Planet(DEnum):
    MERCURY = (3.303e+23, 2.4397e6)
    VENUS   = (4.869e+24, 6.0518e6)
    EARTH   = (5.976e+24, 6.37814e6)
    MARS    = (6.421e+23, 3.3972e6)

    def __init__(self, mass: float, radius: float):
        self.mass   = mass
        self.radius = radius

    G = 6.67300E-11

    def surface_gravity(self) -> float:
        return self.G * self.mass / (self.radius ** 2)

    def surface_weight(self, other_mass: float) -> float:
        return other_mass * self.surface_gravity()

for p in Planet:
    print(f"Weight on {p.name:<8}: {p.surface_weight(75):.2f} N")
# Weight on MERCURY : 277.73 N
# Weight on VENUS   : 665.35 N
# Weight on EARTH   : 735.20 N
# Weight on MARS    : 278.45 N
```

---

## The Big Idea — Enums as Behaviour, Not Just Labels

Most Python code treats enums as glorified constants — named integers you can `if`/`elif` against. That works, but it creates a persistent problem: **the logic that depends on an enum value gets scattered across the codebase**, far from where the enum is defined, and every new constant means hunting down every decision point to add another branch.

`jenum` encourages a fundamentally different approach. Because every constant is a real object that can carry its own method implementations, **the code that varies by enum value lives with the enum itself**. Callers never need to ask "which value is this?" — they just call the method, and each constant does the right thing for itself.

### The before/after

Here's a realistic example. You have an order processing system with different order statuses. The **conventional approach** with plain enums:

```python
# Scattered if/elif blocks — the anti-pattern
class OrderStatus(enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    SHIPPED   = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

# In your email service:
def send_status_email(order):
    if order.status == OrderStatus.PENDING:
        subject = "Order received"
        template = "pending.html"
        send_to = [order.customer_email]
    elif order.status == OrderStatus.CONFIRMED:
        subject = "Order confirmed"
        template = "confirmed.html"
        send_to = [order.customer_email, order.warehouse_email]
    elif order.status == OrderStatus.SHIPPED:
        subject = f"Your order is on the way! Tracking: {order.tracking_id}"
        template = "shipped.html"
        send_to = [order.customer_email]
    elif order.status == OrderStatus.CANCELLED:
        subject = "Order cancelled"
        template = "cancelled.html"
        send_to = [order.customer_email, order.billing_email]
    # ...and so on, repeated in every service that cares about status

# In your inventory service:
def adjust_inventory(order):
    if order.status == OrderStatus.CONFIRMED:
        reserve_stock(order)
    elif order.status == OrderStatus.CANCELLED:
        release_stock(order)
    elif order.status == OrderStatus.DELIVERED:
        confirm_fulfillment(order)
    # ...another block, growing with every new status

# In your analytics service:
def is_billable(order):
    if order.status in (OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED):
        return True
    return False
```

Every time you add a new status, you must find and update every `if`/`elif` chain in every service. Miss one and you have a silent bug.

The **`jenum` approach** — behaviour lives with the enum:

```python
class OrderStatus(DEnum):

    class PENDING(OrderStatus):
        args = ()
        def email_subject(self, order) -> str:
            return "Order received"
        def email_template(self) -> str:
            return "pending.html"
        def email_recipients(self, order) -> list:
            return [order.customer_email]
        def adjust_inventory(self, order):
            pass  # nothing to do yet
        def is_billable(self) -> bool:
            return False

    class CONFIRMED(OrderStatus):
        args = ()
        def email_subject(self, order) -> str:
            return "Order confirmed"
        def email_template(self) -> str:
            return "confirmed.html"
        def email_recipients(self, order) -> list:
            return [order.customer_email, order.warehouse_email]
        def adjust_inventory(self, order):
            reserve_stock(order)
        def is_billable(self) -> bool:
            return True

    class SHIPPED(OrderStatus):
        args = ()
        def email_subject(self, order) -> str:
            return f"Your order is on the way! Tracking: {order.tracking_id}"
        def email_template(self) -> str:
            return "shipped.html"
        def email_recipients(self, order) -> list:
            return [order.customer_email]
        def adjust_inventory(self, order):
            pass  # already reserved
        def is_billable(self) -> bool:
            return True

    class CANCELLED(OrderStatus):
        args = ()
        def email_subject(self, order) -> str:
            return "Order cancelled"
        def email_template(self) -> str:
            return "cancelled.html"
        def email_recipients(self, order) -> list:
            return [order.customer_email, order.billing_email]
        def adjust_inventory(self, order):
            release_stock(order)
        def is_billable(self) -> bool:
            return False

    # Abstract interface — every status must implement these
    def email_subject(self, order) -> str:        raise NotImplementedError
    def email_template(self) -> str:              raise NotImplementedError
    def email_recipients(self, order) -> list:    raise NotImplementedError
    def adjust_inventory(self, order):            raise NotImplementedError
    def is_billable(self) -> bool:                raise NotImplementedError


# Your services become trivial — no branching, no hunting:
def send_status_email(order):
    send_email(
        to       = order.status.email_recipients(order),
        subject  = order.status.email_subject(order),
        template = order.status.email_template(),
    )

def adjust_inventory(order):
    order.status.adjust_inventory(order)

def is_billable(order) -> bool:
    return order.status.is_billable()
```

**Adding a new `REFUNDED` status** now means adding one new inner class to `OrderStatus`. Every service that calls `.email_subject()`, `.adjust_inventory()`, or `.is_billable()` automatically handles the new status — no search, no edits, no forgotten branches. If you forget to implement a method, Python raises `NotImplementedError` at runtime immediately, pointing straight at the gap.

### The principle in one sentence

> **If you find yourself writing `if x == MyEnum.FOO` or `match x: case MyEnum.FOO:`, ask whether that logic belongs on the enum itself.**

The answer is usually yes. The enum already knows what it is — it should also know what to do.

---

## Installation

Install from PyPI:

```bash
pip install jenum
```

Or copy `jenum.py` directly into your project (no dependencies):

```
your_project/
├── jenum.py
└── your_code.py
```

```python
from jenum import DEnum, body
```

Python 3.11+ is required.

---

## Table of Contents

- [The Big Idea — Enums as Behaviour, Not Just Labels](#the-big-idea--enums-as-behaviour-not-just-labels)
- [Core concepts](#core-concepts)
- [Declaration style 1 — Bare tuple](#declaration-style-1--bare-tuple)
- [Declaration style 2 — body()](#declaration-style-2--body)
- [Declaration style 3 — Inline anonymous subclass](#declaration-style-3--inline-anonymous-subclass)
- [Declaration style 4 — @override decorator](#declaration-style-4--override-decorator)
- [Mixing styles](#mixing-styles)
- [Constructor arguments](#constructor-arguments)
- [Custom ordinals](#custom-ordinals)
- [The full API reference](#the-full-api-reference)
- [Inheritance rules](#inheritance-rules)
- [Immutability](#immutability)
- [Comparison and sorting](#comparison-and-sorting)
- [Pattern matching (match/case)](#pattern-matching-matchcase)
- [When if/else is still fine](#when-ifelse-is-still-fine)
- [MDEnum — Mutable Dispatch Enum Fields](#mdenum--mutable-dispatch-enum-fields)
- [vs Python's built-in enum.Enum](#vs-pythons-built-in-enumenum)
- [vs Java enums](#vs-java-enums)
- [How it works internally](#how-it-works-internally)

---

## Core concepts

In `jenum`, every enum constant is a **singleton instance** of the enum class (or a private anonymous subclass of it). This means:

- The enum class defines shared fields, shared methods, and default implementations.
- Each constant carries its own field values, set via the constructor.
- Each constant can override any method with its own implementation.
- Callers interact with the enum through its methods — not by inspecting which constant it is.
- Constants are immutable after construction.
- Iteration is always in ordinal order.

---

## Declaration style 1 — Bare tuple

The simplest style. A constant declared as a tuple passes its elements as constructor arguments. An empty tuple `()` declares a no-arg constant.

```python
class Direction(DEnum):
    NORTH = ()
    SOUTH = ()
    EAST  = ()
    WEST  = ()

    def opposite(self) -> "Direction":
        # The logic lives here, not scattered across callers
        opposites = {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST:  Direction.WEST,
            Direction.WEST:  Direction.EAST,
        }
        return opposites[self]

    def is_vertical(self) -> bool:
        return self in (Direction.NORTH, Direction.SOUTH)
```

```python
Direction.NORTH.opposite()     # Direction.SOUTH
Direction.EAST.is_vertical()   # False
```

Callers never write `if direction == Direction.NORTH` — they ask `direction.is_vertical()` or `direction.opposite()` and the enum answers.

With constructor args:

```python
class Planet(DEnum):
    MERCURY = (3.303e+23, 2.4397e6)
    EARTH   = (5.976e+24, 6.37814e6)

    def __init__(self, mass: float, radius: float):
        self.mass   = mass
        self.radius = radius
```

Ordinals are auto-assigned starting at 0, in declaration order:

```python
Direction.NORTH.ordinal  # 0
Direction.SOUTH.ordinal  # 1
Direction.EAST.ordinal   # 2
Direction.WEST.ordinal   # 3
```

---

## Declaration style 2 — body()

Use `body()` when you need an explicit ordinal but don't need per-constant method overrides.

```python
class HttpStatus(DEnum):
    OK             = body(ordinal=200)
    CREATED        = body(ordinal=201)
    NO_CONTENT     = body(ordinal=204)
    BAD_REQUEST    = body(ordinal=400)
    UNAUTHORIZED   = body(ordinal=401)
    FORBIDDEN      = body(ordinal=403)
    NOT_FOUND      = body(ordinal=404)
    INTERNAL_ERROR = body(ordinal=500)

    def is_success(self) -> bool:
        return 200 <= self.ordinal < 300

    def is_client_error(self) -> bool:
        return 400 <= self.ordinal < 500

    def is_server_error(self) -> bool:
        return self.ordinal >= 500

    def should_retry(self) -> bool:
        # Logic lives here — callers never check specific codes
        return self in (HttpStatus.INTERNAL_ERROR,)
```

```python
# Callers ask, not inspect:
if response.status.is_success():
    process(response)
elif response.status.should_retry():
    retry(request)
else:
    raise ApiError(response.status)
```

`body()` also accepts constructor arguments:

```python
class Coin(DEnum):
    PENNY   = body("penny",   1,  ordinal=1)
    NICKEL  = body("nickel",  5,  ordinal=5)
    DIME    = body("dime",    10, ordinal=10)
    QUARTER = body("quarter", 25, ordinal=25)

    def __init__(self, label: str, cents: int):
        self.label = label
        self.cents = cents

    def make_change(self, amount_cents: int) -> int:
        """How many of this coin fit in the given amount?"""
        return amount_cents // self.cents
```

---

## Declaration style 3 — Inline anonymous subclass

This is `jenum`'s most powerful feature and the closest equivalent to Java's anonymous per-constant class bodies. Write `class CONSTNAME(EnumClass):` directly inside the enum body to give each constant its own method implementations.

This is where the "no if/else" principle pays off most visibly. The branching logic that would otherwise live in callers is instead encoded directly into the constants.

```python
class Operation(DEnum):

    class PLUS(Operation):
        args = ()
        def apply(self, x: float, y: float) -> float: return x + y
        def symbol(self) -> str: return "+"
        def is_invertible(self) -> bool: return True
        def inverse(self) -> "Operation": return Operation.MINUS

    class MINUS(Operation):
        args = ()
        def apply(self, x: float, y: float) -> float: return x - y
        def symbol(self) -> str: return "-"
        def is_invertible(self) -> bool: return True
        def inverse(self) -> "Operation": return Operation.PLUS

    class TIMES(Operation):
        args = ()
        def apply(self, x: float, y: float) -> float: return x * y
        def symbol(self) -> str: return "*"
        def is_invertible(self) -> bool: return True
        def inverse(self) -> "Operation": return Operation.DIVIDE

    class DIVIDE(Operation):
        args = ()
        def apply(self, x: float, y: float) -> float: return x / y
        def symbol(self) -> str: return "/"
        def is_invertible(self) -> bool: return True
        def inverse(self) -> "Operation": return Operation.TIMES

    class MODULO(Operation):
        args = ()
        def apply(self, x: float, y: float) -> float: return x % y
        def symbol(self) -> str: return "%"
        def is_invertible(self) -> bool: return False
        def inverse(self) -> "Operation": raise ValueError("MODULO has no inverse")

    # Default interface (effectively abstract)
    def apply(self, x: float, y: float) -> float:  raise NotImplementedError
    def symbol(self) -> str:                        raise NotImplementedError
    def is_invertible(self) -> bool:                raise NotImplementedError
    def inverse(self) -> "Operation":               raise NotImplementedError
```

```python
# A calculator that never asks which operation it has:
def calculate(x, op, y):
    return op.apply(x, y)

def invert_expression(x, op, y):
    if not op.is_invertible():
        raise ValueError(f"Cannot invert {op.symbol()} expression")
    return op.inverse().apply(x, y)  # no switch, no if/elif

for op in Operation:
    print(f"6 {op.symbol()} 2 = {op.apply(6, 2)}")
```

### The `args` and `ordinal` class attributes

Inside the inner class body, two special class attributes control the constant's construction:

| Attribute | Type | Default | Purpose |
|---|---|---|---|
| `args` | `tuple` | `()` | Arguments passed to the enum's `__init__` |
| `ordinal` | `int` | auto | Explicit ordinal value for this constant |

```python
class Priority(DEnum):

    class CRITICAL(Priority):
        args    = ("red", 3)
        ordinal = 100
        def escalate(self, ticket): page_on_call(ticket)
        def sla_hours(self) -> int: return 1

    class HIGH(Priority):
        args    = ("orange", 2)
        ordinal = 50
        def escalate(self, ticket): send_slack_alert(ticket)
        def sla_hours(self) -> int: return 4

    class LOW(Priority):
        args    = ("green", 1)
        ordinal = 10
        def escalate(self, ticket): create_jira_ticket(ticket)
        def sla_hours(self) -> int: return 72

    def __init__(self, color: str, level: int):
        self.color = color
        self.level = level

    def escalate(self, ticket): raise NotImplementedError
    def sla_hours(self) -> int: raise NotImplementedError


# No if/else anywhere:
def handle_ticket(ticket):
    ticket.priority.escalate(ticket)
    schedule_follow_up(ticket, hours=ticket.priority.sla_hours())
```

### Forward reference — how it works

You might wonder: how can `class PLUS(Operation):` work when `Operation` isn't defined yet? `jenum` solves this with a proxy class injected into the class namespace by `__prepare__`. When the inner class body executes, `Operation` silently resolves to that proxy. The proxy captures the inner class and hands it to the metaclass. By the time you use `Operation.PLUS`, everything is real and correct. You never see or interact with the proxy — it is an internal implementation detail.

---

## Declaration style 4 — @override decorator

When a method body is too long to fit cleanly inside an inner class, or you prefer to define overrides after the class, use the `@override` decorator. The semantics are identical to the inline subclass approach.

```python
class PaymentMethod(DEnum):
    CREDIT_CARD  = body()
    BANK_TRANSFER = body()
    CRYPTO       = body()
    GIFT_CARD    = body()

    def process(self, amount: float, details: dict) -> str:
        raise NotImplementedError

    def fee_percent(self) -> float:
        return 0.0

    def instant(self) -> bool:
        return False


@PaymentMethod.override('CREDIT_CARD')
def process(self, amount, details):
    return charge_stripe(details['token'], amount)

@PaymentMethod.override('CREDIT_CARD')
def fee_percent(self): return 2.9

@PaymentMethod.override('CREDIT_CARD')
def instant(self): return True


@PaymentMethod.override('BANK_TRANSFER')
def process(self, amount, details):
    return initiate_ach(details['routing'], details['account'], amount)

@PaymentMethod.override('BANK_TRANSFER')
def fee_percent(self): return 0.5


@PaymentMethod.override('CRYPTO')
def process(self, amount, details):
    return broadcast_transaction(details['wallet'], amount)

@PaymentMethod.override('CRYPTO')
def instant(self): return True


@PaymentMethod.override('GIFT_CARD')
def process(self, amount, details):
    return redeem_gift_card(details['code'], amount)


# Caller never inspects the payment method — just calls process():
def checkout(cart, payment_method, payment_details):
    total = cart.total * (1 + payment_method.fee_percent() / 100)
    confirmation = payment_method.process(total, payment_details)
    if payment_method.instant():
        ship_immediately(cart)
    return confirmation
```

---

## Mixing styles

All four declaration styles can be freely mixed in a single enum. This lets you use the simplest style for simple constants and the more expressive styles only where you need them.

```python
class NotificationType(DEnum):

    # Simple constants that share the same default behaviour
    INFO    = ("ℹ️",)
    SUCCESS = ("✅",)
    WARNING = ("⚠️",)

    # This one needs its own send logic
    class URGENT(NotificationType):
        args = ("🚨",)
        def send(self, user, message):
            send_sms(user.phone, message)
            send_push(user.device_token, message)
            send_email(user.email, message)  # all three channels

    def __init__(self, icon: str):
        self.icon = icon

    def send(self, user, message):
        # Default: just send a push notification
        send_push(user.device_token, f"{self.icon} {message}")

# Later, add special handling for WARNING without touching callers:
@NotificationType.override('WARNING')
def send(self, user, message):
    send_push(user.device_token, f"{self.icon} {message}")
    log_warning(user, message)  # also log it
```

---

## Constructor arguments

Define `__init__` on your enum class to receive per-constant field values. It works exactly like a regular `__init__`, called with whatever args the constant declares.

```python
class Planet(DEnum):
    MERCURY = (3.303e+23, 2.4397e6)
    VENUS   = (4.869e+24, 6.0518e6)
    EARTH   = (5.976e+24, 6.37814e6)

    def __init__(self, mass: float, radius: float):
        self.mass   = mass
        self.radius = radius

Planet.EARTH.mass    # 5.976e+24
Planet.EARTH.radius  # 6.37814e6
```

Fields set in `__init__` are **immutable** — attempting to reassign them after construction raises `AttributeError`.

For inline subclass constants, pass constructor args via the `args` class attribute:

```python
class Planet(DEnum):
    class EARTH(Planet):
        args = (5.976e+24, 6.37814e6)
        def has_known_life(self) -> bool: return True

    def __init__(self, mass: float, radius: float):
        self.mass   = mass
        self.radius = radius

    def has_known_life(self) -> bool:
        return False
```

---

## Custom ordinals

By default, ordinals are assigned sequentially starting at 0. You can override the ordinal for any constant — useful for mapping to external integer codes like HTTP status codes, Unix signals, or bit flags.

### Setting ordinals

**Via `body()`:**
```python
class Signal(DEnum):
    SIGINT  = body(ordinal=2)
    SIGKILL = body(ordinal=9)
    SIGTERM = body(ordinal=15)
    SIGUSR1 = body(ordinal=30)

    def is_catchable(self) -> bool:
        return self is not Signal.SIGKILL
```

**Via inline subclass:**
```python
class HttpStatus(DEnum):
    class OK(HttpStatus):
        ordinal = 200
        args    = ()
        def is_success(self): return True

    class NOT_FOUND(HttpStatus):
        ordinal = 404
        args    = ()
        def is_success(self): return False

    def is_success(self) -> bool: raise NotImplementedError
```

### Auto-fill skips reserved slots

If you mix explicit and auto-assigned ordinals, auto-assignment skips any values already claimed:

```python
class Example(DEnum):
    A = ()              # auto → 0
    B = body(ordinal=5) # explicit 5
    C = ()              # auto → 6  (skips 5)
    D = body(ordinal=10)# explicit 10
    E = ()              # auto → 11

# ordinals: A=0, B=5, C=6, D=10, E=11
```

### Ordinal validation

Duplicate ordinals raise `ValueError` at class definition time:

```python
class Bad(DEnum):
    X = body(ordinal=1)
    Y = body(ordinal=1)   # ValueError: Bad: duplicate explicit ordinal 1
```

---

## The full API reference

### Instance properties

| Property | Type | Description |
|---|---|---|
| `.name` | `str` | The declared name of the constant (`"EARTH"`, `"PLUS"`, etc.) |
| `.ordinal` | `int` | The ordinal value (auto or explicit) |

### Class methods

| Method | Signature | Description |
|---|---|---|
| `values()` | `() → list[T]` | All constants in ordinal order |
| `value_of(name)` | `(str) → T` | Look up by name; raises `KeyError` if not found |
| `from_ordinal(n)` | `(int) → T` | Look up by ordinal; raises `KeyError` if not found |
| `override(name)` | `(str) → decorator` | Bind a post-hoc method override to a specific constant |

### Subscript / containment

```python
Planet['EARTH']          # same as Planet.value_of('EARTH')
Planet.EARTH in Planet   # True
```

### Iteration

```python
for p in Planet:         # iterates in ordinal order
    print(p.name, p.ordinal)

list(Planet)             # [Planet.MERCURY, Planet.VENUS, Planet.EARTH, Planet.MARS]
len(Planet)              # 4
```

### String representations

```python
str(Planet.EARTH)        # "EARTH"
repr(Planet.EARTH)       # "Planet.EARTH"
```

### Equality and hashing

Constants use **identity equality** — each is a singleton, so `is` and `==` behave identically:

```python
Planet.EARTH == Planet.EARTH   # True
Planet.EARTH is Planet.EARTH   # True  (same object)
Planet.EARTH == Planet.MARS    # False

# Safe to use as dict keys or in sets
status_map = {HttpStatus.OK: "success", HttpStatus.NOT_FOUND: "missing"}
seen = {Planet.EARTH, Planet.MARS}
```

---

## Inheritance rules

### Enum classes with constants are final

Once an enum class has constants defined, it **cannot be subclassed externally**. This mirrors Java's `final` semantics and prevents the confusing state that arises when child classes try to extend a sealed type.

```python
class Planet(DEnum):
    EARTH = (5.976e+24, 6.37814e6)
    ...

class GasGiant(Planet):   # TypeError!
    JUPITER = (...)
```

```
TypeError: Cannot subclass enum 'Planet': enum classes are final once constants
are defined. To add per-constant overrides, write 'class MYCONST(Planet):' inside
the class body.
```

### Abstract base enums are allowed

An enum class with **no constants** acts as a shared abstract base. It can be freely subclassed, which is useful for defining a shared interface that multiple enums implement:

```python
class Printable(DEnum):
    """Abstract base — defines the interface, no constants."""
    def to_display_string(self) -> str:
        raise NotImplementedError

    def to_log_string(self) -> str:
        raise NotImplementedError

class Color(Printable):
    RED   = ()
    GREEN = ()
    BLUE  = ()
    def to_display_string(self): return f"<span class='{self.name.lower()}'>{self.name}</span>"
    def to_log_string(self):     return f"color:{self.name.lower()}"

class Severity(Printable):
    LOW  = ()
    HIGH = ()
    def to_display_string(self): return f"[{self.name}]"
    def to_log_string(self):     return f"severity:{self.name.lower()}"
```

---

## Immutability

Constants are frozen after `__init__` completes. Any attempt to set an attribute raises `AttributeError`:

```python
Planet.EARTH.mass = 0
# AttributeError: Planet.EARTH is immutable: cannot set 'mass' after construction
```

This enforces the singleton contract — a constant's identity, fields, and behaviour are fixed forever at class definition time.

---

## Comparison and sorting

Constants compare by ordinal value, which makes priority and ordering enums natural:

```python
class Priority(DEnum):
    LOW    = body(ordinal=10)
    MEDIUM = body(ordinal=20)
    HIGH   = body(ordinal=30)

def escalation_needed(ticket) -> bool:
    return ticket.priority >= Priority.HIGH

# Sort a list of tickets by priority, highest first:
sorted(tickets, key=lambda t: t.priority, reverse=True)
```

All six comparison operators (`<`, `<=`, `==`, `!=`, `>=`, `>`) are supported. Equality uses identity (`is`), ordering uses ordinal values.

```python
min(Priority)   # Priority.LOW
max(Priority)   # Priority.HIGH
sorted(Priority) # [LOW, MEDIUM, HIGH]
```

---

## Pattern matching (match/case)

`jenum` constants work natively with Python 3.10+ `match`/`case`. This is the one place where case-by-case branching is appropriate — when you genuinely need to produce a value that's structurally different per constant and there's no sensible way to encode it as a method.

```python
def route_request(method: HttpMethod, path: str) -> Response:
    match method:
        case HttpMethod.GET:
            return handle_get(path)
        case HttpMethod.POST:
            return handle_post(path, request.body)
        case HttpMethod.DELETE:
            return handle_delete(path)
        case _:
            return Response(status=HttpStatus.METHOD_NOT_ALLOWED)
```

That said, even here you should ask: *could this `match` be replaced by a method on `HttpMethod`?* If `handle_get`, `handle_post`, etc. are part of a consistent interface, the answer is probably yes.

---

## When if/else is still fine

The "no if/else" principle is a guide, not a law. There are cases where a simple branch is the right call:

**Guard conditions** — checking preconditions before doing work:
```python
if order.status == OrderStatus.CANCELLED:
    return  # nothing to do
process(order)
```

**Comparisons** — ordinal comparisons are naturally expressed as operators:
```python
if ticket.priority >= Priority.HIGH:
    send_alert()
```

**External protocol mapping** — when you receive an integer or string from an external system and need to convert it to an enum before doing anything interesting:
```python
status = HttpStatus.from_ordinal(response.status_code)
# After this line, you never branch on status again — you call methods on it
```

**Truly asymmetric logic** — when only one or two constants need special treatment and the rest share a clean default:
```python
# Fine — the asymmetry is obvious and contained
if coin is Coin.QUARTER:
    print("That's a lot of coins")
else:
    print(f"You have {count} {coin.label}s")
```

The smell to watch for is the **sprawling chain** — three or more branches, spread across multiple files, that all ask "which enum value is this?" That's the signal that the branching logic belongs on the enum.

---

## vs Python's built-in `enum.Enum`

| Feature | `enum.Enum` | `jenum.DEnum` |
|---|---|---|
| Basic named constants | ✅ | ✅ |
| Per-constant field values | ✅ (via `value`) | ✅ (via `__init__`) |
| Multiple fields per constant | ❌ awkward | ✅ natural |
| Shared methods on the enum | ✅ | ✅ |
| Per-constant method override | ❌ not supported | ✅ inline or decorator |
| Custom ordinals | ❌ | ✅ |
| Ordinal-ordered iteration | ❌ (declaration order) | ✅ |
| `from_ordinal()` lookup | ❌ | ✅ |
| Finality guard | ❌ | ✅ |
| Constants are true singletons | ✅ | ✅ |
| `match`/`case` support | ✅ | ✅ |
| Encourages behaviour-on-enum | ❌ | ✅ |
| Optional mutable fields | ❌ | ✅ (`MDEnum`) |

The critical gap is per-constant method overrides. Without them, `enum.Enum` forces you to put branching logic in callers. With `jenum`, the logic stays with the enum.

---

## vs Java enums

| Feature | Java | `jenum.DEnum` |
|---|---|---|
| Constants as singleton instances | ✅ | ✅ |
| Per-constant constructor args | ✅ | ✅ |
| `name()` | ✅ | ✅ (`.name` property) |
| `ordinal()` | ✅ auto only | ✅ auto or explicit |
| `values()` | ✅ | ✅ |
| `valueOf(name)` | ✅ | ✅ `value_of(name)` |
| `Enum.valueOf(Class, name)` | ✅ | use `MyEnum['NAME']` |
| Per-constant method override | ✅ anonymous subclass in body | ✅ inline subclass or `@override` |
| Enum is implicitly `final` | ✅ | ✅ |
| Abstract base enum | ✅ `abstract` methods | ✅ no-constant base class |
| `switch` / pattern match | ✅ | ✅ `match`/`case` |
| `compareTo()` (ordinal order) | ✅ | ✅ `<`, `>`, etc. |
| `EnumSet` / `EnumMap` | ✅ | use `set()` / `dict()` |
| Custom ordinal values | ❌ | ✅ |
| Reverse lookup by ordinal | ❌ (manual) | ✅ `from_ordinal()` |
| Optional mutable fields | ❌ | ✅ (`MDEnum`) |

> `jenum` is the reference implementation for a proposed PEP to add `DEnum` and `MDEnum` to Python's standard `enum` module. See `PEP-DRAFT.md`.

---

## How it works internally

`jenum` is built on three Python metaclass mechanisms working in concert:

**`__prepare__`** runs before the class body executes. It injects a lightweight proxy class into the namespace under the enum's own name. This is what makes `class PLUS(Operation):` work inside the `Operation` body — `Operation` resolves to the proxy, not the not-yet-built real class.

**`_ForwardProxy.__init_subclass__`** fires the moment each inner class (`PLUS`, `MINUS`, etc.) finishes building. It stages the inner class in a module-level `_pending` dict keyed by the proxy's `id()`.

**`DEnumMeta.__new__`** runs after the full class body has executed. It retrieves the staged inner classes from `_pending`, extracts their `args`, `ordinal`, and method overrides, then builds proper anonymous subclasses of the real enum class — one per constant that has overrides. Each constant is then instantiated as a singleton and bound to the enum class as a class attribute.

The proxies are discarded after `__new__` finishes. From user code's perspective, `Operation.PLUS` is simply an instance of `Operation` (or a private subclass of it) with `name="PLUS"`, `ordinal=0`, and its own `apply()` method.

---

## Complete example — a payment processing pipeline

This example demonstrates the full "behaviour-on-enum" pattern in a realistic setting. No caller ever inspects which payment method it has.

```python
from jenum import DEnum, body
from dataclasses import dataclass

@dataclass
class PaymentResult:
    success: bool
    transaction_id: str
    message: str


class PaymentMethod(DEnum):

    class CREDIT_CARD(PaymentMethod):
        args = ("Credit Card", "card")
        def process(self, amount, details) -> PaymentResult:
            # Stripe integration
            charge = stripe.charge(details['token'], int(amount * 100))
            return PaymentResult(True, charge.id, "Charged successfully")
        def fee(self, amount: float) -> float:
            return amount * 0.029 + 0.30
        def is_instant(self) -> bool:
            return True
        def requires_field(self) -> list[str]:
            return ["token"]

    class BANK_TRANSFER(PaymentMethod):
        args = ("Bank Transfer", "bank")
        def process(self, amount, details) -> PaymentResult:
            ref = ach.initiate(details['routing'], details['account'], amount)
            return PaymentResult(True, ref, "ACH transfer initiated (2-3 business days)")
        def fee(self, amount: float) -> float:
            return min(amount * 0.005, 5.00)
        def is_instant(self) -> bool:
            return False
        def requires_field(self) -> list[str]:
            return ["routing", "account"]

    class CRYPTO(PaymentMethod):
        args = ("Cryptocurrency", "crypto")
        def process(self, amount, details) -> PaymentResult:
            tx = blockchain.send(details['wallet'], amount)
            return PaymentResult(True, tx.hash, "Transaction broadcast")
        def fee(self, amount: float) -> float:
            return 0.001  # flat network fee
        def is_instant(self) -> bool:
            return True
        def requires_field(self) -> list[str]:
            return ["wallet"]

    class GIFT_CARD(PaymentMethod):
        args = ("Gift Card", "gift")
        def process(self, amount, details) -> PaymentResult:
            balance = gift_cards.redeem(details['code'], amount)
            return PaymentResult(True, details['code'], f"Redeemed. Remaining: ${balance:.2f}")
        def fee(self, amount: float) -> float:
            return 0.0
        def is_instant(self) -> bool:
            return True
        def requires_field(self) -> list[str]:
            return ["code"]

    def __init__(self, display_name: str, icon: str):
        self.display_name = display_name
        self.icon         = icon

    # Abstract interface
    def process(self, amount: float, details: dict) -> PaymentResult:
        raise NotImplementedError
    def fee(self, amount: float) -> float:
        raise NotImplementedError
    def is_instant(self) -> bool:
        raise NotImplementedError
    def requires_field(self) -> list[str]:
        raise NotImplementedError

    def total_charge(self, amount: float) -> float:
        """Shared calculation — no override needed."""
        return amount + self.fee(amount)


# ── The checkout flow — clean, no branching on payment type ─────────────────

def validate_payment_details(method: PaymentMethod, details: dict):
    missing = [f for f in method.requires_field() if f not in details]
    if missing:
        raise ValueError(f"{method.display_name} requires: {', '.join(missing)}")

def checkout(cart, method: PaymentMethod, details: dict) -> PaymentResult:
    validate_payment_details(method, details)

    total = method.total_charge(cart.subtotal)
    result = method.process(total, details)

    if result.success and method.is_instant():
        ship_immediately(cart)
    elif result.success:
        schedule_shipment_on_confirmation(cart)

    return result

def show_payment_options(cart) -> None:
    for method in PaymentMethod:
        total = method.total_charge(cart.subtotal)
        instant = "instant" if method.is_instant() else "2-3 days"
        print(f"  {method.icon} {method.display_name:<20} ${total:.2f}  ({instant})")
```

Adding a new payment method — say, `PAYPAL` — means adding one new inner class to `PaymentMethod`. Every part of the checkout flow handles it automatically.

---

## Quick reference card

```python
from jenum import DEnum, MDEnum, body

# ── Declaring constants ──────────────────────────────────────────
class MyEnum(DEnum):

    # Style 1: bare tuple (auto ordinal, constructor args)
    A = ()
    B = (arg1, arg2)

    # Style 2: body() (explicit ordinal, optional constructor args)
    C = body()
    D = body(arg1, ordinal=10)

    # Style 3: inline anonymous subclass (per-constant overrides)
    class E(MyEnum):
        args    = (arg1,)
        ordinal = 20          # optional
        def my_method(self): return "E's version"

    # Style 4: post-hoc override (long bodies, defined after class)
    F = body()

    def __init__(self, arg1=None, arg2=None):
        self.arg1 = arg1

    def my_method(self) -> str:
        return "default version"

@MyEnum.override('F')
def my_method(self):
    return "F's version"

# ── Using constants ──────────────────────────────────────────────
MyEnum.A                     # the constant
MyEnum.A.name                # "A"
MyEnum.A.ordinal             # 0
MyEnum.A.my_method()         # "default version"
MyEnum.E.my_method()         # "E's version"
MyEnum.F.my_method()         # "F's version"

MyEnum['A']                  # lookup by name
MyEnum.value_of('A')         # same
MyEnum.from_ordinal(20)      # MyEnum.E
MyEnum.values()              # [A, B, C, D, E, F] in ordinal order
len(MyEnum)                  # 6
MyEnum.A in MyEnum           # True

for constant in MyEnum: ...  # iterate in ordinal order
sorted(MyEnum)               # ordered by ordinal
min(MyEnum), max(MyEnum)     # by ordinal
```

---

## MDEnum — Mutable Dispatch Enum Fields

Sometimes you need an enum to carry **live state** alongside its identity. A device connection tracker, a sensor reading cache, a per-channel message counter — these are cases where the constant itself is stable (you'll always have `CONNECTED`, `DISCONNECTED`, `ERROR`) but the data attached to it changes over time.

`MDEnum` (Mutable Dispatch Enum) handles this. It is identical to `DEnum` (Dispatch Enum) in every respect except that fields declared in `__init__` remain mutable after construction. The enum's identity is still fully locked.

```python
from jenum import MDEnum, body
from datetime import datetime

class DeviceState(MDEnum):
    CONNECTED    = ("unknown",)
    DISCONNECTED = ("",)
    ERROR        = ("",)

    def __init__(self, firmware: str):
        self.firmware  = firmware    # mutable — updated when device reports in
        self.last_seen = None        # mutable — updated on each heartbeat

    def is_stale(self, threshold_seconds: int = 30) -> bool:
        if self.last_seen is None:
            return True
        return (datetime.now() - self.last_seen).seconds > threshold_seconds
```

```python
# Update live state as the device reports in
DeviceState.CONNECTED.firmware  = "2.1.4"
DeviceState.CONNECTED.last_seen = datetime.now()

# The constant itself never changes — identity operations all work normally
if device.state == DeviceState.CONNECTED:
    if device.state.is_stale():
        alert("device not responding")
```

### The mutability contract

Three distinct tiers of protection:

| What | Mutable? | Example |
|---|---|---|
| Fields set in `__init__` | ✅ Yes | `firmware`, `last_seen`, `value`, `count` |
| Enum identity | ❌ Never | `name`, `ordinal` |
| Anything not set in `__init__` | ❌ Never | new attributes, methods |

Trying to violate the contract gives you a precise, actionable error:

```python
DeviceState.CONNECTED.ordinal   = 99    # AttributeError:
# DeviceState.CONNECTED: cannot set 'ordinal' — only fields declared
# in __init__ are mutable: ['firmware', 'last_seen']

DeviceState.CONNECTED.new_field = "x"   # AttributeError:
# DeviceState.CONNECTED: cannot set 'new_field' — only fields declared
# in __init__ are mutable: ['firmware', 'last_seen']
```

The error message tells you exactly which fields *are* allowed to change — no guessing.

### Mutations are shared across all references (singleton semantics)

Because each constant is a singleton, any reference to `DeviceState.CONNECTED` — whether you got it from the class, from `value_of()`, from `from_ordinal()`, or from a variable — is the same object. Mutating it through one reference is immediately visible through all others:

```python
a = DeviceState.CONNECTED
b = DeviceState['CONNECTED']

a.firmware = "3.0.0"
assert b.firmware == "3.0.0"   # same object
assert a is b                   # True
```

This is the expected behaviour for device/session state — there is one `CONNECTED` state in the system, and everyone who holds a reference to it sees the current truth.

### All declaration styles work identically

`MDEnum` inherits all four declaration styles from `DEnum`. Just swap the base class:

```python
class Sensor(MDEnum):

    TEMPERATURE = ("°C",)                     # bare tuple
    PRESSURE    = body("hPa", ordinal=10)     # body() with explicit ordinal

    class HUMIDITY(Sensor):                   # inline subclass with override
        args    = ("%RH",)
        ordinal = 20
        def calibrate(self):
            self.value = self.value * 1.02    # can mutate self.value

    def __init__(self, unit: str):
        self.unit  = unit
        self.value = 0.0
        self.ok    = True

    def calibrate(self):
        pass   # default no-op

# Update readings as data arrives
Sensor.TEMPERATURE.value = 23.5
Sensor.PRESSURE.value    = 1013.25
Sensor.HUMIDITY.value    = 55.0

Sensor.HUMIDITY.calibrate()   # per-constant override mutates self.value

print(f"{Sensor.HUMIDITY.value:.4f}{Sensor.HUMIDITY.unit}")  # 56.1000%RH
```

`@override` also works, and overridden methods can freely mutate `__init__` fields:

```python
class Channel(MDEnum):
    EMAIL = body()
    SMS   = body()
    PUSH  = body()

    def __init__(self):
        self.enabled = True
        self.count   = 0

    def send(self, msg: str) -> str:
        raise NotImplementedError

@Channel.override('EMAIL')
def send(self, msg):
    self.count += 1          # mutates self.count — allowed
    return f"email: {msg}"

@Channel.override('SMS')
def send(self, msg):
    self.count += 1
    return f"sms: {msg}"

Channel.EMAIL.send("hello")
Channel.EMAIL.send("world")

print(Channel.EMAIL.count)   # 2
Channel.EMAIL.enabled = False  # mutable field
```

### MDEnum vs DEnum — choosing the right one

Use **`DEnum`** (immutable) when:
- Constants represent fixed, mathematical, or domain truths (planets, operations, HTTP verbs, directions)
- You want compile-time certainty that nothing changes state
- The enum is shared across threads and you don't want to think about synchronisation

Use **`MDEnum`** (mutable fields) when:
- Constants represent states in a system where each state naturally carries live data (device states, connection states, session states)
- You want a single canonical object per state that always reflects current reality
- The alternative would be a separate dict or dataclass that you'd have to keep in sync with the enum

The rule of thumb: if the enum represents *what something is*, use `DEnum`. If it represents *what something is right now*, and "right now" changes, use `MDEnum`.

### A note on thread safety

`MDEnum` does not add any synchronisation. If multiple threads can read and write the same constant's fields concurrently, add your own locking. A simple approach:

```python
import threading

class DeviceState(MDEnum):
    CONNECTED    = ("unknown",)
    DISCONNECTED = ("",)

    def __init__(self, firmware: str):
        self.firmware  = firmware
        self.last_seen = None
        self._lock     = threading.Lock()   # also a mutable field

    def update(self, firmware: str, timestamp):
        with self._lock:
            self.firmware  = firmware
            self.last_seen = timestamp
```
