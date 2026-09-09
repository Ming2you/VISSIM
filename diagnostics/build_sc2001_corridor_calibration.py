"""Freeze offline NC13 route evidence; never imported by a controller runtime."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def wilson(success, count):
    z = 1.959963984540054
    p = success / count
    mid = (p + z*z/(2*count)) / (1+z*z/count)
    half = z*math.sqrt(p*(1-p)/count + z*z/(4*count*count)) / (1+z*z/count)
    return [max(0., mid-half), min(1., mid+half)]


def build():
    audit = ROOT / 'diagnostics/sc2001_corridor_audit.json'
    source = json.loads(audit.read_text(encoding='utf-8'))
    observations = source['observations']
    fzp = Path(observations['fzp'])
    outcomes = ['R_D_E', 'R_D_W', 'outside_125']
    groups = {'W': ['76'], 'N': ['80'], 'E_SC2002': ['84', '85'],
              'initial_unknown_origin': ['76', '80', '84', '85']}
    priors = {}
    for origin, physical in groups.items():
        counts = Counter(row['outcome'] for row in observations['completed_cohorts'] if row['source'] in physical)
        censored = [row for row in observations['unresolved_or_censored_cohorts'] if row['source'] in physical]
        denominator = sum(counts.values())
        if set(counts) - set(outcomes) or not denominator:
            raise ValueError('Unexpected or empty calibration outcomes')
        priors[origin] = {'physical_sources': physical, 'completed_denominator': denominator,
            'counts': {key: counts[key] for key in outcomes}, 'shares': {key: counts[key]/denominator for key in outcomes},
            'unresolved_or_censored': len(censored), 'censored_vehicle_ids': [row['vehicle'] for row in censored],
            'wilson_95_intervals_conditional_on_completed': {key: wilson(counts[key], denominator) for key in outcomes},
            'censoring_only_share_bounds': {key: [counts[key]/(denominator+len(censored)),
                (counts[key]+len(censored))/(denominator+len(censored))] for key in outcomes}}
    if sum(row['completed_denominator'] for key, row in priors.items() if key != 'initial_unknown_origin') != len(observations['completed_cohorts']):
        raise ValueError('Calibration has unclassified positive cohorts')
    shared = json.loads((ROOT / 'diagnostics/shared_approach_ver2.json').read_text(encoding='utf-8'))
    tree = ET.parse(ROOT / source['topology']['network']['path']).getroot()
    inputs = [{**row.attrib, 'intervals': [x.attrib for x in row.findall('./timeIntVehVols/timeIntervalVehVolume')]}
              for row in tree.findall('./vehicleInputs/vehicleInput') if row.get('link') in {'76', '80', '84', '85', '78', '31', '124'}]
    document = {'schema': 'sc2001-corridor/v1', 'network': source['topology']['network'],
        'storage': 'SC2001_S_out', 'initial_physical_links': ['78', '10703'],
        'jam_source': shared['jam_source'],
        'native_input_evidence': {'inputs': inputs, 'new_demand_added_by_corridor': False,
            'note': '1106 on80 and1107 on76 already feed existing gates. No native input is placed on78/31/124. Source84 comes from upstreamSC2002. This module routes accepted existing movement flow only.'},
        'native_upstream_routes': {key: source['topology']['native_decisions'][key] for key in ['1141', '1142', '1143']},
        'calibration': {'kind': 'offline_empirical_completed_cohort_prior', 'run_id': 'codex_nc_s13_6056c94_20260909_retry',
            'simulation_seed': 13, 'policy': 'NC', 'sampling_sec': 5,
            'window_sec': [1, 5396], 'audit_path': str(audit.relative_to(ROOT)),
            'audit_sha256': hashlib.sha256(audit.read_bytes()).hexdigest(),
            'fzp_path': str(fzp.relative_to(ROOT)), 'fzp_sha256': hashlib.file_digest(fzp.open('rb'), 'sha256').hexdigest(),
            'runtime_reads_training_fzp': False, 'priors': priors,
            'same_seed_evaluation': 'Exploratory calibration-set result; seed14 is reserved for holdout validation.',
            'zero_count_semantics': 'Empirical zero from this calibration sample, not physical impossibility; Wilson upper bounds remain positive.',
            'rare_branch': 'Only three completed R_D_W observations, all from84; source-conditional uncertainty is high.'},
        'incoming_movements': {
            'SC2001_W_to_S': {'origin': 'W', 'physical_source': '76', 'entry_connector': '10723', 'native_decision': '1141', 'native_route': '3'},
            'SC2001_N_to_S': {'origin': 'N', 'physical_source': '80', 'entry_connector': '10721', 'native_decision': '1142', 'native_route': '2'},
            'SC2001_E_SC2002_to_S': {'origin': 'E_SC2002', 'physical_source': '84', 'entry_connector': '10726', 'native_decision': '1143', 'native_route': '3'}},
        'branches': {
            'R_D_E': {'path': ['78', '10703', '31', '10484'], 'target_kind': 'ramp', 'target': 'R_D_E'},
            'R_D_W': {'path': ['78', '10703', '31', '10774', '124', '10480'], 'target_kind': 'ramp', 'target': 'R_D_W'},
            'outside_125': {'path': ['78', '10703', '31', '10774', '124', '10775'], 'target_kind': 'external', 'target': None}},
        'excluded_native_prior': {'decision': '1137', 'decision_position_on_31_m': 28.5473612813,
            'entry_10703_position_on_31_m': source['topology']['sc2001_entry_on_31_pos_m'],
            'unreachable_return_connector': '10704', 'reason': 'Both decision1137 and return79 divergence are upstream of the78 merge position.'},
        'limitations': [
            'Full NC seed13 FZP was used only offline to estimate these frozen constants. No current control-run future observations are read at runtime.',
            'Five-second observations select completed, observed78 cohorts. Eight lost/end-censored cohorts and all denominators are retained; sampling and survival bias remain.',
            'Incoming accepted movements retain W/N/E_SC2002 origin. Initial78/10703 origin is unobserved and uses the explicitly pooled calibration prior.',
            'Existing31/124 stocks are not split using guessed origin and their capacity is not duplicated. New SC2001 cohorts remain in source78 storage throughout post78 branch travel.',
            'Capacity uses physical78 length and two lanes only. This conservative spatial aggregation can cause upstream spillback too early and does not reproduce local31/124 occupancy or lane changes.',
            'Each destination has its own FIFO cohorts. Shared two-lane source service and physical branch connector lane capacities constrain accepted transfers; full cross-lane FIFO blocking is not simulated.',
            'Existing31 traffic and SC2001 traffic share actual finite ramp receiving queues. Exterior125 downstream congestion is represented only by the existing finite boundary service capacity.',
            'Measured initial speed/position and the existing urban speed floor set travel delay; these do not predict subsequent within-corridor shockwaves.',
            'Incoming turn connectors10723/10721/10726 are outsideOmega. Their short travel is represented in receiving78 stock after accepted movement, so modeled area entry timing is advanced by that connector travel; this is the existing receiving-stock timing approximation.',
            'The learned zero W branch in sources76/80 is an empirical sample zero. It is not replaced with an invented pseudocount or declared structurally impossible.']}
    output = ROOT / 'diagnostics/sc2001_corridor_nc13.json'
    output.write_text(json.dumps(document, indent=2), encoding='utf-8')
    print(json.dumps({key: {k: row[k] for k in ['completed_denominator', 'counts', 'unresolved_or_censored']} for key, row in priors.items()}, indent=2))


if __name__ == '__main__':
    build()
