"""Validated opt-in physical cell lengths; no traffic dynamics or grid inference."""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping


def content_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def geometry_fingerprint(geometry):
    """Ignore seed, controls, cell partition and demand; pin physical attachments."""
    chains = {road: [{k: row[k] for k in ("link", "offset_m", "length_m", "lanes")}
                     for row in rows] for road, rows in geometry["chains"].items()}
    fields = ("id", "kind", "road", "connector", "from_link", "to_link",
              "from_pos_m", "to_pos_m", "chain_pos_m", "length_m", "lanes", "input_no")
    ports = [{k: row[k] for k in fields if k in row}
             for row in sorted(geometry["boundaries"], key=lambda x: x["id"])]
    return content_sha256({"chains": chains, "ports": ports})


def validate_profile(document):
    if document.get("schema") != "freeway-physical-cell-geometry/v1":
        raise ValueError("Unsupported physical freeway geometry profile")
    roads = document["roads"]
    if set(roads) != {"FW_E", "FW_W"}:
        raise ValueError("Physical geometry requires both freeway directions")
    for road, row in roads.items():
        edges, lengths, lanes = (row[k] for k in
                                ("segment_bounds_m", "segment_lengths_km", "segment_lanes"))
        if len(edges) != 22 or len(lengths) != 21 or len(lanes) != 21 or edges[0] != 0:
            raise ValueError("Physical geometry requires 21 ordered cells: " + road)
        if not all(math.isfinite(float(v)) for v in edges + lengths + lanes):
            raise ValueError("Non-finite physical geometry: " + road)
        for a, b, length, lane in zip(edges, edges[1:], lengths, lanes):
            if (b <= a or length <= 0 or lane <= 0 or int(lane) != lane
                    or abs((b-a)/1000-length) > 1e-10):
                raise ValueError("Inconsistent physical cell length/lanes: " + road)
    return document


def cell_lengths_km(net, link, count):
    """Return the exact lengths used in continuity; absent opt-in is legacy."""
    if not getattr(net, "freeway_variable_cell_lengths", False):
        return [net.freeway_segment_length_km] * count
    profiles = getattr(net, "freeway_segment_length_profile_km", None)
    if not isinstance(profiles, Mapping):
        raise ValueError("Variable-cell continuity requires an explicit length profile")
    values = profiles.get(str(link))
    if not isinstance(values, (list, tuple)) or len(values) != count:
        raise ValueError("Variable-cell profile does not cover all cells: " + str(link))
    values = list(map(float, values))
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("Variable-cell lengths must be finite and positive")
    return values
