"""Inspect one completed benchmark against retained cacheON, without reruns."""
import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'runtime_pair2400_numericfix'
spec=importlib.util.spec_from_file_location('retained_compare',BASE/'compare.py')
cmp=importlib.util.module_from_spec(spec);spec.loader.exec_module(cmp)
read=cmp.read

def main():
    out=HERE/'hot_full_comparison.json'
    assert not out.exists(),'Preserve completed comparison'
    plan=read(HERE/'hot_full_benchmark_plan.json')
    assert plan['status']=='complete_pending_quality_and_time_comparison' and plan['launches_consumed']==1
    for name,digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
    before=cmp.inspect(BASE/'cache_on',read(BASE/'cache_on.execution.json'))
    after=cmp.inspect(HERE/'hot_full',read(HERE/'hot_full.execution.json'))
    policies=[deepcopy(r['policy']) for r in (before,after)]
    for policy in policies:
        for flag in ('lazy_trial_derivatives','stock_geometry_hotpath'):policy.pop(flag,None)
    comparisons=dict(same_search_budget_and_physical_policy=cmp.difference(*policies),
        all_three_commands=cmp.difference(before['action_blocks'],after['action_blocks']),
        native_first_block_writer=cmp.difference(before['first_physical_csv'],after['first_physical_csv'],atol=0),
        costs_owners_and_constraints=cmp.difference(before['costs_and_constraints'],after['costs_and_constraints']))
    equivalent=not any(comparisons.values())
    target=after['external_process_wall_sec']<=600
    result=dict(status='equivalent' if equivalent else 'differences_require_review',
        target_full_decision_seconds=600,target_time_met=target,
        full_decision_quality_and_time_pass=equivalent and target,
        comparisons=comparisons,runs=dict(cache_on=before,hot_lazy=after),
        process_wall_reduction_percent=100*(1-after['external_process_wall_sec']/before['external_process_wall_sec']),
        additional_predictions=0,native_runs=0,
        limitations=['One saved2400s decision under recorded competing native workload.',
            'Nonconverged output is the best observed feasible command, not a proven optimum.',
            'No full8100s native speed or performance result is claimed.'])
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(status=result['status'],seconds=after['external_process_wall_sec'],
        target_time_met=target,comparison_differences={k:len(v) for k,v in comparisons.items()},
        query_stats=after['query_stats'])))

if __name__=='__main__':main()
