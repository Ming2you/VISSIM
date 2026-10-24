"""Read-only, position-aware SC2001 outlet topology and observed FZP cohorts."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def network_audit():
    path = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    tree = ET.parse(path).getroot()
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    merge = links['10703'].find('toLinkEndPt')
    entry = float(merge.get('pos'))
    branches = []
    for connector in ['10704', '10484', '10774']:
        link = links[connector]
        source = link.find('fromLinkEndPt')
        target = link.find('toLinkEndPt')
        branches.append({'connector': connector, 'source_link': source.get('lane').split()[0],
            'source_pos': float(source.get('pos')), 'target_link': target.get('lane').split()[0],
            'direction': link.get('direction'), 'first_source_lane': int(source.get('lane').split()[1]),
            'lanes': len(link.findall('./lanes/lane')), 'ahead_of_sc2001_entry': float(source.get('pos')) >= entry})
    decisions = {}
    for key in ['1141', '1142', '1143', '1137']:
        node = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{key}']")
        rows = []
        for route in node.findall('./vehRoutSta/vehicleRouteStatic'):
            rows.append({**route.attrib, 'path': [node.get('link')] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]})
        decisions[key] = {**node.attrib, 'routes': rows}
    return {'network': {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()},
            'sc2001_entry_on_31_pos_m': entry, 'branches': branches, 'native_decisions': decisions,
            'decision_1137_is_ahead_of_entry': float(decisions['1137']['pos']) >= entry,
            'rule_source': 'https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Strassennetz_Verb_str_Attr.htm',
            'rule': 'PTV2020 documents no-route vehicles following the next ALL connector; no equal/default route split is assumed here.'}


def scan(fzp):
    active, upstream = {}, {}
    counts, lanes, traces = Counter(), Counter(), Counter()
    outcomes = []
    with fzp.open(encoding='utf-8-sig', errors='replace') as handle:
        for line in handle:
            if line.startswith('$VEHICLE:'):
                names = line.split(':', 1)[1].strip().split(';')
                index = {key: names.index(key) for key in ['SIMSEC', 'NO', 'LANE\\LINK\\NO', 'LANE\\INDEX', 'POS']}
                continue
            if line.startswith(('*', '$')) or not line.strip():
                continue
            cells = line.strip().split(';')
            vehicle, link = cells[index['NO']], cells[index['LANE\\LINK\\NO']]
            if link in {'76', '80', '84', '85'}:
                upstream[vehicle] = link
            if link == '78' and vehicle not in active:
                active[vehicle] = {'vehicle': vehicle, 'source': upstream.get(vehicle, 'unobserved'),
                    'entered_78_sec': float(cells[index['SIMSEC']]), 'first_78_lane': cells[index['LANE\\INDEX']],
                    'trace': [], 'last_31_lane': None}
            row = active.get(vehicle)
            if row is None:
                continue
            if not row['trace'] or row['trace'][-1] != link:
                row['trace'].append(link)
            if link == '31':
                row['last_31_lane'] = cells[index['LANE\\INDEX']]
                row['last_31_pos_m'] = float(cells[index['POS']])
            result = ('R_D_E' if link in {'10484', '24'} else 'R_D_W' if link in {'10480', '26'} else
                      'outside_125' if link in {'10775', '125'} else 'returned_79' if link in {'10704', '79'} else None)
            if result:
                row['outcome'] = result; row['outcome_sec'] = float(cells[index['SIMSEC']])
                row['outcome_evidence'] = 'observed_connector' if link in {'10484', '10480', '10775', '10704'} else 'observed_receiver_road'
                counts[(row['source'], result)] += 1
                lanes[(row['first_78_lane'], row['last_31_lane'], result)] += 1
                traces[tuple(row['trace'])] += 1
                outcomes.append(row)
                del active[vehicle]
    return {'fzp': str(fzp), 'counts': [{'source': a, 'outcome': b, 'vehicles': count} for (a, b), count in counts.items()],
            'lane_counts': [{'first_78_lane': a, 'last_31_lane': b, 'outcome': c, 'vehicles': count} for (a, b, c), count in lanes.items()],
            'observed_paths': [{'path': list(path), 'vehicles': count} for path, count in traces.most_common()],
            'unresolved_or_censored_cohorts': list(active.values()), 'completed_cohorts': outcomes,
            'limits': 'Retrospective diagnostic only. Five-second sampling misses some short links/lane changes; observed outcomes are not a native route prior or future controller input.'}


if __name__ == '__main__':
    run = ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry'
    output = {'topology': network_audit(), 'observations': scan(next((run / 'vissim_eval').glob('*.fzp')))}
    (ROOT / 'diagnostics/sc2001_corridor_audit.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps({'branches': output['topology']['branches'], 'counts': output['observations']['counts'],
                      'lanes': output['observations']['lane_counts'], 'unresolved': len(output['observations']['unresolved_or_censored_cohorts'])}, indent=2))
