import json,pickle
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc105_initial340 import candidate
from evaluation.controllers.area_runtime import model_inventory
from evaluation.controllers.control_area_objective import get_ledger
base=Path('E:/VISSIM_analysis/20261011_vsl_response349')
args=pickle.loads((base/'projection_window2250_v2/terminal_initialization_inputs.pickle').read_bytes())
cfg,state,*rest=args
before=pickle.dumps(state,protocol=5)
result,proof=candidate.install(*args)
assert pickle.dumps(state,protocol=5)==before
get_ledger(result).assert_stocks(model_inventory(result,cfg))
out=base/'terminal2250_after.json'
assert not out.exists()
out.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:proof[k] for k in ('physical_vehicles','source_vehicles','ready_before','ready_after','moved_queue_to_storage','retained_posthead')}))
print('alternate_connector_records',sum('10660' in v.get('physical_path',[]) for v in proof['vehicles']))
