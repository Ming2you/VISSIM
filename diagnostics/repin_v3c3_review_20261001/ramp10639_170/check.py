"""Read completed caches: separate connector entry, signal passage and merge.

No forecasts or fitting. Native signal passage is a 30s stock-balance inference,
not a subsecond signal validation. Seed61 forecasts are explicitly historical.
"""
import csv
import gzip
import hashlib
import json
import math
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
ROOT = R.parent.parent
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
F = I / 'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
RAMPS = ('10639', '10681', '10490', '10484')
ARMS = ('hold', 'release', 'hold_vsl90', 'release_vsl90')
TIMES = [round(2670.1 + 30*k, 1) for k in range(16)]
PINS = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pin(p):
    PINS[str(p)] = sha(p)
    return p


def read(p):
    pin(p)
    with (gzip.open(p, 'rt', encoding='utf-8') if p.suffix == '.gz'
          else p.open(encoding='utf-8-sig')) as f:
        return json.load(f)


def csvrows(p):
    pin(p)
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def close(a, b, label):
    assert abs(a-b) < 1e-7, (label, a, b)


def main():
    started = time.perf_counter()
    assert not (HERE/'results.json').exists(), 'Preserve completed results'
    prior = read(R/'recovery_lateral169/protocol.json')
    protocol = dict(previous_goal_turn='NO_PROGRESS: explanation of completed evidence only',
        hypothesis='10639 RM gain error contains entry forecast and post-head merge/storage errors, not only an incorrect green-to-service curve.',
        budget=dict(cached_seeds=2, arms_per_seed=4, east_ramps=4, forecasts=0, fitting=0, native=0, FZP=0),
        native_head_rule='H = N_post(end)-N_post(start)+connector departures; forward connector only, entries upstream of head, no unresolved losses.',
        time_limit='30s inferred crossings cannot identify exact pulse/startup delay or microscopic accepted gaps.',
        model_versions={'67':'Frozen rejected169, not production', '61':'Historical route_inventory/storage; not an independent test of169'},
        limitations='Connector TTT only, not Omega. Budget shortfalls count service opportunities, not distinct vehicles. No future observations are fed to a forecast.',
        protected_sha256=prior['protected_sha256'], STOP=prior['STOP'])
    save('protocol.json', protocol)
    pin(Path(__file__))
    result = []
    snapshots = []
    service_checks = 0
    event_checks = 0
    for seed in (67, 61):
        for arm in ARMS:
            folder = I/f'heldout{seed}_freeway_20260930/observations'/arm
            cohorts = read(folder/'port_cohorts_30s.json')
            ports = {(round(float(r['window_end_s']), 1), r['connector']): r
                     for r in csvrows(folder/'ports_30s.csv')}
            events = csvrows(folder/'port_events.csv')
            path = (R/f'recovery_lateral169/forecast/state/s67_late_{arm}.json.gz' if seed == 67
                    else F/f'route_inventory/s61_late/storage_{arm}.json.gz')
            pred = read(path)
            for cid in RAMPS:
                rows = [r for r in pred['ramps'] if r['start']['connector_id'] == cid]
                assert len(rows) == 450
                meta = pred['diagnostics']['dynamic_ramp_boundary']['metadata']['RM_C'+cid]
                head = meta['head_position_m']
                stocks = {}
                for t in TIMES:
                    cc = cohorts[str(t)][cid]
                    post = [x for x in cc if x[0] >= head]
                    stocks[t] = (len(cc), len(post))
                    close(len(cc), float(ports[t, cid]['end_n_veh']), 'cohort/port stock')
                    snapshots.append(dict(seed=seed, arm=arm, connector=cid, time=t,
                        n=len(cc), post_n=len(post), pre_n=len(cc)-len(post),
                        post_stopped=sum(x[1] < 5 for x in post),
                        upstream_stopped=sum(x[0] < head and x[1] < 5 for x in cc),
                        nearest_post_position_from_head_m=min((x[0]-head for x in post), default=None),
                        post_mean_speed_kmh=sum(x[1] for x in post)/len(post) if post else None))
                close(rows[0]['start']['connector_veh'], stocks[TIMES[0]][0], 'initial connector')
                close(rows[0]['start']['downstream_travelling_veh']+rows[0]['start']['merge_ready_veh'],
                      stocks[TIMES[0]][1], 'initial posthead')
                for a, b in zip(TIMES, TIMES[1:]):
                    r = [x for x in rows if a <= x['start_sec'] < b-1e-6]
                    assert len(r) == 30
                    native = ports[b, cid]
                    arr = float(native['arrivals_veh'])
                    merge = float(native['departures_veh'])
                    assert float(native['unresolved_absences_veh']) == 0
                    close(float(native['conservation_residual_veh']), 0., 'native conservation')
                    n0, p0 = stocks[a]
                    n1, p1 = stocks[b]
                    head_count = p1-p0+merge
                    assert head_count >= 0
                    close(n1-n0, arr-merge, 'native connector')
                    close((n1-p1)-(n0-p0), arr-head_count, 'native upstream')
                    ev = [e for e in events if e['connector'] == cid and a < float(e['time_s']) <= b+1e-6]
                    close(sum(e['kind']=='arrival' for e in ev), arr, 'entry events')
                    close(sum(e['kind']=='departure' for e in ev), merge, 'departure events')
                    assert all(float(e['position_m']) < head for e in ev if e['kind']=='arrival')
                    event_checks += 1
                    sums = {key: math.fsum(x[key] for x in r) for key in (
                        'requested_arrivals_veh', 'admitted_arrivals_veh', 'head_service_veh',
                        'head_service_limit_veh', 'accepted_merge_veh', 'receiving_budget_veh',
                        'unused_receiving_budget_veh')}
                    shortages = dict(head_ready_shortfall_veh=0., posthead_space_shortfall_veh=0.,
                                     receiving_bound_seconds=0, eligibility_bound_seconds=0)
                    for x in r:
                        assert len(x['local_receipts']) == 1
                        lc = x['local_receipts'][0]
                        ready_loss = space_loss = free_sum = 0.
                        # Capacity and readiness are per lane: do not borrow an
                        # unused opportunity from the other10681 lane.
                        for lane in x['lane_receipts']:
                            s = lane['head_service_limit_veh']
                            available = lane['start']['head_ready_veh']+lane['arrived_at_head_veh']
                            post_before = lane['start']['downstream_travelling_veh']+lane['start']['merge_ready_veh']-lane['accepted_merge_veh']
                            free = max(0., lane['nominal_posthead_storage_veh']-post_before)
                            ready = max(0., s-available)
                            space = max(0., min(s, available)-free)
                            close(s-lane['head_service_veh'], ready+space, 'lane head opportunity ledger')
                            close(lane['accepted_merge_veh'], min(lane['eligible_merge_veh'], lane['receiving_budget_veh']), 'lane merge min')
                            ready_loss += ready
                            space_loss += space
                            free_sum += free
                        close(free_sum, lc['posthead_free_before_service_veh'], 'reconstructed free storage')
                        close(x['head_service_limit_veh']-x['head_service_veh'], ready_loss+space_loss, 'head opportunity ledger')
                        shortages['head_ready_shortfall_veh'] += ready_loss
                        shortages['posthead_space_shortfall_veh'] += space_loss
                        shortages['receiving_bound_seconds'] += int(x['eligible_merge_veh'] > x['receiving_budget_veh']+1e-8)
                        shortages['eligibility_bound_seconds'] += int(x['eligible_merge_veh'] < x['receiving_budget_veh']-1e-8)
                        service_checks += 1
                    start, end = r[0]['start'], r[-1]['end']
                    pre = lambda s: s['upstream_travelling_veh']+s['head_ready_veh']
                    post = lambda s: s['downstream_travelling_veh']+s['merge_ready_veh']
                    close(end['connector_veh']-start['connector_veh'], sums['admitted_arrivals_veh']-sums['accepted_merge_veh'], 'model connector')
                    close(post(end)-post(start), sums['head_service_veh']-sums['accepted_merge_veh'], 'model posthead')
                    close(pre(end)-pre(start), sums['admitted_arrivals_veh']-sums['head_service_veh'], 'model prehead')
                    actual = dict(arrival=arr, head=head_count, merge=merge, n0=n0, n1=n1, post0=p0, post1=p1,
                                  ttt=(n0+n1)*30/7200., pre_ttt=(n0-p0+n1-p1)*30/7200., post_ttt=(p0+p1)*30/7200.)
                    predicted = dict(arrival=sums['admitted_arrivals_veh'], head=sums['head_service_veh'], merge=sums['accepted_merge_veh'],
                        n0=start['connector_veh'], n1=end['connector_veh'], post0=post(start), post1=post(end),
                        ttt=(start['connector_veh']+end['connector_veh'])*30/7200.,
                        pre_ttt=(pre(start)+pre(end))*30/7200., post_ttt=(post(start)+post(end))*30/7200.)
                    result.append(dict(seed=seed, arm=arm, connector=cid, start=a, end=b,
                        actual=actual, predicted=predicted, model_budgets={**sums, **shortages},
                        green_schedule=[x['green_sec'] for x in r],
                        nominal_posthead_capacity_veh=r[0]['nominal_posthead_storage_veh']))
    blocks = []
    for seed in (67, 61):
        for arm in ARMS:
            for cid in RAMPS:
                for a,b in [(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1),(2670.1,3120.1)]:
                    rr = [x for x in result if x['seed']==seed and x['arm']==arm and x['connector']==cid and a<=x['start'] and x['end']<=b]
                    z = dict(seed=seed, arm=arm, connector=cid, start=a, end=b)
                    for kind in ('actual', 'predicted'):
                        z[kind] = {k:sum(x[kind][k] for x in rr) for k in ('arrival','head','merge','ttt','pre_ttt','post_ttt')}
                        z[kind].update({k:rr[0][kind][k] for k in ('n0','post0')})
                        z[kind].update({k:rr[-1][kind][k] for k in ('n1','post1')})
                    z['budgets'] = {k:sum(x['model_budgets'][k] for x in rr) for k in rr[0]['model_budgets']}
                    blocks.append(z)
    save('results.json', dict(rows_30s=result, blocks=blocks, native_snapshots=snapshots))
    for p,d in {**PINS, **prior['protected_sha256'], prior['STOP']['path']:prior['STOP']['sha256']}.items():
        assert sha(p)==d, p
    save('verification.json', dict(input_sha256=PINS, checked_30s_native_event_windows=event_checks,
        checked_model_seconds=service_checks, exact_initial_stocks=True,
        native_connector_and_pre_post_conservation=True, model_connector_and_pre_post_conservation=True,
        core_and_stop_preserved=True, results_sha256=sha(HERE/'results.json')))
    save('completion.json', dict(status='cached_diagnosis_complete_not_qualified', seconds=time.perf_counter()-started,
        forecasts=0, fits=0, native=0, FZP=0, progress=True))
    for z in blocks:
        if z['connector']=='10639' and z['arm'] in ('hold','release'):
            print(json.dumps(z, ensure_ascii=False))


if __name__ == '__main__':
    main()
