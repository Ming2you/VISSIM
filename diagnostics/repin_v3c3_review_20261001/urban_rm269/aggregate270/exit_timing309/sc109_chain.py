"""Closed native head/exit timing; future observations are diagnosis only."""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import pickle
import statistics
import xml.etree.ElementTree as ET

from evaluation.controllers import obs150_contract as oc

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = HERE.parents[4]
CACHE = Path('E:/VISSIM_analysis/20261010_exit_timing309')
MODEL = Path('E:/VISSIM_analysis/20261010_sc109_composite308/forecast2400_v2')
RUNS = {
    'hold': Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
    'city': Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29'),
}
GROUPS = {
    'SC107_W_p3': (1220000201, '107', '2', ['SC107_W_SC1004_to_E_SC108', 'SC107_W_SC1004_to_S', 'SC107_W_SC1005_to_E_SC108', 'SC107_W_SC1005_to_S']),
    'SC108_W_p3': (178, '108', '2', ['SC108_W_SC107_to_E_SC109', 'SC108_W_SC107_to_S']),
    'SC108_side_p3': (21, '108', '2', ['SC108_W_to_E_SC109']),
    'SC109_W_p3': (173, '109', '2', ['SC109_W_SC108_to_E']),
}
PINS = {}


def raw(p):
    p = Path(p)
    b = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(b).hexdigest()
    return b


def read(p):
    return json.loads(raw(p))


def summary(rows, tails=()):
    times = [r['time'] for r in rows]
    base = -sum((2850 - t) / 3600 for t in times)
    return dict(known_count=len(rows), tail_count=sum(n for _, n in tails),
                count150=[sum(a < t <= a + 150 for t in times) + sum(n for e, n in tails if e == a + 150) for a in (2400, 2550, 2700)],
                cost_lower=base - sum(n * (2850 - (e - 1)) / 3600 for e, n in tails),
                cost_upper=base - sum(n * (2850 - e) / 3600 for e, n in tails))


