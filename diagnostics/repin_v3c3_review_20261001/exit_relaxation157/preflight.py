"""Verify the sole speed-feedback change before autonomous experiments."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace as NS
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
assert not (HERE/'forecast/status.json').exists()
old=h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
new=h.exit_relaxation157_source(old)
assert [k for k in new if new[k]!=old[k]]==['RouteLaneRegion']
def methods(s):return {n.name:ast.dump(n) for n in ast.parse(s).body[0].body if isinstance(n,ast.FunctionDef)}
a,b=methods(old['RouteLaneRegion']),methods(new['RouteLaneRegion'])
assert a.keys()==b.keys() and all(a[k]==b[k] for k in a if k!='speed')
def functions(s):return {n.name:ast.dump(n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
a=functions((HERE/'helper_before.py.txt').read_text(encoding='utf-8'));b=functions(Path(h.__file__).read_text(encoding='utf-8'))
assert set(b)-set(a)=={'exit_relaxation157_source'}
assert all(a[k]==b[k] for k in a if k!='validate_frozen132')
classes=[]
for source in (old,new):
    ns={};exec(compile(source['RouteLaneRegion'],'157fixture','exec'),ns)
    cls=ns['RouteLaneRegion'];obj=cls.__new__(cls)
    obj.road='FW_E';obj.n0={20:[10.],21:[2.]};obj.lengths=[.2]*31
    obj.oldv={19:[30.],20:[40.]};obj.split19_oldv=[[30.],[30.]];obj.exchange_v={20:[40.]}
    obj.off_access={'10483':0};obj.off_requests={'10483':[.3]};obj.off_sent={'10483':[.05]}
    obj.outgoing={20:[.1]};obj.merge={20:[0.]};obj.next={20:[{'unit':9.}]};obj.next_v={}
    classes.append(obj)
net=NS(v_free=110.,rho_crit=50.,alpha_vsl=0.,metanet_a_m=2.,rho_max=180.,v_min=5.,
    metanet_tau_h=12/3600,metanet_kappa_veh_km_lane=5.,freeway_vsl_fd_response={},
    offramp_route_inventory={'branches':{'10483':{'source_cell':20}}})
cfg=NS(network=net,simulation=NS(T_f_h=1/3600),freeway_follower=NS(vsl_set=[50.,110.]))
state=NS(time_sec=100.,freeway_density={'FW_E':[20.]*31},freeway_speed={'FW_E':[40.]*31})
# A deliberately simple relaxation operator isolates the placement contract;
# full METANET + flow behavior is checked by the subsequent native-state replays.
mn=NS(segment_vsl=lambda *a:110.,effective_desired_speed_kmh=lambda *a:60.,select_anticipation_nu=lambda *a:10.,
      metanet_speed_update_kmh=lambda v,up,rho,down,target,*a:v+.1*(target-v))
before=[copy.deepcopy(o.next) for o in classes]
blocked=[o.speed(20,state,cfg,None,mn,None,0.,5.) for o in classes]
assert abs(blocked[0]-10.8)<1e-8 and abs(blocked[1]-37.08)<1e-8
assert all(o.next==v for o,v in zip(classes,before))
for o in classes:o.off_sent['10483']=[.3]
free=[o.speed(20,state,cfg,None,mn,None,0.,5.) for o in classes]
assert free==[42.,42.]
for o in classes:o.off_sent['10483']=[0.];o.outgoing[20]=[0.]
closed=[o.speed(20,state,cfg,None,mn,None,0.,5.) for o in classes]
assert closed==[5.,36.5]
protocol=h.read(h.R/'transition150/replay/protocol.json')
for p,digest in protocol['protected_sha256'].items():assert h.sha(p)==digest,p
assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
h.save(HERE/'preflight.json',dict(status='pass',helper_sha256=h.sha(h.__file__),other_helper_functions_unchanged=len(a)-1,
    only_speed_method_changed=True,flows_and_parameters_unchanged=True,unit_operator='synthetic0.1 relaxation, not physical prediction',
    blocked=blocked,unconstrained=free,closed=closed,new_forecasts=0,budget450=9))
(HERE/'executed_helper.py.txt').write_bytes(Path(h.__file__).read_bytes())
print('PRECHECK PASS: same free case; blocked and closed targets use finite response; all flow methods unchanged.')
