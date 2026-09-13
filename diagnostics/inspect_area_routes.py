from pathlib import Path
import json
import xml.etree.ElementTree as ET
import sys
ROOT = Path(__file__).resolve().parents[1]
physical = json.loads((ROOT / 'diagnostics/control_area_membership.json').read_text(encoding='utf-8'))
tree = ET.parse(ROOT / physical['network']['path']).getroot()
links = {x.get('no'): x for x in tree.findall('./links/link')}
heads = {}
for h in tree.findall('.//signalHead'):
    lane = h.get('lane', '').split()
    if lane:
        heads.setdefault(lane[0], []).append(dict(h.attrib))
adj = {}
for key, e in links.items():
    f, t = e.find('fromLinkEndPt'), e.find('toLinkEndPt')
    if f is not None:
        adj.setdefault(f.get('lane').split()[0], []).append((key, t.get('lane').split()[0]))
starts = sys.argv[1:] or ['1220042300', '100', '1220008501']
if starts and starts[0].startswith('in_'):
    tuning = json.loads((ROOT / 'evaluation/configs/n21_n7_20260908.json').read_text(encoding='utf-8'))
    detectors = json.loads((ROOT / tuning['detector_mapping_json']).read_text(encoding='utf-8'))
    starts = [k for k, v in detectors['link_to_origins'].items() if starts[0] in v]
for start in starts:
    frontier = [(start, [])]
    visited = set()
    print('START', start)
    for _ in range(5):
        new = []
        for link, path in frontier:
            if link in visited:
                continue
            visited.add(link)
            print(json.dumps({'link': link, 'path': path, 'heads': heads.get(link, []), 'next': adj.get(link, [])}))
            if heads.get(link) and link != start:
                continue
            for conn, target in adj.get(link, []):
                new.append((target, path + [link, conn]))
        frontier = new
