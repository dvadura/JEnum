"""
Comprehensive tests for DEnum (immutable Java-style enums).
"""
import pytest
from jenum import DEnum, body


# ─── Module-level fixture enums ───────────────────────────────────────────────

class Direction(DEnum):
    NORTH = ()
    SOUTH = ()
    EAST  = ()
    WEST  = ()


class Planet(DEnum):
    MERCURY = (3.303e+23, 2.4397e6)
    VENUS   = (4.869e+24, 6.0518e6)
    EARTH   = (5.976e+24, 6.37814e6)

    def __init__(self, mass: float, radius: float):
        self.mass   = mass
        self.radius = radius

    def surface_gravity(self) -> float:
        G = 6.67300e-11
        return G * self.mass / (self.radius ** 2)


class HttpStatus(DEnum):
    OK                    = body(ordinal=200)
    CREATED               = body(ordinal=201)
    BAD_REQUEST           = body(ordinal=400)
    NOT_FOUND             = body(ordinal=404)
    INTERNAL_SERVER_ERROR = body(ordinal=500)


class Operation(DEnum):
    class PLUS(Operation):
        args = ()
        def apply(self, x, y): return x + y
        def symbol(self): return "+"

    class MINUS(Operation):
        args = ()
        def apply(self, x, y): return x - y
        def symbol(self): return "-"

    class TIMES(Operation):
        args = ()
        def apply(self, x, y): return x * y
        def symbol(self): return "*"

    class DIVIDE(Operation):
        args = ()
        def apply(self, x, y): return x / y
        def symbol(self): return "/"


class PaymentMethod(DEnum):
    CASH   = ()
    CREDIT = ()
    DEBIT  = ()

    def fee(self) -> float: return 0.0


@PaymentMethod.override('CREDIT')
def fee(self) -> float: return 0.025  # noqa: E302

@PaymentMethod.override('DEBIT')
def fee(self) -> float: return 0.01  # noqa: E302


class Priority(DEnum):
    LOW    = body(ordinal=10)
    MEDIUM = body(ordinal=20)
    HIGH   = body(ordinal=30)


class Processor(DEnum):
    FAST = ()
    SLOW = ()

    def process(self):
        raise NotImplementedError(f"{self.name}.process() not implemented")


@Processor.override('FAST')
def process(self): return "fast result"  # noqa: E302


# ─── TestDeclarationStyles ────────────────────────────────────────────────────

