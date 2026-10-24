"""Offline NC13 origin-specific turn counts; runtime never reads this FZP."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics')]
from build_sc2001_corridor_calibration import wilson

CONTRACTS = {
    'SC1004_E': {
        'sources': {'58': 'SC1005_to_SC1004', '10498': 'SC1005_to_SC1004', '10501': 'SC107_to_SC1004'},
        'core': {'52'},
        'outcomes': {'10628': 'right', '47': 'right', '10629': 'through', '68': 'through', '10630': 'left', '67': 'left'},
        'decision': '1123', 'entry_connectors': {'SC1005_to_SC1004': '10498', 'SC107_to_SC1004': '10501'}},
    'SC107_W': {
        'sources': {'61': 'SC1005_to_SC107', '10499': 'SC1005_to_SC107', '10621': 'SC1004_to_SC107'},
        'core': {'387', '10614', '10615', '1220000201'},
        'outcomes': {'10622': 'left', '1220043300': 'left', '10023': 'through', '1220000402': 'through',
                     '10616': 'right', '381': 'right', '10607': 'right', '1': 'right'},
        'decision': '1061', 'entry_connectors': {'SC1005_to_SC107': '10499', 'SC1004_to_SC107': '10621'}}}


def scan_rows(rows):
    active = {group: {} for group in CONTRACTS}
    completed, censored = [], []
    for time, vehicle, link in rows:
        for group, contract in CONTRACTS.items():
            cohort = active[group].get(vehicle)
            if link in contract['sources']:
                source = contract['sources'][link]
                if cohort is None:
                    active[group][vehicle] = {'vehicle': vehicle, 'group': group, 'origin': source,
                                              'entered_sec': time, 'source_link': link, 'core_observed': False}
                elif cohort['origin'] != source:
                    raise ValueError('One uncompleted approach cohort changed physical origin')
                continue
            if cohort is None:
                continue
            if link in contract['core']:
                cohort['core_observed'] = True
                continue
            if link in contract['outcomes']:
                completed.append(dict(cohort, outcome=contract['outcomes'][link], outcome_link=link, outcome_sec=time))
            else:
                censored.append(dict(cohort, reason='unobserved_turn_or_left_reviewed_path', next_link=link, last_sec=time))
            del active[group][vehicle]
    for group in active.values():
        censored.extend(dict(row, reason='end_or_interior_disappearance') for row in group.values())
    return completed, censored


def fzp_rows(path):
    with path.open('rb') as handle:
        for raw_line in handle:
            if raw_line.startswith((b'*', b'$')) and not raw_line.startswith(b'$VEHICLE:'):
                continue
            line = raw_line.decode('ascii')
            if line.startswith('$VEHICLE:'):
                index = {name: i for i, name in enumerate(line.strip().split(':', 1)[1].split(';'))}
                continue
            if line.startswith(('$', '*')) or not line.strip():
                continue
            cells = line.strip().split(';')
            yield float(cells[index['SIMSEC']]), cells[index['NO']], cells[index['LANE\\LINK\\NO']]


def build():
    path = next((ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/vissim_eval').glob('*.fzp'))
    completed, censored = scan_rows(fzp_rows(path))
    base = json.loads((ROOT / 'diagnostics/physical_movement_routes_ver2.json').read_text(encoding='utf-8'))
    tree = ET.parse(ROOT / base['network']['path']).getroot()
    links = {row.get('no'): row for row in tree.findall('./links/link')}
    priors, positions = {}, {}
    for group, contract in CONTRACTS.items():
        decision = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{contract['decision']}']")
        for origin, connector in contract['entry_connectors'].items():
            merge = links[connector].find('toLinkEndPt')
            position = {'entry_connector': connector, 'entry_link': merge.get('lane').split()[0],
                        'entry_position_m': float(merge.get('pos')), 'decision': contract['decision'],
                        'decision_link': decision.get('link'), 'decision_position_m': float(decision.get('pos'))}
            position['decision_ahead_of_entry'] = (position['entry_link'] == position['decision_link']
                and position['entry_position_m'] <= position['decision_position_m'])
            positions[origin] = position
            counts = Counter(row['outcome'] for row in completed if row['origin'] == origin)
            lost = [row for row in censored if row['origin'] == origin]
            total = sum(counts.values())
            if not total:
                raise ValueError(f'No completed physical cohorts for {origin}')
            priors[origin] = {'counts': {turn: counts[turn] for turn in ['left', 'through', 'right']},
                'completed_denominator': total, 'censored_denominator': len(lost),
                'shares': {turn: counts[turn]/total for turn in ['left', 'through', 'right']},
                'wilson_95_intervals_conditional_on_completed': {turn: wilson(counts[turn], total) for turn in ['left', 'through', 'right']},
                'censoring_only_bounds': {turn: [counts[turn]/(total+len(lost)), (counts[turn]+len(lost))/(total+len(lost))] for turn in ['left', 'through', 'right']}}
    output = {'schema': 'dynamic-turn-offline-priors/v1', 'network': base['network'],
        'source': {'fzp_path': str(path.relative_to(ROOT)), 'sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest(),
                   'run_id': 'codex_nc_s13_6056c94_20260909_retry', 'seed': 13, 'sampling_sec': 5,
                   'window_sec': [1, 5396], 'runtime_reads_training_fzp': False},
        'priors': priors, 'native_decision_positions': positions,
        'completed_cohorts': completed, 'censored_cohorts': censored,
        'limitations': ['Frozen offline NC13 calibration-set priors; seed14 holdout validation remains required.',
            'Source and outcome are observed from the same vehicle; five-second sampling and censoring may bias completed-cohort ratios.',
            'Connector/receiver road outcome observations prove the physical branch; route intention is not queried.',
            'A sample zero is not a physical impossibility. No invented pseudocount is inserted.',
            'Native static route identities are used to validate topology only; applying their weights is not inferred from geometric reachability.']}
    (ROOT / 'diagnostics/dynamic_area_nc13_calibration.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps({'priors': priors, 'positions': positions}, indent=2))


if __name__ == '__main__':
    build()
