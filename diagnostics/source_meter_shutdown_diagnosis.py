"""Bounded recorded-choice audit and two held-meter/budget counterfactuals.

No optimizer or VISSIM. All policy vectors except meters and their summed budget
are identical. Observations after1200 enter only the comparison, never forecast.
"""
from __future__ import annotations
import copy,json,pickle,time,sys
from pathlib import Path
from unittest.mock import patch
from diagnostics.audit_live_prediction_interval import ROOT,load,sha,stock_snapshot
from diagnostics.probe_model_area_integration import build_projected,replay_provenance
from evaluation.controllers import vissim_stackelberg_adapter as adapter,area_runtime,area_meter_finalization
from src.controllers import rollout_endpoint
from src.controllers.leader import Leader
from src.models.state import ControlAction
from src.models.demand import DemandStep
from src.simulation import coupling

RUN='codex_area_sources_beta0_s13_20260910'
CONFIG=ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
OUTPUT=ROOT/'diagnostics/source_meter_shutdown_diagnosis.json'

def selected(diag):
    prefixes=('leader_nuf_','leader_candidate_','leader_second_','leader_full_',
              'leader_coarse_','leader_fallback_','leader_objective_',
              'leader_ramp_queue','leader_density_','leader_mfd_storage_penalty',
              'leader_pfo_','control_area_follower_','control_area_meter_',
              'rw_meter_requested_','rw_meter_realized_','rw_meter_green_',
              'rw_spill_','distributed_response_')
    return {k:v for k,v in diag.items() if k.startswith(prefixes) and not isinstance(v,dict)}