def main():
    assert not (HERE / 'sc109_chain.json').exists()
    cfg, state, _ = pickle.loads(raw(A / 'citysplit287/forecast2400/initial.pickle'))
    initial = read(RUNS['hold'] / 'state_002400.json')['vehicle_records']
    assert initial == read(RUNS['city'] / 'state_002400.json')['vehicle_records']
    physical = {r['veh_no']: r for r in initial['records']}
    assert initial['complete'] and len(physical) == initial['record_count'] == initial['collection_count_before'] == initial['collection_count_after']
    assert initial['unobservable_count'] == initial['external_source_count'] == 0
    provenance = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    support = {k: v for k, v in provenance.items() if any(x == 'storage:SC108_to_SC109' or x.startswith('movement:SC109_W_SC108_') for x in v)}
    local_ids = {i for i, v in physical.items() if str(v['link_no']) in support}
    assert len(local_ids) == round(sum(sum(v.values()) for v in support.values())) == 53

    def category(veh):
        return 'initial_local' if veh in local_ids else ('initial_elsewhere' if veh in physical else 'absent_initial')

    def annotate(veh, time):
        return dict(vehicle=veh, time=time, category=category(veh), initial_link=physical.get(veh, {}).get('link_no'))

    network = ET.fromstring(raw(ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    xml_heads = {k: [h.attrib for h in network.findall('./signalHeads/signalHead') if h.get('lane').split()[0] == str(s[0]) and h.get('sg') == s[1] + ' ' + s[2]] for k, s in GROUPS.items()}
    assert all(xml_heads.values())
    reconciliation = read(HERE / 'assessment.json')
    cache_done = read(CACHE / 'completion.json')
    exits, heads, totals, model, cohorts = {}, {}, {}, {}, {}
    for arm, folder in RUNS.items():
        cp = Path(cache_done['arms'][arm]['cache'])
        payload = raw(cp)
        assert hashlib.sha256(payload).hexdigest() == cache_done['arms'][arm]['sha256']
        selected = []
        for r in json.loads(gzip.decompress(payload))['events']:
            if r['kind'] != 'observed_exit':
                continue
            witness = reconciliation['native_observed_pair_topology'][r['from_link'] + '->' + r['to_link']]
            if witness['edge'] == ['173', '10285']:
                selected.append(dict(annotate(r['vehicle'], r['mid_sec']), high_sec=r['high_sec']))
        exits[arm] = selected
        cohorts[arm] = {}
        for cat in ('initial_local', 'initial_elsewhere', 'absent_initial'):
            rows = [r for r in selected if r['category'] == cat]
            cohorts[arm][cat] = dict(count=len(rows), cost=-sum((2850-r['time'])/3600 for r in rows),
                # Include shared 2395.1->2400.1 baseline transition in first bin.
                count150=[sum(at < r['high_sec'] <= at+150 for r in rows) for at in (2400, 2550, 2700)],
                initial_links=dict(Counter(str(r['initial_link']) for r in rows if r['initial_link'] is not None)))
        assert sum(c['count'] for c in cohorts[arm].values()) == reconciliation['native'][arm]['173->10285']['count']
        assert abs(sum(c['cost'] for c in cohorts[arm].values()) - reconciliation['native'][arm]['173->10285']['cost']) < 1e-8
        heads[arm] = {k: [] for k in GROUPS}
        tails = {k: [] for k in GROUPS}
        for end in (2550, 2700, 2850):
            obs = read(folder / f'state_{end:06}.json')
            b = oc.load_bundle(obs)
            dets, _ = oc.read_detector_csv(b.obs['detector_config']['path'], b.obs['detector_config']['sha256'])
            raw(b.obs['detector_config']['path'])
            raw(folder / b.obs['mer']['chunk'])
            w = oc.assign_window(b.obs, b.mer_rows)
            for k, (link, sc, sg, _) in GROUPS.items():
                wanted = [d for d in dets if d.role == 'head' and d.link == link and oc.parse_head_ref(d.ref)[2] == sg]
                assert wanted, k
                heads[arm][k].extend(dict(annotate(r.veh, r.t_entry), detector=d.dcp_no) for d in wanted for r in w.entries[d.dcp_no])
                tails[k].append((end, sum(w.tails[d.dcp_no] for d in wanted)))
        totals[arm] = {k: summary(v, tails[k]) for k, v in heads[arm].items()}
        response = json.loads(gzip.decompress(raw(MODEL / (arm + '.response.json.gz'))))
        model[arm] = {}
        for k, spec in GROUPS.items():
            moves = {'movement:' + m for m in spec[3]}
            rows = [r for r in response['transfers'] if r['source'] in moves and r['source'] != r['target']]
            model[arm][k] = dict(count=sum(r['vehicles'] for r in rows),
                count150=[sum(r['vehicles'] for r in rows if at <= r['start_sec'] < at+150) for at in (2400,2550,2700)],
                cost_lower=-sum(r['vehicles']*(2850-r['start_sec'])/3600 for r in rows),
                cost_upper=-sum(r['vehicles']*(2850-r['end_sec'])/3600 for r in rows))
    stage_maps = {}
    for arm in RUNS:
        stage_maps[arm] = {}
        for key, rows in dict(heads[arm], exit=exits[arm]).items():
            by_id = defaultdict(list)
            for r in rows:
                by_id[r['vehicle']].append(r['time'])
            # Repeated crossings are not silently treated as one observation.
            stage_maps[arm][key] = {i: t[0] for i,t in by_id.items() if len(t) == 1}
    matched = {}
    for cohort in ('initial_local', 'initial_elsewhere'):
        ids = {i for i in stage_maps['hold']['exit'].keys() & stage_maps['city']['exit'].keys() if category(i) == cohort}
        stages = {}
        for stage in (*GROUPS, 'exit'):
            paired = sorted(ids & stage_maps['hold'][stage].keys() & stage_maps['city'][stage].keys())
            diff = [stage_maps['city'][stage][i] - stage_maps['hold'][stage][i] for i in paired]
            stages[stage] = dict(pairs=len(paired), sum_delay_sec=sum(diff), mean_delay_sec=statistics.mean(diff) if diff else None)
        all_chain = sorted(ids & set.intersection(*(set(stage_maps[arm][key]) for arm in RUNS for key in ('SC107_W_p3','SC108_W_p3','SC109_W_p3','exit'))))
        chain = [{**{key: stage_maps['city'][key][i]-stage_maps['hold'][key][i] for key in ('SC107_W_p3','SC108_W_p3','SC109_W_p3','exit')},
                  'vehicle': i, 'initial_link': physical[i]['link_no']} for i in all_chain]
        matched[cohort] = dict(exit_pairs=len(ids), stages=stages, all_chain=chain,
            chain_mean_delay_sec={key:statistics.mean(r[key] for r in chain) for key in ('SC107_W_p3','SC108_W_p3','SC109_W_p3','exit')} if chain else {})
    deltas = {k: dict(native_cost_lower=totals['city'][k]['cost_lower']-totals['hold'][k]['cost_upper'],
        native_cost_upper=totals['city'][k]['cost_upper']-totals['hold'][k]['cost_lower'],
        model_cost_lower=model['city'][k]['cost_lower']-model['hold'][k]['cost_upper'],
        model_cost_upper=model['city'][k]['cost_upper']-model['hold'][k]['cost_lower']) for k in GROUPS}
    raw(Path(__file__))
    for p in ('diag_c3_r2/U7.md', 'diag_c3/C3_DIAGNOSIS.md'):
        raw(A.parent.parent / 'upstream_worklog/02_urban_b2' / p)
    result = dict(status='complete_sc109_upstream_timing_diagnosis', initial_local_count=len(local_ids),
        initial_provenance=support, native_exit_cohorts=cohorts, native_head_summary=totals, model_heads=model,
        head_deltas=deltas, matched_initial_exit_pairs=matched, head_events=heads, exit_events=exits, xml_heads=xml_heads,
        source_pins=PINS, budget=dict(forecasts=0, native=0, fzp_scans=0, fits=0),
        limits=['Exit edge classification is a bounded topology witness, not exact route reconstruction.',
                'Matched exit cohorts are survivor-conditioned. Delay is diagnostic, not an unbiased whole-control causal effect.',
                'Head totals include unresolved final1s MER tails; individual joins omit these unobserved vehicle IDs.',
                'SC107/108 p3 heads include through and right turns; model comparison pools those movements.',
                'The common pre-control5s transition is included and cancels in exit-cost differences.',
                'Head/connector locations and native5s/model10s quadratures differ; no future timing is a predictor input.'])
    (HERE/'sc109_chain.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print('COHORTS', json.dumps(cohorts))
    print('HEADS', json.dumps(dict(native=totals,model=model,delta=deltas)))
    print('MATCHED', json.dumps({k:{x:v[x] for x in ('exit_pairs','stages','chain_mean_delay_sec')} for k,v in matched.items()}))


if __name__ == '__main__':
    main()
