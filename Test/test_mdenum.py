"""
Comprehensive tests for MDEnum (mutable Java-style enums).

Module-level fixture enums are shared across test classes.
Each test class that mutates shared state provides a setup_method
to reset mutable fields to their post-construction defaults.
"""
import pytest
from jenum import MDEnum, body


# ─── Module-level fixture enums ───────────────────────────────────────────────

class DeviceState(MDEnum):
    CONNECTED    = ("unknown",)
    DISCONNECTED = ("",)
    ERROR        = ("",)

    def __init__(self, firmware: str):
        self.firmware  = firmware
        self.last_seen = None


class Counter(MDEnum):
    A = body()
    B = body()

    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1


class Sensor(MDEnum):
    class TEMPERATURE(Sensor):
        args = ("celsius", 37.0)
        def calibrate(self):
            self.value = 36.6

    HUMIDITY = ("percent",)
    PRESSURE = body("hPa", ordinal=10)

    def __init__(self, unit: str, value: float = 0.0):
        self.unit  = unit
        self.value = value

    def calibrate(self):
        self.value = 0.0


# ─── TestMDEnumMutability ─────────────────────────────────────────────────────

class TestMDEnumMutability:

    def setup_method(self):
        DeviceState.CONNECTED.firmware     = "unknown"
        DeviceState.CONNECTED.last_seen    = None
        DeviceState.DISCONNECTED.firmware  = ""
        DeviceState.DISCONNECTED.last_seen = None
        DeviceState.ERROR.firmware         = ""
        DeviceState.ERROR.last_seen        = None

    def test_init_field_mutable_post_construction(self):
        DeviceState.CONNECTED.firmware = "2.1.4"
        assert DeviceState.CONNECTED.firmware == "2.1.4"

    def test_none_field_can_be_assigned(self):
        from datetime import datetime
        ts = datetime(2025, 1, 1)
        DeviceState.CONNECTED.last_seen = ts
        assert DeviceState.CONNECTED.last_seen == ts

    def test_field_can_be_reassigned_repeatedly(self):
        DeviceState.CONNECTED.firmware = "1.0"
        DeviceState.CONNECTED.firmware = "2.0"
        DeviceState.CONNECTED.firmware = "3.0"
        assert DeviceState.CONNECTED.firmware == "3.0"

    def test_different_constants_fields_are_independent(self):
        DeviceState.CONNECTED.firmware    = "fw-conn"
        DeviceState.DISCONNECTED.firmware = "fw-disc"
        assert DeviceState.CONNECTED.firmware    == "fw-conn"
        assert DeviceState.DISCONNECTED.firmware == "fw-disc"


# ─── TestMDEnumIdentityImmutable ──────────────────────────────────────────────

class TestMDEnumIdentityImmutable:
    """
    The private backing attributes (_name_, _ordinal_, etc.) and the public
    property aliases (name, ordinal) are all locked post-construction.

    Private identity attrs raise "identity".
    Public aliases (name, ordinal) are not in __init__ so they raise
    the "only fields declared in __init__" error.
    """

    def test_cannot_set_private_name(self):
        with pytest.raises(AttributeError, match="identity"):
            DeviceState.CONNECTED._name_ = "RENAMED"

    def test_cannot_set_private_ordinal(self):
        with pytest.raises(AttributeError, match="identity"):
            DeviceState.CONNECTED._ordinal_ = 99

    def test_cannot_set_initialized(self):
        with pytest.raises(AttributeError, match="identity"):
            DeviceState.CONNECTED._initialized_ = False

    def test_cannot_set_mutable_fields(self):
        with pytest.raises(AttributeError, match="identity"):
            DeviceState.CONNECTED._mutable_fields_ = frozenset()

    def test_cannot_set_name_property(self):
        # 'name' is not in __init__, so raises the mutable-fields error
        with pytest.raises(AttributeError):
            DeviceState.CONNECTED.name = "RENAMED"

    def test_cannot_set_ordinal_property(self):
        # 'ordinal' is not in __init__, same reason
        with pytest.raises(AttributeError):
            DeviceState.CONNECTED.ordinal = 99


# ─── TestMDEnumNewAttributeRejected ───────────────────────────────────────────

class TestMDEnumNewAttributeRejected:

    def test_undeclared_field_raises(self):
        with pytest.raises(AttributeError, match="only fields declared in __init__"):
            DeviceState.CONNECTED.new_field = "x"

    def test_error_message_lists_allowed_fields(self):
        with pytest.raises(AttributeError) as exc_info:
            DeviceState.CONNECTED.unknown_attr = "x"
        msg = str(exc_info.value)
        assert "firmware"  in msg
        assert "last_seen" in msg


# ─── TestMDEnumSingleton ──────────────────────────────────────────────────────

class TestMDEnumSingleton:

    def setup_method(self):
        DeviceState.CONNECTED.firmware  = "unknown"
        DeviceState.CONNECTED.last_seen = None

    def test_mutation_visible_through_all_references(self):
        DeviceState.CONNECTED.firmware = "2.1.4"
        assert DeviceState.CONNECTED.firmware             == "2.1.4"
        assert DeviceState["CONNECTED"].firmware           == "2.1.4"
        assert DeviceState.value_of("CONNECTED").firmware == "2.1.4"
        assert DeviceState.from_ordinal(0).firmware       == "2.1.4"

    def test_all_references_are_same_object(self):
        conn = DeviceState.CONNECTED
        assert conn is DeviceState["CONNECTED"]
        assert conn is DeviceState.value_of("CONNECTED")
        assert conn is DeviceState.from_ordinal(0)


# ─── TestMDEnumDeclarationStyles ──────────────────────────────────────────────

