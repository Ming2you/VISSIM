"""Saved two-state head-resource comparison and causal past queued headways."""
import ast
import gzip
import hashlib
import json
import statistics
from pathlib import Path

L=Path(__file__).resolve().parent;I=L.parent.parent;U=I.parents[2]
OUT=L/'service329';CP=L/'city_path'
D=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins={}
def read(p):
    raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest();return raw
def load(p):
    raw=read(p);return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)

baseline=load(CP/'head_lane_verification.json')
results={}
for at in (2250,3600):
    old=load(CP/f'{at}_after_hl/initial.json')
    new=load(CP/f'{at}_svc/initial.json')
    assert old['state']==new['state']
    assert old['simulation']==new['simulation'] and old['forecast_boundary']==new['forecast_boundary']
    caps1=old['network']['movement_capacity_by_movement_veh_h'];caps2=new['network']['movement_capacity_by_movement_veh_h']
    changed={k:[v,caps2[k]] for k,v in caps1.items() if v!=caps2[k]}
    assert set(changed)=={'SC1002_E_SC101_to_W_SC1001','SC1002_E_SC101_to_N_SC2004'}
    for field in old['network']:
        if field!='movement_capacity_by_movement_veh_h':assert old['network'][field]==new['network'][field],field
    assert load(CP/f'{at}_after_hl/projection.json')==load(CP/f'{at}_svc/projection.json')
    before=load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}_after_hl/held_actual.json')
    after=load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}_svc/held_actual.json')
    assert before['commands']==after['commands']
    assert before['physical_cell_states'][0]==after['physical_cell_states'][0]
    mass=max(abs(r['residual']) for r in after['ramps'].values());assert mass<1e-8
    receipt=load(CP/f'{at}_svc/receipt.json');assert receipt['forecast_count']==1
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in receipt['pins'].items())
    trace=load(CP/f'{at}_svc/trace.json.gz')
    def flow(s=None,t=None):return sum(r['vehicles'] for r in trace['transfers'] if r['end_sec']<=at+150
        and (s is None or r['source']==s) and (t is None or r['target']==t))
    flows=dict(upstream329=flow('movement:SC1002_E_SC101_to_W_SC1001'),
        downstream29=flow('movement:SC1001_E_SC1002_to_W_RAMP'),ramp_arrival=flow(t='ramp:RM_C10484'),
        ramp_merge=flow('ramp:RM_C10484','merge_pending:RM_C10484'))
    previous=baseline['states'][str(at)]
    service=load(CP/f'{at}_svc/service_projection.json')['head_resources']['observations']['10691']
    assert abs(caps2['SC1002_E_SC101_to_W_SC1001']-service['observed_only_floor_veh_h'])<1e-8
    old_runtime=load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}_after_hl/runtime.json')
    new_runtime=load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}_svc/runtime.json')
    existing_rates={k:[v,new_runtime['metadata'].get(k)] for k,v in old_runtime['metadata'].items()
                    if k.startswith('head_resource_final_rate_')}
    assert len(existing_rates)==7 and all(a==b for a,b in existing_rates.values())
    results[at]=dict(native=previous['native_first150'],before=previous['arms']['after_hl']['flows_first150'],
        after=flows,service=service,changed_caps=changed,unchanged_projection=True,
        same_states_buffers_speeds_commands=True,ramp_mass_max=mass,existing7_head_rates_unchanged=existing_rates,
        ttt450_before=before['ttt_omega_veh_h'],ttt450_after=after['ttt_omega_veh_h'])

