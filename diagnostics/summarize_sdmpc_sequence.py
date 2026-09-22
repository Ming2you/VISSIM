"""Collect existing evidence only; never launch predictions or VISSIM."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagnostics/sdmpc_sequence_20260921'


def main():
    def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
    fifo={name:read(name+'/comparison.json') for name in ('fifo_h1','fifo_h3')}
    sequence=read('three_blocks_h3/comparison.json')
    directions=read('sequence_directions/report.json')
    proposal=read('sequence_proposal_v3/report.json')
    restoration=read('sequence_restoration/report.json')
    test_log=(OUT/'tests_final.log').read_text(encoding='utf-8-sig')
    tests=re.search(r'Ran (\d+) tests.*\bOK\b',test_log,re.DOTALL)
    if tests is None:raise ValueError('Completed passing test log required')
    if '파라미터 검사 PASS' not in (OUT/'verify_parameters_final.log').read_text(encoding='utf-8-sig'):
        raise ValueError('Passing parameter check required')
    current=[
        'evaluation/controllers/physical_urban_transport.py',
        'evaluation/controllers/lane_urban_runtime.py',
        'evaluation/controllers/sdmpc.py',
        'evaluation/controllers/sdmpc_sequence.py',
        'evaluation/controllers/sdmpc_tangent_worker.py',
        'evaluation/controllers/area_follower_objective.py',
        'diagnostics/test_sdmpc_fifo_batch.py',
        'diagnostics/test_sdmpc_sequence.py',
        'diagnostics/check_sdmpc_fifo.py',
        'diagnostics/check_sdmpc_three_blocks.py',
        'diagnostics/check_sdmpc_sequence_directions.py',
        'diagnostics/check_sdmpc_sequence_proposal.py',
        'diagnostics/check_sdmpc_sequence_transport.py',
        'diagnostics/check_sdmpc_sequence_restoration.py',
        'diagnostics/summarize_sdmpc_sequence.py',
        'diagnostics/sdmpc_sequence_20260921/config_candidate.json',
        'docs/SDMPC_SEQUENCE_20260921.md',
        'docs/SDMPC_CONTINUOUS_DERIVATIVES_20260921.md',
    ]
    files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in current}
    (OUT/'change_sources.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8')
    report=dict(schema='sdmpc-sequence-qualification/v1',state_sec=900,
        native_applied=False,full_sdmpc_decision=False,run_9000_started=False,
        reference_control_axes=77,sequence_control_axes=231,interval_sec=150,horizon_sec=450,
        fifo=fifo,sequence=sequence,directions=directions,
        native_model_proposal=dict(path='sequence_proposal_v3/report.json',
            feasible_candidates=proposal['feasible_candidates'],
            improving_feasible_candidates=proposal['improving_feasible_candidates'],
            qp_sec=proposal['qp_sec'],wall_sec=proposal['wall_sec'],
            source_equivalence=proposal['derivative_to_native_source_equivalence']),
        nonlinear_restoration=dict(path='sequence_restoration/report.json',
            feasible=restoration['feasible'],iterations=restoration['iterations'],wall_sec=restoration['wall_sec']),
        tests=dict(count=int(tests.group(1)),passed=True,path='tests_final.log'),
        parameters_verified=True,
        retained_failures=[dict(path='sequence_proposal.log',reason='SciPy sandbox access'),
                           dict(path='sequence_proposal_v2.log',reason='Unstable future payload pickle memo')],
        pending=['Complete SDMPC solve convergence/time','Short actual VISSIM application','9000s NC/CL comparison'],
        source_manifest='change_sources.json')
    (OUT/'qualification_summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['native_model_proposal']))


if __name__=='__main__':main()
