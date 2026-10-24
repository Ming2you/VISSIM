"""One saved-state domain/writer/model check; no optimizer, COM or live writes."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes,hashlib,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'capture4500_v2'
F=Path('D:/VISSIM_runs/20261006_min2_storage90_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
AT=4500
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
  raise Done()
 sdmpc_pfo.solve=audit
 tuning=HERE.parent/'urban257/min_green2/config.json'
 save('protocol.json',{'frozen_root':str(ROOT),'tuning_sha256':hashlib.sha256(tuning.read_bytes()).hexdigest(),'state':str(F/'state_004500.json'),'max_predictions':1,'native_runs':0,'optimization_iterations':0,'live_files_readonly':True})
 sys.argv=[adapter.__file__,'--state-json',str(F/'state_004500.json'),'--previous-action-json',str(F/'action_004350.json'),'--out-action-json',str(OUT/'unused.json'),'--out-action-csv',str(OUT/'unused.csv'),'--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),'--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),'--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),'--tuning-json',str(tuning),'--controller','wu-link']
 start=time.perf_counter()
 try:adapter.main()
 except Done:save('completion.json',{'status':'complete','seconds':time.perf_counter()-start})
 else:raise AssertionError('Diagnostic hook not reached')
if __name__=='__main__':main()
