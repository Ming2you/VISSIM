"""Compare the two completed unit-contract forecasts, without rerunning them."""
import ast
import gzip
import hashlib
import json
import math
from pathlib import Path

L=Path(__file__).resolve().parent;I=L.parent.parent;U=I.parents[2]
O=L/'physical_speed';CP=L/'city_path';pins={}
assert not (O/'verification.json').exists()
def load(p):
    data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)
def same(a,b):assert a==b
oldbuffer=load(L/'ramp10484_path_v2/verification.json')['states']
newbuffer=load(O/'buffer_audit/verification.json')['states']
results={}
for at in (2250,3600):
    old=load(CP/f'{at}_svc/initial.json');new=load(CP/f'{at}_ps/initial.json')
    same(old,new)
    for name in ('projection.json','service_projection.json'):
        same(load(CP/f'{at}_svc'/name),load(CP/f'{at}_ps'/name))
    receipt=load(CP/f'{at}_ps/receipt.json')
    assert receipt['forecast_count']==1 and receipt['future_observation_inputs'] is False
    for p,h in receipt['pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    transport=load(CP/f'{at}_ps/physical_speed.json')
    assert transport['direct_transport']['travel']['speed_source']=='physical_observation'
    delays={}
    for m,entry in transport['direct_transport']['travel']['incoming'].items():
        segments=transport['direct_transport']['travel']['paths']['RM_C10484']
        assert len(segments)==1 and segments[0]['link']==entry['link']=='31'
        distance=entry['distance']+segments[0]['stop']-entry['position']
        v=max(new['travel_parameters']['urban_avg_speed_km_h']/2.5,
              transport['observed'].get(entry['origin'],new['travel_parameters']['urban_avg_speed_km_h']))
        delays[m]=dict(distance_m=distance,physical_speed_kmh=v,seconds=math.ceil(distance/(v/3.6)))
    before=load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}_svc/held_actual.json')
    after=load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}_ps/held_actual.json')
    same(before['commands'],after['commands'])
    same(before['physical_cell_states'][0],after['physical_cell_states'][0])
    mass=max(abs(r['residual']) for r in after['ramps'].values());assert mass<1e-8
    trace=load(CP/f'{at}_ps/trace.json.gz')
    def flow(source):return sum(r['vehicles'] for r in trace['transfers']
        if r['source']==source and r['end_sec']<=at+150)
    f={m:flow('movement:'+m) for m in ('SC1002_E_SC101_to_W_SC1001','SC1001_E_SC1002_to_W_RAMP')}
    assert newbuffer[str(at)]['native']==oldbuffer[str(at)]['native']
    results[at]=dict(native=oldbuffer[str(at)]['native'],before=oldbuffer[str(at)]['model'],
        after=newbuffer[str(at)]['model'],bins30=newbuffer[str(at)]['bins30'],
        delays=delays,head_flows_first150=f,all8_ramp_mass_max=mass,
        omega_ttt450_before=before['ttt_omega_veh_h'],omega_ttt450_after=after['ttt_omega_veh_h'],
        effective_speed_source=transport['direct_transport']['travel']['speed_source'])

for p,h in load(O/'protocol.json')['pins_unchanged'].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
before=load(L/'service329/candidate_config.json');after=load(O/'candidate_config.json')
before['urban']['sc1001_destination_travel']['speed_source']='physical_observation';same(before,after)
for name,path in [('route_choice_corridor.py',U/'evaluation/controllers/route_choice_corridor.py'),
                  ('test_sc1001_destination_travel.py',U/'diagnostics/sdmpc_n31_20260924/tests/test_sc1001_destination_travel.py'),
                  ('audit_city_arrival.py',L/'audit_city_arrival.py'),
                  ('audit_ramp10484_path.py',L/'audit_ramp10484_path.py'),
                  ('check_transport_ad.py',I/'check_transport_ad.py')]:
    ast.parse(path.read_text(encoding='utf-8-sig'))
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest()
    (O/(name+'.after.txt')).write_bytes(data)
result=dict(status='bounded_comparison_complete',previous_goal_turn='progress',current_goal_turn='progress',
    goal='ACTIVE/NOT_QUALIFIED',adopted=False,new_coupled_forecasts=2,session29985='exit0',
    model_buffer_replays=2,tests_passed=16,parameter_check='PASS with inherited calibration warnings',
    physical_path_scalar_forward_ad='PASS; four fixed-speed outputs only; not full SDMPC AD',
    native_runs=0,fzp_scans=0,coefficient_fits=0,live_polls=0,push=0,
    states=results,source_check=load(O/'source_check.json'),pins=pins,
    caveats=['Same seed29; only first150 seconds match actual future commands.',
             'Legacy effective speeds, initial states/queues/buffers, capacities and held commands unchanged.',
             'Improved2250 merge error, slightly worse3600 deficit. Not an adopted calibration or gain validation.'])
(O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'states':results},indent=2))