class TestDeclarationStyles:

    def test_bare_tuple_no_args(self):
        assert Direction.NORTH.name    == "NORTH"
        assert Direction.NORTH.ordinal == 0

    def test_bare_tuple_with_constructor_args(self):
        assert Planet.EARTH.mass   == pytest.approx(5.976e+24)
        assert Planet.EARTH.radius == pytest.approx(6.37814e6)

    def test_body_no_args(self):
        class Flag(DEnum):
            ON  = body()
            OFF = body()
        assert Flag.ON.name  == "ON"
        assert Flag.OFF.name == "OFF"

    def test_body_explicit_ordinal(self):
        assert HttpStatus.OK.ordinal       == 200
        assert HttpStatus.NOT_FOUND.ordinal == 404

    def test_body_with_args_and_ordinal(self):
        class Sized(DEnum):
            SMALL = body("s", ordinal=1)
            LARGE = body("l", ordinal=3)
            def __init__(self, code: str):
                self.code = code
        assert Sized.SMALL.code    == "s"
        assert Sized.SMALL.ordinal == 1
        assert Sized.LARGE.code    == "l"
        assert Sized.LARGE.ordinal == 3

    def test_inline_subclass_dispatch(self):
        assert Operation.PLUS.apply(3, 4)   == 7
        assert Operation.MINUS.apply(10, 3) == 7
        assert Operation.TIMES.apply(3, 4)  == 12
        assert Operation.DIVIDE.apply(8, 4) == pytest.approx(2.0)

    def test_inline_subclass_symbol(self):
        assert Operation.PLUS.symbol()   == "+"
        assert Operation.MINUS.symbol()  == "-"
        assert Operation.TIMES.symbol()  == "*"
        assert Operation.DIVIDE.symbol() == "/"

    def test_inline_subclass_ordinal(self):
        assert Operation.PLUS.ordinal   == 0
        assert Operation.MINUS.ordinal  == 1
        assert Operation.TIMES.ordinal  == 2
        assert Operation.DIVIDE.ordinal == 3

    def test_override_decorator_overrides_selected(self):
        assert PaymentMethod.CREDIT.fee() == pytest.approx(0.025)
        assert PaymentMethod.DEBIT.fee()  == pytest.approx(0.01)

    def test_override_decorator_leaves_others_unchanged(self):
        assert PaymentMethod.CASH.fee() == pytest.approx(0.0)

    def test_mixed_styles_all_four(self):
        class Mixed(DEnum):
            A = ()               # style 1: bare tuple
            B = body(ordinal=10) # style 2: body()
            class C(Mixed):      # style 3: inline subclass
                args = ()
                def describe(self): return "inline C"
            D = ()               # style 1 again
            def describe(self): return "default"

        @Mixed.override('A')     # style 4: @override
        def describe(self): return "overridden A"

        assert Mixed.A.describe() == "overridden A"
        assert Mixed.B.describe() == "default"
        assert Mixed.C.describe() == "inline C"
        assert Mixed.D.describe() == "default"

    def test_inline_subclass_args_omitted_defaults_to_empty(self):
        # No 'args' attribute → defaults to ()
        class NoArgs(DEnum):
            class ITEM(NoArgs):
                pass  # no args defined
        assert NoArgs.ITEM.name == "ITEM"

    def test_inline_subclass_non_tuple_args_gets_wrapped(self):
        class Wrapped(DEnum):
            class SINGLE(Wrapped):
                args = "hello"   # single non-tuple → wrapped to ("hello",)
            def __init__(self, s: str):
                self.value = s
        assert Wrapped.SINGLE.value == "hello"


# ─── TestOrdinals ─────────────────────────────────────────────────────────────

class TestOrdinals:

    def test_auto_ordinals_start_at_zero_sequential(self):
        assert Direction.NORTH.ordinal == 0
        assert Direction.SOUTH.ordinal == 1
        assert Direction.EAST.ordinal  == 2
        assert Direction.WEST.ordinal  == 3

    def test_auto_ordinals_skip_explicitly_reserved_slots(self):
        class Skipped(DEnum):
            FIRST = ()               # auto
            ZERO  = body(ordinal=0)  # explicit 0
            LAST  = ()               # auto
        # ZERO claims 0; FIRST gets next available (1); LAST gets 2
        assert Skipped.ZERO.ordinal  == 0
        assert Skipped.FIRST.ordinal == 1
        assert Skipped.LAST.ordinal  == 2

    def test_explicit_ordinals_need_not_be_in_declaration_order(self):
        class Scrambled(DEnum):
            C = body(ordinal=2)
            A = body(ordinal=0)
            B = body(ordinal=1)
        # values() must return in ordinal order regardless of declaration order
        assert Scrambled.values() == [Scrambled.A, Scrambled.B, Scrambled.C]

    def test_duplicate_explicit_ordinal_raises(self):
        with pytest.raises(ValueError, match="duplicate explicit ordinal"):
            class Dup(DEnum):
                X = body(ordinal=5)
                Y = body(ordinal=5)

    def test_negative_ordinal_raises(self):
        with pytest.raises(ValueError, match="non-negative int"):
            class Neg(DEnum):
                X = body(ordinal=-1)

    def test_float_ordinal_raises(self):
        with pytest.raises(ValueError, match="non-negative int"):
            class Float(DEnum):
                X = body(ordinal=1.5)


# ─── TestAPI ──────────────────────────────────────────────────────────────────

