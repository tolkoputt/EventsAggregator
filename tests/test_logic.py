import pytest

from eventsaggregator.services.logic import is_valid_seat


@pytest.mark.parametrize(
    ("pattern", "seat", "expected"),
    [
        ("A1-10,B1-5", "A1", True),
        ("A1-10,B1-5", "A10", True),
        ("A1-10,B1-5", "A11", False),
        ("A1-10,B1-5", "B5", True),
        ("A1-10,B1-5", "B6", False),
        ("A1-10,B1-5", "C1", False),
        ("A1-10,B1-5", "A0", False),
    ],
)
def test_is_valid_seat(pattern, seat, expected):
    assert is_valid_seat(pattern, seat) is expected
