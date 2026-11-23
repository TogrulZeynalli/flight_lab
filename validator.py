"""Row validation: airport list loading, single-row checks, record building."""

from datetime import datetime
import math
import re

FLIGHT_ID_RE = re.compile(r"^[A-Za-z0-9]{2,8}$")
AIRPORT_RE = re.compile(r"^[A-Z]{3}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def load_airports(path: str) -> set[str]:
    """Read an airport list file and return the set of codes.

    One code per line. Strip whitespace; skip blank lines and lines
    starting with '#'.
    """
    airports: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            airports.add(line)
    return airports


def _is_valid_datetime(value: str) -> bool:
    """Check that value matches YYYY-MM-DD HH:MM strictly and is a real calendar time."""
    if not DATETIME_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False


def validate_row(fields: list[str], airports: set[str]) -> str | None:
    """Check one CSV row (fields as returned by csv.reader, not yet stripped).

    Return None if the row is valid, otherwise the error code of the
    FIRST failing check (checks 1-11 in the specification, in order).
    Does not check for duplicates.
    """
    # 1. WRONG_FIELD_COUNT
    if len(fields) != 6:
        return "WRONG_FIELD_COUNT"

    stripped = [field.strip() for field in fields]

    # 2. MISSING_FIELD
    if any(val == "" for val in stripped):
        return "MISSING_FIELD"

    flight_id, origin, destination, dep_str, arr_str, price_str = stripped

    # 3. INVALID_FLIGHT_ID
    if not FLIGHT_ID_RE.match(flight_id):
        return "INVALID_FLIGHT_ID"

    # 4. INVALID_ORIGIN
    if not AIRPORT_RE.match(origin) or origin not in airports:
        return "INVALID_ORIGIN"

    # 5. INVALID_DESTINATION
    if not AIRPORT_RE.match(destination) or destination not in airports:
        return "INVALID_DESTINATION"

    # 6. SAME_ORIGIN_DESTINATION
    if origin == destination:
        return "SAME_ORIGIN_DESTINATION"

    # 7. INVALID_DEPARTURE
    if not _is_valid_datetime(dep_str):
        return "INVALID_DEPARTURE"

    # 8. INVALID_ARRIVAL
    if not _is_valid_datetime(arr_str):
        return "INVALID_ARRIVAL"

    # 9. ARRIVAL_NOT_AFTER_DEPARTURE
    dep_dt = datetime.strptime(dep_str, "%Y-%m-%d %H:%M")
    arr_dt = datetime.strptime(arr_str, "%Y-%m-%d %H:%M")
    if arr_dt <= dep_dt:
        return "ARRIVAL_NOT_AFTER_DEPARTURE"

    # 10. INVALID_PRICE
    try:
        price = float(price_str)
    except ValueError:
        return "INVALID_PRICE"

    if not math.isfinite(price):
        return "INVALID_PRICE"

    # 11. NON_POSITIVE_PRICE
    if price <= 0:
        return "NON_POSITIVE_PRICE"

    return None


def to_record(fields: list[str]) -> dict:
    """Turn a valid row into a flight record dictionary.

    Keys: flight_id, origin, destination, departure_datetime,
    arrival_datetime (stripped strings) and price (float).
    """
    stripped = [field.strip() for field in fields]
    return {
        "flight_id": stripped[0],
        "origin": stripped[1],
        "destination": stripped[2],
        "departure_datetime": stripped[3],
        "arrival_datetime": stripped[4],
        "price": float(stripped[5]),
    }