class TestAPI:

    def test_name_property_bare_tuple(self):
        assert Direction.NORTH.name == "NORTH"
        assert Direction.SOUTH.name == "SOUTH"

    def test_name_property_body(self):
        assert HttpStatus.OK.name       == "OK"
        assert HttpStatus.NOT_FOUND.name == "NOT_FOUND"

    def test_name_property_inline_subclass(self):
        assert Operation.PLUS.name  == "PLUS"
        assert Operation.MINUS.name == "MINUS"

    def test_ordinal_property(self):
        assert Direction.NORTH.ordinal == 0
        assert HttpStatus.OK.ordinal   == 200

    def test_values_returns_list_in_ordinal_order_auto(self):
        vals = Direction.values()
        assert vals == [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
        ords = [v.ordinal for v in vals]
        assert ords == sorted(ords)

    def test_values_returns_list_in_ordinal_order_explicit(self):
        vals = HttpStatus.values()
        ords = [v.ordinal for v in vals]
        assert ords == sorted(ords)
        assert vals[0] is HttpStatus.OK

    def test_value_of_returns_correct_constant(self):
        assert Direction.value_of("NORTH")      is Direction.NORTH
        assert HttpStatus.value_of("NOT_FOUND") is HttpStatus.NOT_FOUND

    def test_value_of_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="has no member"):
            Direction.value_of("NONEXISTENT")

    def test_from_ordinal_returns_correct_constant(self):
        assert Direction.from_ordinal(0)    is Direction.NORTH
        assert HttpStatus.from_ordinal(404) is HttpStatus.NOT_FOUND

    def test_from_ordinal_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="has no member with ordinal"):
            Direction.from_ordinal(999)

    def test_subscript_same_as_value_of(self):
        assert Direction["NORTH"]       is Direction.NORTH
        assert HttpStatus["NOT_FOUND"]  is HttpStatus.NOT_FOUND

    def test_subscript_unknown_raises_key_error(self):
        with pytest.raises(KeyError):
            _ = Direction["NOWHERE"]

    def test_containment_true_for_member(self):
        assert Direction.NORTH in Direction
        assert Direction.EAST  in Direction

    def test_containment_false_for_string(self):
        assert "NORTH" not in Direction

    def test_containment_false_for_int(self):
        assert 0 not in Direction

    def test_len(self):
        assert len(Direction)   == 4
        assert len(HttpStatus)  == 5
        assert len(Operation)   == 4

    def test_iteration_ordinal_order(self):
        names = [c.name for c in Direction]
        assert names == ["NORTH", "SOUTH", "EAST", "WEST"]

    def test_list_equals_values(self):
        assert list(Direction)  == Direction.values()
        assert list(HttpStatus) == HttpStatus.values()

    def test_shared_method_works_on_all_constants(self):
        for planet in Planet:
            assert planet.surface_gravity() > 0


# ─── TestStringRepresentation ─────────────────────────────────────────────────

class TestStringRepresentation:

    def test_str_returns_name(self):
        assert str(Direction.NORTH)      == "NORTH"
        assert str(HttpStatus.NOT_FOUND) == "NOT_FOUND"

    def test_repr_returns_class_dot_name(self):
        assert repr(Direction.NORTH) == "Direction.NORTH"
        assert repr(HttpStatus.OK)   == "HttpStatus.OK"

    def test_repr_strips_anon_suffix_for_inline_subclass(self):
        # type(Operation.PLUS).__name__ is "Operation.PLUS" (anonymous subclass);
        # __repr__ strips everything after the first '.' to get the class prefix.
        assert repr(Operation.PLUS)  == "Operation.PLUS"
        assert repr(Operation.MINUS) == "Operation.MINUS"

    def test_repr_of_enum_class_contains_name_and_members(self):
        r = repr(Direction)
        assert "Direction" in r
        assert "NORTH"     in r
        assert "SOUTH"     in r
        assert "EAST"      in r
        assert "WEST"      in r

    def test_repr_of_enum_class_format(self):
        r = repr(Direction)
        assert r.startswith("<jenum Direction:")


# ─── TestEqualityAndHashing ───────────────────────────────────────────────────

