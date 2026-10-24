"""Close the bounded cell-fit experiment and restore its temporary source install."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / 'completion.json'
    assert not target.exists(), 'Already closed; do not repeat source restoration.'
    assessment = json.loads((HERE / 'assessment.json').read_bytes())
    fit = json.loads((HERE / 'fit.json').read_bytes())
    assert assessment['forecasts'] == 6 and fit['solver_success']
    executed = json.loads((HERE / 'executed_sources.json').read_bytes())
    before = json.loads((HERE / 'before.json').read_bytes())
    archive = HERE.parent / 'lane10682_target_transport/executed_sources'
    previous = json.loads((HERE.parent / 'lane10682_route_access/completion.json').read_bytes())
    stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert set(executed) == set(before) and len(before) == 7
    assert sha(stop) == previous['stop_sha256']
    # All owned forecast sessions exited before this closeout. Validate every
    # source and backup first, so another task's modifications are not replaced.
    for relative, digest in executed.items():
        assert sha(ROOT / relative) == digest, relative
        assert sha(archive / Path(relative).name) == digest, relative
        assert sha(HERE / (Path(relative).name + '.before')) == before[relative], relative
    for relative in before:
        (ROOT / relative).write_bytes((HERE / (Path(relative).name + '.before')).read_bytes())
    for relative, digest in before.items():
        assert sha(ROOT / relative) == digest, relative
    for path, digest in previous['production_exact'].items():
        assert sha(Path(path)) == digest, path
    assert sha(stop) == previous['stop_sha256']
    result = {
        'status': 'bounded_fit_evaluated_not_adopted_sources_restored',
        'goal_status': 'ACTIVE/NOT_QUALIFIED',
        'fit_cells': [11],
        'fit_parameters': ['rho_crit', 'nu_downstream_ge_local', 'nu_downstream_lt_local'],
        'fit_residual_calls': fit['residual_calls'],
        'forecasts': assessment['forecasts'],
        'forecast_compute_sec': assessment['wall_sec'],
        'owned_sessions': {'48766': 'EXIT0', '67041': 'EXIT0'},
        'source_archive_reused': str(archive),
        'source_archive_hashes': executed,
        'restored_exact': before,
        'previous_production_exact': previous['production_exact'],
        'stop_sha256': sha(stop),
        'mass_residual': assessment['mass_residual'],
        'route_residual': assessment['route_residual'],
        'resource_exceedance': assessment['resource_exceedance'],
        'engineering_tests': 'REVIEW50 22 PASS reused because all executed source bytes are identical; not rerun.',
        'new_equation_parity_rows': fit['executed_lane_equations'],
        'new_equation_parity_max_error': fit['exact_executed_lane_equation_max_error'],
        'new_native': 0, 'new_fzp_scans': 0, 'push': 0,
        'qualification': 'Cell11/12 speed improved, but seed47 upstream recovery and off-ramp entry worsened. No full cellwise calibration or gain qualification claim.',
        'next_causal_question': 'Does a frozen through-flow lane split inferred from only three vehicles create the false upstream queue? Current-window alternatives are diagnostics, not yet autonomous predictions.',
        'next_order': ['boundary/lane allocation and off-ramp entry/drain/storage', 'remaining cell coefficients', 'common-initial physical control gains and held-out response', 'SDMPC selection'],
        'limits': ['Both anticipation coefficients reached declared lower bounds; do not expand a coefficient grid to hide the structural error.', 'Seed47 pair changes urban signals, not RM release.', 'Small seed43 VSL cost sign is not the sole rejection reason.', 'No future observations were supplied to autonomous forecasts.'],
    }
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: result[key] for key in ('status', 'forecasts', 'forecast_compute_sec', 'new_native', 'new_fzp_scans')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
