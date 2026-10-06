"""One saved-state domain/writer/model check; no optimizer, COM or live writes."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes,hashlib,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--at',type=int,default=4500);ap.add_argument('--out',default='verify4500');ap.add_argument('--no-prediction',action='store_true');ap.add_argument('--tuning');ap.add_argument('--single-prediction',action='store_true');ap.add_argument('--cold-prices',action='store_true',help='Offline reference/writer diagnostic only: do not reuse a different policy price history');args=ap.parse_args()
OUT=HERE/args.out
F=Path('D:/VISSIM_runs/20261006_min2_storage90_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
AT=args.at
read=lambda p:json.loads(p.read_bytes())
def save(name,v):(OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
class Done(BaseException):pass
def main():
 OUT.mkdir(exist_ok=False);os.chdir(ROOT);sys.path.insert(0,str(ROOT))
 os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0',PYTHONDONTWRITEBYTECODE='1',RW_DECISION_FAIL_FAST='1')
 k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
 from evaluation.controllers import vissim_stackelberg_adapter as adapter,obs150_contract as oc,head_service_resources,vsl_exposure_history,sdmpc_pfo,sdmpc,sdmpc_sequence as seq
 from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
 from evaluation.controllers import area_leader_objective as constraints
 import numpy as np
 opened=set()
 def opened_file(event,values):
  if event=='open' and isinstance(values[0],str) and values[1] in ('r','rb'):
   p=Path(values[0]).resolve()
   if p.is_relative_to(ROOT) and not p.is_relative_to(OUT):opened.add(p.relative_to(ROOT).as_posix())
 sys.addaudithook(opened_file)
 if args.cold_prices:
  sdmpc.load_prices=lambda *a,**kw:(np.zeros(2),{'source':'offline_reference_check_cold_prices','committed':False})
 from evaluation.controllers import signal_actuation_contract as signals
 validate_native=signals._validate_native_vector
 def diagnose_native(net,signal,raw,values):
  try:return validate_native(net,signal,raw,values)
  except ValueError:
   save('native_bounds_failure.json',{'signal':signal,'values':values,'bounds':signals._native_phase_bounds(net,signal,raw)})
   raise
 signals._validate_native_vector=diagnose_native
 history=[]
 def readonly(raw,derived):
  p=oc.resolve(raw[oc.RAW_STATE_KEY],oc.derived_path(derived['sim_sec']));assert p.read_bytes()==oc.derived_bytes(derived);return p
 oc.write_derived=readonly
 observe=head_service_resources.observe
 def warm(original,cfg,raw,previous_path,caps,plan,distribute,options):
  return probe.replay_head_history(observe,original,cfg,raw,caps,plan,distribute,options,folder=F,sim_sec=AT,output=OUT,history_inputs=history)
 head_service_resources.observe=warm
 initialize=vsl_exposure_history.initialize
 vsl_exposure_history.initialize=lambda context,raw,state,cfg:probe.replay_vsl_history(initialize,context,raw,state,cfg,OUT,known_missing_online_cutoffs=[])
 from evaluation.controllers import physical_ramp_branches as ramps
 captured=[]
 original_bounds=ramps.configure_operating_bounds
 def bound_capture(state,cfg,reference):
  captured[:]=[state,cfg]
  proof=original_bounds(state,cfg,reference);save('bounds.json',proof);return proof
 ramps.configure_operating_bounds=bound_capture
 def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
  def clean(x):
   if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
   if isinstance(x,(tuple,list)):return [clean(v) for v in x]
   if isinstance(x,(str,int,float,bool)) or x is None:return x
   if hasattr(x,'tolist'):return x.tolist()
   return repr(x)[:600]
  state,cfg=captured
  save('state.json',clean(vars(state)))
  save('network.json',clean(vars(cfg.network)))
  save('reference.json',clean(vars(reference)))
  save('coordinates.json',clean({'axes':coord.axes,'bounds':[coord.lower,coord.upper]}))
  if args.tuning:
   from evaluation.controllers.control_area_objective import physical_membership_from_ledger
   config=read(tuning);area=read(ROOT/config['control_area_objective']['membership_path'])
   physical=physical_membership_from_ledger(area)
   raw=read(F/f'state_{AT:06}.json')
   observed=sum(physical[str(v['link_no'])] for v in raw['vehicle_records']['records'])
   seeded=sum(v['inside'] for v in state._control_area_ledger.stocks.values())
   assert abs(observed-seeded)<1e-6,(observed,seeded)
   guard=cfg.network.urban_storage_guard
   assert len(guard['signals'])==17 and any(x['link']=='66' for x in guard['lanes'])
   assert cfg.network.control_area_routes['input:gate:in_SC1004_S']['target_inside'] is True
   save('expanded_area_check.json',{'observed_inside_veh':observed,'seeded_inside_veh':seeded,
        'link66_inside':physical['66'],'link38_outside':not physical['38'],'urban_signals':len(guard['signals']),
        'link66_guard_lanes':[x for x in guard['lanes'] if x['link']=='66'],
        'gate66':cfg.network.control_area_routes['input:gate:in_SC1004_S']})
  from evaluation.controllers import urban_storage_guard as ug
  proof=coord.validate(reference)
  from evaluation.controllers import signal_actuation_contract as signals
  for block in seq.actions(reference,3):signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
  if policy.get('fixed_vsl'):
   from evaluation.controllers.control_hold import fixed_vsl_values
   decoded=coord.decode(coord.encode(reference),reference)
   scheduled=[]
   for j,block in enumerate(seq.actions(decoded,3)):
    t=AT+j*cfg.simulation.T_c_sec
    expected=fixed_vsl_values(block.vsl,policy['fixed_vsl'],cfg.network.freeway_vsl_zone_heads,t)
    assert block.vsl==expected,(t,block.vsl,expected)
    signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
    scheduled.append({'sim_sec':t,'vsl':block.vsl})
   save('scheduled_vsl.json',scheduled)
  save('writer.json',{'proof':proof,'urban_blocks':[b.urban_storage_receipt for b in coord.blocks],
       'greens':reference.green_times,'meter':[ramps.physical_commands(c,cfg) for c in seq.actions(reference,3)]})
  if args.no_prediction:raise Done()
  candidates=[reference];names=['protected_seed']
  zz=coord.encode(reference)
  for block in range(3):
   for j,axis in enumerate(coord.axes):
    if axis['owner']=='SC1001' and axis['kind']=='green' and axis['key']=='p2' and axis['block']==block:
     zz[j]+=2./axis['scale']
  if not args.single_prediction and coord.valid(zz):
   candidate=coord.decode(zz,reference);coord.validate(candidate);candidates.append(candidate);names.append('left_plus2_p4_minus2')
  rows=[]
  for name,action in zip(names,candidates):
   item=evaluate([action],derivatives=False)[0]
   feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance'])
   rows.append({'name':name,'model_feasible':feasible,'objective_veh_h':item['objective_veh_h'],
       'costs':item['sdmpc_omega_partition']['costs'],'resource_summary':item['resource_summary'],
       'green':action.green_times,'quantities':item['quantities']})
   save('predictions.json',rows)
   assert feasible,'Existing model constraints failed'
  raise Done()
 sdmpc_pfo.solve=audit
 tuning=Path(args.tuning).resolve() if args.tuning else HERE/'config.json'
 save('protocol.json',{'frozen_root':str(ROOT),'tuning_sha256':hashlib.sha256(tuning.read_bytes()).hexdigest(),'state':str(F/f'state_{AT:06}.json'),'max_predictions':0 if args.no_prediction else 1 if args.single_prediction else 2,'native_runs':0,'optimization_iterations':0,'live_files_readonly':True,'cold_prices':args.cold_prices})
 sys.argv=[adapter.__file__,'--state-json',str(F/f'state_{AT:06}.json'),'--previous-action-json',str(F/f'action_{AT-150:06}.json'),'--out-action-json',str(OUT/'unused.json'),'--out-action-csv',str(OUT/'unused.csv'),'--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),'--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),'--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),'--tuning-json',str(tuning),'--controller','wu-link']
 start=time.perf_counter()
 try:adapter.main()
 except Done:
  save('completion.json',{'status':'complete','seconds':time.perf_counter()-start})
  save('runtime_reads.json',sorted(opened))
 else:raise AssertionError('Diagnostic hook not reached')
if __name__=='__main__':main()