class TestEqualityAndHashing:

    def test_constant_equal_to_itself(self):
        assert Direction.NORTH == Direction.NORTH

    def test_different_constants_not_equal(self):
        assert Direction.NORTH != Direction.SOUTH

    def test_not_equal_to_string(self):
        assert Direction.NORTH != "NORTH"

    def test_not_equal_to_int(self):
        assert Direction.NORTH != 0

    def test_hash_is_stable(self):
        h = hash(Direction.NORTH)
        assert hash(Direction.NORTH) == h
        assert hash(Direction.NORTH) == h

    def test_hash_consistent_with_equality(self):
        assert Direction.NORTH == Direction.NORTH
        assert hash(Direction.NORTH) == hash(Direction.NORTH)

    def test_usable_as_dict_keys(self):
        d = {
            Direction.NORTH: "up",
            Direction.SOUTH: "down",
            Direction.EAST:  "right",
            Direction.WEST:  "left",
        }
        assert d[Direction.NORTH] == "up"
        assert d[Direction.WEST]  == "left"

    def test_usable_in_sets_deduplication(self):
        s = {Direction.NORTH, Direction.SOUTH, Direction.NORTH}
        assert len(s) == 2
        assert Direction.NORTH in s


# ─── TestComparison ───────────────────────────────────────────────────────────

class TestComparison:

    def test_less_than(self):
        assert Priority.LOW    < Priority.MEDIUM
        assert Priority.MEDIUM < Priority.HIGH

    def test_less_than_or_equal(self):
        assert Priority.LOW    <= Priority.LOW
        assert Priority.MEDIUM <= Priority.HIGH

    def test_greater_than(self):
        assert Priority.HIGH   > Priority.MEDIUM
        assert Priority.MEDIUM > Priority.LOW

    def test_greater_than_or_equal(self):
        assert Priority.HIGH >= Priority.HIGH
        assert Priority.HIGH >= Priority.MEDIUM

    def test_comparison_with_non_denum_raises_type_error(self):
        with pytest.raises(TypeError):
            _ = Priority.LOW < 5

    def test_min(self):
        assert min(Priority) is Priority.LOW

    def test_max(self):
        assert max(Priority) is Priority.HIGH

    def test_sorted(self):
        shuffled = [Priority.HIGH, Priority.LOW, Priority.MEDIUM]
        assert sorted(shuffled) == [Priority.LOW, Priority.MEDIUM, Priority.HIGH]

    def test_sorted_reverse(self):
        shuffled = [Priority.LOW, Priority.HIGH, Priority.MEDIUM]
        assert sorted(shuffled, reverse=True) == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]


# ─── TestImmutability ─────────────────────────────────────────────────────────

class TestImmutability:

    def test_cannot_set_init_field_after_construction(self):
        with pytest.raises(AttributeError, match="immutable"):
            Planet.EARTH.mass = 999.0

    def test_cannot_set_name_property(self):
        with pytest.raises(AttributeError, match="immutable"):
            Direction.NORTH.name = "SOUTH"

    def test_cannot_set_ordinal_property(self):
        with pytest.raises(AttributeError, match="immutable"):
            Direction.NORTH.ordinal = 99

    def test_cannot_set_new_attribute(self):
        with pytest.raises(AttributeError, match="immutable"):
            Direction.NORTH.new_field = "x"

    def test_inline_subclass_constant_is_also_immutable(self):
        with pytest.raises(AttributeError, match="immutable"):
            Operation.PLUS.new_field = "x"


# ─── TestInheritance ──────────────────────────────────────────────────────────

class TestInheritance:

    def test_external_subclassing_finalized_enum_raises(self):
        with pytest.raises(TypeError, match="final"):
            class Sub(Direction):
                pass

    def test_abstract_base_can_be_subclassed(self):
        class Shape(DEnum):
            def area(self): raise NotImplementedError

        class Circle(Shape):
            SMALL = ()
            LARGE = ()

        assert Circle.SMALL.name == "SMALL"
        assert Circle.LARGE.name == "LARGE"

    def test_abstract_base_has_zero_constants(self):
        class Base(DEnum):
            pass
        assert len(Base)     == 0
        assert Base.values() == []

    def test_multiple_concrete_subclasses_of_same_base_are_independent(self):
        class Color(DEnum):
            pass

        class RGB(Color):
            RED   = ()
            GREEN = ()
            BLUE  = ()

        class CMYK(Color):
            CYAN    = ()
            MAGENTA = ()
            YELLOW  = ()
            BLACK   = ()

        assert len(RGB)  == 3
        assert len(CMYK) == 4
        assert RGB.RED not in CMYK


