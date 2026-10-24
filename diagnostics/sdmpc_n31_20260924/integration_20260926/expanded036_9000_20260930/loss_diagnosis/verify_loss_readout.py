"""Summarize completed-run caches only. No model, COM, or live-run access."""
import csv
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {}


def read(relative, table=False):
    path = HERE / relative
    data = path.read_bytes()
    PINS[relative] = hashlib.sha256(data).hexdigest()
    text = data.decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text))) if table else json.loads(text)


def main():
    summary = read('summary.json')
    omega = read('omega_delta_5s.csv', True)
    links = read('link_contributions_exact5s.csv', True)
    cells = read('physical_cell_snapshots_150s.csv', True)
    errors = read('saved_one_step_count_errors.csv', True)
    onset = read('early_onset/summary.json')
    decisions = read('../analysis/sdmpc_decisions.json')['decisions']
    rows = []
    for time in (1500, 1650, 1800, 2100, 2250, 3300, 3900, 4500, 4800, 6000, 7500, 9000):
        groups = defaultdict(lambda: {'nc': 0, 'sdmpc': 0})
        for r in cells:
            if float(r['sim_sec']) != time or r['road'] != 'FW_E':
                continue
            cell = int(r['cell'])
            group = 'upstream_0_9' if cell < 10 else 'middle_10_20' if cell < 21 else 'merge_21_23' if cell < 24 else 'downstream_24_30'
            groups[group][r['arm']] += int(r['n'])
        assert len(groups) == 4
        o = min(omega, key=lambda r: abs(float(r['sim_sec']) - time))
        row = {'snapshot_sec': time, 'omega_sample_sec': float(o['sim_sec']),
               'cumulative_delta_TTT_veh_h': float(o['delta_TTT_veh_h'])}
        row.update({g + '_delta_n': v['sdmpc'] - v['nc'] for g, v in groups.items()})
        row['east_delta_n'] = sum(v['sdmpc'] - v['nc'] for v in groups.values())
        # Aggregate signed errors, retaining location; do not call this causal attribution.
        for lo, hi in ((0, 9), (10, 20), (21, 23), (24, 30)):
            rr = [r for r in errors if float(r['target_sec']) == time and r['road'] == 'FW_E' and lo <= int(r['cell']) <= hi]
            assert len(rr) == hi - lo + 1
            row[f'one_step_error_cells_{lo}_{hi}'] = sum(float(r['error_pred_minus_actual_n']) for r in rr)
        rows.append(row)
    total = float(omega[-1]['delta_TTT_veh_h'])
    assert abs(sum(float(r['delta_TTT_veh_h']) for r in links) - total) < 1e-7
    assert all(r['conservation_residual'] == 0 for r in onset['flows'])
    for d in decisions:
        assert d['written_command_binding_passed'] and d['command_bounds_and_slew_passed']
        assert abs(d['held_surrogate_objective_veh_h'] - d['selected_surrogate_objective_veh_h'] - d['predicted_reduction_from_held_veh_h']) < 1e-7
    periods = summary['periods']
    result = {'scope': 'Completed seed29 expanded036 versus NC; no current CTG evaluation.',
              'sign': 'SDMPC minus NC; positive TTT means loss.',
              'rows': rows,
              'decision_count': len(decisions),
              'predicted_improvement_over_1e_6_count': sum(d['predicted_reduction_from_held_veh_h'] > 1e-6 for d in decisions),
              'held_equivalent_count': sum(abs(d['predicted_reduction_from_held_veh_h']) <= 1e-6 for d in decisions),
              'converged_count': sum(bool(d['sdmpc_converged']) for d in decisions),
              'rm_restricted_count': sum(bool(d['restricted_meters']) for d in decisions),
              'loss_after_6000_veh_h': sum(r['delta_TTT_veh_h'] for r in periods if r['start_s'] >= 6000),
              'loss_after_6000_fraction_of_net_loss': sum(r['delta_TTT_veh_h'] for r in periods if r['start_s'] >= 6000) / total,
              'source_sha256': PINS,
              'limitations': ['150s instantaneous spatial snapshots; not FZP-average heatmap.',
                              'One-step errors are executed-command forecasts, not alternative-policy ranks.',
                              'Decisions have different initial states; predicted improvements are not summed.',
                              'Policy pair does not isolate a single lever causal effect.'],
              'checks_passed': True}
    output = HERE / 'verified_loss_readout.json'
    assert not output.exists(), 'Preserve existing evidence; do not overwrite.'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'source_sha256', 'limitations')}, ensure_ascii=False))
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == '__main__':
    main()
