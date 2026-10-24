"""Cached target-lane receiving diagnosis; no fitting or traffic rollout.

Future native states are used only for retrospective algebra and labels. They
are never supplied to the autonomous plant. Gap opportunities are not realized
merge capacity. Event timestamps retain the original five-second brackets.
"""
import collections
import csv
import gzip
import hashlib
import json
import math
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph

HERE = Path(__file__).resolve().parent
R = HERE.parent
ROOT = R.parent.parent
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
F = I / 'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
PINS = {}
WINDOWS = ((2670.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path):
    PINS[str(path)] = sha(path)
    return path


def read(path):
    pin(path)
    with (gzip.open(path, 'rt', encoding='utf-8') if path.suffix == '.gz'
          else path.open(encoding='utf-8-sig')) as f:
        return json.load(f)


def csvrows(path):
    pin(path)
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def mean(values):
    values = list(values)
    return math.fsum(values)/len(values) if values else None


def main():
    started = time.perf_counter()
    assert not (HERE/'protocol.json').exists(), 'Preserve completed or failed work'
    previous = read(R/'ramp10639_170/protocol.json')
    pin(Path(__file__))
    pin(ROOT/'evaluation/controllers/physical_ramp_boundary.py')
    network = I/'selected/network/native_seed29.inpx'
    assert sha(network) == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    xml = ET.parse(pin(network)).getroot()
    mapping = read(F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    offsets = dict(zip(mapping['chain_links'], mapping['chain_offsets_m']))
    bounds = mapping['segment_bounds_m']
    connections = {}
    for cid, end in [('10639', 'toLinkEndPt'), ('10682', 'fromLinkEndPt')]:
        link = next(x for x in xml.findall('.//links/link') if x.get('no') == cid)
        e = link.find(end)
        road, lane = map(int, e.get('lane').split())
        connections[cid] = dict(link=road, lane=lane, x_m=offsets[road]+float(e.get('pos')))
    assert connections['10639']['lane'] == connections['10682']['lane'] == 1
    merge_x = connections['10639']['x_m']
    exit_x = connections['10682']['x_m']
    cfg = read(R/'coupled_recovery153/candidate/reference_config.json')['freeway']
    spec = cfg['physical_ramp_receiving_nodes']['RM_C10639']
    protocol = dict(previous_goal_turn='PROGRESS: source/evidence handoff committed and remote verified at85e3454b',
        question='Does target-lane congestion near10639/10682 disappear in the aggregate gap/receiving inputs?',
        scope='Seed67 release110/90 cached native five-second frames, port events and frozen171 autonomous records; physical cells8--13.',
        budget=dict(native=0, FZP=0, forecasts=0, fits=0),
        prior=['Claude03_codex_review/REVIEW rows12--16: mechanism not transferable coefficients',
               'route_inventory:10639 merges must not be reclassified as10682 exits',
               '103 initial timing did not solve gain', '154 lane-conflict change in19--25 failed',
               '170 mean-state gap failed;171 admission changes wait location only'],
        limitations='Same-cell five-second lane transfers omit cross-cell lane-change location and within-step reversals. Future exit labels have right censoring. Native algebra is conditional diagnosis, not forecast or causal effect. Mean conflict flow has no microscopic gap information.',
        protected_sha256=previous['protected_sha256'], STOP=previous['STOP'],
        geometry=connections, merge_to_exit_m=exit_x-merge_x)
    save('protocol.json', protocol)
    summaries, samples, lane_balances, event_checks = [], [], [], []
    conservation_checks = 0
    for arm in ('release', 'release_vsl90'):
        doc = read(F/f'flow67/{arm}_frames.json.gz')
        frames = {round(float(t), 6): {str(vid): dict(zip(doc['fields'], v)) for vid, v in frame.items()}
                  for t, frame in doc['frames'].items()}
        times = sorted(frames)
        assert len(times) == 91 and times[0] == 2670.1 and times[-1] == 3120.1
        pred = read(R/f'prehead_storage171/forecast/state/s67_late_{arm}.json.gz')
        ramps = {round(x['start_sec'], 6): x for x in pred['ramps'] if x['ramp'] == 'RM_C10639'}
        cells = {(round(x['time_s'], 6), x['cell']): x for x in pred['cells'] if x['road'] == 'FW_E'}
        region = pred['diagnostics']['roads'][0]['joint_lane_region']['specification']['cells']
        assert 10 not in region
        ev = csvrows(I/f'heldout67_freeway_20260930/observations/{arm}/port_events.csv')
        merge_events = [e for e in ev if e['connector'] == '10639' and e['kind'] == 'departure'
                        and times[0] < float(e['time_s']) <= times[-1]]
        exit_events = {e['vehicle']: float(e['time_s']) for e in ev
                       if e['connector'] == '10682' and e['kind'] == 'arrival'}
        reexit = [e for e in merge_events if exit_events.get(e['vehicle'], -1) > float(e['time_s'])]
        assert not reexit, 'Do not confuse actual ramp through cohorts with the next off-ramp demand'
        event_checks.append(dict(arm=arm, merge10639_events=len(merge_events),
            subsequently_observed10682_exits=len(reexit), censoring='Only recorded future port events; route inventory supplies the complementary structural prohibition.'))
        for t, u in zip(times, times[1:]):
            a, b = frames[t], frames[u]
            changes = collections.defaultdict(collections.Counter)
            for vid in a.keys() | b.keys():
                x, y = a.get(vid), b.get(vid)
                sx = (x['cell'], x['lane']) if x else None
                sy = (y['cell'], y['lane']) if y else None
                if sx == sy:
                    continue
                kind = ('lateral' if x and y and x['cell'] == y['cell'] else
                        'longitudinal' if x and y else 'appearance')
                if sx: changes[sx][kind+'_out'] += 1
                if sy: changes[sy][kind+'_in'] += 1
            for cell in range(8, 14):
                length = (bounds[cell+1]-bounds[cell])/1000
                for lane in range(1, 5):
                    n0 = sum(x['cell'] == cell and x['lane'] == lane for x in a.values())
                    n1 = sum(x['cell'] == cell and x['lane'] == lane for x in b.values())
                    delta = changes[cell, lane]
                    assert n1-n0 == sum(v if k.endswith('_in') else -v for k, v in delta.items())
                    conservation_checks += 1
                    lane_balances.append(dict(arm=arm, start=t, end=u, cell=cell, lane=lane, n0=n0, n1=n1, **delta))
                    rows = [(vid, x) for vid, x in a.items() if x['cell'] == cell and x['lane'] == lane]
                    stopped = [(vid, x) for vid, x in rows if x['speed_kmh'] < 5.]
                    samples.append(dict(arm=arm, time=t, cell=cell, lane=lane, n=n0,
                        rho=n0/length, v_sum=math.fsum(x['speed_kmh'] for _, x in rows),
                        stopped=len(stopped), stopped_eventually10682=sum(exit_events.get(vid, -1) > t for vid, _ in stopped)))
        for lo, hi in WINDOWS:
            state_samples = []
            for t in times:
                if not lo <= t < hi-1e-6: continue
                fr = frames[t]
                x9 = [x for x in fr.values() if x['cell'] == 9]
                x9lane = [x for x in x9 if x['lane'] == 1]
                length9 = (bounds[10]-bounds[9])/1000
                q_mean = sum(x['speed_kmh'] for x in x9)/length9/4
                q_lane = sum(x['speed_kmh'] for x in x9lane)/length9
                r = ramps[t]
                audit = r['receiving_node']
                cap = audit['unlimited_node_canonical_budget_vph']
                gap = lambda q: gap_acceptance_supply_vph(q, spec['critical_gap_sec'], spec['followup_sec'])
                assert abs(gap(audit['conflicting_vph_per_lane'])-audit['gap_supply_vph_per_lane']) < 1e-8
                # Lane9 still contains future10682 traffic; fixed upstream10643 split
                # is removed only in the mean-law reproduction, not the lane variant.
                state_samples.append(dict(time=t,
                    native_mean_gap_vph=min(cap, gap(q_mean*(1-audit['off_split_removed']))),
                    native_lane9_gap_vph=min(cap, gap(q_lane)),
                    model_gap_vph=r['receiving_budget_veh']*3600,
                    canonical_vph=cap))
            s = [x for x in samples if x['arm'] == arm and lo <= x['time'] < hi-1e-6]
            cell_rows = []
            for cell in range(8, 14):
                z = [x for x in s if x['cell'] == cell]
                one = [x for x in z if x['lane'] == 1]
                p = [v for (t, c), v in cells.items() if c == cell and lo < t <= hi+1e-6]
                cell_rows.append(dict(cell=cell, native_aggregate_rho=mean(x['rho'] for x in z),
                    native_aggregate_v=math.fsum(x['v_sum'] for x in z)/sum(x['n'] for x in z),
                    native_lane1_rho=mean(x['rho'] for x in one),
                    native_lane1_v=math.fsum(x['v_sum'] for x in one)/sum(x['n'] for x in one),
                    native_lane1_stopped=mean(x['stopped'] for x in one),
                    native_lane1_stopped_eventually10682=mean(x['stopped_eventually10682'] for x in one),
                    model_endpoint30s_aggregate_rho=mean(x['rho_veh_per_km_lane'] for x in p),
                    model_endpoint30s_aggregate_v=mean(x['v_kmh'] for x in p)))
            rows = [ramps[t] for t in sorted(ramps) if lo <= t < hi-1e-6]
            native_merge = sum(lo < float(e['time_s']) <= hi+1e-6 for e in merge_events)
            summaries.append(dict(arm=arm, start=lo, end=hi, cells=cell_rows,
                native_merge=native_merge, model_merge=sum(x['accepted_merge_veh'] for x in rows),
                model_eligible_bound_seconds=sum(x['eligible_merge_veh'] < x['receiving_budget_veh']-1e-8 for x in rows),
                native_conditioned_gap_samples=state_samples,
                gap_means={k:mean(x[k] for x in state_samples) for k in state_samples[0] if k != 'time'},
                actual_target_lane_is_represented=False, model_lane_region=region))
    save('results.json', dict(summaries=summaries, lane_samples_5s=samples,
         lane_balances_5s=lane_balances, event_checks=event_checks))
    for p, digest in {**PINS, **previous['protected_sha256'], previous['STOP']['path']:previous['STOP']['sha256']}.items():
        assert sha(p) == digest, p
    save('verification.json', dict(input_sha256=PINS, protected_and_STOP_preserved=True,
        lane_endpoint_balances_checked=conservation_checks,
        target_geometry_verified=True, model_gap_reproduction_samples=180,
        results_sha256=sha(HERE/'results.json'),
        limitations='Native statistics use5s left samples; model cell means use30s endpoint samples. Not an exact RMSE or timing-matched speed comparison. No actual microscopic gap inference.'))
    save('completion.json', dict(status='cached_target_lane_diagnosis_complete_not_qualified',
         elapsed_sec=time.perf_counter()-started, forecasts=0, fits=0, native=0, FZP=0, progress=True))
    for s in summaries:
        print(json.dumps({k:s[k] for k in ['arm','start','native_merge','model_merge','gap_means']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
