"""Running queries against the flight database."""

from datetime import datetime
import math
import re

DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

RECORD_KEYS = {
    "flight_id",
    "origin",
    "destination",
    "departure_datetime",
    "arrival_datetime",
    "price",
}

ALLOWED_QUERY_KEYS = RECORD_KEYS | {"min_price", "sort_by", "order", "limit"}


def _is_valid_datetime(value: object) -> bool:
    if not isinstance(value, str) or not DATETIME_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False


def _is_number(value: object) -> bool:
    # In Python, bool is a subclass of int; booleans are explicitly not numbers here
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_query(query: dict) -> bool:
    if not isinstance(query, dict):
        return False

    # Unknown keys
    if any(k not in ALLOWED_QUERY_KEYS for k in query):
        return False

    # String equality keys
    for key in ("flight_id", "origin", "destination"):
        if key in query and not isinstance(query[key], str):
            return False

    # Datetime range keys
    for key in ("departure_datetime", "arrival_datetime"):
        if key in query and not _is_valid_datetime(query[key]):
            return False

    # Numeric price filters
    for key in ("price", "min_price"):
        if key in query and not _is_number(query[key]):
            return False

    # Sorting options
    if "order" in query and "sort_by" not in query:
        return False

    if "sort_by" in query:
        if not isinstance(query["sort_by"], str) or query["sort_by"] not in RECORD_KEYS:
            return False

    if "order" in query:
        if query["order"] not in ("asc", "desc"):
            return False

    # Limit
    if "limit" in query:
        if not _is_int(query["limit"]) or query["limit"] < 0:
            return False

    return True


def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object.

    Valid query:   {"query": query, "matches": [...]}
    Invalid query: {"query": query, "error": "INVALID_QUERY", "matches": []}
    """
    if not _validate_query(query):
        return {
            "query": query,
            "error": "INVALID_QUERY",
            "matches": [],
        }

    matches: list[dict] = []
    for flight in db:
        if "flight_id" in query and flight["flight_id"] != query["flight_id"]:
            continue
        if "origin" in query and flight["origin"] != query["origin"]:
            continue
        if "destination" in query and flight["destination"] != query["destination"]:
            continue
        if (
            "departure_datetime" in query
            and flight["departure_datetime"] < query["departure_datetime"]
        ):
            continue
        if (
            "arrival_datetime" in query
            and flight["arrival_datetime"] > query["arrival_datetime"]
        ):
            continue
        if "price" in query and flight["price"] > query["price"]:
            continue
        if "min_price" in query and flight["price"] < query["min_price"]:
            continue
        matches.append(flight)

    if "sort_by" in query:
        sort_key = query["sort_by"]
        reverse = query.get("order", "asc") == "desc"
        matches = sorted(matches, key=lambda rec: rec[sort_key], reverse=reverse)

    if "limit" in query:
        matches = matches[: query["limit"]]

    return {
        "query": query,
        "matches": matches,
    }


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if isinstance(queries, dict):
        query_list = [queries]
    else:
        query_list = queries
    return [run_query(db, q) for q in query_list]