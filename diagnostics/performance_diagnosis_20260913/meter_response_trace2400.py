"""Two raw canonical captures: actual hold versus RM_C10490g8, no new dynamics."""
from pathlib import Path
import collections
import copy
import gc
import hashlib
import json
import math
import os
import pickle
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name('lever_counterfactual2400')/'meter_trace10490_attempt01'
RUN=ROOT/'evaluation/runs/codex_fid_cl9000_s13_v3/decisions_codex_fid_cl9000_s13_v3'
CONFIG=ROOT/'diagnostics/selected_control_demand/codex_fid_cl9000_s13_v3/config.json'
MID='RM_C10490'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
psha=lambda v:hashlib.sha256(pickle.dumps(v,protocol=5)).hexdigest()


def analyze_capture(point,cfg):
    response=point.control_area_response
    initial=response['initial_freeway_operands']
    out={'response_sha256':psha(response),'control_area':point.control_area,'initial_omega_stock_veh':math.fsum(r['inside'] for r in initial['stock_cohorts'].values()),
        'model_constraint_coverage':response['model_constraint_coverage'],'ttt_by_stock_veh_h':{},'ttt_by_group_veh_h':{},
        'windows':[],'query_T_f':[],'release_T_u':[],'accepted_merge_T_f':[]}
    def group(key):
        if key.startswith('freeway:'):return 'mainline'
        if key.startswith('ramp:'):return 'onramp_connector'
        if key.startswith('merge_pending:'):return 'merge_pending'
        return 'urban_and_other'
    totals=collections.defaultdict(list)
    for row in response['residence']:
        for key,value in row['inside_veh'].items():totals[key].append(row['dt_h']*value)
    out['ttt_by_stock_veh_h']={k:math.fsum(v) for k,v in totals.items()}
    for key,value in out['ttt_by_stock_veh_h'].items():out['ttt_by_group_veh_h'].setdefault(group(key),0.);out['ttt_by_group_veh_h'][group(key)]+=value
    out['ttt_residence_sum_veh_h']=math.fsum(out['ttt_by_stock_veh_h'].values())
    assert math.isclose(out['ttt_residence_sum_veh_h'],point.control_area['ttt_veh_h'],abs_tol=1e-7,rel_tol=0.)
    from evaluation.controllers.control_area_objective import get_ledger
    for i,end in enumerate((2550.,2700.,2850.)):
        rows=[r for r in response['residence'] if r['end_sec']<=end]
        transfers=[r for r in response['transfers'] if r['end_sec']<=end]
        ttt=math.fsum(r['dt_h']*math.fsum(r['inside_veh'].values()) for r in rows)
        td=math.fsum(r['ttd_veh'] for r in transfers);entered=math.fsum(r['entered_veh'] for r in transfers)
        ledger=get_ledger(point.states[i]);stock=math.fsum(r['inside'] for r in ledger.stocks.values())
        assert point.states[i].time_sec==end
        assert math.isclose(ttt,ledger.metrics.ttt_veh_h,abs_tol=1e-7,rel_tol=0.)
        assert math.isclose(td,ledger.metrics.ttd_veh,abs_tol=1e-7,rel_tol=0.)
        out['windows'].append({'start_sec':2400.,'end_sec':end,'TTT_veh_h':ttt,'TD_veh':td,'entered_veh':entered,'end_omega_stock_veh':stock,
            'closure_veh':stock-(out['initial_omega_stock_veh']+entered-td)})
    query={};urban={}
    for r in response['resource_allocations']:
        if r['resource']!=MID:continue
        if r['kind'].startswith('ramp_release_query_'):
            key=(r['start_sec'],r['end_sec']);row=query.setdefault(key,{'start_sec':key[0],'end_sec':key[1]})
            kind=r['kind'][len('ramp_release_query_'):]
            row[kind+'_veh_per_T_f']=r['available_veh'];row['accepted_query_veh_per_T_f']=r['accepted_total_veh']
        if r['kind'].startswith('urban_meter_release_'):
            key=(r['start_sec'],r['end_sec']);row=urban.setdefault(key,{'start_sec':key[0],'end_sec':key[1]})
            kind=r['kind'][len('urban_meter_release_'):]
            row[kind+'_veh']=r['available_veh'];row['accepted_release_veh']=r['accepted_total_veh']
    for key,row in sorted(query.items()):
        values={kind:row[kind+'_veh_per_T_f'] for kind in ('available','capacity','density_receiving','request')}
        minimum=min(values.values())
        assert math.isclose(minimum,row['accepted_query_veh_per_T_f'],abs_tol=1e-8,rel_tol=0.)
        row['binding_min_terms']=[kind for kind,v in values.items() if math.isclose(v,minimum,abs_tol=1e-8,rel_tol=0.)]
        row['request_strictly_limits']=values['request'] < min(v for k,v in values.items() if k!='request')-1e-8
        out['query_T_f'].append(row)
    transfers=response['transfers'];ramp='ramp:'+MID;pending='merge_pending:'+MID
    for key,row in sorted(urban.items()):
        events=[r for r in transfers if r['start_sec']==key[0] and r['end_sec']==key[1] and r['stage']=='urban']
        incoming=[r for r in events if r['target']==ramp]
        departing=[r for r in events if r['source']==ramp and r['target']==pending]
        row['accepted_incoming_veh']=math.fsum(r['vehicles'] for r in incoming)
        row['incoming_sources']={source:math.fsum(r['vehicles'] for r in incoming if r['source']==source) for source in {r['source'] for r in incoming}}
        row['accepted_departing_veh']=math.fsum(r['vehicles'] for r in departing)
        row['stock_after_release_and_incoming_veh']=row['stock_veh']-row['accepted_release_veh']+row['accepted_incoming_veh']
        assert math.isclose(row['accepted_release_veh'],row['accepted_departing_veh'],abs_tol=1e-8,rel_tol=0.)
        assert math.isclose(row['accepted_release_veh'],min(row['stock_veh'],row['request_veh']),abs_tol=1e-8,rel_tol=0.)
        out['release_T_u'].append(row)
    for r in response['freeway_frames']:
        out['accepted_merge_T_f'].append({'start_sec':r['start_sec'],'end_sec':r['end_sec'],
            'accepted_merge_veh_h':r['actual_ramp_release_veh_h'][MID],
            'accepted_merge_veh':r['actual_ramp_release_veh_h'][MID]*(r['end_sec']-r['start_sec'])/3600,
            'post_landing_connector_stock_veh':r['model_stock_veh']['ramp:'+MID]})
    out['binding_counts']=dict(collections.Counter(k for r in out['query_T_f'] for k in r['binding_min_terms']))
    out['strict_request_binding_times']=[r['start_sec'] for r in out['query_T_f'] if r['request_strictly_limits']]
    out['captured_steps']={'T_f_queries':len(out['query_T_f']),'T_u_releases':len(out['release_T_u']),'accepted_merge_T_f':len(out['accepted_merge_T_f'])}
    out['initial_omega_ramp_cohorts']={k:v for k,v in initial['stock_cohorts'].items() if k.startswith(('ramp:','merge_pending:'))}
    out['all_ramp_residence_duration_sec']={k:math.fsum(r['dt_h']*3600 for r in response['residence'] if k in r['inside_veh']) for k in out['initial_omega_ramp_cohorts']}
    return out


