"""Bounded SC12 -> SC6 source audit using closed obs150 and saved forecasts.

No raw FZP scan, future-input substitution, new model forecast or rate fitting.
A matched vehicle ID at two heads is a path witness, not a full arrival census.
"""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc

ORIGINAL = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
NATIVE = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
LINKS = dict(SC12_E=1220013600, SC12_W=1220012103, SC12_S=1210012700, SC12_N=1220015000, SC6_S=1210018302)
TO_SC6 = ('SC12_E_SC106_to_N_SC6', 'SC12_W_SC11_to_N_SC6', 'SC12_S_SC16_to_N_SC6')
PINS = {}


def pin(p):
    data = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(data).hexdigest()
    return data


def read(p):
    return json.loads(pin(p))


def heads_and_entries(folder, end):
    raw = read(folder / f'state_{end:06}.json')
    derived_path = folder / 'obs150' / f'derived_{end:06}.json'
    derived = read(derived_path) if derived_path.exists() else None
    bundle = oc.load_bundle(raw)
    detectors, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'], bundle.obs['detector_config']['sha256'])
    pin(Path(bundle.obs['detector_config']['path']))
    pin(folder / bundle.obs['mer']['chunk'])
    window = oc.assign_window(bundle.obs, bundle.mer_rows)
    oc.validate_raw(bundle.obs, detectors, expected_simres=10)
    boundaries = oc.evaluate_boundaries(bundle.obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
    if derived is not None:
        assert derived['head_window']['end_sec'] == end
    physical = {}
    events = {}
    for label, link in LINKS.items():
        wanted = [d for d in detectors if d.role == 'head' and d.link == link]
        physical[label] = ([row for row in derived['head_window']['heads'] if str(row['link']) == str(link)]
            if derived is not None else [dict(head_id=d.ref.split('|')[0], lane=d.lane,
                crossings=boundaries[d.boundary_ref].cross, green_sec=None, qualified_crossings=None,
                source='raw_counter_and_boundary_contract') for d in wanted])
        assert {d.ref.split('|')[0] for d in wanted} == {r['head_id'] for r in physical[label]}
        events[label] = [(d.lane, r.veh, r.t_entry) for d in wanted for r in window.entries[d.dcp_no]]
        known = len(events[label])
        unresolved = sum(window.tails[d.dcp_no] for d in wanted)
        total = sum(row['crossings'] for row in physical[label])
        assert known + unresolved == total, (label, end, known, unresolved, total)
        physical[label] = dict(rows=physical[label], crossings=total,
            known_ids=known, unresolved_ids=unresolved, detector_count=len(wanted))
    return physical, events


def main():
    assert not (HERE / 'assessment.json').exists(), 'Preserve completed audit; no overwrite'
    sys.path.insert(0, str(H))
    from qualify_native2400 import validate_scope
    validate_scope(read(H/'native2400_analysis/summary.json'),
        read(H/'native2400_analysis/observed_input_qualification.json'))
    network_path = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree = ET.fromstring(pin(network_path))
    geometry = {label: [dict(head_id=h.get('no'), lane=int(h.get('lane').split()[1]),
        position_m=float(h.get('pos')), sc=h.get('sg').split()[0], sg=h.get('sg').split()[1])
        for h in tree.findall('./signalHeads/signalHead') if h.get('lane').split()[0] == str(link)]
        for label,link in LINKS.items()}
    assert {h['head_id'] for h in geometry['SC12_E']} == {'50601','50602','61601','61602'}
    assert {h['sc'] for h in geometry['SC12_E']} == {'12','13'}
    network = read(H / 'selection2400/network.json')
    model_sources = {m:dict(spec=network['urban_movements'][m],
        rate_veh_h=network['movement_capacity_by_movement_veh_h'][m],
        physical_turns=network['control_area_routes']['movement:'+m]['physical_turns']) for m in TO_SC6}
    observed = {}
    for end in (1950,2100,2250,2400,2850,3000,3150,3300):
        observed[str(end)], _ = heads_and_entries(ORIGINAL,end)
        assert observed[str(end)]['SC12_E']['detector_count'] == 0

    native = {}
    for arm in ('hold','selected'):
        folder = NATIVE / arm / f'decisions_sdmpc31_g_2400_{arm}_s29'
        upstream_events = defaultdict(list)
        rows = []
        for end in (2250,2400,2550,2700,2850):
            current, events = heads_and_entries(folder,end)
            for label in ('SC12_W','SC12_S','SC12_N'):
                for lane,veh,t in events[label]:
                    upstream_events[veh].append((t,label,lane))
            if end <= 2400:
                continue
            matches, travel, unknown = Counter(), defaultdict(list), 0
            for lane,veh,t in events['SC6_S']:
                prior = [e for e in upstream_events[veh] if e[0] < t]
                if prior:
                    tu,source,source_lane = max(prior)
                    label=source+'_lane'+str(source_lane)
                    matches[label] += 1
                    travel[label].append(t-tu)
                else:
                    unknown += 1
            assert sum(matches.values()) + unknown == current['SC6_S']['known_ids']
            rows.append(dict(start_sec=end-150, heads=current,
                sc6_crossers_prior_sc12_known_path=dict(matches),
                matched_travel_sec={k:dict(n=len(v),minimum=min(v),median=sorted(v)[len(v)//2],maximum=max(v)) for k,v in travel.items()},
                no_prior_sc12_head_match=unknown))
        native[arm] = rows

    model = {}
    for arm in ('hold','selected'):
        p=H / 'selection2400_discrete' / (arm+'_response.json.gz')
        response=json.loads(gzip.decompress(pin(p)))
        rows=[]
        for start in (2400,2550,2700):
            transfers=[t for t in response['transfers'] if start <= t['start_sec'] < start+150]
            incoming=Counter()
            sc12=Counter()
            for t in transfers:
                if t['target']=='storage:SC12_to_SC6' and t['source'] != t['target']:
                    incoming[t['source'] or 'exogenous_boundary']+=t['vehicles']
                if (t['source'] or '').startswith('movement:SC12_') and t['source'] != t['target']:
                    sc12[t['source']]+=t['vehicles']
            rows.append(dict(start_sec=start, sources_to_sc6_veh=dict(incoming),
                sc12_movement_departures_veh=dict(sc12), total_to_sc6_veh=sum(incoming.values())))
        model[arm]=rows
        del response
    # Stock/head identity is separate from current-observation rate support.
    stage3=ROOT/'diagnostics/repin_v3c3_review_20261001/upstream_worklog/02_urban_b2/impl/STAGE3.md'
    diag=stage3.parent.parent/'diag_c3/C3_DIAGNOSIS.md'
    pin(stage3); pin(diag)
    pin(ROOT/'evaluation/controllers/signal_head_observation.py')
    pin(ROOT/'evaluation/controllers/obs150_observation.py')
    report=dict(status='source_diagnosis_only', geometry=geometry, model_sources=model_sources,
        past_observation=observed, native_path_witnesses=native, model=model,
        findings=[
            'SC12 east link1220013600 contains both SC12 and SC13 heads on each lane. physical_groups excludes multiple heads; the pinned detector table never collected either SC12 downstream head.',
            'SC12 W northbound model rate remains206.530612veh/h despite observed short-green head passages. This head shares downstream connector lanes; do not declare a unique connector resource without shared-head/phase proof.',
            'Claude STAGE3 U4/U5 already covers multi-head ownership and shared physical lane budgets; its network/rates are not silently transplanted.',
            'Observed two-head ID matches establish actual routes/travel times only. No match does not mean SC12 east or a side entry; old events, missing east detectors and permitted MER tails prevent a complete arrival census.'
        ],
        future_inputs=False, model_changes=0, new_predictions=0, native_runs=0, fzp_scans=0,
        limitations=['Head counts are not connector counts where turns share lanes.',
            'Predicted departures include future internal dynamics, while past achieved rates are not saturation capacity.',
            'This audit does not certify a net gain or quantify how much the unobserved SC12 east path causes the joint Omega mismatch.'],
        source_pins=PINS)
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for arm,rows in native.items():
        print(arm,[dict(t=r['start_sec'],sc6=r['heads']['SC6_S']['crossings'],matched=r['sc6_crossers_prior_sc12_known_path'],unknown=r['no_prior_sc12_head_match']) for r in rows])
    print('model_sources', {a:[r['sources_to_sc6_veh'] for r in rows] for a,rows in model.items()})
    print('DONE',len(PINS),'pins')


if __name__ == '__main__':
    main()
