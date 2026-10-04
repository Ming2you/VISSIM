"""Compile current physical routes once; no forecast or native execution."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
from evaluation.controllers.omega_distance import urban_path_catalog

HERE=Path(__file__).resolve().parent
integration=HERE.parent.parent
network=integration/'selected/network/native_seed29.inpx'
snapshot=json.loads((HERE/'distance_state3600.json').read_bytes())
assignments=snapshot['state']['local_observation_summary']['projection_diagnostics']['physical_stock_assignment_by_link']
cfg=NS(network=NS(**snapshot['network']))
starts=[]
for link,rows in assignments.items():
    for stock,n in rows.items():
        if stock.startswith('storage:') and n>0 and snapshot['stocks'].get(stock,{}).get('inside',0)>0:
            starts.append((link,stock[8:]))
catalog=urban_path_catalog(network,cfg,initial_starts=starts)
audit=json.loads((HERE/'distance_ordinary_audit_result.json').read_bytes())
active_errors={m:catalog['errors'].get(m) for m in audit['ordinary_unresolved_accepted_movements']
               if m not in catalog['path_families']}
output=HERE/'ordinary_geometry_v2.json'
assert not output.exists()
result=dict(network_sha256=hashlib.sha256(network.read_bytes()).hexdigest(),
    source_sha256=hashlib.sha256(Path('evaluation/controllers/omega_distance.py').read_bytes()).hexdigest(),
    previous_positive_unresolved_remaining=active_errors,initial_starts=len(starts),catalog=catalog)
output.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(dict(previous_positive_unresolved=active_errors,
    native_source_errors=catalog['native_source_errors'],initial_errors=catalog['initial_errors'])))
