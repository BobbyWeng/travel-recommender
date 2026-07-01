#!/usr/bin/env python3
import json
import sys
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "destinations.json"

VALID_TAGS = {
    "city", "beach", "nature", "food", "museum", "nightlife", "relaxation",
    "hiking", "public_transport", "family", "budget", "music", "history",
    "coffee", "outdoor", "skiing", "architecture", "art", "shopping",
    "entertainment", "golf", "quirky", "sports", "culture", "technology",
    "boating", "theme_parks", "wildlife", "beer", "movie",
}

VALID_DEST_TYPES = {"city", "beach", "nature_gateway", "resort"}

REQUIRED_FIELDS = [
    "id", "city", "state", "country", "country_code", "iata_code",
    "latitude", "longitude", "timezone", "cost_level",
    "public_transport_score", "walkability_score", "tags", "active",
    "monthly_climate", "recommended_stay_days", "destination_type",
    "gateway_airports",
]


def validate():
    errors = []

    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} not found")
        return False

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    dests = data.get("destinations", [])
    if not dests:
        errors.append("No destinations found in file")

    if not (55 <= len(dests) <= 65):
        errors.append(f"Destination count {len(dests)} not in range 55-65")

    ids = [d["id"] for d in dests]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate destination IDs found")

    seen_iatas = set()
    for d in dests:
        city = d.get("city", "unknown")

        for field in REQUIRED_FIELDS:
            if field not in d:
                errors.append(f"{city}: missing required field '{field}'")

        iata = d.get("iata_code", "")
        if len(iata) != 3 or not iata.isupper():
            errors.append(f"{city}: IATA code '{iata}' is not 3 uppercase letters")

        if iata in seen_iatas:
            errors.append(f"{city}: duplicate IATA code '{iata}'")
        seen_iatas.add(iata)

        lat = d.get("latitude")
        lon = d.get("longitude")
        if lat is not None and not (-90 <= lat <= 90):
            errors.append(f"{city}: latitude {lat} out of range")
        if lon is not None and not (-180 <= lon <= 180):
            errors.append(f"{city}: longitude {lon} out of range")

        cost = d.get("cost_level")
        if cost is not None and not (1 <= cost <= 5):
            errors.append(f"{city}: cost_level {cost} out of range 1-5")

        transport = d.get("public_transport_score")
        if transport is not None and not (1 <= transport <= 10):
            errors.append(f"{city}: public_transport_score {transport} out of range 1-10")

        walk = d.get("walkability_score")
        if walk is not None and not (1 <= walk <= 10):
            errors.append(f"{city}: walkability_score {walk} out of range 1-10")

        for tag in d.get("tags", []):
            if tag not in VALID_TAGS:
                errors.append(f"{city}: invalid tag '{tag}'")

        dest_type = d.get("destination_type")
        if dest_type and dest_type not in VALID_DEST_TYPES:
            errors.append(f"{city}: invalid destination_type '{dest_type}'")

        tz = d.get("timezone", "")
        valid_prefixes = ("America/", "Pacific/", "US/")
        if tz and not any(tz.startswith(p) for p in valid_prefixes):
            errors.append(f"{city}: invalid timezone '{tz}'")

        gateways = d.get("gateway_airports", [])
        if not gateways:
            errors.append(f"{city}: no gateway airports")
        else:
            iatas = [g["iata"] for g in gateways]
            if d.get("iata_code") and d["iata_code"] not in iatas:
                errors.append(f"{city}: primary IATA not in gateway_airports")
            if len(iatas) != len(set(iatas)):
                errors.append(f"{city}: duplicate gateway IATA codes")

        stay = d.get("recommended_stay_days", 0)
        if not (1 <= stay <= 14):
            errors.append(f"{city}: recommended_stay_days {stay} out of range 1-14")

        climates = d.get("monthly_climate", [])
        months = {c.get("month") for c in climates}
        if months != set(range(1, 13)):
            errors.append(f"{city}: climate data has months {months}, expected 1-12")

        for c in climates:
            m = c.get("month", "?")
            temp = c.get("temp_avg_c")
            if temp is not None and not (-40 <= temp <= 45):
                errors.append(f"{city}: month {m} temp_avg_c {temp} out of range")
            precip_days = c.get("precip_days")
            if precip_days is not None and not (0 <= precip_days <= 31):
                errors.append(f"{city}: month {m} precip_days {precip_days} out of range")
            precip_mm = c.get("precip_mm")
            if precip_mm is not None and precip_mm < 0:
                errors.append(f"{city}: month {m} precip_mm {precip_mm} negative")

    if errors:
        print(f"Validation failed with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return False

    print(f"All validations passed ({len(dests)} destinations checked)")
    return True


if __name__ == "__main__":
    sys.exit(0 if validate() else 1)
