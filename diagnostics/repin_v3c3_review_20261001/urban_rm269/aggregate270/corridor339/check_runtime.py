"""Protect the same nested rollout order as the completed337 physical pair."""
from pathlib import Path
import inspect,json
from evaluation.controllers.aggregate_route_corridors import Routes
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339.runtime import source_hooks
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook

original=Routes.advance_one
with source_hooks() as receipt, hook('source_path_current_physical_speed'):
    chain=[];f=Routes.advance_one
    while f is not None:
        chain.append(f.__code__.co_filename.replace('\\','/'))
        f=inspect.getclosurevars(f).nonlocals.get('original_advance')
    assert len(chain)==3
    assert chain[0].endswith('sc101_route_tags303/candidate.py')
    assert chain[1].endswith('sc101_clock299/candidate.py')
    assert chain[2].endswith('branch_service315/candidate.py:scoped-original')
    assert receipt['branch']['rates']=={'1129:branch:bypass':904}
assert Routes.advance_one is original
report=dict(status='passed',outer_to_inner=chain,restored_exact=True,forecasts=0,native_runs=0)
Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('RUNTIME_ORDER_PASS')
