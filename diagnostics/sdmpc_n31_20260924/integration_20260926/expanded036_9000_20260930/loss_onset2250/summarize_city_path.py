"""Verify the bounded urban-arrival diagnosis from its saved outputs."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent.parent
U = I.parents[2]
OUT = HERE/'city_path'
native = json.loads((OUT/'native.json').read_bytes())
records = {}
sources = {}


def load(path):
    data = path.read_bytes()
    sources[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


for at in (2250,3600):
    arms = {}
    for suffix in ('','_after'):
        trace = load(OUT/f'{at}{suffix}/trace.json.gz')
        item = load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}{suffix}/held_actual.json')
        initial = load(OUT/f'{at if at!=2250 or suffix else "2250_init"}{suffix}/initial.json')
        def transfer(source=None,target=None):
            return sum(r['vehicles'] for r in trace['transfers'] if r['end_sec']<=at+150
                and (source is None or r['source']==source) and (target is None or r['target']==target))
        delays = [r['delay_steps'] for r in trace['delay_calls']
                  if r['link']=='SC1002_to_SC1001' and r['time_sec']<at+150]
        stock = initial['state']
        flows = dict(upstream329=transfer('movement:SC1002_E_SC101_to_W_SC1001'),
            downstream29=transfer('movement:SC1001_E_SC1002_to_W_RAMP'),
            ramp_arrival=transfer(target='ramp:RM_C10484'),
            ramp_merge=transfer('ramp:RM_C10484','merge_pending:RM_C10484'))
        # Every accepted regular discharge equals its pre-receiving intention
        # for these two turns; later resource sharing does not cause the loss.
        turn_limits = {}
        for m in ('SC1002_E_SC101_to_W_SC1001','SC1001_E_SC1002_to_W_RAMP'):
            rows=[r for r in trace['resources'] if r['resource']==m and
                  r['kind']=='urban_movement_intended_limit' and r['end_sec']<=at+150]
            residual=max(abs(r['accepted_total_veh']-r['available_veh']) for r in rows)
            assert residual<1e-8
            turn_limits[m] = dict(post_intention_shortfall_max=residual,
                initial_queue=stock['queue'][m],final_queue=trace['states'][0]['queue'][m])
        assert abs(item['ttt_omega_veh_h']-trace['ttt'])<1e-9
        assert max(abs(r['residual']) for r in item['ramps'].values())<1e-8
        arms[suffix or 'before']=dict(flows_first150=flows,delay_range= [min(delays),max(delays)],
            ttt450=item['ttt_omega_veh_h'],turn_limits=turn_limits,commands=item['commands'],
            stock=stock,physical_initial=item['physical_cell_states'][0],
            ramp_conservation_max=max(abs(r['residual']) for r in item['ramps'].values()))
    b,a=arms['before'],arms['_after']
    assert b['commands']==a['commands']
    assert b['physical_initial']==a['physical_initial']
    assert all(b['stock'][k]==a['stock'][k] for k in ('queue','storage','arrival_buffer','release_buffer'))
    evidence=json.loads((U/'outputs/urban_storage_capacity_jam168_20260815.json').read_bytes())
    key='SC1002_to_SC1001'
    lanes=evidence['urban_link_storage_veh'][key]/evidence['urban_link_length_km'][key]/evidence['jam_density_veh_km_lane']
    for arm in arms.values():
        arm['moving_speed_before_lane_correction']=arm['stock']['urban_link_speed_kph'][key]/lanes
        del arm['stock'],arm['physical_initial'],arm['commands']
    records[at]=dict(before=b,after=a,native={k:v for k,v in native['results'][str(at)].items()
        if k in ('native_upstream329','native_downstream29','head_to_head','initial329_lanes','bins','signal_transitions')},
        same_commands=True,same_initial_stocks_and_buffers=True,same_initial_freeway_arrays=True)

before=load(OUT/'speed_regression_before.json')
assert before['passed'] is False
after_speed=records[2250]['after']['moving_speed_before_lane_correction']
assert abs(after_speed-before['moving_only_expected'])<1e-8
unchanged={}
for source,digest in load(HERE/'speed_binding/protocol.json')['pins'].items():
    path=Path(source)
    if path.name=='lane_plant_runtime.py':
        # That protocol pins the pre-fix regression. Compare to the explicitly
        # saved accepted binding fix, rather than treating it as a new change.
        digest=hashlib.sha256((HERE/'speed_binding/lane_plant_runtime_after.txt').read_bytes()).hexdigest()
    unchanged[source]=hashlib.sha256(path.read_bytes()).hexdigest()==digest
assert all(unchanged.values())

old=ast.parse((OUT/'adapter_before.txt').read_text(encoding='utf-8-sig'))
new=ast.parse((U/'evaluation/controllers/vissim_stackelberg_adapter.py').read_text(encoding='utf-8-sig'))
def functions(tree):
    return {n.name:ast.dump(n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,b=functions(old),functions(new)
changed=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)]
assert changed==['build_local_observation_summary']
result=dict(previous_goal_turn='progress',current_goal_turn='progress',stage='completed_bounded_diagnosis',
    active_goal='ACTIVE/NOT_QUALIFIED',new_forecasts=4,new_initialization_only=1,
    native_runs=0,fzp_scans=0,coefficient_fits=0,live_polls=0,push=0,
    sessions={8709:'exit0',47591:'exit0',59462:'exit0_initialization_only',5877:'exit0',31159:'exit0'},
    regression=dict(before_expected_failure=True,after_pass=True,expected_speed=before['moving_only_expected'],
                    actual_after_speed=after_speed),tests=dict(passed=8,failed=0,
        repaired_test_fixture='Old StubTrafficState config lacked simulation/mpc/cycle fields required by tau diagnostics'),
    unchanged_pins=unchanged,changed_source_functions=changed,states=records,source_pins=sources,
    native_source_pins=native['pins'],qualification='Arrival aggregation semantics fixed; RM merge and queue allocation errors remain. No gain/candidate/SDMPC/NP/NUF qualification.')
(OUT/'verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({t:{k:{s:arm[s] for s in ('flows_first150','delay_range','ttt450','moving_speed_before_lane_correction')}
    for k,arm in row.items() if k in ('before','after')} for t,row in records.items()},indent=2))