def main():
    began=time.monotonic();run=ROOT/'evaluation/runs'/RUN;dec=run/('decisions_'+RUN)
    paths=[CONFIG,Path(__file__),run/'area_candidate_source_manifest.json',
           ROOT/'diagnostics/source_interval_1200_1350.json']
    for sec in (900,1050,1200,1350,1500):
        paths += [dec/f'{kind}_{sec:06d}.json' for kind in ('state','action')]
    manifest=load(paths[2]);tuning=load(CONFIG)
    paths += [ROOT/p for p in manifest['source_sha256']]
    before=replay_provenance(tuning,*paths)
    assert all(sha(ROOT/p)==h for p,h in manifest['source_sha256'].items())
    assert any(r['sha256']==sha(CONFIG) for r in manifest['outputs'].values())
    cfg,state,detectors,tuning,raw,mapping,meta=build_projected(CONFIG,dec/'state_001200.json',dec/'action_001050.json',fixture_inputs=False)
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,3,calibration,detectors)
    control=adapter.control_from_json(dec/'action_001200.json',cfg,ControlAction)
    original_vectors={k:copy.deepcopy(getattr(control,k)) for k in ('N_P_star','green_times','offsets','vsl')}
    initial=stock_snapshot(state,cfg);arms={};leader=Leader(cfg)
    inadmissible=control.copy();inadmissible.ramp_metering={k:1800. for k in inadmissible.ramp_metering}
    area_meter_finalization.finalize(inadmissible,cfg)
    quantization={'requested_vph':{k:1800. for k in inadmissible.ramp_metering},
                  'realized_vph':dict(inadmissible.ramp_metering),'realized_sum_vph':sum(inadmissible.ramp_metering.values()),
                  'candidate_admissible':False,'reason':'Exceeds7200 leader box; excluded from endpoint comparison.',
                  'physical_green_sec':{k:v for k,v in inadmissible.diagnostics.items() if k.startswith('rw_meter_green_')}}
    reuse='--reuse-partial' in sys.argv
    prior_proof=None
    if reuse:
        partial=load(OUTPUT.with_name(OUTPUT.stem+'_partial.json'))
        prior_proof=partial['source_sha256']
        assert all(sha(ROOT/p)==h for p,h in prior_proof.items() if Path(ROOT/p).resolve()!=Path(__file__).resolve())
        assert set(partial['paired'])=={'recorded_closed','reopen_DW_FE_only'}
        arms=partial['paired']
    for name in (() if reuse else ('recorded_closed','reopen_DW_FE_only')):
        private=control.copy()
        if name=='reopen_DW_FE_only':private.ramp_metering.update(R_D_W=1800.,R_F_E=1800.)
        requested=dict(private.ramp_metering)
        area_meter_finalization.finalize(private,cfg)
        private.N_UF_star=sum(private.ramp_metering.values())
        assert all(getattr(private,k)==v for k,v in original_vectors.items())
        assert private.N_UF_star==sum(private.ramp_metering.values())
        assert private.N_UF_star<=cfg.leader.N_UF_star_range[1]
        if name=='reopen_DW_FE_only':
            assert all(private.ramp_metering[k]==control.ramp_metering[k] for k in ('R_F_W','R_D_E'))
            assert all(private.ramp_metering[k]==1800. for k in ('R_D_W','R_F_E'))
            assert all(private.diagnostics['rw_meter_green_'+k]==10. for k in ('RM_C10480','RM_C10482','RM_C10639','RM_C10681'))
        snapshot=pickle.dumps((state,private,forecast),protocol=5)
        expected={k:copy.deepcopy(getattr(private,k)) for k in (*original_vectors,'N_UF_star','ramp_metering')}
        trace=[];original=coupling.freeway_substep
        def observe(*args,**kwargs):
            if time.monotonic()-began>85:raise TimeoutError('Bounded diagnostic85s computation budget exceeded')
            assert all(getattr(args[1],k)==v for k,v in expected.items()),'held meter/budget/control changed'
            result=original(*args,**kwargs)
            trace.append({'elapsed_sec':(len(trace)+1)*cfg.simulation.T_f_sec,
                          'ramp_queues_veh':dict(args[0].ramp_queue),
                          'E8_speed_kph':args[0].freeway_speed['FW_E'][8],
                          'E9_speed_kph':args[0].freeway_speed['FW_E'][9],
                          'diagnostics':dict(result[1])})
            return result
        with patch.object(coupling,'freeway_substep',observe):
            point=rollout_endpoint.evaluate_price_point(state,private,forecast,[],
                rollout_endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'))
        assert not point.aborted and len(point.states)==3 and len(trace)==45
        assert pickle.dumps((state,private,forecast),protocol=5)==snapshot
        ends=[]
        for i,s in enumerate(point.states,1):
            s._control_area_ledger.assert_stocks(area_runtime.model_inventory(s,cfg))
            metrics=vars(s._control_area_ledger.metrics).copy()
            terms=leader.objective_terms(point.states[:i],private,control,
                metrics['ttt_veh_h']-cfg.network.control_area_beta_seconds/3600*metrics['ttd_veh'],True)
            ends.append({'elapsed_sec':i*cfg.simulation.T_c_sec,'stocks':stock_snapshot(s,cfg),
                         'area_metrics':metrics,'flow_counts':dict(s._control_area_ledger.flow_counts),
                         'leader_terms_for_held_control':terms})
        arms[name]={'N_UF_star_vph':private.N_UF_star,'requested_meters_vph':requested,'meters_vph':dict(private.ramp_metering),
                    'physical_green_sec':{k:v for k,v in private.diagnostics.items() if k.startswith('rw_meter_green_')},
                    'endpoints':ends,'trace':trace,'input_unchanged':True}
        OUTPUT.with_name(OUTPUT.stem+'_partial.json').write_text(json.dumps({'status':'partial','paired':arms,'source_sha256':before},ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    assert all(getattr(control,k)==v for k,v in original_vectors.items())
    choices=[]
    for sec in (900,1050,1200,1350,1500):
        action=load(dec/f'action_{sec:06d}.json');observed=load(dec/f'state_{sec:06d}.json')
        records=observed['vehicle_records']['records'];spill={}
        for key,entries in detectors['ramp_spillback_links'].items():
            if key not in state.ramp_queue:continue
            row=[]
            for e in entries:
                support=[r for r in records if str(r['link_no'])==str(e['link'])]
                cutoff=e.get('conn_pos_m',-1.)
                eligible=[r for r in support if r['stopped'] and (not e['queue_lanes'] or r['lane_no'] in e['queue_lanes']) and (cutoff<0 or r['position_m']<=cutoff)]
                row.append({'spec':e,'physical_count':len(support),'stopped_total':sum(bool(r['stopped']) for r in support),
                            'guard_eligible_stopped_veh':len(eligible),'eligible_ids':[r['veh_no'] for r in eligible]})
            spill[key]=row
        choices.append({'sim_sec':sec,'N_UF_star_vph':action['N_UF_star'],'ramp_metering_vph':action['ramp_metering'],
                        'raw_ramp_queue_veh':{k:observed['ramp_counts'][k] for k in state.ramp_queue},'spill_observation_recomputed':spill,
                        'diagnostics':selected(action['diagnostics']),
                        'guard_metadata':{k:v for k,v in action['metadata'].items() if k.startswith('rw_spill_')},
                        'full_recorded_diagnostics':action['diagnostics']})
    reference=load(ROOT/'diagnostics/source_interval_1200_1350.json')
    first=arms['recorded_closed']['endpoints'][0]
    first_agreement={k:first['area_metrics'][k]-reference['model']['metrics'][k] for k in ('ttt_veh_h','ttd_veh','entered_veh')}
    assert all(abs(v)<1e-10 for v in first_agreement.values())
    assert first['stocks']['ramp_queues_veh']==reference['model']['final']['ramp_queues_veh']
    report={'schema':'source-meter-shutdown/v1','run':RUN,'decision_sec':1200,
        'method':'Two installed canonical450s held-control endpoints; meter plus group-budget intervention, no optimizer. Near beta0. Future physical observations are never forecast inputs.',
        'interpretation':'450s is a model counterfactual, not observed causal performance; full candidate reoptimization/box-walk and changed green/offset are excluded.',
        'source_sha256':before,'source_changes':[p for p,h in before.items() if sha(ROOT/p)!=h],
        'elapsed_sec':time.monotonic()-began,'initial':initial,'choices':choices,'paired':arms,
        'forecast_used':[vars(step) for step in forecast],
        'first150_vs_independent_held_audit_metric_residual':first_agreement,
        'first150_vs_independent_held_audit_ramp_queues_exact':True,
        'separate_inadmissible_quantization':quantization,
        'cfg':{'leader':vars(cfg.leader),'mpc':vars(cfg.mpc),'ramp_capacity_veh_h':cfg.network.ramp_capacity_veh_h,
               'ramp_queue_capacity_veh':{r:cfg.network.ramp_queue_cap(r) for r in state.ramp_queue},
               'spill_guard':tuning['actuation']['real_world_ramp_metering']['spillback_guard'],
               'far':vars(cfg.prediction) if hasattr(cfg,'prediction') else None,
               'observed_meter_context':cfg.network.control_area_meter_context},
        'reference_interval_path':'diagnostics/source_interval_1200_1350.json',
        'reused_partial_endpoint_source_sha256':prior_proof,
        'partial_reuse_reason':'Diagnostic metadata serialization correction only; every endpoint runtime/input hash reverified. No endpoint recomputed.' if reuse else None,
        'reference_interval_sha256':sha(ROOT/'diagnostics/source_interval_1200_1350.json')}
    if report['source_changes']:raise ValueError('Source inputs changed')
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(OUTPUT),'elapsed_sec':report['elapsed_sec'],'source_changes':[]}))

if __name__=='__main__':main()
