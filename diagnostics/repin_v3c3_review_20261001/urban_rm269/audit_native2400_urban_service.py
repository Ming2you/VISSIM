"""Three suspect approaches, existing prediction receipts and observed heads.

No new prediction, calibration, FZP scan or native run. Head crossings do not
equal downstream-link exits; compare only the matching signal stop lines.
"""
import ctypes
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc
from qualify_native2400 import validate_scope

GROUPS = {
    'SC6_S': dict(head_link=1210018302, movements=[
        'SC6_S_SC12_to_E_SC104', 'SC6_S_SC12_to_N_SC103', 'SC6_S_SC12_to_W_SC5']),
    'SC6_E': dict(head_link=1220021201, movements=[
        'SC6_E_SC104_to_N_SC103', 'SC6_E_SC104_to_S_SC12', 'SC6_E_SC104_to_W_SC5']),
    'SC1001_S_left': dict(head_link=40, movements=['SC1001_S_SC1003_to_W_RAMP']),
}


def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    out = HERE / 'native2400_analysis/urban_service_audit.json'
    assert not out.exists()
    read = lambda p: json.loads(p.read_bytes())
    proof = read(out.parent / 'summary.json')
    validate_scope(proof, read(out.parent / 'observed_input_qualification.json'))
    points = read(HERE / 'native2400_predicted_stocks.json')
    report = dict(groups=GROUPS, arms={}, source_pins={}, new_forecasts=0, fzp_scans=0,
        limitations=['Signal head crossings, not downstream corridor exit or isolated causal contributions.',
                    'SC1001_S_left uses the three installed left-turn heads on40; other turns are excluded.',
                    'Sums of substep service/stock ceilings are diagnostics, not independently realizable capacity.'])
    for arm in ('hold', 'selected'):
        path = HERE / 'selection2400_discrete' / (arm + '_response.json.gz')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == points['source_pins'][str(path)]
        report['source_pins'][str(path)] = digest
        with gzip.open(path, 'rt', encoding='utf8') as f:
            response = json.load(f)
        rows = {g: [dict(start_sec=t, end_sec=t+150, predicted_head_veh=0.,
                         intended_limit_veh=0., intended_accepted_veh=0.,
                         by_movement={m:0. for m in v['movements']})
                    for t in (2400,2550,2700)] for g,v in GROUPS.items()}
        owner = {m:g for g,v in GROUPS.items() for m in v['movements']}
        for transfer in response['transfers']:
            key = transfer.get('source') or ''
            if not key.startswith('movement:') or key[9:] not in owner:
                continue
            m = key[9:]
            row = rows[owner[m]][int((transfer['start_sec']-2400)//150)]
            row['predicted_head_veh'] += transfer['vehicles']
            row['by_movement'][m] += transfer['vehicles']
        for resource in response['resource_allocations']:
            if resource['kind'] != 'urban_movement_intended_limit' or resource['resource'] not in owner:
                continue
            row = rows[owner[resource['resource']]][int((resource['start_sec']-2400)//150)]
            row['intended_limit_veh'] += resource['available_veh']
            row['intended_accepted_veh'] += resource['accepted_total_veh']
        del response
        folder = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29') / arm / f'decisions_sdmpc31_g_2400_{arm}_s29'
        for block,end in enumerate((2550,2700,2850)):
            path = folder / f'state_{end:06d}.json'
            report['source_pins'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            raw = read(path)
            bundle = oc.load_bundle(raw)
            ds,_ = oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
            oc.validate_raw(bundle.obs,ds,expected_simres=10)
            boundaries = oc.evaluate_boundaries(bundle.obs,ds,bundle.frame_end,bundle.frame_start,bundle.err_rows)
            for group,defn in GROUPS.items():
                heads = [d for d in ds if d.role=='head' and d.link==defn['head_link']]
                assert heads and len({d.lane for d in heads})==len(heads)
                row = rows[group][block]
                row['actual_head_by_lane'] = {str(d.lane):boundaries[d.boundary_ref].cross for d in heads}
                row['actual_head_veh'] = sum(row['actual_head_by_lane'].values())
                row['prediction_minus_actual_veh'] = row['predicted_head_veh']-row['actual_head_veh']
                assert abs(row['predicted_head_veh']-row['intended_accepted_veh'])<1e-7
        report['arms'][arm] = rows
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({a:{g:[(r['actual_head_veh'],round(r['predicted_head_veh'],2))
        for r in rows] for g,rows in gs.items()} for a,gs in report['arms'].items()},indent=2))


if __name__ == '__main__':
    main()
