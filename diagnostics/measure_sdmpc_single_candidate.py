"""Time the current SDMPC with one budget candidate and two outer iterations.

Reuse the qualified full-decision harness and its exact saved runtime. Only its
leader-candidate count is read from the explicit benchmark config. No controller
method is replaced, no previous prediction cache is imported, and no VISSIM runs.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from diagnostics import check_sdmpc_three_blocks as runtime
    from diagnostics import check_sdmpc_full_decision as harness
    source, output, config = map(Path, sys.argv[1:4])
    tuning = json.loads(config.read_text(encoding='utf-8'))
    base_path = ROOT / 'diagnostics/sdmpc_stream_summary_20260922/config_candidate.json'
    original_tuning = json.loads(base_path.read_text(encoding='utf-8'))
    expected = json.loads(json.dumps(original_tuning))
    expected['adapter']['joint_owner_game']['max_leader_candidates'] = 1
    if tuning != expected:
        raise ValueError('Only max_leader_candidates may differ from the qualified config')
    original_context = runtime.context

    def one_candidate_context(request):
        coord, callbacks, ctx, options = original_context(request)
        policy = request['owned'][0].cfg.network.sdmpc_options
        if policy['max_iterations'] != 2 or policy['derivative_workers'] != 8:
            raise ValueError('Expected two outer iterations and eight workers')
        before = dict(options)
        options = dict(options, max_leader_candidates=tuning['adapter']['joint_owner_game']['max_leader_candidates'])
        path = Path(__file__).resolve()
        request['bootstrap']['runtime_sources'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        (output / 'benchmark_contract.json').write_text(json.dumps(dict(
            algorithm='Current VISSIM SDMPC; 8c01693 port NOT implemented',
            source_request=str(source.resolve()), candidate_count=1,
            max_iterations_per_candidate=2, workers=8, old_options=before,
            effective_options=options, config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
            horizon_sec=450, control_blocks=3, state_sec=900,
            fresh_process=True, reuses_prior_prediction_results=False,
            scope='Whole decision including initial prediction, optimization and in-model final validation; no separate exact audit'),
            indent=2) + '\n', encoding='utf-8')
        return coord, callbacks, ctx, options

    # Adapt the diagnostic harness's configuration boundary, never its solver.
    runtime.context = one_candidate_context
    try:
        harness.main()
    finally:
        runtime.context = original_context
    result = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    if not result['completed'] or result['source_changes']:
        raise RuntimeError('Benchmark did not complete with unchanged sources')
    candidates = result['selection']['candidates']
    if len(candidates) != 1:
        raise RuntimeError('Benchmark ran more than one budget candidate')
    print(json.dumps(dict(benchmark_verified=True, wall_sec=result['wall_sec'],
                         candidate_count=1, max_iterations_per_candidate=2,
                         accepted_iterations=candidates[0]['accepted_steps'],
                         converged=result['selection']['converged']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
