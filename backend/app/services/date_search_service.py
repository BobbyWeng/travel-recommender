from datetime import date, timedelta

from app.schemas.search import DateCombo


def generate_date_combinations(
    preferred_date: date,
    flexibility_days: int,
    trip_length_min: int,
    trip_length_max: int,
) -> list[DateCombo]:
    if trip_length_min > trip_length_max:
        raise ValueError("trip_length_min 不能大于 trip_length_max")

    combos: list[DateCombo] = []
    seen: set[tuple[date, date]] = set()

    start_range = preferred_date - timedelta(days=flexibility_days)
    end_range = preferred_date + timedelta(days=flexibility_days)

    current_depart = start_range
    while current_depart <= end_range:
        for nights in range(trip_length_min, trip_length_max + 1):
            return_date = current_depart + timedelta(days=nights)
            key = (current_depart, return_date)
            if key not in seen:
                seen.add(key)
                combos.append(
                    DateCombo(
                        departure_date=current_depart,
                        return_date=return_date,
                        nights=nights,
                    )
                )
        current_depart += timedelta(days=1)

    combos.sort(key=lambda c: (c.departure_date, c.nights))
    return combos
