"""Train-only achieved GREEN discharge lower bound; no saturation estimation.

Consumes the retained, hash-pinned head events. It never scans the full FZP or
changes production inputs. The two existing SC15 time holdouts remain excluded.
"""
from pathlib import Path
from collections import Counter
import csv, hashlib, json
from diagnostics.sc1004_head_service_identifiability import geometry, _union_green_overlap

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'diagnostics/sc1004_head_service_identifiability'
OUT = ROOT / 'diagnostics/sc1004_resource_service_calibration'
TRAIN = [(0, 900), (1350, 2700), (3150, 5400)]
HOLDOUT = [(900, 1350), (2700, 3150)]
MEMBERS = ['SC1004_W_to_E_SC1005', 'SC1004_offE_to_E_SC1005', 'SC1004_offW_to_E_SC1005']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def file(suffix): return Path(str(BASE)+suffix)


def subset(events, windows):
    # A bracket touching a window edge is excluded, with no interpolation.
    return [e for e in events if any(a < e['lower_sec'] <= e['upper_sec'] < b for a,b in windows)]


def summary(events, windows, program, offset):
    selected = subset(events, windows)
    seconds = sum(_union_green_overlap(program, ('2',), a,b,offset) for a,b in windows)
    return {'windows_sec': windows, 'crossing_events': len(selected),
            'unique_vehicle_ids': len({e['vehicle_id'] for e in selected}),
            'native_green_exposure_sec': seconds,
            'achieved_green_discharge_lower_bound_veh_h': 3600*len(selected)/seconds,
            'legacy_cap_green_upper_bound_veh': 619.5918367346939*seconds/3600,
            'events': selected}


def build():
    report = load(file('.json')); extract = load(file('.extract.json'))
    if sha(file('.selected.fzp.gz')) != extract['extract_sha256']:
        raise ValueError('Retained exact physical extract changed')
    geo, sig, program, offset, controller = geometry()
    for name, expected in report['source_sha256'].items():
        # The old report pins many unrelated runtime sources. The physical
        # evidence sources below, not later runtime code, establish this prior.
        if name.startswith('network/') and sha(ROOT/name) != expected:
            raise ValueError('Pinned physical evidence changed: '+name)
    if report['source_changes'] or report['native_clock']['groups']['2']['state_mismatch_seconds']:
        raise ValueError('Original extraction/clock audit failed')
    rows = list(csv.DictReader(file('.head_crossings.csv').open(encoding='utf-8')))
    fields = ['vehicle_id','lower_sec','upper_sec','head','lane','observed_subsequent_connector']
    events = []
    for row in rows:
        if (row['physical_resource'] != '10634' or row['guaranteed_green'] != 'True'
                or row['resource_join_verified'] != 'True' or row['repeated_head_vehicle_id'] != 'False'):
            continue
        e = {k: row[k] for k in fields}
        for k in ('vehicle_id','lane'): e[k] = int(e[k])
        for k in ('lower_sec','upper_sec'): e[k] = float(e[k])
        events.append(e)
    events.sort(key=lambda e:(e['lower_sec'],e['upper_sec'],e['vehicle_id'],e['head']))
    if len({(e['vehicle_id'],e['head'],e['lower_sec'],e['upper_sec']) for e in events}) != len(events):
        raise ValueError('Duplicated physical resource event')
    train = summary(events, TRAIN, program, offset)
    holdouts = [summary(events, [w], program, offset) for w in HOLDOUT]
    whole = summary(events, [(0,5400)], program, offset)
    excluded = len(events)-train['crossing_events']-sum(h['crossing_events'] for h in holdouts)
    if len(events) != report['shared_10634_observed_resource']['guaranteed_green_and_subsequent_connector_verified_crossings']:
        raise ValueError('Resource event population differs from independent audit')
    source_paths = [Path(__file__),file('.json'),file('.extract.json'),file('.head_crossings.csv'),
                    ROOT/'diagnostics/route_choice_corridor_ver2.json',sig]
    heads = sorted([h for h in geo['71']['heads'] if h['sg']=='2'],key=lambda h:h['head'])
    result = {'schema':'physical-shared-service-calibration/v1',
        'classification':'offline_achieved_green_discharge_lower_bound',
        'selected_estimator':'verified_crossing_count / full_train_native_green_seconds * 3600',
        'seed':13,'time_holdouts_excluded_from_fit_sec':HOLDOUT,'seed14_validation':'pending',
        'network':load(ROOT/'diagnostics/route_choice_corridor_ver2.json')['network'],
        'source_run':report['run'],'original_fzp':extract['fzp'],
        'retained_extract':{'path':str(file('.selected.fzp.gz').relative_to(ROOT)).replace('\\','/'),
                            'sha256':extract['extract_sha256'], 'selected_raw_bytes_sha256':extract['selected_uncompressed_sha256']},
        'resource':{'connector':'10634','source_link':'71','target_link':'56','lanes':3,
                    'controller':'1004','signal_group':'2','signal':'SC1004','phase':'SC1004_p3',
                    'members':MEMBERS,'head_by_lane':{str(h['lane']):h['head'] for h in heads},
                    'inherited_service_veh_h':619.5918367346939,
                    'selected_service_veh_h':train['achieved_green_discharge_lower_bound_veh_h']},
        'native_clock':{'sig_file':{'path':str(sig.relative_to(ROOT)).replace('\\','/'),'sha256':sha(sig)},
                        'program_no':int(controller['progNo']),'program_offset_sec':program.program_offset_sec,
                        'controller_offset_sec':offset,'cycle_sec':program.cycle_length_sec,
                        'lsa_state_mismatch_seconds':[],'lsa_first_observed_sec':75.},
        'train':train,'holdout_observed':holdouts,'full_observed':whole,
        'window_boundary_excluded_events':excluded,
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in source_paths},
        'limits':['This is a necessary lower bound on an aggregate GREEN hard cap, not a saturation estimate or statistical confidence interval.',
                  'GREEN exposure includes unused/initially unverified seconds, while every counted crossing bracket is verified GREEN and later joins10634.',
                  'Distinct lane/head visits by the same vehicle consume service again; exact event duplicates are rejected. No vehicle-completion or Omega TTD is inferred here.',
                  'Train-only1509.33 differs from full-observation1484.44; the latter includes held time windows and is never the selected prior.',
                  'Receiving, route eligibility and storage constraints remain separate. This value is not multiplied by3 lanes or by3 model members.']}
    OUT.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Separate opt-in copy. The active evidence and config remain byte-identical.
    document=load(ROOT/'diagnostics/route_choice_corridor_ver2.json')
    document['service_resource_calibration']={'path':str(OUT.with_suffix('.json').relative_to(ROOT)).replace('\\','/'),
                                             'sha256':sha(OUT.with_suffix('.json'))}
    (ROOT/'diagnostics/route_choice_corridor_sc1004_calibrated.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'train':{k:v for k,v in train.items() if k!='events'},
         'holdout':[{k:v for k,v in h.items() if k!='events'} for h in holdouts],
         'full':{k:v for k,v in whole.items() if k!='events'},'window_boundary_excluded_events':excluded},indent=2))
    return result


if __name__=='__main__': build()
