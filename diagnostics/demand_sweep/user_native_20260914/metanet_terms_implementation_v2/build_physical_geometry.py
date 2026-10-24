"""Build a 21-cell grid from saved physical geometry, without reading traffic."""
from __future__ import annotations

import bisect
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.freeway_geometry import content_sha256, geometry_fingerprint, validate_profile


def build(geometry, mapping):
    roads = {}
    for road, chain in geometry["chains"].items():
        end = float(geometry["bounds"][road][-1])
        sections = []
        for part in chain:
            lane = int(part["lanes"])
            if not sections or sections[-1]["lanes"] != lane:
                sections.append({"start_m": float(part["offset_m"]), "lanes": lane})
        for i, section in enumerate(sections):
            section["end_m"] = sections[i+1]["start_m"] if i+1 < len(sections) else end
            section["ideal_cells"] = 21*(section["end_m"]-section["start_m"])/end
            section["cells"] = math.floor(section["ideal_cells"])
        for i in sorted(range(len(sections)), key=lambda i: sections[i]["ideal_cells"]-sections[i]["cells"], reverse=True)[:21-sum(s["cells"] for s in sections)]:
            sections[i]["cells"] += 1
        edges, lanes = [0.0], []
        for section in sections:
            n = section["cells"]
            if n < 1:
                raise ValueError("Lane section is too short for the retained 21-cell grid")
            length = (section["end_m"]-section["start_m"])/n
            if length < 400:
                raise ValueError("Grid would contain a cell shorter than 400m")
            edges.extend(section["start_m"]+length*i for i in range(1, n))
            edges.append(section["end_m"])
            lanes.extend([section["lanes"]]*n)
        lengths = [(b-a)/1000 for a,b in zip(edges, edges[1:])]
        roads[road] = {"segment_bounds_m": edges, "segment_lengths_km": lengths,
                       "segment_lanes": lanes, "lane_sections": sections}
    ports = copy.deepcopy(geometry["boundaries"])
    for port in ports:
        cell = min(20, bisect.bisect_right(roads[port["road"]]["segment_bounds_m"], port["chain_pos_m"])-1)
        field = "from_cell" if port["kind"] == "offramp" else "to_cell"
        port["previous_cell"] = port[field]
        port[field] = cell
    profile = {"schema": "freeway-physical-cell-geometry/v1", "cell_index_base": 0,
        "source_network": geometry["network"], "source_mapping": geometry["mapping"],
        "source_mapping_content_sha256": content_sha256(mapping),
        "physical_geometry_sha256": geometry_fingerprint(geometry),
        "roads": roads, "ports": ports,
        "policy": "21 cells per direction; each constant-lane section partitioned uniformly; physical lane changes are exact cell edges. Native network/DSD/input/route/signal values are unchanged.",
        "supported_scope": "canonical freeway component; full local follower requires a variable-length kernel before enabling GNE"}
    return validate_profile(profile)


def main():
    source = HERE.parent/'metanet_calibration_v1/seed13_observations/geometry.json'
    geometry = json.loads(source.read_text(encoding='utf-8'))
    mapping = json.loads(Path(geometry['mapping']['path']).read_text(encoding='utf-8-sig'))
    profile = build(geometry, mapping)
    profile['source_geometry_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    target = HERE/'physical_geometry21_v1.json'
    with target.open('x',encoding='utf-8') as stream:
        json.dump(profile,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps({'profile': str(target), 'physical_geometry_sha256': profile['physical_geometry_sha256'],
                      'roads': {road: {'cells':len(row['segment_lanes']), 'min_m':min(row['segment_lengths_km'])*1000,
                                      'max_m':max(row['segment_lengths_km'])*1000,
                                      'lane_sections':row['lane_sections']} for road,row in profile['roads'].items()}},ensure_ascii=False))


if __name__ == '__main__':
    main()