class TestMDEnumDeclarationStyles:

    def setup_method(self):
        Sensor.TEMPERATURE.value = 37.0
        Sensor.TEMPERATURE.unit  = "celsius"
        Sensor.HUMIDITY.value    = 0.0
        Sensor.HUMIDITY.unit     = "percent"
        Sensor.PRESSURE.value    = 0.0
        Sensor.PRESSURE.unit     = "hPa"

    def test_bare_tuple_works(self):
        assert DeviceState.CONNECTED.name     == "CONNECTED"
        assert DeviceState.CONNECTED.firmware == "unknown"

    def test_body_with_ordinal_works(self):
        assert Sensor.PRESSURE.ordinal == 10
        assert Sensor.PRESSURE.unit    == "hPa"

    def test_inline_subclass_construction(self):
        assert Sensor.TEMPERATURE.name == "TEMPERATURE"
        assert Sensor.TEMPERATURE.unit == "celsius"

    def test_inline_subclass_per_constant_override(self):
        Sensor.TEMPERATURE.value = 99.0
        Sensor.TEMPERATURE.calibrate()
        assert Sensor.TEMPERATURE.value == pytest.approx(36.6)

    def test_override_decorator_works_and_can_mutate(self):
        class Toggle(MDEnum):
            ON  = ()
            OFF = ()
            def __init__(self):
                self.active = False
            def activate(self):
                self.active = True

        @Toggle.override('ON')
        def activate(self):
            self.active = True

        Toggle.ON.activate()
        assert Toggle.ON.active is True
        assert Toggle.OFF.active is False


# ─── TestMDEnumOverrideMutation ───────────────────────────────────────────────

class TestMDEnumOverrideMutation:

    def setup_method(self):
        Counter.A.count = 0
        Counter.B.count = 0
        Sensor.TEMPERATURE.value = 37.0
        Sensor.HUMIDITY.value    = 0.0
        Sensor.PRESSURE.value    = 0.0

    def test_inline_subclass_calibrate_modifies_value(self):
        Sensor.TEMPERATURE.value = 100.0
        Sensor.TEMPERATURE.calibrate()
        assert Sensor.TEMPERATURE.value == pytest.approx(36.6)

    def test_base_calibrate_resets_to_zero(self):
        Sensor.HUMIDITY.value = 55.0
        Sensor.HUMIDITY.calibrate()
        assert Sensor.HUMIDITY.value == pytest.approx(0.0)

    def test_shared_method_can_mutate_field(self):
        Counter.A.increment()
        Counter.A.increment()
        assert Counter.A.count == 2

    def test_per_constant_mutations_do_not_affect_others(self):
        Counter.A.count = 10
        Counter.B.count = 20
        assert Counter.A.count == 10
        assert Counter.B.count == 20


# ─── TestMDEnumInheritedBehaviors ─────────────────────────────────────────────

class TestMDEnumInheritedBehaviors:

    def test_name_property(self):
        assert DeviceState.CONNECTED.name    == "CONNECTED"
        assert DeviceState.DISCONNECTED.name == "DISCONNECTED"

    def test_ordinal_property(self):
        assert DeviceState.CONNECTED.ordinal    == 0
        assert DeviceState.DISCONNECTED.ordinal == 1

    def test_values(self):
        vals = DeviceState.values()
        assert len(vals) == 3
        assert vals[0] is DeviceState.CONNECTED

    def test_value_of(self):
        assert DeviceState.value_of("CONNECTED") is DeviceState.CONNECTED

    def test_from_ordinal(self):
        assert DeviceState.from_ordinal(0) is DeviceState.CONNECTED

    def test_iteration(self):
        names = [c.name for c in DeviceState]
        assert "CONNECTED"    in names
        assert "DISCONNECTED" in names
        assert "ERROR"        in names

    def test_len(self):
        assert len(DeviceState) == 3

    def test_str(self):
        assert str(DeviceState.CONNECTED) == "CONNECTED"

    def test_repr(self):
        assert repr(DeviceState.CONNECTED) == "DeviceState.CONNECTED"

    def test_equality_identity_semantics(self):
        assert DeviceState.CONNECTED == DeviceState.CONNECTED
        assert DeviceState.CONNECTED != DeviceState.DISCONNECTED

    def test_hash_usable_as_dict_key(self):
        d = {DeviceState.CONNECTED: "conn", DeviceState.ERROR: "err"}
        assert d[DeviceState.CONNECTED] == "conn"

    def test_finality(self):
        with pytest.raises(TypeError, match="final"):
            class Sub(DeviceState):
                pass

    def test_ordinal_comparison_operators(self):
        assert DeviceState.CONNECTED < DeviceState.ERROR
        assert DeviceState.ERROR     > DeviceState.CONNECTED


# ─── TestMDEnumInternalState ──────────────────────────────────────────────────

class TestMDEnumInternalState:

    def test_mutable_fields_is_frozenset(self):
        mf = object.__getattribute__(DeviceState.CONNECTED, "_mutable_fields_")
        assert isinstance(mf, frozenset)

    def test_mutable_fields_contains_exactly_init_names(self):
        mf = object.__getattribute__(DeviceState.CONNECTED, "_mutable_fields_")
        assert mf == frozenset({"firmware", "last_seen"})

    def test_mutable_stage_does_not_exist_after_construction(self):
        with pytest.raises(AttributeError):
            object.__getattribute__(DeviceState.CONNECTED, "_mutable_stage_")

    def test_counter_mutable_fields(self):
        mf = object.__getattribute__(Counter.A, "_mutable_fields_")
        assert mf == frozenset({"count"})

    def test_sensor_mutable_fields(self):
        mf = object.__getattribute__(Sensor.HUMIDITY, "_mutable_fields_")
        assert mf == frozenset({"unit", "value"})