def worker():
    os.chdir(ROOT);os.environ['RW_OFFSET_WRITER']='experiment';sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    started=time.perf_counter()
    paths=[Path(__file__),CONFIG,RUN/'state_002400.json',RUN/'action_002250.json',RUN/'action_002250.csv',RUN/'action_002400.joint.json']
    paths+=list((ROOT/'evaluation/controllers').glob('*.py'))
    pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
    report={'completed':False,'endpoint_limit':2,'native_run':False,'solver_runs':0,'price_fits':0,'source_sha256':pins,'arms':{},'ramp':MID}
    try:
        from diagnostics.probe_model_area_integration import build_projected
        from evaluation.controllers import vissim_stackelberg_adapter as a,area_follower_objective as area,physical_ramp_branches as ramps
        from evaluation.controllers.area_leader_objective import install_joint_price_field
        from src.models.state import ControlAction,segment_vsl
        from src.models.demand import DemandStep
        from src.controllers import rollout_endpoint as ep
        cfg,state,det,tuning,raw,mapping,metadata=build_projected(CONFIG,RUN/'state_002400.json',RUN/'action_002250.json',fixture_inputs=False)
        cal=a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        forecast=a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
        follower=a.build_priced_wu_link_controller(cfg,tuning).nash_solver
        previous=a.control_from_json(RUN/'action_002250.json',cfg,ControlAction);previous,_=area.expand_shared_vsl_action(previous,cfg,segment_vsl_func=segment_vsl)
        hold=previous.copy();hold.N_P_star=2400.;hold.N_UF_star=2996.9313872526645
        field=json.loads((RUN/'action_002400.joint.json').read_text())['selected_price_field']
        nodes={s:n for s,n in cfg.network.signal_actuation_contract['nodes'].items() if n.get('native_clock_basis') is not None}
        assert json.dumps(field['context']['native_clock_nodes'],sort_keys=True)==json.dumps(nodes,sort_keys=True)
        field['context']['native_clock_nodes']=copy.deepcopy(nodes)
        install_joint_price_field(follower,hold,field,expected_owners=tuple(cfg.network.signals)+tuple(cfg.network.freeway_links),expected_context=field['context'],nuf_mode='equality')
        greens={r:hold.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps};greens[MID]=8.
        g8=ramps.candidate_from_greens(hold,previous,cfg,greens)
        controls={'hold':hold,'g8':g8}
        report['ramp_definition']=cfg.network.physical_ramp_branches['ramps'][MID]
        report['native_RG_pulse_in_model']=False
        report['model_clock_sec']={'T_f':cfg.simulation.T_f_sec,'T_u':cfg.simulation.T_u_sec,'T_c':cfg.simulation.T_c_sec}
        frozen=pickle.dumps((follower,state,previous,hold,g8,forecast),protocol=5)
        report['frozen_inputs_sha256']=hashlib.sha256(frozen).hexdigest();report['forecast_sha256']=psha(forecast)
        report['setup_sec']=time.perf_counter()-started
        for name,control in controls.items():
            t=time.perf_counter()
            with area.shared_query_runtime_scope():
                point=ep.evaluate_price_point(state,control,forecast,(),ep.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
            assert not point.aborted and len(point.states)==3 and point.control_area_response['model_constraint_coverage']['complete']
            assert pickle.dumps((follower,state,previous,hold,g8,forecast),protocol=5)==frozen
            payload=pickle.dumps(point.control_area_response,protocol=5)
            path=OUT/(name+'_captured_response.pickle');path.write_bytes(payload)
            result=analyze_capture(point,cfg)
            result.update(endpoint_wall_sec=time.perf_counter()-t,raw_response_file=path.name,raw_response_file_sha256=hashlib.sha256(payload).hexdigest())
            report['arms'][name]=result
            print(json.dumps({'arm':name,'TTT':point.control_area['ttt_veh_h'],'steps':result['captured_steps'],'binding':result['binding_counts'],'strict':result['strict_request_binding_times']}),flush=True)
            del point,payload;gc.collect()
        report['checks']={'hold_TTT_replays':math.isclose(report['arms']['hold']['control_area']['ttt_veh_h'],326.0873745673935,abs_tol=1e-7,rel_tol=0.),
            'g8_TTT_replays':math.isclose(report['arms']['g8']['control_area']['ttt_veh_h'],326.1104357193934,abs_tol=1e-7,rel_tol=0.),'frozen_inputs_preserved':True}
        report['endpoint_calls']=2;report['completed']=all(report['checks'].values())
    except Exception:
        report['error']=traceback.format_exc();print(report['error'],flush=True)
    finally:
        report['source_changes']=[p for p,h in pins.items() if sha(ROOT/p)!=h];report['completed']=report['completed'] and not report['source_changes']
        report['wall_sec']=time.perf_counter()-started
        (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    return 0 if report['completed'] else 1


def main():
    if sys.argv[1:]==['--worker']:return worker()
    OUT.mkdir(exist_ok=False);started=time.perf_counter();receipt={'completed':False,'timeout_sec':300,'owned_child_only':True,'native_run':False}
    try:
        with (OUT/'stdout.txt').open('xb') as out,(OUT/'stderr.txt').open('xb') as err:
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker'],cwd=ROOT,stdout=out,stderr=err,timeout=300)
        receipt.update(exit_code=result.returncode,completed=result.returncode==0)
    except subprocess.TimeoutExpired:receipt['error']='Owned offline child exceeded300s and was terminated.'
    finally:
        receipt['wall_sec']=time.perf_counter()-started;(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt),flush=True)
    return 0 if receipt['completed'] else 1


if __name__=='__main__':sys.exit(main())
