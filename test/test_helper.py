import pytest
from stockcv.helpers import Value, ValueException

_MIN = 10
_SPAN = 2
_MAX = 50


@pytest.mark.parametrize("test_value", [i for i in range(_MIN, _MAX, _SPAN)])
def test_value_doesnt_change_when_inside_range(test_value):
    value = Value(min_value=_MIN, max_value=_MAX, initialized_value=test_value)
    assert value.value == test_value


@pytest.mark.parametrize("test_value", [i for i in range(_MIN, _MAX - 3, _SPAN)])
def test_value_changes_when_changed_to_something_within_range(test_value):
    value = Value(min_value=_MIN, max_value=_MAX, initialized_value=test_value)
    assert value.value == test_value
    value.value = test_value + _SPAN
    assert value.value == test_value + _SPAN


@pytest.mark.parametrize("test_value", [i for i in range(_MIN, _MAX - 5, _SPAN)])
def test_value_changes_when_min_is_moved_above_value(test_value):
    value = Value(min_value=_MIN, max_value=_MAX, initialized_value=test_value)
    assert value.value == test_value
    value.min = test_value + _SPAN
    assert value.min == test_value + _SPAN
    assert value.value == test_value + _SPAN


@pytest.mark.parametrize("test_value", [i for i in range(_MIN + 5, _MAX, _SPAN)])
def test_value_changes_when_max_is_moved_below_value(test_value):
    value = Value(min_value=_MIN, max_value=_MAX, initialized_value=test_value)
    assert value.value == test_value
    value.max = test_value - _SPAN
    assert value.max == test_value - _SPAN
    assert value.value == test_value - _SPAN


@pytest.mark.parametrize("test_value", [i for i in range(_MIN, _MAX, _SPAN)])
def test_value_raises_when_min_is_greater_than_max(test_value):
    value = Value(
        min_value=test_value - _SPAN,
        max_value=test_value + _SPAN,
        initialized_value=test_value,
    )
    assert value.value == test_value
    with pytest.raises(ValueException):
        value.min = test_value + (_SPAN * 2)


@pytest.mark.parametrize("test_value", [i for i in range(_MIN, _MAX, _SPAN)])
def test_value_raises_when_max_is_less_than_min(test_value):
    value = Value(
        min_value=test_value - _SPAN,
        max_value=test_value + _SPAN,
        initialized_value=test_value,
    )
    assert value.value == test_value
    with pytest.raises(ValueException):
        value.max = test_value - (_SPAN * 2)


@pytest.mark.parametrize("test_value", [i for i in range(_MIN, _MAX, _SPAN)])
def test_value_percent(test_value):
    value = Value(min_value=_MIN, max_value=_MAX, initialized_value=test_value)
    assert value.value_percent == (test_value - _MIN) / (_MAX - _MIN)


@pytest.mark.parametrize("test_value", [i / 10 for i in range(0, 10, 1)])
def test_initialized_percent(test_value):
    _min = 100
    _max = 200
    print("abc123 ", test_value)
    value = Value(min_value=_min, max_value=_max, initialized_percent=test_value)
    assert value.value_percent == test_value
    assert value.value == (_max - _min) * test_value + _min
