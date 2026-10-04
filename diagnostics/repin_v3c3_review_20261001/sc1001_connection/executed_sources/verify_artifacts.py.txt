"""Archive the tested boundary candidate and check saved evidence; no rollout."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVIEW = HERE.parent
INTEGRATION = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def functions(path):
    result = {}
    def visit(node, prefix=''):
        for item in getattr(node, 'body', []):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[prefix + item.name] = ast.dump(item, include_attributes=False)
            elif isinstance(item, ast.ClassDef):
                visit(item, prefix + item.name + '.')
    visit(ast.parse(path.read_text(encoding='utf-8-sig')))
    return result


def differences(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in sorted(a.keys() | b.keys()):
            child = path + '/' + key
            if key not in a:
                out.append({'path': child, 'before_present': False, 'after': b[key]})
            elif key not in b:
                out.append({'path': child, 'before': a[key], 'after_present': False})
            else:
                out.extend(differences(a[key], b[key], child))
        return out
    return [] if a == b else [{'path': path, 'before': a, 'after': b}]


def main():
    before = json.loads((HERE / 'before.json').read_bytes())
    changes = {}
    for rel, expected in before.items():
        current = ROOT / rel
        snapshot = HERE / (current.name + '.before.txt')
        assert sha(snapshot) == expected, rel
        old, new = functions(snapshot), functions(current)
        changes[rel] = {
            'before_sha256': expected, 'after_sha256': sha(current),
            'changed_functions': sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
            'added_functions': sorted(new.keys() - old.keys()),
            'removed_functions': sorted(old.keys() - new.keys()),
        }
        assert not changes[rel]['removed_functions'], rel
    assert changes['evaluation/controllers/physical_ramp_branches.py']['after_sha256'] == before['evaluation/controllers/physical_ramp_branches.py']

    pins = json.loads((REVIEW / 'visit_routing_verification.json').read_bytes())['core_pins']
    pins.pop('evaluation/controllers/lane_plant_runtime.py')
    base = INTEGRATION / 'expanded036_9000_20260930/loss_onset2250/source_sc101/readiness_candidate/candidate_config.json'
    pins[str(base.relative_to(ROOT))] = '9b613bfb151a417a6a8f0c131d316f96e839570473aecca2cb841e27361b2883'
    for rel, expected in pins.items():
        assert sha(ROOT / rel) == expected, rel

    candidate = HERE / 'candidate_config.json'
    delta = differences(json.loads(base.read_bytes()), json.loads(candidate.read_bytes()))
    assert delta == [{'path': '/urban/shared_sc1001_approach', 'before_present': False, 'after': 'boundary_only_v1'}], delta
    assert sha(candidate) == 'f319982bba1baab0d1104af45d48d31bfd5748771fac1e0eb2bb073d61c7e23f'
    assessment = json.loads((HERE / 'assessment.json').read_bytes())
    for rel, expected in assessment['source_pins'].items():
        assert sha(ROOT / rel) == expected, rel
    test_log = (HERE / 'unit_tests_quantity_fixed.log').read_text(encoding='utf-8-sig')
    assert 'Ran 16 tests' in test_log and test_log.rstrip().endswith('OK')
    pair = json.loads((HERE / 'sc1001_pair3.json').read_bytes())
    assert pair['status'] == 'CANONICAL_PAIR_FORECAST_PASS'
    assert pair['forecasts'] == 2 and pair['mass_ledger_matches']

    sources = [ROOT / rel for rel in before if rel != 'evaluation/controllers/physical_ramp_branches.py']
    sources += [ROOT / 'diagnostics/test_shared_signal_approach.py', HERE / 'check_connection.py', HERE / 'summarize.py', Path(__file__).resolve()]
    archive = HERE / 'executed_sources'
    archive.mkdir(exist_ok=True)
    source_pins = {}
    for source in sources:
        # Paths are unique within this small, explicit source set.
        target = archive / (source.name + '.txt')
        if target.exists():
            assert target.read_bytes() == source.read_bytes(), target
        else:
            target.write_bytes(source.read_bytes())
        source_pins[str(source.relative_to(ROOT))] = sha(source)
    result = {
        'status': 'ARTIFACTS_VERIFIED_BOUNDARY_CANDIDATE_NOT_GAIN_QUALIFIED',
        'upstream_commit': 'bd39205d7f0b2178ae9cd3be1232e00a84ee666f',
        'function_changes_from_turn_snapshot': changes,
        'unchanged_core_pins': pins,
        'candidate_config_difference': delta,
        'candidate_config_sha256': sha(candidate),
        'executed_source_pins': source_pins,
        'assessment_sha256': sha(HERE / 'assessment.json'),
        'saved_unit_tests': {'passed': 16, 'log_sha256': sha(HERE / 'unit_tests_quantity_fixed.log'), 'rerun_in_this_verifier': False},
        'execution': {'completed_450s_forecasts': 5, 'final_comparison_forecasts': 2,
            'initial_failure': 'Existing downstream ownership at10695; preserved/fixed before successful init2.',
            'pair2_failure': 'After first forecast, diagnostic follower reference absent; fixed in harness, final pair3 passed.',
            'final_pair': 'pair3', 'final_pair_status': pair['status'],
            'new_native_runs': 0, 'fzp_rescans': 0, 'coefficient_fits': 0, 'sdmpc_selections': 0, 'pushes': 0},
        'qualification': {'goal': 'ACTIVE / NOT_QUALIFIED', 'operational_default_enabled': False,
            'full_rollout_derivative_verified': False, 'new_independent_state_or_seed_verified': False,
            'new_four_arm_vsl_rm_response_verified': False,
            'remaining': ['Shared head discharge still low (130.28 vs native180–186 vehicles).',
                '58 initial vehicles lack causal city/off source classification for N_P.',
                'Future origin-specific routing and upstream city timing remain prior approximations.',
                'RM rank preserved; no material improvement of RM gain error established.']},
    }
    (HERE / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'changed_functions': changes, 'archived_sources': len(sources)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
