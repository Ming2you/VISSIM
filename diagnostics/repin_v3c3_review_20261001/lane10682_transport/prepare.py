"""One bounded physical candidate, based on the archived conservative allocator."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REVIEW=HERE.parent
F=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

assert not (HERE/'before.json').exists()
pins=json.loads((REVIEW/'lane10682_feasibility/verification.json').read_bytes())['production_current']
for path,h in pins.items(): assert sha(Path(path))==h,path
files=['evaluation/controllers/'+n+'.py' for n in (
    'physical_lane_groups','offramp_routing','area_freeway_accounting',
    'lane_freeway_runtime','lane_ramp_runtime','runtime_setup')]
before={p:sha(ROOT/p) for p in files}
for p in files: (HERE/(Path(p).name+'.before')).write_bytes((ROOT/p).read_bytes())
write(HERE/'before.json',before)

# Same selected network, native 4-lane geometry and connector lane mapping.
manifest=json.loads((REVIEW/'retained10638/candidate_manifest.json').read_bytes())
net=ROOT/manifest['sources']['network']['path']
assert sha(net)==manifest['sources']['network']['sha256']
xml=ET.parse(net).getroot()
links={x.attrib['no']:x for x in xml.findall('./links/link')}
access={}
for no in ['10643','10682','10639','10681']:
    access[no]={k: links[no].find(k).attrib for k in ('fromLinkEndPt','toLinkEndPt')}
write(HERE/'geometry_access.json',access)

# One independent training seed's already-cached endpoints. These are empirical
# adjacent-lane exchange hazards, not exact lane-change event counts or gain fit.
cache=F/'cohort_early/s29_none_frames.json.gz'
src=json.loads(gzip.decompress(cache.read_bytes()))
assert src['fields']==['cell','speed_kmh','x_m','lane']
frames=sorted((float(t),vs) for t,vs in src['frames'].items() if float(t)<=2670.1)
events=[[0.]*4 for _ in range(4)];exposure=[0.]*4
for (ta,a),(tb,b) in zip(frames,frames[1:]):
    assert abs(tb-ta-5)<1e-6
    for vid,row in a.items():
        if not 9<=row[0]<=12: continue
        later=b.get(vid)
        if later is None or not 9<=later[0]<=12: continue
        g=row[3]-1;k=later[3]-1
        exposure[g]+=tb-ta
        if abs(g-k)==1: events[g][k]+=1
rates=[[n/exposure[g] if exposure[g] else 0. for n in row] for g,row in enumerate(events)]
write(HERE/'exchange_profile.json',dict(training_seed=29,window=[frames[0][0],frames[-1][0]],
    cache=str(cache),sha256=sha(cache),events=events,eligible_vehicle_seconds=exposure,
    rates=rates,limitation='5-second endpoint changes, missed internal changes; no target/control fit'))

# Single region; four physical lanes. Confirm every branch/merge from XML.
spec=dict(cells=[9,10,11,12],lanes=4,exchange_rates_per_sec=rates,
    inlet_lane_to_group={str(i):i-1 for i in range(1,5)},off_access={},ramp_access={})
for no in ['10643','10682']:
    spec['off_access'][no]=int(access[no]['fromLinkEndPt']['lane'].split()[-1])-1
for no in ['10639','10681']:
    spec['ramp_access']['RM_C'+no]=int(access[no]['toLinkEndPt']['lane'].split()[-1])-1
candidate=json.loads((REVIEW/'retained10638/candidate_config.json').read_bytes())
candidate['freeway']['route_lane_regions']={'FW_E':spec}
write(HERE/'candidate_config.json',candidate)
write(HERE/'protocol.json',dict(status='prepared',budget_candidates=1,forecast_budget=6,
    checks=['43NC/RM/VSL/both450','47RMhold/selected450'],
    first_gate='accepted-flow class conservation and unchanged default',
    final_gate='8exit entry/drain/storage and43forming/47recovery, then cost ranks',
    no_native=True,no_push=True,not_controller_qualified=True))
print(json.dumps(dict(access=access,rates=rates,before=before),ensure_ascii=False))
