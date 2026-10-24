"""Independent bounded same-cardinality cfg mutation audit; no model solve."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from diagnostics.test_prehead_dispatch_optimization import fixture, CANDIDATE, original

ROOT = Path(__file__).resolve().parents[1]


def result(call):
    try:
        return {'returned': call()}
    except Exception as exc:
        return {'exception': type(exc).__name__, 'message': str(exc)}


def main():
    paths = list((ROOT/'evaluation/controllers').glob('*.py')) + list((ROOT/'vendor').rglob('*.py')) + [
        ROOT/'diagnostics/prepare_prehead_dispatch_optimization.py',
        ROOT/'diagnostics/prehead_dispatch_optimization.patch',
        ROOT/'diagnostics/test_prehead_dispatch_optimization.py', Path(__file__)]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    cases = []
    for mutation in ('branch_movement', 'origin', 'wn_membership', 'kind'):
        cfg, state = fixture()
        CANDIDATE.prepare_dispatch_index(cfg)
        source = cfg.network.native_internal_inputs['inputs']
        source_count = len(source)
        row = source['1093']
        if mutation == 'branch_movement':
            row['prehead_spec']['branches']['2']['movement'] = 'C'
            old = result(lambda: original.limit_intended(deepcopy(state), cfg, 'C', 4., 8., 180))
            new = result(lambda: CANDIDATE.limit_intended(deepcopy(state), cfg, 'C', 4., 8., 180))
        elif mutation == 'origin':
            row['prehead_spec']['origin'] = 'empty_origin'
            cfg.network.urban_link_storage_veh['empty_origin'] = 100.
            state.urban_link_storage['empty_origin'] = 100.
            old = result(lambda: original._check(deepcopy(state), cfg))
            new = result(lambda: CANDIDATE._check(deepcopy(state), cfg))
        else:
            if mutation == 'wn_membership': row['prehead_spec']['wn_movements'] = ['B', 'C']
            else: row['kind'] = 'irrelevant'
            state.urban_movement_queue['A'] -= 2.
            def receive(module):
                copied = deepcopy(state)
                module.receive_accepted(copied, cfg, 'A', 2., 180)
                return copied.native_input_prehead_state
            old = result(lambda: receive(original))
            new = result(lambda: receive(CANDIDATE))
        assert old != new, mutation
        assert len(source) == source_count
        assert cfg.network.native_prehead_dispatch_index['source_inputs'] is source
        assert CANDIDATE._dispatch_index(cfg) is not None
        cases.append({'mutation': mutation, 'same_source_identity': True, 'same_source_count': True,
                      'index_remained_active': True, 'original': old, 'indexed_proposal': new})
    query = r"native_internal_inputs\s*=|native_internal_inputs\[|native_internal_inputs.*(update|pop|clear|setdefault)|prehead_spec\[|prehead_spec.*(update|pop|clear|setdefault)"
    scan = subprocess.run(['rg', '-n', query, 'evaluation', 'vendor'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if scan.returncode not in (0, 1): raise RuntimeError(scan.stderr)
    report = {'schema': 'prehead-dispatch-independent-review/v1',
        'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
        'production_applied': False, 'endpoint_or_optimizer_executed': False,
        'recommendation': 'Do not apply identity/count-only index without an enforced immutable or full-value invalidation contract.',
        'scope': 'Actual original and proposed methods on synthetic valid prehead state; all four cases mutate cfg after index construction. Not evidence of mutation during current live runs.',
        'writer_search': {'command': ['rg', '-n', query, 'evaluation', 'vendor'], 'stdout': scan.stdout,
                          'interpretation': 'Only direct assignment is native_internal_input.configure. Alias-based mutation absence requires reviewed consumers too; this search alone cannot prove deep immutability.'},
        'cases': cases, 'source_sha256': before,
        'source_changes': [str(p.relative_to(ROOT)) for p in paths if hashlib.sha256(p.read_bytes()).hexdigest()!=before[str(p.relative_to(ROOT))]]}
    out = ROOT/'diagnostics/prehead_dispatch_independent_review.json'
    out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'cases':len(cases), 'source_changes':report['source_changes'], 'output':str(out)}, indent=2))


if __name__ == '__main__': main()
