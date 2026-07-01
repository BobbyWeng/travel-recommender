from datetime import date

from app.services.date_search_service import generate_date_combinations


def test_basic_generation():
    combos = generate_date_combinations(
        preferred_date=date(2026, 9, 20),
        flexibility_days=5,
        trip_length_min=4,
        trip_length_max=6,
    )
    assert len(combos) > 0
    for c in combos:
        assert c.nights >= 4
        assert c.nights <= 6
        assert (c.return_date - c.departure_date).days == c.nights


def test_no_flexibility():
    combos = generate_date_combinations(
        preferred_date=date(2026, 9, 20),
        flexibility_days=0,
        trip_length_min=5,
        trip_length_max=5,
    )
    assert len(combos) == 1
    assert combos[0].departure_date == date(2026, 9, 20)
    assert combos[0].return_date == date(2026, 9, 25)
    assert combos[0].nights == 5


def test_flex_1_nights_range():
    combos = generate_date_combinations(
        preferred_date=date(2026, 9, 20),
        flexibility_days=1,
        trip_length_min=3,
        trip_length_max=4,
    )
    assert len(combos) == 6
    dates = {(c.departure_date, c.return_date) for c in combos}
    assert (date(2026, 9, 19), date(2026, 9, 22)) in dates
    assert (date(2026, 9, 20), date(2026, 9, 23)) in dates
    assert (date(2026, 9, 21), date(2026, 9, 24)) in dates
    assert (date(2026, 9, 19), date(2026, 9, 23)) in dates
    assert (date(2026, 9, 20), date(2026, 9, 24)) in dates
    assert (date(2026, 9, 21), date(2026, 9, 25)) in dates


def test_no_duplicates():
    combos = generate_date_combinations(
        preferred_date=date(2026, 9, 20),
        flexibility_days=5,
        trip_length_min=4,
        trip_length_max=6,
    )
    seen = set()
    for c in combos:
        key = (c.departure_date, c.return_date)
        assert key not in seen, f"重复: {key}"
        seen.add(key)


def test_sorted_order():
    combos = generate_date_combinations(
        preferred_date=date(2026, 9, 20),
        flexibility_days=3,
        trip_length_min=4,
        trip_length_max=5,
    )
    for i in range(len(combos) - 1):
        assert combos[i].departure_date <= combos[i + 1].departure_date


def test_invalid_range():
    try:
        generate_date_combinations(
            preferred_date=date(2026, 9, 20),
            flexibility_days=0,
            trip_length_min=6,
            trip_length_max=4,
        )
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_expected_count():
    combos = generate_date_combinations(
        preferred_date=date(2026, 9, 20),
        flexibility_days=5,
        trip_length_min=4,
        trip_length_max=6,
    )
    expected = 11 * 3
    assert len(combos) == expected, f"期望 {expected}，实际 {len(combos)}"
