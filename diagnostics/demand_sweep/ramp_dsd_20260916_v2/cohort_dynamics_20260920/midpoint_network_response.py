"""Locate midpoint response in initial cohorts and network boundary timing.

Existing FZP only. New-born numeric IDs are not paired as identical vehicles.
Boundary moments are accounting contributions, not independent causal effects.
"""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import marginal_boundary_timing as a
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_meter_midpoint as mid

K, OUT, e = mid.K, mid.OUT, mid.e


def main():
    out = OUT / 'network_response_v2'; out.mkdir(exist_ok=False)
    result = e.load(OUT / 'result_v2.json')
    g = e.load(OUT / 'observations/rm6/geometry.json')
    root = ET.parse(OUT / 'prepared_rm6/network/baseline.inpx').getroot()
    links = {int(n.get('no')) for n in root.findall('./links/link')}
    sources = {int(n.get('link')) for n in root.findall('./vehicleInputs/vehicleInput')}
    chain = {r['link']: r for r in g['chains']['FW_E']}
    ports = {r['connector']: r for r in g['boundaries'] if r['road'] == 'FW_E' and r['kind'] in ('ramp', 'offramp')}
    main_sources = {r['to_link'] for r in g['boundaries'] if r['road'] == 'FW_E' and r['kind'] == 'source'}
    terminal = g['chains']['FW_E'][-1]
    paths = dict(rm8=a.m.BANK/'run_rm8/vissim_eval/baseline_001.fzp', rm6=OUT/'run_rm6/vissim_eval/baseline_001.fzp')
    stamps = {arm: (p.stat().st_size, p.stat().st_mtime_ns) for arm, p in paths.items()}
    streams = {arm: a.frames(p, links) for arm, p in paths.items()}
    initial = initial_main = None
    previous = None
    events, trace, source_differences = [], [], []
    first_link_changes = {}
    bins = {t: {arm: Counter() for arm in paths} for t in (2700, 2850, 3000)}
    cohort = {arm: Counter() for arm in paths}
    input_births = {arm: Counter() for arm in paths}
    changed_initial = set()
    for (t, base), (u, ctl) in zip(streams['rm8'], streams['rm6'], strict=True):
        assert t == u
        current = {'rm8': base, 'rm6': ctl}
        if t == a.START:
            assert base == ctl and len(base) == 5208
            initial = set(base)
            initial_main = {v for v, r in base.items() if r['link'] in chain}
            assert len(initial_main) == 676
        else:
            for vid in base.keys() & ctl.keys() & initial:
                if base[vid] != ctl[vid]:
                    changed_initial.add(vid)
                    link = str(base[vid]['link'])
                    first_link_changes.setdefault(link, dict(time_s=t, vehicle=vid, rm8=base[vid], rm6=ctl[vid]))
            births = {}
            for arm, frame in current.items():
                # Compare birth features grouped by source/time, not numeric IDs.
                births[arm] = Counter((r['link'], r['lane'], r['pos'], r['speed'])
                    for v, r in frame.items() if v not in previous[arm] and r['link'] in sources)
                input_births[arm].update(r[0] for r in births[arm].elements())
            if births['rm8'] != births['rm6']:
                affected = sorted({r[0] for r in (births['rm8']-births['rm6']) | (births['rm6']-births['rm8'])})
                source_differences.append(dict(time_s=t, sources=affected,
                    rm8=[list(r) for r in births['rm8'].elements()], rm6=[list(r) for r in births['rm6'].elements()],
                    previous_source_vehicles_exact={str(link):
                        {v:r for v,r in previous['rm8'].items() if r['link']==link} ==
                        {v:r for v,r in previous['rm6'].items() if r['link']==link} for link in affected}))
            for arm, frame in current.items():
                block = min(end for end in bins if t <= end)
                for v, r in frame.items():
                    if r['link'] in chain:
                        bins[block][arm]['main_seconds'] += 1
                        if v in initial_main:
                            bins[block][arm]['initial_seconds'] += 1
                            cohort[arm][v] += 1
            old_main = {v:r for v,r in previous['rm6'].items() if r['link'] in chain}
            main = {v:r for v,r in ctl.items() if r['link'] in chain}
            for v, r in main.items():
                if v in old_main: continue
                before = previous['rm6'].get(v)
                if before and before['link'] in ports and ports[before['link']]['kind']=='ramp':
                    kind = 'merge_'+str(before['link'])
                elif r['link'] in main_sources and before is None:
                    kind = 'source'
                else:
                    raise AssertionError(('Unclassified mainline entry',t,v,before,r))
                events.append(dict(time_s=t,vehicle=v,kind=kind,sign=1))
            for v, r in old_main.items():
                if v in main: continue
                now = ctl.get(v)
                if now and now['link'] in ports and ports[now['link']]['kind']=='offramp':
                    kind = 'off_'+str(now['link'])
                elif now is None and r['link']==terminal['link'] and r['pos']+r['speed']/3.6+3>=terminal['length_m']:
                    kind = 'terminal_inferred'
                else:
                    raise AssertionError(('Unclassified mainline exit',t,v,r,now))
                events.append(dict(time_s=t,vehicle=v,kind=kind,sign=-1))
            assert len(main)-len(old_main) == sum(r['sign'] for r in events if r['time_s']==t)
        trace.append(dict(time_s=t, **{arm: dict(main_n=sum(r['link'] in chain for r in frame.values()),
            initial_main_n=sum(v in initial_main and r['link'] in chain for v,r in frame.items())) for arm,frame in current.items()}))
        previous = current
    reference = e.load(K / 'marginal_boundary_timing_v1/rm8.json')
    rows = {}
    for end in (2700, 2850, 3000):
        selected = [r for r in trace if a.START < r['time_s'] <= end]
        costs = {arm: sum(r[arm]['main_n'] for r in selected)/3600 for arm in paths}
        initial_costs = {arm: sum(r[arm]['initial_main_n'] for r in selected)/3600 for arm in paths}
        moments = Counter()
        for r in events:
            if r['time_s'] <= end: moments[r['kind']] += r['sign']*(end-r['time_s']+1)/3600
        assert abs(costs['rm8']-reference['prefix'][str(end)]['ttt_veh_h']) < 1e-8
        assert abs(costs['rm6'] - (676*(end-a.START)/3600 + sum(moments.values()))) < 1e-8
        base_moments = reference['prefix'][str(end)]['moments']
        diff = {kind:moments.get(kind,0)-base_moments.get(kind,0) for kind in moments.keys()|base_moments.keys()}
        delta = costs['rm6']-costs['rm8']
        assert abs(sum(diff.values())-delta) < 1e-8
        rows[str(end)] = dict(delta_main_ttt=delta, delta_initial_main=initial_costs['rm6']-initial_costs['rm8'],
            delta_later_main=delta-initial_costs['rm6']+initial_costs['rm8'], signed_boundary_moments=diff)
    assert abs(rows['3000']['delta_main_ttt']-result['actual_deltas_vs_g8']['rm6']['mainline']) < 1e-8, rows['3000']
    for arm, p in paths.items(): assert stamps[arm] == (p.stat().st_size, p.stat().st_mtime_ns)
    # Stronger future-input deletion, including the cached event list.
    data = a.m.prepare_data(a.m.BANK / 'observations/rm8')
    model = e.load_base_model(data.geometry, a.m.MODEL/'config.json')
    profile = e.load(a.m.MODEL/'port_profile.json')
    data.port_events = copy.deepcopy(data.events)
    removed = {}
    for name in ('events','heads','port_events'):
        original = getattr(data,name)
        setattr(data,name,[r for r in original if float(r['time_s'])<=a.START])
        removed[name] = len(original)-len(getattr(data,name))
    data.cells = {t:r for t,r in data.cells.items() if t<=a.START}
    data.port_cohorts = {t:r for t,r in data.port_cohorts.items() if float(t)<=a.START}
    for name in ('flows','boundaries','ports','headstocks','arrivals','departures','head_counts'):
        values = getattr(data,name)
        kept = {k:v for k,v in values.items() if k[0]<=a.START}
        setattr(data,name,Counter(kept) if isinstance(values,Counter) else kept)
    window = e.window(data,model,a.START,'history_forecast',profile,lambda t:({'RM_C10490':6},{}))
    assert json.loads(json.dumps(window)) == e.load(OUT/'forecast_window.json')
    e.save(out/'events_rm6.json',events)
    e.save(out/'trace.json',trace)
    e.save(out/'source_birth_differences.json',source_differences)
    e.save(out/'first_initial_vehicle_changes.json',first_link_changes)
    report = dict(qualified=False, initial_global=5208, initial_mainline=676,
        changed_initial_global=len(changed_initial), continuity_steps=450, prefix=rows,
        source_birth_counts={arm:dict(v) for arm,v in input_births.items()},
        source_birth_different_seconds=len(source_differences), first_source_difference=source_differences[:1],
        strict_future_removed=removed, strict_forecast_window_exact=True,
        source_receipts={arm:dict(path=str(paths[arm].relative_to(e.ROOT)),bytes=s[0],mtime_ns=s[1]) for arm,s in stamps.items()},
        source_pins={p.relative_to(e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),Path(a.__file__),OUT/'protocol.json',OUT/'result_v2.json',K/'marginal_boundary_timing_v1/rm8.json')},
        limitations=['Birth-feature differences are observed variation,not proof of a particular random-number implementation.',
            'Mainline boundary moments are conservation accounting,not separable causal benefit.',
            'Initial vehicle identity is matched;new-born numeric IDs are not paired.',
            'No physical coefficients changed and no fresh-seed qualification.'])
    e.save(out/'result.json',report)
    print(json.dumps(dict(prefix=rows,source_birth_different_seconds=len(source_differences),
        first_source_difference=source_differences[:1],strict_future_window_exact=True)),flush=True)


if __name__ == '__main__': main()
