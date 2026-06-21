import json
from copy import deepcopy
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"
EVENTS_PATH = DATASETS_DIR / "events.json"

_MAP_KEYS = [
    "event",
    "risk_analysis",
    "junctions",
    "critical_zones",
    "deployment",
    "infrastructure",
    "diversions",
    "emergency_corridors",
    "alerts",
]


def _default_map_payload():
    # Fallback map payload keeps dashboard layers stable when source files are empty.
    return {
        "event": {
            "name": "City Event",
            "type": "General",
            "venue": {
                "name": "City Center",
                "lat": 12.9788,
                "lon": 77.5996,
            },
            "impact_radius": 1000,
        },
        "risk_analysis": {
            "score": 0,
            "level": "Low",
            "affected_junctions": 0,
            "critical_junctions": 0,
        },
        "junctions": [],
        "critical_zones": [],
        "deployment": {
            "officers": [],
            "barricades": [],
        },
        "infrastructure": {
            "hospitals": [],
            "schools": [],
            "fire_stations": [],
            "police_stations": [],
        },
        "diversions": [],
        "emergency_corridors": [],
        "alerts": [],
    }


def _read_json(path):
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4)


def _build_base_union_document():
    base = _default_map_payload()
    base["events"] = []
    return base


def normalize_events_document(payload):
    base = _build_base_union_document()

    if isinstance(payload, list):
        base["events"] = payload
        return base

    if not isinstance(payload, dict):
        return base

    merged = deepcopy(base)

    for key, value in payload.items():
        merged[key] = value

    events_value = payload.get("events")
    if isinstance(events_value, list):
        merged["events"] = events_value
    elif not isinstance(merged.get("events"), list):
        merged["events"] = []

    return merged


def load_events_document():
    raw_payload = _read_json(EVENTS_PATH)
    normalized_payload = normalize_events_document(raw_payload)

    if raw_payload != normalized_payload:
        _write_json(EVENTS_PATH, normalized_payload)

    return normalized_payload


def append_event(event_data):
    payload = load_events_document()
    payload["events"].append(event_data)
    _write_json(EVENTS_PATH, payload)


def save_event_records(event_records):
    payload = load_events_document()
    payload["events"] = event_records if isinstance(event_records, list) else []
    _write_json(EVENTS_PATH, payload)
