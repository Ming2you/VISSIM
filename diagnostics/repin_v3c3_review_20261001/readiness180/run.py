"""Finite current-state exit-readiness diagnostic; no fitting or plant mutation."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
R = HERE.parent
U = R.parent.parent
I = U / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
ARMS = ('hold', 'release', 'hold_vsl90', 'release_vsl90')
WINDOWS = ((2700.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1))
STOP = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')

def read(p):
    opener = gzip.open if p.suffix == '.gz' else open
    with opener(p, 'rt', encoding='utf-8') as f:
        return json.load(f)

def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if p.suffix == '.gz' else open
    with opener(p, 'wt', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=None if p.suffix == '.gz' else 2, allow_nan=False)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def summarize(rows):
    def count(key): return sum(bool(r[key]) for r in rows)
    return {
        'vehicle_snapshots': len(rows), 'unique_vehicles': len({r['vehicle'] for r in rows}),
        'native_exit_next5s': count('exit'), 'freeflight_ready': count('ready'),
        'ready_and_exit': sum(r['ready'] and r['exit'] for r in rows),
        'notready_but_exit': sum(not r['ready'] and r['exit'] for r in rows),
        'own_stop': count('own_stop'), 'own_slow': count('own_slow'),
        'ahead_stop': count('ahead_stop'), 'ahead_slow': count('ahead_slow'),
        'exit_despite_ahead_stop': sum(r['exit'] and r['ahead_stop'] for r in rows),
        'ready_no_ahead_stop': sum(r['ready'] and not r['ahead_stop'] for r in rows),
        'ready_no_ahead_stop_and_exit': sum(r['ready'] and not r['ahead_stop'] and r['exit'] for r in rows),
        'ready_no_ahead_slow': sum(r['ready'] and not r['ahead_slow'] for r in rows),
        'exit_after_current_own_stop': sum(r['exit'] and r['own_stop'] for r in rows),
        'overlap_with_leader': sum(r['leader_gap_m'] is not None and r['leader_gap_m'] < 0 for r in rows),
        'distance_mean_m': sum(r['distance_m'] for r in rows) / len(rows) if rows else None,
        'speed_mean_kmh': sum(r['speed'] for r in rows) / len(rows) if rows else None,
    }

def main():
    network = I / 'selected/network/native_seed29.inpx'
    old = read(R / 'transport_once179/protocol.json')
    protected = {Path(p): h for p, h in old['protected_sha256'].items()}
    assert all(sha(p) == h for p, h in protected.items())
    assert sha(network) == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    assert sha(STOP) == old['STOP']['sha256']
    branch = next(e for e in ET.parse(network).findall('.//link') if e.get('no') == '10483').find('fromLinkEndPt')
    assert branch.get('lane') == '119 1'
    branch_pos = float(branch.get('pos'))
    physical_length = read(R / 'exit_sending131/attempt2/protocol.json')['physical_exit_length_m']
    inputs = [Path(__file__), network, R / 'transport_once179/protocol.json', R / 'exit_sending131/attempt2/protocol.json']
    for arm in ARMS:
        inputs += [R / f'blocking176/{arm}_frames.json.gz', I / f'heldout67_freeway_20260930/observations/{arm}/port_events.csv']
    hashes = {str(p): sha(p) for p in inputs}
    save(HERE / 'protocol.json', {
        'previous_goal_turn': 'PROGRESS179: fixed repeated upstream speed transport, candidate remains rejected.',
        'question': 'Does current exit readiness or stopped traffic ahead explain branch-entry prediction errors?',
        'scope': 'Seed67 four recorded controls; cell20 lane1 exit10483; current snapshots only as features.',
        'windows': WINDOWS, 'branch_link': 119, 'branch_lane': 1, 'branch_pos_m': branch_pos, 'physical_exit_length_m':physical_length,
        'predictor': 'Freeflight ready iff 0<=distance_to_branch<=speed/3.6*5. No acceleration, future speed, or fitted constant.',
        'barrier': 'Any observed same-link/lane vehicle with front ahead and at/before branch, speed<=1 km/h (secondary<5). This is an instantaneous indicator, not a permanent obstacle.',
        'outcome': 'Same vehicle native connector10483 arrival in (t,t+5]; future events used only as labels.',
        'budget': {'native': 0, 'fzp_reads': 0, 'forecasts': 0, 'fits': 0},
        'limitations': ['5s events are interval-censored; no precise detector crossing time.', 'No treatment causality from different realized late states.', 'Overlapping vehicle footprints during lane changes are flagged, not physical collision evidence.', 'Entry is internal off-ramp transfer, not Omega termination.', 'Current cell20 cohort excludes vehicles arriving from upstream within next5s; count these separately.'],
        'protected_sha256': {str(p): h for p,h in protected.items()}, 'input_sha256': hashes,
        'STOP_sha256': sha(STOP),
    })
    out, details = {}, []
    for arm in ARMS:
        data = read(R / f'blocking176/{arm}_frames.json.gz')
        ix = {k:j for j,k in enumerate(data['fields'])}
        events = []
        with (I / f'heldout67_freeway_20260930/observations/{arm}/port_events.csv').open(encoding='utf-8-sig', newline='') as f:
            for e in csv.DictReader(f):
                if int(e['connector']) == 10483 and e['kind'] == 'arrival':
                    events.append((round(float(e['time_s']), 1), str(int(float(e['vehicle'])))))
        assert len(events) == len(set(events))
        windows = []
        for a,b in WINDOWS:
            rows, all_exit, cohort_exit = [], 0, 0
            lane_mean_sending, class_mean_sending = 0.0, 0.0
            for step in range(round((b-a)/5)):
                t = round(a+5*step, 1)
                frame = data['frames'][str(t)]
                lane = sorted([(vid,z) for vid,z in frame.items() if int(z[ix['link']]) == 119 and int(z[ix['lane']]) == 1], key=lambda z:z[1][ix['pos']])
                targets = {vid for vid,z in lane if int(z[ix['cell']]) == 20 and str(z[ix['nextlink']]) == '10483'}
                lane20 = [z for _,z in lane if int(z[ix['cell']]) == 20]
                lane_v = sum(float(z[ix['speed']]) for z in lane20)/len(lane20) if lane20 else 0.0
                lane_mean_sending += min(len(targets),len(targets)*lane_v/3.6*5/physical_length)
                class_mean_sending += min(len(targets),sum(float(z[ix['speed']]) for vid,z in lane if vid in targets)/3.6*5/physical_length)
                actual = {vid for et,vid in events if t < et <= t+5+1e-7}
                all_exit += len(actual)
                cohort_exit += len(actual & targets)
                for j,(vid,z) in enumerate(lane):
                    if vid not in targets: continue
                    pos, v = float(z[ix['pos']]), float(z[ix['speed']])
                    distance = branch_pos-pos
                    assert distance >= -0.01, (arm,t,vid,distance)
                    ahead = [(vv,zz) for vv,zz in lane[j+1:] if float(zz[ix['pos']]) > pos and float(zz[ix['pos']]) <= branch_pos]
                    leader = lane[j+1][1] if j+1 < len(lane) else None
                    row = {'arm':arm,'t':t,'vehicle':vid,'speed':v,'distance_m':distance,
                           'ready':0 <= distance <= v/3.6*5,
                           'exit':vid in actual, 'own_stop':v<=1,'own_slow':v<5,
                           'ahead_stop':any(float(zz[ix['speed']])<=1 for _,zz in ahead),
                           'ahead_slow':any(float(zz[ix['speed']])<5 for _,zz in ahead),
                           'leader_gap_m':float(leader[ix['pos']])-float(leader[ix['length']])-pos if leader is not None else None,
                           'current_lane_change':z[ix['lnchg']], 'n_ahead_before_branch':len(ahead)}
                    rows.append(row)
            z = summarize(rows)
            assert z['native_exit_next5s'] == cohort_exit
            z.update({'window':[a,b], 'all_native_exits':all_exit, 'current_cohort_exits':cohort_exit,
                      'lane_mean_sending':lane_mean_sending,'class_mean_sending':class_mean_sending,
                      'exits_not_in_current_cohort':all_exit-cohort_exit,
                      'subgroups':{name:summarize([r for r in rows if predicate(r)]) for name,predicate in {
                          'ahead_stop':lambda r:r['ahead_stop'], 'no_ahead_stop':lambda r:not r['ahead_stop'],
                          'last50m':lambda r:r['distance_m']<=50, 'upstream150m':lambda r:r['distance_m']>50,
                          'own_stopped':lambda r:r['own_stop'], 'own_not_stopped':lambda r:not r['own_stop'],
                      }.items()}})
            windows.append(z); details.extend(rows)
        out[arm] = {'windows':windows, 'total':summarize([r for r in details if r['arm']==arm])}
        out[arm]['total']['all_native_exits'] = sum(w['all_native_exits'] for w in windows)
        out[arm]['total']['exits_not_in_current_cohort'] = sum(w['exits_not_in_current_cohort'] for w in windows)
        for key in ('lane_mean_sending','class_mean_sending'):
            out[arm]['total'][key] = sum(w[key] for w in windows)
    assert [w['all_native_exits'] for w in out['release']['windows']] == [51,29,45]
    assert [w['all_native_exits'] for w in out['release_vsl90']['windows']] == [51,43,45]
    assert all(sha(p) == h for p,h in protected.items())
    assert all(sha(Path(p)) == h for p,h in hashes.items())
    assert sha(STOP) == old['STOP']['sha256']
    save(HERE / 'rows.json.gz', details)
    save(HERE / 'summary.json', out)
    save(HERE / 'verification.json', {'status':'complete','preserved':True,'rows':len(details),
         'blocks':12,'native_counts_match131':True,'native':0,'fzp_reads':0,'fit':0,'forecasts':0,
         'overall_goal':'ACTIVE_NOT_QUALIFIED'})
    print(json.dumps({k:v['total'] for k,v in out.items()}, indent=2))

if __name__ == '__main__':
    main()
