"""Read completed first150 resources; no forecast or service-coefficient fit."""
import gzip
import hashlib
import json
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
response_path = HERE/'replay2400_candidate/recorded_response.json.gz'
with gzip.open(response_path, 'rt', encoding='utf8') as stream:
    response = json.load(stream)
network_path = HERE/'init2400/network.json'
network = json.loads(network_path.read_bytes())
groups = defaultdict(list)
for row in response['resource_allocations']:
    for source in row['accepted_by_source_veh']:
        if source.startswith('movement:SC1004_S_to_'):
            groups[(source, row['kind'], row['resource'])].append(row)
report = []
for (source, kind, resource), rows in sorted(groups.items()):
    report.append(dict(movement=source, kind=kind, resource=resource, samples=len(rows),
        accepted_veh=sum(r['accepted_by_source_veh'][source] for r in rows),
        mean_available_veh=sum(r['available_veh'] for r in rows)/len(rows),
        positive_binding_samples=sum(r['accepted_total_veh'] > 1e-8 and
            abs(r['accepted_total_veh']-r['available_veh']) < 1e-7 for r in rows),
        unused_space_samples=sum(r['available_veh'] > r['accepted_total_veh']+1e-7 for r in rows)))
cap = {m: v for m, v in network['movement_capacity_by_movement_veh_h'].items() if m.startswith('SC1004_S_to_')}
doc = dict(start_sec=2400, end_sec=2550, service_caps_veh_h=cap, resources=report,
    source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (response_path, network_path)},
    scope='Discrete recorded-command model diagnosis; capacity binding does not identify the true native saturation rate.',
    interpretation='N and prehead E use their intended-service limits while receiving space remains; W-to68 first150 flow already matches10 observed vs10.08 predicted. Do not raise all66 movements.',
    prior_work='U7 and urban66_service already corrected ETA/head resources. No repeat patch or fitted rate added here.',
    native_new_runs=0, model_predictions=0, coefficients_changed=0)
(HERE/'service_binding_audit.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Recorded66 resource binding from existing response; no new predictions')
