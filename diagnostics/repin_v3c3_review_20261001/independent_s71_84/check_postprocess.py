"""Small source/command checks; no native execution or model forecast."""
import ast
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
P=I/'native_rm_observation2700_s71_four84'
OUT=Path(__file__).parent
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200 import analyze_pair as analysis

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

protocol=read(P/'protocol.json')
checks=[]
for label,key,value in [('seed','seed',31),('arms','arms',['nc','rm']),
                        ('start','start_sec',900),('end','end_sec',3150),
                        ('control_start','control_start_sec',900),('factorial','native_factorial',False),
                        ('resolution','sim_resolution',1),('recording','vehicle_record_interval_sec',1),
                        ('future','future_observation_inputs',True),('network','network_sha256','wrong')]:
    bad=copy.deepcopy(protocol);bad[key]=value
    try:analysis.independent_four_protocol(bad)
    except AssertionError:checks.append(label+' rejected')
    else:raise AssertionError(label+' unexpectedly accepted')
assert analysis.independent_four_protocol(protocol)
assert analysis.observation_profile_pair(protocol)=='four71'
for seed,arms,label in ((47,['hold','release'],'rm47'),(67,['release','release_vsl90'],'vsl67')):
    assert analysis.observation_profile_pair(dict(controller='diagnostic-ramp-profile',
        start_sec=2700,end_sec=3150,seed=seed,arms=arms))==label
checks.extend(['seed71 accepted','legacy47 accepted','legacy67 accepted'])

helper=I/'probe_selected_arrival_path.py'
tree=ast.parse(helper.read_text(encoding='utf-8-sig'))
for path in (helper,Path(analysis.__file__)):
    compile(path.read_text(encoding='utf-8-sig'),str(path),'exec')
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='probe_levers')
block=next(n for n in fn.body if isinstance(n,ast.If) and ast.unparse(n.test)=='four_arm_receipt is not None')
code=compile(ast.fix_missing_locations(ast.Module(body=[block],type_ignores=[])),str(helper),'exec')
rows=list(csv.DictReader((P/'nc/commands/action_002100.csv').open(encoding='utf-8-sig')))
ramps={row['id']:dict(sc_no=int(row['sc_no'])) for row in rows if row['kind']=='ramp_meter'}
meter_axis=[dict(kind='meter',key=k,block=b,scale=1,allowed=list(range(11))) for b in range(3) for k in ramps]
vsl_axis=[dict(kind='vsl',key='FW_E__seg13',block=b,scale=1,allowed=list(range(50,111,10))) for b in range(3)]
axes=meter_axis+vsl_axis
class Vector(list):
    def copy(self):return Vector(self)
class Coord:
    def __init__(self):self.axes=axes
    def decode(self,z,reference):
        return {(a['block'],a['kind'],a['key']):(10 if a['kind']=='meter' else 110)+z[j] for j,a in enumerate(self.axes)}
    def validate(self,values):
        for a in self.axes:assert values[(a['block'],a['kind'],a['key'])] in a['allowed']

with tempfile.TemporaryDirectory(prefix='vissim84_postprocess_') as tmp:
    tmp=Path(tmp);summary=tmp/'synthetic_summary.json';summary.write_text('{}')
    proof=dict(passed=True,seed=71,prefix_cutoff_sec=2250,precontrol_prefix_exact=True,
        independent_four_arm=True,protocol=dict(path=str(P/'protocol.json'),sha256=digest(P/'protocol.json')),
        native_summary=dict(path=str(summary),sha256=digest(summary)),
        profiles={a:dict(path=str(P/f'{a}_fixed_profile.json'),sha256=digest(P/f'{a}_fixed_profile.json')) for a in ('rm','vsl','both')})
    receipt=tmp/'synthetic_receipt.json';receipt.write_text(json.dumps(proof))
    scope=dict(four_arm_receipt=receipt,json=json,hashlib=hashlib,Path=Path,
        state=NS(time_sec=2250),selected_path=None,meter_only=False,signal_exchange=False,
        meter_ramp=None,vsl_zone=None,replay_pair=None,east_meter_first8_screen=False,east_meter_progressive_screen=False,
        ownership=NS(writes=[('dsd',n,None,'FW_E__seg13') for n in (63,64,65,66)]),
        cfg=NS(network=NS(physical_ramp_branches={'ramps':ramps})),coord=Coord(),anchor=Vector([0.]*len(axes)),
        reference=NS(diagnostics={'rw_meter_green_'+k:10 for k in ramps},vsl={'FW_E__seg13':110}),
        candidates={},profile_pins={})
    exec(code,scope)
    purpose=next(n for n in ast.walk(fn) if isinstance(n,ast.JoinedStr) and 'Four executed seed' in ast.unparse(n))
    scope['receipt']={'all_actuator_and_step_constraints_checked':True}
    assert 'seed71' in eval(compile(ast.Expression(purpose),str(helper),'eval'),scope)
    compared=0
    for arm,values in scope['candidates'].items():
        for b,sec in enumerate((2250,2400,2550)):
            actual=list(csv.DictReader((P/arm/'commands'/f'action_{sec:06d}.csv').open(encoding='utf-8-sig')))
            for row in actual:
                if row['kind']=='ramp_meter':
                    assert values[(b,'meter',row['id'])]==float(row['green_sec']);compared+=1
                elif row['kind']=='vsl' and int(row['dsd_no']) in (63,64,65,66):
                    assert values[(b,'vsl','FW_E__seg13')]==float(row['speed_kph']);compared+=1
    assert compared==108
    # Exercise the actual existing binding function with a tiny synthetic state.
    binder=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bind_fixed_replay_reference')
    env=dict(json=json,copy=copy,hashlib=hashlib)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[binder],type_ignores=[])),str(helper),'exec'),env)
    for cutoff in (2250,2700):
        folder=tmp/str(cutoff);folder.mkdir();out=folder/'output';out.mkdir()
        original=folder/f'action_{cutoff-150:06d}.json'
        payload=read(P/'nc/commands/action_002100.json');payload['metadata']['sim_sec']=cutoff-150
        original.write_text(json.dumps(payload));original.with_suffix('.csv').write_bytes((P/'nc/commands/action_002100.csv').read_bytes())
        state=folder/f'state_{cutoff:06d}.json'
        state.write_text(json.dumps(dict(sim_sec=cutoff,run_provenance=dict(run_id='synthetic-unit'),obs150=dict(run_id='synthetic-unit'))))
        rec=dict(observation_cutoff_sec=cutoff,native_summary='synthetic-unit',
                 files={str(p.resolve()):digest(p) for p in (original,original.with_suffix('.csv'),state)})
        target=env['bind_fixed_replay_reference'](rec,folder,out)
        bound=read(target)
        assert {k:v for k,v in bound.items() if k not in ('metadata','run_provenance')}=={k:v for k,v in payload.items() if k!='metadata'}
        assert target.with_suffix('.csv').read_bytes()==original.with_suffix('.csv').read_bytes()
        checks.append(f'physical command binding {cutoff} unchanged')

result=dict(passed=True,checks=checks,actual_profile_to_writer_value_comparisons=compared,
    source_pins={str(p):digest(p) for p in (helper,Path(analysis.__file__),P/'protocol.json')},
    model_rollouts=0,native_runs=0,fzp_scans=0,
    limitation='Synthetic binding and protocol/command tests; real seed71 observation initialization and postprocessing remain pending.')
(OUT/'postprocess_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result),flush=True)