# ─── TestMethodOverrides ──────────────────────────────────────────────────────

class TestMethodOverrides:

    def test_inline_subclass_per_constant_dispatch(self):
        assert Operation.PLUS.apply(2, 3)   == 5
        assert Operation.MINUS.apply(10, 4) == 6
        assert Operation.TIMES.apply(3, 5)  == 15

    def test_default_method_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            Processor.SLOW.process()

    def test_override_on_plain_constant(self):
        assert Processor.FAST.process() == "fast result"

    def test_override_on_inline_subclass_constant(self):
        class Tagged(DEnum):
            class SPECIAL(Tagged):
                args = ()
                def label(self): return "special-default"
            PLAIN = ()
            def label(self): return "plain-default"

        @Tagged.override('SPECIAL')
        def label(self): return "overridden-special"

        assert Tagged.SPECIAL.label() == "overridden-special"
        assert Tagged.PLAIN.label()   == "plain-default"

    def test_multiple_overrides_on_same_constant(self):
        class Multi(DEnum):
            TARGET = ()
            def alpha(self): return "a_default"
            def beta(self):  return "b_default"

        @Multi.override('TARGET')
        def alpha(self): return "a_overridden"

        @Multi.override('TARGET')
        def beta(self): return "b_overridden"

        assert Multi.TARGET.alpha() == "a_overridden"
        assert Multi.TARGET.beta()  == "b_overridden"

    def test_override_returns_original_function(self):
        class Ret(DEnum):
            X = ()
            def method(self): return "x"

        result = Ret.override('X')(lambda self: "overridden")
        assert callable(result)


# ─── TestEdgeCases ────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_single_constant_enum(self):
        class Singleton(DEnum):
            ONLY = ()
        assert len(Singleton)         == 1
        assert Singleton.ONLY.name    == "ONLY"
        assert Singleton.ONLY.ordinal == 0
        assert Singleton.values()     == [Singleton.ONLY]

    def test_empty_enum(self):
        class Empty(DEnum):
            pass
        assert len(Empty)     == 0
        assert Empty.values() == []
        assert list(Empty)    == []

    def test_values_returns_new_list_each_call(self):
        v1 = Direction.values()
        v2 = Direction.values()
        assert v1 == v2
        assert v1 is not v2

    def test_inline_forward_reference_resolves_correctly(self):
        assert Operation.PLUS is Operation['PLUS']

    def test_constants_usable_as_dict_keys_realistic(self):
        dispatch = {
            Operation.PLUS:   lambda x, y: x + y,
            Operation.MINUS:  lambda x, y: x - y,
            Operation.TIMES:  lambda x, y: x * y,
            Operation.DIVIDE: lambda x, y: x / y,
        }
        assert dispatch[Operation.PLUS](10, 5)   == 15
        assert dispatch[Operation.MINUS](10, 5)  == 5
        assert dispatch[Operation.TIMES](10, 5)  == 50
        assert dispatch[Operation.DIVIDE](10, 5) == pytest.approx(2.0)

    def test_constants_usable_in_set_intersection_union(self):
        s1 = {Direction.NORTH, Direction.EAST}
        s2 = {Direction.NORTH, Direction.WEST}
        assert s1 & s2 == {Direction.NORTH}
        assert Direction.NORTH in (s1 | s2)
        assert Direction.EAST  in (s1 | s2)
        assert Direction.WEST  in (s1 | s2)

    def test_repeated_iteration_same_order(self):
        first  = list(Direction)
        second = list(Direction)
        assert first == second

    def test_match_case_native(self):
        result = None
        d = Direction.NORTH
        match d:
            case Direction.NORTH:
                result = "north"
            case Direction.SOUTH:
                result = "south"
            case _:
                result = "other"
        assert result == "north"
