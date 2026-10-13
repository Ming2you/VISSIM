"""Archive this bounded candidate and restore only its two exact baseline files."""
import datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
assert not (HERE/'restoration.json').exists()
p=read(HERE/'plan.json');a=read(HERE/'comparison.json')
assert a['forecasts']==3 and not a['calibration_control_gate_passed']
assert a['delta_omega_veh_h']['actual']>0>a['delta_omega_veh_h']['predicted']
assert a['unused3300']['final_W_out']['predicted']>a['unused3300']['final_W_out']['previous']>a['unused3300']['final_W_out']['actual']
records=[]
for name in ('route_choice_corridor','urban_flow_accounting'):
    current=ROOT/'evaluation/controllers'/f'{name}.py'
    before=HERE/f'{name}.before.py';archive=HERE/f'{name}.candidate.py.preserved'
    assert current.resolve().is_relative_to(ROOT.resolve())
    assert sha(current)==p['source_pins'][str(current)]
    assert not archive.exists()
    archive.write_bytes(current.read_bytes());current.write_bytes(before.read_bytes())
    assert sha(current)==sha(before)
    records.append(dict(file=str(current),candidate_archive=str(archive),candidate_sha256=sha(archive),restored_sha256=sha(current)))
test=ROOT/'tests/test_known_wout_connector_stage.py';archive=HERE/'test_known_wout_connector_stage.py.preserved'
assert test.resolve().is_relative_to(ROOT.resolve()) and sha(test)==p['source_pins'][str(test)] and not archive.exists()
test.rename(archive)
restoration=dict(status='exact_baseline_restored',files=records,test_archive=str(archive),test_sha256=sha(archive),
    reason='Finite connector stage improves local stock, but selected late drain and whole-network decision remain unqualified. Preserve experimental candidate, do not promote it or fit another rate in this scope.',
    full_ad=0,full_optimization=0,native_runs=0,active_queue_changed=False)
save(HERE/'restoration.json',restoration)
p['status']='complete_local_stock_improvement_not_adopted';p['comparison']='comparison.json';p['restoration']='restoration.json'
p['source_pin_interpretation']='Historical experimental sources are preserved in *.candidate.py.preserved; production core restored exactly. Re-running this config requires deliberate restoration and requalification, not a blind retry.'
save(HERE/'plan.json',p)
parent=read(H/'plan.json')
save(HERE/'parent_plan_before.json',parent)
parent['connector_stage']=dict(status=p['status'],tests=33,fixed_forecasts=3,new_fitted_coefficients=0,new_native=0,full_ad=0,
    comparison='connector_stage/comparison.json',restoration='connector_stage/restoration.json',calibration_control_gate_passed=False)
parent['next']='Reuse completed connector-stage response to separate late W_out clearance: initial known10681 cohorts versus later prechoice inflow/route choice and physical52/66 entry. Do not refit a global discharge rate or repeat the completed three predictions. Connector geometry staging is archived as a local improvement, not an adopted control-gain fix. Bound any next structural combination by observed lane access, preserve current stock/route ownership, then validate meaningful control response before end-to-end SDMPC wall comparison.'
parent['previous_goal_turn']=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),classification='progress',completed=[
    'Single geometry-only finite connector stage implemented and tested:33 tests and three fixed predictions; no coefficient fit, optimizer or native.',
    'Six endpoint absolute W_out stock errors reduce202.13->95.16veh; first150 held/selected stock now110.29/72.95 vsnative103/78.',
    'Late selected stock still12.50/2.97 vsnative56/22; modelDeltaOmega-6.564 vsactual+4.193. Unused3300stock error1.00->3.17. Not adopted; exact baseline two files restored and candidate preserved.'
],next=parent['next'])
save(H/'plan.json',parent)
print(json.dumps(restoration,ensure_ascii=False,indent=2))
