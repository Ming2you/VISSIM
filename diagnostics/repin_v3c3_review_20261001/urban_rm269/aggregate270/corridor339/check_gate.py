"""Recorded-state regression for source-entry coverage; no model forecasts."""
from pathlib import Path
from copy import deepcopy
import hashlib, json, pickle, xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339 import gate_coverage as new
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331 import gate_coverage as old
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.control_area_objective import get_ledger

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = HERE.parents[4]


def main():
    np = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    network = np.read_bytes()
    results = {}
    pins = {str(np): hashlib.sha256(network).hexdigest()}
    for at in (2400, 3300, 2700):
        if at == 2700:
            path = A/'validation282/forecast2700_v3/initial.pickle'
            source = Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')
        else:
            folder = A/f'transfer331/build{at}_v2'
            path = folder/'canonical.pickle'
            source = Path(json.loads((folder/'summary.json').read_bytes())['source'])
        cfg, state, _ = pickle.loads(path.read_bytes())
        raw, frame, current_pins = load(source, at)
        pins.update(current_pins)
        pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        lanes = adapter._contiguous_stopline_queue(raw, per_lane=True)
        before = pickle.dumps(state, protocol=5)
        changed_cfg = deepcopy(cfg)
        with new.enabled(changed_cfg, network) as coverage:
            changed, receipt = new.gate.install(changed_cfg, state, raw, frame, network, lanes)
        assert pickle.dumps(state, protocol=5) == before
        assert all(abs(sum(v[side] for v in get_ledger(state).stocks.values()) -
                       sum(v[side] for v in get_ledger(changed).stocks.values())) < 1e-8
                   for side in ('inside', 'outside'))
        if at != 2700:
            legacy_cfg = deepcopy(cfg)
            with old.enabled(network):
                legacy, legacy_receipt = new.gate.install(legacy_cfg, state, raw, frame, network, lanes)
            diffs = [k for k in set(vars(legacy)) | set(vars(changed))
                     if not equal(getattr(legacy, k, None), getattr(changed, k, None))]
            assert not diffs, (at, diffs)
            assert equal(legacy_receipt, receipt)
            receipt['legacy_state_exact'] = True
        else:
            row = next(r for r in frame['vehicles'] if r[1] == 10199)
            projected = next(r for r in receipt['current_initial'] if r['vehicle'] == row[0])
            assert projected['pre_signal'] and projected['movement'] is None
            assert projected['gate_due_sec'] > at and projected['post_sec'] > 0
            assert '10199' in coverage['entry_paths']
            # Prove that the old path rejected this independently observed stock.
            try:
                with old.enabled(network):
                    new.gate.install(deepcopy(cfg), state, raw, frame, network, lanes)
            except ValueError as exc:
                assert str(exc) == 'Uncovered source-owned current link'
            else:
                raise AssertionError('Expected the pre-fix recorded failure')
            bad = list(row); bad[9] = 123456
            try:
                new.current_route(bad, ET.fromstring(network), coverage['entry_paths'], new.gate.current_route)
            except ValueError as exc:
                assert 'next connector' in str(exc)
            else:
                raise AssertionError('Contradictory current route accepted')
        receipt['coverage'] = coverage
        results[str(at)] = receipt
        print('GATE_CHECK', at, receipt.get('legacy_state_exact'), len(receipt['current_initial']), flush=True)
    pins.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), Path(new.__file__))})
    report = dict(status='passed_three_recorded_states_and_bad_next_route', states=results,
                  source_pins=pins, forecasts=0, fits=0, native_runs=0)
    (HERE/'check_gate.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__':
    main()
