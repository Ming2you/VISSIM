"""Validate saved binding regressions and fixed recorded-state forecasts."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent.parent
U = I.parents[2]
OUT = HERE/'speed_binding'
read = lambda p: json.loads(p.read_bytes())
before, after = (read(OUT/f'{s}_2250_audit.json') for s in ('before','after'))
assert not any(before['checks'].values()) and all(after['checks'].values())
changes = {}
for ramp, old in before['actual'].items():
    new = after['actual'][ramp]
    changed = [k for k in old.keys()|new.keys() if old.get(k) != new.get(k)]
    if ramp in before['declared']:
        assert set(changed) <= {'travel_speed_kmh','posthead_travel_speed_kmh','post_head_travel_sec','travel_model'}
        assert new['travel_model'] == 'Separate supplied approach/post-head speeds; receiving queue adds delay explicitly'
    else:
        assert not changed
    changes[ramp] = changed

def first150(folder, case, start):
    result = read(folder/f'{case}.json')
    trace = json.loads(gzip.decompress((folder/f'{case}_RM_C10484_trace.json.gz').read_bytes()))
    assert not trace['future_observation_inputs']
    row = dict(initial=trace['initial_stock']['connector_veh'])
    for kind in ('arrival','merge'):
        row[kind] = sum(r['vehicles'] for r in trace['transfers'] if r['start_sec'] < start+150 and
            ((kind=='arrival' and r['target']=='ramp:RM_C10484') or
             (kind=='merge' and r['source']=='ramp:RM_C10484' and r['target']=='merge_pending:RM_C10484')))
    row['head'] = sum(r['accepted_total_veh'] for r in trace['resources']
        if r['kind']=='physical_ramp_head_service' and r['start_sec'] < start+150)
    row['final'] = row['initial']+row['arrival']-row['merge']
    assert max(abs(r['residual']) for r in result['ramps'].values()) < 1e-8
    assert result['validation']['all_actuator_and_step_constraints_checked']
    for state in result.get('physical_cell_states',[]):
        assert set(state['density']) == {'FW_E','FW_W'}
        assert all(len(v)==31 and min(v)>=0 for v in state['density'].values())
    return row,result,trace

oldfolder = I/'closedloop_recorded2250_lever450_RM_C10484_trace10484_loss_onset_s29_v1'
newfolder = I/'closedloop_recorded2250_lever450_RM_C10484_trace10484_speed_binding_forecast_2250_r2'
comparisons = {}
for case in ('held_actual','meter_RM_C10484_flat8'):
    b,bfull,bt = first150(oldfolder,case,2250)
    a,afull,at = first150(newfolder,case,2250)
    assert afull['commands'] == bfull['commands']
    comparisons[case] = dict(before150=b,after150=a,before450=bfull['ttt_omega_veh_h'],
        after450=afull['ttt_omega_veh_h'],before_ramp450=bfull['ramps']['RM_C10484'],
        after_ramp450=afull['ramps']['RM_C10484'])
    if case=='held_actual':
        movement='movement:SC1001_E_SC1002_to_W_RAMP'
        head29_prediction=sum(r['vehicles'] for r in at['transfers']
            if r['source']==movement and r['target']=='storage:SC1001_W_out' and r['start_sec']<2400)
new3600 = I/'closedloop_recorded3600_lever450_RM_C10484_trace10484_bnd_forecast_3600'
first,new,trace = first150(new3600,'held_actual',3600)
old = read(I/'closedloop_recorded3600_select_check_e036_r2/summary.json')['results']['held_actual']
assert old['commands'] == new['commands']
native_command=read(Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29/action_003600.json'))
assert all(new['commands'][0][k]==native_command[k] for k in ('green_times','offsets','vsl'))
independent = dict(before450=old['ttt_omega_veh_h'],after450=new['ttt_omega_veh_h'],after150=first,
    native150=dict(initial=2,arrival=23,head=23,merge=23,final=2),
    before_ramp450=old['ramps']['RM_C10484'],after_ramp450=new['ramps']['RM_C10484'],
    scope='Another state in seed29, NOT an independent seed or full9000 validation')
protocol=read(OUT/'protocol.json')
for name,sha in protocol['pins'].items():
    if name.endswith('lane_plant_runtime.py'):
        assert hashlib.sha256((OUT/'lane_plant_runtime_before.txt').read_bytes()).hexdigest()==sha
    else:
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,name
source=U/'evaluation/controllers/lane_plant_runtime.py'
oldtree=ast.parse((OUT/'lane_plant_runtime_before.txt').read_text(encoding='utf-8-sig'))
newtree=ast.parse(source.read_text(encoding='utf-8-sig'))
functions=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
oldf,newf=functions(oldtree),functions(newtree)
changed=[k for k in oldf.keys()|newf.keys() if oldf.get(k)!=newf.get(k)]
assert len(changed)==1,changed
(OUT/'lane_plant_runtime_after.txt').write_bytes(source.read_bytes())
report=dict(binding_regression='before FAIL / after PASS',changed_functions=changed,ramp_metadata_changes=changes,
    comparison2250=comparisons,independent3600=independent,
    road29_first150=dict(predicted=head29_prediction,actual=31,
        scope='Two dedicated straight head detectors on29 into10119->31; no conversion of all this traffic to10484 demand'),
    limitations=['2250 progressive forecast completed compute but hit Windows path length saving its trace; unavailable result is not counted as validation.',
        'Three saved predictions out of four attempted; no repeat of failed progressive run.',
        'Seven ramp invariant tests passed; eighth existing smoke fixture missing port_profile.json, not reported PASS.',
        'NP/NUF and optimizer/native gain not evaluated; no additional capacity or reward.',
        'Post-head speed is a supplied travel approximation and remains receiving-constrained; faster travel alone is not proven recovery accuracy.'],
    native_gain_qualified=False,core_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
protocol.update(stage='completed_with_diagnostic_output_failure',forecasts_attempted=4,forecasts_saved=3,
    sessions={'binding_before':75708,'binding_after':59167,'forecast2250':29188,'forecast3600':7342},
    source_changed_functions=changed,new_native=0,new_fzp=0,coefficient_fits=0,live_polls=0,
    goal='ACTIVE/NOT_QUALIFIED')
(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(binding='PASS',comparison2250=comparisons,independent3600=independent,road29=report['road29_first150'])))
