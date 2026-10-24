"""Two frozen-source offline responses; no optimization, COM, live writes or fit."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes,hashlib,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('E:/VISSIM_runtime/20261005_shared124/frozen/sdmpc31_26569d54_202610051903')
OUT=HERE/'rejection3150'
F=Path('D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
AT=3150
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
 def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
  from src.models.state import ControlAction
  saved=read(F/'action_003150.joint.json')['selection']
  row=saved['candidates'][2];recovery=saved['central_multiplier'][2]
  seed=adapter.control_from_json(F/'action_003150.json',coord.cfg,ControlAction)
  seed.N_P_star,seed.N_UF_star=row['np_cap'],row['nuf_target']
  action=coord.decode(np.array(recovery['selected_point']),seed);coord.validate(action)
  expected=next(x for x in saved['meter_neighbor_audit']['candidates'] if x['candidate']=='RM_C10681:release' and x['nuf_target']==row['nuf_target'])
  assert sdmpc.token(action)==expected['incumbent_action_token'],'Do not analyze a different incumbent'
  release=dict(sdmpc.meter_neighbors(coord,action))['RM_C10681:release']
  # Preserve frozen evaluator behavior. Only two scalar predictions are requested.
  results=evaluate([action,release],derivatives=False)
  assert abs(results[0]['objective_veh_h']-row['objective'])<1e-7
  assert abs(results[1]['objective_veh_h']-expected['objective'])<1e-7
  follower=adapter._PHASE_VECTOR_FOLLOWER['ref'];out={}
  for name,a,item in zip(('incumbent','release'),(action,release),results):
   q=constraints.shared_quantity_constraints(follower,a,item['quantities'],start_sec=AT,horizon_steps=3,np_mode='cap',target_np_veh=a.N_P_star,np_tolerance_veh=options['np_tolerance_veh'],nuf_mode='cap',target_nuf_veh_h=a.N_UF_star,nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
   out[name]={'objective':item['objective_veh_h'],'constraints':q,'model_feasible':sdmpc_pfo.model_feasible(item,options['shared_tolerance']),
     'coverage':item['model_constraint_coverage'],'resource_summary':item['resource_summary'],
     'omega_partition':item['sdmpc_omega_partition'],'ramps':[c.diagnostics['rw_meter_green_RM_C10681'] for c in seq.actions(a,3)]}
  save('assessment.json',out);save('reproduction.json',{'incumbent_objective_error':results[0]['objective_veh_h']-row['objective'],'release_objective_error':results[1]['objective_veh_h']-expected['objective'],'native_runs':0,'optimizations':0,'predictions':2,'coefficients_changed':False})
  print(json.dumps({k:{'objective':v['objective'],'np':v['constraints']['np'],'nuf':v['constraints']['nuf'],'model_feasible':v['model_feasible'],'resource_max':v['resource_summary']['max_exceedance_veh'],'ramps':v['ramps']} for k,v in out.items()}),flush=True)
  raise Done()
 sdmpc_pfo.solve=audit
 tuning=ROOT/'diagnostics/repin_v3c3_review_20261001/spillback256/config.json'
 save('protocol.json',{'frozen_root':str(ROOT),'tuning_sha256':hashlib.sha256(tuning.read_bytes()).hexdigest(),'state':str(F/'state_003150.json'),'max_predictions':2,'native_runs':0,'optimization_iterations':0,'live_files_readonly':True})
 sys.argv=[adapter.__file__,'--state-json',str(F/'state_003150.json'),'--previous-action-json',str(F/'action_003000.json'),'--out-action-json',str(OUT/'unused.json'),'--out-action-csv',str(OUT/'unused.csv'),'--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),'--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),'--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),'--tuning-json',str(tuning),'--controller','wu-link']
 start=time.perf_counter()
 try:adapter.main()
 except Done:save('completion.json',{'status':'complete','seconds':time.perf_counter()-start})
 else:raise AssertionError('Diagnostic hook not reached')
if __name__=='__main__':main()
