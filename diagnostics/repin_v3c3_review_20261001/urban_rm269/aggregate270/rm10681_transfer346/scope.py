"""Reuse the completed isolated10681 experiment in the current Omega701.

Full per-link costs may be subtracted because the exact native prefix is
identical. They must not be labelled absolute450s costs. No FZP is read.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = HERE.parents[4]
OLD = ROOT / 'diagnostics/repin_v3c3_review_20261001/rm_restart219/native238'
COMMANDS = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/native_rm10681_reopen4650_238'
MEMBERSHIP = ROOT / 'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'
SOURCE = Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE / 'scope.json').exists(), 'Preserve completed evidence'
    summary = read(OLD / 'analysis/summary.json')
    protocol = read(COMMANDS / 'protocol.json')
    assert summary['counterfactual_valid'] and summary['paired_prefix_exact']
    assert summary['original_initial_history_exact'] and summary['start_sec'] == 4650 and summary['end_sec'] == 5100
    assert summary['prefixes']['hold'] == summary['prefixes']['selected'] == summary['original_prefix']
    assert all(x['native_execution_passed'] for x in summary['arms'].values())
    assert protocol['network_sha256'] == sha(protocol['network'])
    assert protocol['seed'] == 29
    inside = set(map(str, read(MEMBERSHIP)['inside_links']))
    assert len(inside) == 701
    metrics = {arm: read(OLD / 'analysis' / arm / 'area_metrics.json') for arm in ('hold', 'selected')}
    links = set().union(*(d['physical_link_residence'] for d in metrics.values()))
    delta = {k: metrics['selected']['physical_link_residence'].get(k, {}).get('ttt_veh_h', 0.) -
                metrics['hold']['physical_link_residence'].get(k, {}).get('ttt_veh_h', 0.) for k in links}
    old_inside = {k for d in metrics.values() for k, v in d['physical_link_residence'].items() if v['inside']}
    legacy_delta = sum(v for k, v in delta.items() if k in old_inside)
    assert abs(legacy_delta - summary['delta_TTT_veh_h']) < 1e-7
    # Compare the actual commands, including all other meters, not their labels.
    fields = ('N_P_star', 'N_UF_star', 'green_times', 'offsets', 'vsl', 'inflow_outflow_allocation')
    commands = {}
    for t in (4650, 4800, 4950):
        hold = read(OLD / 'held_writer' / f'action_{t:06}.json')
        selected = read(COMMANDS / 'selected/commands' / f'action_{t:06}.json')
        for key in fields:
            assert hold[key] == selected[key], (t, key)
        assert all(hold['ramp_metering'][k] == v for k, v in selected['ramp_metering'].items() if k != 'RM_C10681')
        commands[t] = {a: d['diagnostics']['rw_meter_green_RM_C10681'] for a, d in [('hold', hold), ('selected', selected)]}
    assessment = read(OLD / 'assessment.json')
    result = dict(status='scope_verified', start_sec=4650, end_sec=5100, seed=29,
        actual_commands=commands, prefix_exact_rows=summary['original_prefix']['rows'],
        comparison='selected minus hold; exact common prefix cancels',
        old_omega_delta=legacy_delta, omega701_delta=sum(v for k, v in delta.items() if k in inside),
        outside701_delta=sum(v for k, v in delta.items() if k not in inside),
        added_area_delta=sum(v for k, v in delta.items() if k in inside - old_inside),
        physical_link_delta=delta,
        focus_physical_link_delta={k: delta.get(k, 0.) for k in ('52','66','68','121','10681')},
        ramp_native={a: d['actual'] for a, d in assessment['ramp10681'].items()},
        forecasts=0, optimizer=0, native=0, fzp_scans=0,
        limitations=['Cached5s sampled costs; original final4.9s tail hold retained.',
            'The old whole-Omega number used a smaller area. Only resummed differences are comparable with701.',
            'Old hold10681 green0 is a historical actuator reference, not a legal new minimum2 candidate.',
            'Selected was outside its inherited NUF cap. Physical response is not feasible SDMPC selection proof.',
            'State4650 was used by the old model, but not to fit the frozen331 aggregate corrections.',
            'Missing LSA is preserved; original native execution uses approved LDP evidence.'],
        source_pins={str(p): sha(p) for p in [Path(__file__), MEMBERSHIP, OLD/'assessment.json',
            OLD/'analysis/summary.json', COMMANDS/'protocol.json', Path(protocol['network']),
            *[OLD/'analysis'/a/'area_metrics.json' for a in metrics],
            *[OLD/'held_writer'/f'action_{t:06}.json' for t in commands],
            *[COMMANDS/'selected/commands'/f'action_{t:06}.json' for t in commands]]})
    (HERE/'scope.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ('status','omega701_delta','old_omega_delta','added_area_delta','focus_physical_link_delta','actual_commands')}))


if __name__ == '__main__':
    main()
