import json,pickle
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339 import project
from evaluation.controllers.area_runtime import model_inventory
from evaluation.controllers.control_area_objective import get_ledger
base=Path('E:/VISSIM_analysis/20261011_vsl_response349')
args=pickle.loads((base/'projection_optimized3300_v3/corridor_initialization_inputs.pickle').read_bytes())
original=project.owned_residual
def inspect(cfg,raw,link,residual,support):
    try:return original(cfg,raw,link,residual,support)
    except Exception:
        print(json.dumps(dict(link=link,residual_count=len(residual),support=support,
            fraction=support.get(project.STORAGE,0)/len(residual) if residual else None)),flush=True)
        raise
project.owned_residual=inspect
before=pickle.dumps(args[1],protocol=5)
result,proof=project.install(*args)
assert pickle.dumps(args[1],protocol=5)==before
get_ledger(result).assert_stocks(model_inventory(result,args[0]))
out=base/'corridor3300_after.json';assert not out.exists()
out.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(status='passed',source_vehicles=proof['source_vehicles'],
    post_head=sum(v['post_head_owner_retained'] for v in proof['vehicles']),
    conserved=proof['physical_conservation'])))
