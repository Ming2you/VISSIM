"""Verify saved, bounded north-route diagnostics; no forecasts or VISSIM."""
import gzip
import hashlib
import json
import math
from pathlib import Path

from evaluation.controllers import obs150_contract as oc

HERE = Path(__file__).resolve().parent
OUT = HERE / 'north_prior221'
ROOT = HERE.parents[2]
DEC = Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')


def read(path):
    return json.loads(path.read_bytes())


def main():
    protocol = read(OUT / 'protocol.json')
    completion = read(OUT / 'completion.json')
    assert completion == dict(status='COMPLETE', source_and_inputs_unchanged=True, STOP_unchanged=True)
    for rel, digest in protocol['source_sha256'].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel
    for path, digest in protocol['inputs'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    stop = protocol['STOP']
    assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest() == stop['sha256']
    prior = read(OUT / 'north_prior.json')
    weights = {k: v['weight'] for k, v in prior['evidence'].items()}
    assert sum(weights.values()) == 8
    assert {k: v / 8 for k, v in weights.items()} == prior['replacement_beta']

    reports = {}
    initial = None
    for arm in ('baseline', 'native_prior'):
        folder = OUT / arm
        report = read(folder / 'summary.json')
        parity = read(folder / 'endpoint_parity.json')
        assert report['status'] == 'PASS'
        if arm == 'baseline':
            assert parity['exact'] and len(parity['fields']) == 93
        rows = json.loads(gzip.decompress((folder / 'receipts.json.gz').read_bytes()))
        assert len(rows) == 1200
        stock_initial = {k: v['initial'] for k, v in report['ramps'].items()}
        if initial is None:
            initial = stock_initial
        else:
            assert initial == stock_initial
        errors = []
        for ramp, result in report['ramps'].items():
            rr = [r for r in rows if r['ramp'] == ramp]
            assert len(rr) == 150
            arrivals = math.fsum(r['after_finish']['cumulative_admitted_veh'] - r['before']['cumulative_admitted_veh'] for r in rr)
            merges = math.fsum(r['receipt']['accepted_merge_veh'] for r in rr)
            heads = math.fsum(r['receipt']['head_service_veh'] for r in rr)
            for got, expected in ((arrivals, result['predicted']['arrivals']), (merges, result['predicted']['merge']), (heads, result['predicted']['head'])):
                assert abs(got - expected) < 1e-9
            residual = result['initial']['connector_veh'] + arrivals - merges - result['end']['connector_veh']
            errors.append(abs(residual))
            assert abs(residual) < 1e-9
        response = json.loads(gzip.decompress((folder / 'response.json.gz').read_bytes()))
        assert response['model_constraint_coverage']['complete']
        assert response['conditional_model_feasibility_witness']
        assert not response['physical_native_fidelity_certificate']
        transfers = {key: math.fsum(r['vehicles'] for r in response['transfers'] if r.get('source') == 'movement:' + key)
                     for key in ('SC1003_N_SC1001_to_S_SC1004', 'SC1004_N_SC1003_to_W')}
        reports[arm] = dict(prediction_wall_sec=read(folder / 'replayed_prediction.json')['wall_sec'],
            mass_residual_max=max(errors), transfers=transfers,
            ramps={k: dict(predicted=v['predicted'], errors=v['errors'], end=v['end']['connector_veh']) for k, v in report['ramps'].items()})

    # Independent cached native head counts. No COM or FZP read.
    raw_path = DEC / 'state_001050.json'
    raw = read(raw_path)
    bundle = oc.load_bundle(raw)
    assignment = oc.assign_window(bundle.obs, bundle.mer_rows)
    assert assignment.lag_ok and assignment.end_s == 1050
    detectors, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'], bundle.obs['detector_config']['sha256'])
    head = [d for d in detectors if d.role == 'head' and d.link == 39]
    lane_counts = {}
    through_ids = []
    for d in head:
        assert assignment.tails[d.dcp_no] == 0
        events = assignment.entries[d.dcp_no]
        lane_counts[str(d.lane)] = len(events)
        if d.lane in (1, 2):
            through_ids.extend(x.veh for x in events)
    assert lane_counts == {'1': 5, '2': 6, '3': 2, '4': 3}
    paths = read(HERE / 'upstream220v2/native_paths.json')
    arrivals_from39 = [x['veh'] for x in paths['arrivals'] if x['state900'] and x['state900']['link_no'] == 39]
    assert len(arrivals_from39) == 7 and set(arrivals_from39) <= set(through_ids)
    data = dict(status='PASS_BOUNDED_DIAGNOSTIC_NOT_GAIN_QUALIFICATION',
        predictions150=2, fits=0, native_runs=0, FZP_reads=0,
        initial_ramp_inventories_equal=True, source_and_inputs_unchanged=True, STOP_unchanged=True,
        reports=reports, native_head39=dict(lanes=lane_counts, connector10495_lanes=[1, 2],
            through_total=len(through_ids), later10681_ids=arrivals_from39,
            raw_state_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest()),
        limitations=['900--1050 only; no independent seed/congested-state or control-gain validation.',
            'Same initial projected state and actual command, but generic initial transit can be re-split by new beta.',
            'The diagnostic does not yet preserve observed destinations for all link46 initial vehicles.',
            'Physical-speed candidate remains OFF, and frozen native9000 runtime is unchanged.'])
    (OUT / 'verification.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=data['status'], predictions150=2, wall_sec=sum(x['prediction_wall_sec'] for x in reports.values()), native_head39=lane_counts)))


if __name__ == '__main__':
    main()
