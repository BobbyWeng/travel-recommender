import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "destinations.json"

VALID_TAGS = {
    "city", "beach", "nature", "food", "museum", "nightlife", "relaxation",
    "hiking", "public_transport", "family", "budget", "music", "history",
    "coffee", "outdoor", "skiing", "architecture", "art", "shopping",
    "entertainment", "golf", "quirky", "sports", "culture", "technology",
    "boating", "theme_parks", "wildlife", "beer", "movie",
}

VALID_DEST_TYPES = {"city", "beach", "nature_gateway", "resort"}


def _load_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_destination_count():
    data = _load_data()
    dests = data["destinations"]
    assert 55 <= len(dests) <= 65


def test_unique_ids():
    data = _load_data()
    ids = [d["id"] for d in data["destinations"]]
    assert len(ids) == len(set(ids))


def test_iata_format():
    data = _load_data()
    for d in data["destinations"]:
        assert len(d["iata_code"]) == 3, f"{d['city']} IATA not 3 chars"
        assert d["iata_code"].isupper(), f"{d['city']} IATA not uppercase"


def test_coordinate_ranges():
    data = _load_data()
    for d in data["destinations"]:
        assert -90 <= d["latitude"] <= 90, f"{d['city']} lat out of range"
        assert -180 <= d["longitude"] <= -60, f"{d['city']} lon out of US range"


def test_twelve_months_climate():
    data = _load_data()
    for d in data["destinations"]:
        months = {c["month"] for c in d["monthly_climate"]}
        assert months == set(range(1, 13)), f"{d['city']} missing months"


def test_cost_level_range():
    data = _load_data()
    for d in data["destinations"]:
        assert 1 <= d["cost_level"] <= 5, f"{d['city']} cost_level {d['cost_level']}"


def test_transport_score_range():
    data = _load_data()
    for d in data["destinations"]:
        assert 1 <= d["public_transport_score"] <= 10, f"{d['city']} transport {d['public_transport_score']}"
        assert 1 <= d["walkability_score"] <= 10, f"{d['city']} walk {d['walkability_score']}"


def test_valid_tags():
    data = _load_data()
    for d in data["destinations"]:
        for tag in d["tags"]:
            assert tag in VALID_TAGS, f"{d['city']} has invalid tag: {tag}"


def test_destination_type_valid():
    data = _load_data()
    for d in data["destinations"]:
        assert d.get("destination_type") in VALID_DEST_TYPES, f"{d['city']} invalid type: {d.get('destination_type')}"


def test_gateway_airports_structure():
    data = _load_data()
    for d in data["destinations"]:
        gateways = d.get("gateway_airports", [])
        assert len(gateways) >= 1, f"{d['city']} no gateway airports"
        iatas = [g["iata"] for g in gateways]
        assert d["iata_code"] in iatas, f"{d['city']} primary IATA not in gateways"
        assert len(iatas) == len(set(iatas)), f"{d['city']} duplicate gateway IATAs"


def test_timezone_valid():
    data = _load_data()
    valid_prefixes = ("America/", "Pacific/", "US/")
    for d in data["destinations"]:
        tz = d.get("timezone", "")
        assert any(tz.startswith(p) for p in valid_prefixes), f"{d['city']} invalid timezone: {tz}"


def test_recommended_stay_days():
    data = _load_data()
    for d in data["destinations"]:
        stay = d.get("recommended_stay_days", 0)
        assert 1 <= stay <= 14, f"{d['city']} stay days {stay}"


def test_climate_data_reasonable():
    data = _load_data()
    for d in data["destinations"]:
        for c in d["monthly_climate"]:
            assert -40 <= c["temp_avg_c"] <= 45, f"{d['city']} month {c['month']} temp {c['temp_avg_c']}"
            assert 0 <= c["precip_days"] <= 31, f"{d['city']} month {c['month']} precip_days"
            assert c["precip_mm"] >= 0, f"{d['city']} month {c['month']} precip_mm negative"
