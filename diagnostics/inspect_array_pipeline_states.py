import pickle
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_records import unpack
for name in ('off','on'):
    obj=pickle.loads((ROOT/f'diagnostics/sdmpc_array_pipeline_20260922/states_v1/{name}_states.pickle').read_bytes())
    state=obj['states'][0]
    print(name,type(state),flush=True)
    ledger=state['_control_area_ledger'] if isinstance(state,dict) else state._control_area_ledger
    records=ledger['_packed_response_records'] if isinstance(ledger,dict) else ledger._packed_response_records
    block=unpack(records[0])
    for row in block['resource_allocations'][123316:123321]:print(row,flush=True)
