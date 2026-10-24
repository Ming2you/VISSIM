"""Verify consumed past observer inputs without forecasting or changing native data."""
import hashlib
import json
from pathlib import Path

from evaluation.controllers import lane_plant_runtime as runtime
from evaluation.controllers import obs150_contract as oc, obs150_observation as observer

HERE = Path(__file__).resolve().parent
I = HERE.parent
OUT = HERE/'history_inputs'
OLD = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
NEW = Path('D:/VISSIM_runs/20261001_onset2250_s29/held_actual/decisions_sdmpc31_g_2250_held_actual_s29')


def main():
    OUT.mkdir(exist_ok=False)
    pins = {}
    def read(p):
        data = p.read_bytes()
        pins[str(p)] = hashlib.sha256(data).hexdigest()
        return json.loads(data)
    tuning = read(I/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json')
    manifest = Path(tuning['freeway']['lane_plant'])
    doc = read(manifest)
    paths = {k: runtime.read_pin(p) for k,p in doc['sources'].items()}
    context = observer.load_context(doc, paths, manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
    geometry = read(paths['geometry'])
    fw_links = set(map(int, geometry['addresses']))
    ramps = {int(b['connector']) for b in geometry['boundaries'] if b['kind'] == 'ramp'}
    results = []
    for end in range(150, 2251, 150):
        raws = [read(folder/f'state_{end:06d}.json') for folder in (OLD,NEW)]
        derived = [observer.derive(raw,context) for raw in raws]
        original = read(OLD/'obs150'/f'derived_{end:06d}.json')
        assert derived[0] == original, ('Original derivation changed',end)
        for arm, d in zip(('old','new'),derived):
            (OUT/f'{arm}_{end:06d}.json').write_bytes(oc.derived_bytes(d))
        # run_id and inputs record provenance; every other derived field is
        # compared exactly, including head-service windows and lane boundaries.
        differing = [k for k in derived[0] if k not in ('run_id','inputs') and derived[0][k] != derived[1][k]]
        bundles = [oc.load_bundle(raw) for raw in raws]
        frames = []
        for key in ('frame_start','frame_end'):
            pair = [getattr(b,key)['vehicles'] for b in bundles]
            # VSL state uses mainline vehicle records, but only counts on ramps.
            fw_equal = [v for v in pair[0] if int(v[1]) in fw_links] == [v for v in pair[1] if int(v[1]) in fw_links]
            ramp_equal = all(sum(int(v[1])==r for v in pair[0]) == sum(int(v[1])==r for v in pair[1]) for r in ramps)
            frames.append(dict(frame=key,mainline_records_exact=fw_equal,ramp_stocks_exact=ramp_equal))
        current = {k:raws[0][k] == raws[1][k] for k in raws[0]
                   if k not in ('network_path','sim_period_sec','run_provenance','obs150','lane_plant_observation')}
        results.append(dict(end_sec=end,derived_physical_differences=differing,frames=frames,
            current_physical_different=[k for k,equal in current.items() if not equal],
            local_scan_ok_equal=raws[0]['local_observation'].get('scan_ok') == raws[1]['local_observation'].get('scan_ok')))
        print(json.dumps(results[-1]),flush=True)
    assert all(not r['derived_physical_differences'] and r['local_scan_ok_equal']
               and all(f['mainline_records_exact'] and f['ramp_stocks_exact'] for f in r['frames']) for r in results)
    assert not results[-1]['current_physical_different']
    report = dict(stage='observer_payloads_exact',checks=results,input_sha256=pins,
        head_and_vsl_reinitialization_performed=False,original_native_prefix_reproduction_passed=False,
        new_forecasts=0,new_native_runs=0,fzp_scans=0,
        limitation='This verifies observer payloads and VSL physical frame inputs, not the full historical observer execution or past command readbacks.')
    (OUT/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
