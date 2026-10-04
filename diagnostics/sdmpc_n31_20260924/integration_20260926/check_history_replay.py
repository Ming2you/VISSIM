"""Replay closed R3 observations in scratch; never edit native evidence or run VISSIM."""
from pathlib import Path
from types import SimpleNamespace as NS
import copy
import hashlib
import json
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.lane_plant_runtime import bin_frame, _physical_sign_heads
from evaluation.controllers.vsl_exposure_history import initialize

SOURCE = ROOT.parent / 'sd31'
NATIVE = Path('D:/VISSIM_runs/20260924_sd31_gain/sdmpc31_g_gain_s29_r3/decisions_sdmpc31_g_gain_s29_r3')


def load(path):
    return json.loads(path.read_bytes())


def main():
    pins = {}
    def pinned(path):
        data = path.read_bytes()
        pins[str(path)] = hashlib.sha256(data).hexdigest()
        return data

    geometry = json.loads(pinned(SOURCE / 'diagnostics/sdmpc_n31_20260924/port_gain/geometry.json'))
    reference = json.loads(pinned(SOURCE / 'diagnostics/sdmpc_n31_20260924/port_gain/candidate.json'))
    network = Path(geometry['network']['path'])
    assert hashlib.sha256(pinned(network)).hexdigest() == geometry['network']['sha256']
    mapping = json.loads(pinned(SOURCE / reference['mapping_json']))
    groups = [dict(road=s['model_link'], parent=int(s['model_segment_index']),
                   dsds=[int(d['dsd_no']) for d in s['dsds']]) for s in mapping['segments'] if s.get('dsds')]
    transport = reference['freeway']['component_vsl_transport']
    config = NS(network=NS(physical_vsl_sign_binding=True, physical_vsl_groups=groups),
                freeway_follower=NS(vsl_set=[float(v) for v in range(50, 111, 10)]))
    confs = {r: NS(network=NS(component_vsl_transport=transport), simulation=NS(T_f_sec=1)) for r in transport}
    previous = json.loads(pinned(NATIVE / 'obs150/vsl_cohorts_000750.json'))
    context = dict(plant_mode='v2', manifest_sha256=previous['manifest_sha256'], geometry=geometry,
                   paths={'network': network}, component=NS(base=NS(network=NS(component_vsl_transport=transport))))
    checks = []
    with tempfile.TemporaryDirectory(prefix='history_replay_', dir=HERE) as directory:
        scratch = Path(directory)
        (scratch / 'obs150').mkdir()
        (scratch / 'obs150/vsl_cohorts_000750.json').write_bytes(pinned(NATIVE / 'obs150/vsl_cohorts_000750.json'))
        (scratch / 'vsl_readback.csv').write_bytes(pinned(NATIVE / 'vsl_readback.csv'))
        for end in (900, 1050, 1200, 1350):
            native = json.loads(pinned(NATIVE / f'state_{end:06d}.json'))
            obs = copy.deepcopy(native[oc.RAW_STATE_KEY])
            for frame in obs['frames'].values():
                original = NATIVE / frame['path']
                data = pinned(original)
                assert hashlib.sha256(data).hexdigest() == frame['sha256']
                target = scratch / frame['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            obs['directory'] = str(scratch)
            derived = json.loads(pinned(NATIVE / f'obs150/derived_{end:06d}.json'))
            vehicles = load(scratch / obs['frames']['current']['path'])['vehicles']
            state = NS(lane_freeway_runtime=NS(configs=confs), freeway_density={}, freeway_effective_lanes={})
            for road in confs:
                cells, rows, dropped = bin_frame(geometry, vehicles, road, drop_before_start=True)
                assert not dropped
                lanes = [c['lane_km'] / c['length_km'] for c in cells]
                state.freeway_effective_lanes[road] = lanes
                state.freeway_density[road] = [len(row) / (cell['length_km'] * lane) for row, cell, lane in zip(rows, cells, lanes)]
            metadata = initialize(context, {oc.RAW_STATE_KEY: obs, oc.MERGED_DERIVED_KEY: derived}, state, config)
            actual_path = scratch / f'obs150/vsl_cohorts_{end:06d}.json'
            expected_bytes = pinned(NATIVE / f'obs150/vsl_cohorts_{end:06d}.json')
            if actual_path.read_bytes() != expected_bytes:
                (HERE / f'history_mismatch_{end}_actual.json').write_bytes(actual_path.read_bytes())
                (HERE / f'history_mismatch_{end}_expected.json').write_bytes(expected_bytes)
                actual, expected = load(actual_path), json.loads(expected_bytes)
                print('receipt differences', {k: {'actual': actual[k], 'expected': expected[k]} for k in actual if actual[k] != expected[k] and k != 'cohorts'})
                raise AssertionError(f'Receipt differs at {end}')
            # Consumers must retain the posterior through an independent candidate copy.
            original_cohorts = {r: copy.deepcopy(e.cohorts) for r, e in state._component_vsl_exposure.items()}
            future = copy.deepcopy(state)
            assert future._component_vsl_exposure is not state._component_vsl_exposure
            for exp in future._component_vsl_exposure.values():
                assert all(value == 0 for row in exp.tangents for value in row.values())
                n = [sum(row.values()) for row in exp.cohorts]
                exp.advance(n, n, [0.] * (len(n)-1), [0.] * len(n), 0., [0.] * len(n), [110.] * len(n))
            for road, exp in future._component_vsl_exposure.items():
                for before, after in zip(original_cohorts[road], exp.cohorts):
                    assert all(abs(before.get(c, 0.) - after.get(c, 0.)) < 1e-12 for c in before.keys() | after.keys())
                assert state._component_vsl_exposure[road].cohorts == original_cohorts[road]
            checks.append(dict(cutoff=end, receipt_byte_exact=True, audit=metadata['observed_vsl_history']['audit']))
        # Verify sign ownership uses the physical groups on this unchanged historical geometry.
        head_of = _physical_sign_heads(context, config.network, 'FW_E', [0, 5, 10, 15])
        assert len(head_of) == 31
    report = dict(status='PASS', scope='Existing R3 seed29 closed observation replay; not gain or future prediction validation',
                  checks=checks, physical_head_of_cell=head_of, source_sha256=pins)
    (HERE / 'history_native_replay.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(dict(status=report['status'], byte_exact_receipts=len(checks), cutoffs=[x['cutoff'] for x in checks])))


if __name__ == '__main__':
    main()
