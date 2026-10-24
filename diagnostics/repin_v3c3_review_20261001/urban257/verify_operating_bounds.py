"""One saved-state domain/writer/model check; no optimizer, COM or live writes."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes,hashlib,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'min_green2/observed4200_v2'
F=Path('D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
AT=4200
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
 original_bounds=ramps.configure_operating_bounds
 def bound_capture(state,cfg,reference):
  proof=original_bounds(state,cfg,reference);save('bounds.json',proof);return proof
 ramps.configure_operating_bounds=bound_capture
 def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
  proof=coord.validate(reference)
  written=[]
  for c in seq.actions(reference,3):
   rows=ramps.physical_commands(c,coord.cfg)
   assert len(rows)==8 and all(2<=r['green_sec']<=10 for r in rows.values())
   assert c.green_times==coord.reference.green_times and c.offsets==coord.reference.offsets and c.vsl==coord.reference.vsl
   written.append(rows)
  save('writer.json',{'validation':proof,'blocks':written,'held_domain_feasible':bool(coord.valid(coord.encode(coord.reference))),
   'seed_domain_feasible':bool(coord.valid(coord.encode(reference))),'axes':len(coord.axes)})
  item=evaluate([reference],derivatives=False)[0]
  feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance'])
  save('model.json',{'model_feasible':feasible,'objective':item['objective_veh_h'],
   'coverage':{k:v for k,v in item['model_constraint_coverage'].items() if not isinstance(v,(list,dict))},
   'resource_summary':item['resource_summary'],'native_runs':0,'optimizations':0,'predictions':1,
   'scope':'Feasible operating-domain seed from actual4200. No claim of optimized performance or no future spillback.'})
  print('OPERATING_SEED',feasible,'greens', {r:v['green_sec'] for r,v in written[0].items()},flush=True)
  assert feasible,'Protected seed failed existing model feasibility checks'
  raise Done()
 sdmpc_pfo.solve=audit
 tuning=HERE/'min_green2/config.json'
 save('protocol.json',{'frozen_root':str(ROOT),'tuning_sha256':hashlib.sha256(tuning.read_bytes()).hexdigest(),'state':str(F/'state_004200.json'),'max_predictions':1,'native_runs':0,'optimization_iterations':0,'live_files_readonly':True})
 sys.argv=[adapter.__file__,'--state-json',str(F/'state_004200.json'),'--previous-action-json',str(F/'action_004050.json'),'--out-action-json',str(OUT/'unused.json'),'--out-action-csv',str(OUT/'unused.csv'),'--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),'--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),'--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),'--tuning-json',str(tuning),'--controller','wu-link']
 start=time.perf_counter()
 try:adapter.main()
 except Done:save('completion.json',{'status':'complete','seconds':time.perf_counter()-start})
 else:raise AssertionError('Diagnostic hook not reached')
if __name__=='__main__':main()