windows=[]
for end in (1800,1950,2100,2250,3150,3300,3450,3600):
    start=end-150
    initial=load(D/f'state_{start:06d}.json')
    raw=load(D/f'state_{end:06d}.json')
    derived=load(D/f'obs150/derived_{end:06d}.json')['head_window']
    mer=raw['obs150']['mer'];data=read(D/mer['chunk'])
    assert hashlib.sha256(data).hexdigest()==mer['chunk_sha256']
    events=[r for line in data.decode('utf-8').splitlines() if (r:=json.loads(line))[2] is not None
            and start<=r[2]<end and r[1] in (960172,960173)]
    signal=raw['obs150']['signal_log']
    current=signal['start']['1002-6'];active_start=start if current=='GREEN' else None
    greens=[]
    for e in signal['events']:
        if (e[1],e[2])!=('1002','6'):continue
        if current=='GREEN' and e[-1]!='GREEN':greens.append((active_start,e[0]))
        if current!='GREEN' and e[-1]=='GREEN':active_start=e[0]
        current=e[-1]
    if current=='GREEN':greens.append((active_start,end))
    lanes=[]
    for lane,dcp in ((2,960173),(3,960172)):
        ids={r['veh_no'] for r in initial['vehicle_records']['records']
             if r['link_no']==329 and r['lane_no']==lane and r['stopped']}
        ordered=sorted([r for r in events if r[1]==dcp],key=lambda r:r[2])
        intervals=[]
        for a,b in zip(ordered,ordered[1:]):
            if a[4] in ids and b[4] in ids and any(g<=a[2]<b[2]<h for g,h in greens):
                intervals.append(b[2]-a[2])
        head=next(r for r in derived['heads'] if r['link']=='329' and r['lane']==lane)
        assert head['crossings']==len(ordered)
        lanes.append(dict(lane=lane,initial_stopped=len(ids),queued_same_lane_pair_count=len(intervals),
            queued_pair_headways_sec=intervals,
            median_headway_sec=statistics.median(intervals) if intervals else None,
            green_sec=head['green_sec'],qualified=head['qualified_crossings'],
            whole_green_rate_vph=3600*head['qualified_crossings']/head['green_sec'] if head['green_sec'] else 0))
    windows.append(dict(start=start,end=end,green_intervals=greens,lanes=lanes))

old=ast.parse((OUT/'head_service_resources.before.py.txt').read_text(encoding='utf-8-sig'))
source=U/'evaluation/controllers/head_service_resources.py';new=ast.parse(source.read_text(encoding='utf-8-sig'))
def funcs(tree):return {n.name:ast.dump(n) for n in tree.body if isinstance(n,ast.FunctionDef)}
a,b=funcs(old),funcs(new);changed=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)]
assert changed==['configure']
base=load(CP/'head_lane_config.json');candidate=load(OUT/'candidate_config.json')
candidate['urban']['capacity']['head_resource_contract']=base['urban']['capacity']['head_resource_contract']
assert candidate==base
unchanged={}
for name,digest in load(L/'speed_binding/protocol.json')['pins'].items():
    path=Path(name)
    if path.name=='lane_plant_runtime.py':digest=hashlib.sha256((L/'speed_binding/lane_plant_runtime_after.txt').read_bytes()).hexdigest()
    unchanged[name]=hashlib.sha256(path.read_bytes()).hexdigest()==digest
assert all(unchanged.values())
(OUT/'head_service_resources.after.py.txt').write_bytes(read(source))
(OUT/'audit_city_arrival.after.py.txt').write_bytes(read(L/'audit_city_arrival.py'))
report=dict(status='bounded_diagnosis_complete',previous_goal_turn='progress',current_goal_turn='progress',
    goal='ACTIVE/NOT_QUALIFIED',adopted=False,physical_forecasts=2,session27123='exit0',tests_passed=6,
    native_runs=0,fzp_scans=0,coefficient_fits=0,live_polls=0,push=0,
    source_functions_changed=changed,states=results,past_queued_headways=windows,
    limitations=['Headways are retrospective conditional pairs of initially stopped vehicles; not a saturation calibration.',
                 'Same seed29 states. No independent seed or candidate ranking validation.',
                 'First150 shared actual commands; full450 held commands differ from later native actions.',
                 'Initial queue candidate remains optional; production config unchanged.'],
    unchanged_pins=unchanged,source_pins=pins)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'states':results,'headways':[{'end':r['end'],'lanes':[
    {k:v for k,v in lane.items() if k!='queued_pair_headways_sec'} for lane in r['lanes']]} for r in windows]},indent=2))
