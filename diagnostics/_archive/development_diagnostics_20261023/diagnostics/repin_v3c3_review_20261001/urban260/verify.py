"""One saved-state domain/writer/model check; no optimizer, COM or live writes."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes,hashlib,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--at',type=int,default=4500);ap.add_argument('--out',default='verify4500');ap.add_argument('--no-prediction',action='store_true');ap.add_argument('--tuning');ap.add_argument('--single-prediction',action='store_true');ap.add_argument('--cold-prices',action='store_true',help='Offline reference/writer diagnostic only: do not reuse a different policy price history');ap.add_argument('--decisions',type=Path,help='Saved decision folder; read-only');ap.add_argument('--recorded-first-step',action='store_true',help='Replay actual applied command for150s; future observation is target only');ap.add_argument('--full-selection',action='store_true',help='Continue through canonical PFO/SDMPC with unchanged tuning budgets and actual historical prices');ap.add_argument('--execution-check',type=Path,help='Compare protected seed and saved selected command in the discrete model; two predictions only');
ap.add_argument('--meter-candidates',action='store_true',help='Four finite RM combinations on saved final city/VSL commands; no optimizer or native execution')
args=ap.parse_args()
if args.meter_candidates and (args.full_selection or args.execution_check or args.recorded_first_step or args.no_prediction or args.single_prediction):ap.error('--meter-candidates is a separate bounded comparison')
if args.full_selection and (args.no_prediction or args.single_prediction or args.recorded_first_step or args.cold_prices or args.execution_check):ap.error('--full-selection must retain the complete optimizer and actual price history')
if args.execution_check and (args.no_prediction or args.single_prediction or args.recorded_first_step or args.cold_prices):ap.error('--execution-check is a separate two-prediction diagnostic')
OUT=HERE/args.out
F=Path('D:/VISSIM_runs/20261006_min2_storage90_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
if args.decisions:F=args.decisions.resolve()
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
 if args.meter_candidates:
  from evaluation.controllers.sdmpc_tangent_surrogate import Query
  original_query_init=Query.__init__
  def stock_query_init(self,*a,**kw):
   original_query_init(self,*a,**kw)
   runner=self.runner
   self.runner=lambda request:runner(dict(request,diagnostic_stock_costs=True))
  Query.__init__=stock_query_init
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
 original_pfo_solve=sdmpc_pfo.solve
 forecasts=[]
 forecast_original=adapter.demand_from_state
 def capture_forecast(*a,**kw):
  result=forecast_original(*a,**kw);forecasts[:]=result;return result
 adapter.demand_from_state=capture_forecast
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
  if args.full_selection:
   return original_pfo_solve(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit)
  if args.meter_candidates:
   from src.models.state import ControlAction
   path=F/f'action_{AT:06}.json'
   assert Path(str(path)+'.applied').is_file()
   selected=adapter.control_from_json(path,cfg,ControlAction)
   coord.validate(selected)
   # Keep the saved final non-RM controls and cap values. Reset only meters
   # to the protected previous command, then test East, West10480 and both.
   z=coord.encode(selected);basez=coord.encode(reference)
   for j,axis in enumerate(coord.axes):
    if axis['kind']=='meter':z[j]=basez[j]
   base=coord.decode(z,selected)
   alternatives=dict(sdmpc.meter_neighbors(coord,base))
   east=alternatives.get('FW_E:tighten',base)
   west=alternatives.get('RM_C10480:tighten',base)
   both=coord.encode(east);westz=coord.encode(west)
   for j,axis in enumerate(coord.axes):
    if axis['kind']=='meter' and axis['key']=='RM_C10480':both[j]=westz[j]
   combined=coord.decode(both,east)
   rows=[];seen={}
   for name,action in [('previous_meters',base),('east_tighten',east),('west10480_tighten',west),('combined',combined)]:
    coord.validate(action)
    for b,original in zip(seq.actions(action,3),seq.actions(selected,3)):
     assert b.green_times==original.green_times and b.offsets==original.offsets and b.vsl==original.vsl
     signals.validate_writer(b,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
    identity=tuple(coord.encode(action))
    if identity in seen:
     rows.append(dict(name=name,duplicate_of=seen[identity]));continue
    seen[identity]=name
    began=time.perf_counter();item=evaluate([action],derivatives=False)[0]
    quantity_proof=constraints.shared_quantity_constraints(adapter._PHASE_VECTOR_FOLLOWER['ref'],action,item['quantities'],start_sec=AT,horizon_steps=3,
      np_mode='cap',target_np_veh=selected.N_P_star,np_tolerance_veh=options['shared_tolerance'],
      nuf_mode='cap',target_nuf_veh_h=selected.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
    stock=item['diagnostic_stock_costs_veh_h']
    assert abs(sum(stock.values())-item['objective_veh_h'])<1e-7
    save(name+'_response.json',clean(item));save(name+'_action.json',clean(vars(action)))
    rows.append(dict(name=name,objective_veh_h=item['objective_veh_h'],seconds=time.perf_counter()-began,
      costs_by_stock_veh_h=stock,owner_costs_veh_h=item['sdmpc_omega_partition']['costs'],
      shared_constraints=quantity_proof,model_feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance']),
      merge=item['control_area']['predicted_ramp_merge'],flow_counts=item['control_area']['flow_counts'],
      greens=[{r:b.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps} for b in seq.actions(action,3)],
      writer_validated=True))
    save('meter_comparison.json',dict(at=AT,rows=rows,scope='Same saved state and final city/VSL controls; continuous 450s model, not native causal evidence',native_runs=0))
    print(name,item['objective_veh_h'],quantity_proof['feasible'],flush=True)
   save('meter_comparison.json',dict(at=AT,rows=rows,scope='Same saved state and final city/VSL controls; continuous 450s model, not native causal evidence',native_runs=0))
   raise Done()
  if args.execution_check:
   from collections import Counter
   from src.models.state import ControlAction
   from evaluation.controllers import area_follower_objective as shared
   from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
   selected_path=args.execution_check.resolve()
   selected=adapter.control_from_json(selected_path,cfg,ControlAction)
   coord.validate(selected)
   for block in seq.actions(selected,3):signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
   seed=reference.copy();seed.N_P_star=selected.N_P_star;seed.N_UF_star=selected.N_UF_star
   follower=adapter._PHASE_VECTOR_FOLLOWER['ref']
   assert follower.cfg is cfg
   counts=Counter();first_cycle=[];active=None;meter_greens=[]
   apply=PhysicalRampBoundary.apply_head_service
   def observe_head(buffer,service_veh,*,mode,**kw):
    if str(buffer.connector_id)=='10681':
     index=int((buffer.time_sec-AT)//cfg.simulation.T_c_sec)
     assert 0<=index<3
     g=meter_greens[index]
     expected='GREEN' if buffer.time_sec%10<g else 'RED'
     assert mode==expected,(buffer.time_sec,mode,expected)
     if mode=='RED':assert abs(service_veh)<1e-12
     counts[mode]+=1
     if buffer.time_sec<AT+10:first_cycle.append([buffer.time_sec,mode,service_veh])
    return apply(buffer,service_veh,mode=mode,**kw)
   PhysicalRampBoundary.apply_head_service=observe_head
   rows=[]
   try:
    for name,active in [('protected_seed',seed),('selected',selected)]:
     counts.clear();first_cycle.clear();started=time.perf_counter()
     meter_greens=[block.diagnostics['rw_meter_green_RM_C10681'] for block in seq.actions(active,3)]
     batch=shared.evaluate_shared_owner_batch(follower,state,seed,forecasts,[active],horizon_steps=3)
     assert batch['endpoint_calls']==1 and batch['requested']==1
     item=batch['results'][0]
     assert counts['GREEN']==360 and counts['RED']==540,(name,counts)
     quantity_proof=constraints.shared_quantity_constraints(follower,active,item['quantities'],start_sec=AT,horizon_steps=3,
         np_mode='cap',target_np_veh=selected.N_P_star,np_tolerance_veh=options['shared_tolerance'],
         nuf_mode='cap',target_nuf_veh_h=selected.N_UF_star,nuf_tolerance_veh_h=options['shared_tolerance'])
     save(name+'_discrete_response.json',clean(item))
     rows.append(dict(name=name,objective_veh_h=item['objective_veh_h'],seconds=time.perf_counter()-started,
         model_feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance']),shared_constraints=quantity_proof,
         meter10681_phase_calls=dict(counts),first_meter_cycle=list(first_cycle),
         costs=item['sdmpc_omega_partition']['costs'],merge=item['control_area']['predicted_ramp_merge'],
         resource_summary=item['resource_summary']))
     save('discrete_check.json',dict(start_sec=AT,end_sec=AT+450,rows=rows,native_runs=0,
          selected_source_sha256=hashlib.sha256(selected_path.read_bytes()).hexdigest(),
          scope='Two unchanged-input discrete signal/RG meter model predictions; not VISSIM traffic or an optimizer rerun'))
   finally:PhysicalRampBoundary.apply_head_service=apply
   raise Done()
  if args.recorded_first_step:
   from src.models.state import ControlAction
   from src.controllers import rollout_endpoint as endpoint
   from evaluation.controllers import area_meter_finalization as meters
   path=F/f'action_{AT:06}.json'
   assert path.with_suffix('.json.applied').is_file()
   action=meters.prepare_held_actual_reference(adapter.control_from_json(path,cfg,ControlAction),cfg)
   signals.validate_writer(action,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
   point=endpoint.evaluate_price_point(state,action,forecasts[:1],(),
       endpoint.ObjectiveSpec(cfg,depth_override=1,box_walk=False,score_mode='raw'),capture_response=True)
   assert not point.aborted and len(point.states)==1
   # Only read the future after prediction; never provide it to initialization or rollout.
   future_path=F/f'state_{AT+150:06}.json';future=read(future_path)
   assert future['vehicle_records']['complete'] and future['sim_sec']==AT+150
   response=point.control_area_response
   import gzip
   with gzip.open(OUT/'recorded_response.json.gz','wt',encoding='utf-8') as h:json.dump(response,h,ensure_ascii=False,allow_nan=False)
   final=point.states[-1]
   source='SC1003_to_SC1001'
   moves={m:s for m,s in cfg.network.urban_movements.items() if s['origin']==source}
   def local(s):
    return dict(movement_queue={m:s.urban_movement_queue[m] for m in moves},
       occupied_storage=cfg.network.urban_link_storage_veh[source]-s.urban_link_storage[source],
       arrival_buffer=s.urban_arrival_buffer.get(source,{}),release_buffer=s.urban_storage_release_buffer.get(source,{}))
   rows=future['vehicle_records']['records']
   save('recorded_first_step.json',dict(start_sec=AT,end_sec=AT+150,ttt_omega_veh_h=point.ttt,
      recorded_action_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
      future_target_sha256=hashlib.sha256(future_path.read_bytes()).hexdigest(),future_used_as_input=False,
      initial=local(state),final=local(final),
      native_stocks={str(link):dict(n=sum(v['link_no']==link for v in rows),
        stopped=sum(v['link_no']==link and v['stopped'] for v in rows)) for link in (40,10493,10492,31,124)},
      native_left_head=future['obs150']['detectors']['960164'],
      predicted_movement_flow={m:point.control_area['flow_counts'].get('movement:'+m,0.) for m in moves},
      native_queue_comparison_scope='Model queue is ready contiguous stock; native stopped stock also contains disconnected tails. Head and connector boundaries differ by a few metres. No causal lever-gain claim.'))
   raise Done()
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
   save(name+'_response.json',clean(item))
   feasible=sdmpc_pfo.model_feasible(item,options['shared_tolerance'])
   rows.append({'name':name,'model_feasible':feasible,'objective_veh_h':item['objective_veh_h'],
       'costs':item['sdmpc_omega_partition']['costs'],'resource_summary':item['resource_summary'],
       'green':action.green_times,'quantities':item['quantities']})
   save('predictions.json',rows)
   assert feasible,'Existing model constraints failed'
  raise Done()
 sdmpc_pfo.solve=audit
 tuning=Path(args.tuning).resolve() if args.tuning else HERE/'config.json'
 save('protocol.json',{'frozen_root':str(ROOT),'tuning_sha256':hashlib.sha256(tuning.read_bytes()).hexdigest(),'state':str(F/f'state_{AT:06}.json'),'max_predictions':4 if args.meter_candidates else None if args.full_selection else 1 if args.recorded_first_step else 0 if args.no_prediction else 1 if args.single_prediction else 2,'prediction_horizon_sec':150 if args.recorded_first_step else 450,'native_runs':0,'optimization_iterations':None if args.full_selection else 0,'live_files_readonly':True,'cold_prices':args.cold_prices,'full_selection':args.full_selection,'budgets':'unchanged tuning; actual calls/iterations in joint result' if args.full_selection else 'bounded reference check'})
 sys.argv=[adapter.__file__,'--state-json',str(F/f'state_{AT:06}.json'),'--previous-action-json',str(F/f'action_{AT-150:06}.json'),'--out-action-json',str(OUT/'unused.json'),'--out-action-csv',str(OUT/'unused.csv'),'--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),'--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),'--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),'--tuning-json',str(tuning),'--controller','wu-link']
 start=time.perf_counter()
 try:adapter.main()
 except Done:
  save('completion.json',{'status':'complete','seconds':time.perf_counter()-start})
  save('runtime_reads.json',sorted(opened))
 else:
  if not args.full_selection:raise AssertionError('Diagnostic hook not reached')
  assert (OUT/'unused.json').is_file() and (OUT/'unused.csv').is_file()
  save('completion.json',{'status':'complete','seconds':time.perf_counter()-start,'full_selection':True,'native_execution':False})
  save('runtime_reads.json',sorted(opened))
if __name__=='__main__':main()
