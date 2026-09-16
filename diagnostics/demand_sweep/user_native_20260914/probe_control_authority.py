"""Narrow control-path checks; no native counterfactual or full Omega cost claim."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
CAL=HERE/'metanet_calibration_v1'
sys.path.insert(0,str(CAL))
from boundary_factory import ObservationData,build_window
from canonical_harness import load_base_model,ControlAction,TrafficState,DemandStep,DEFAULT_CONFIG
from evaluate import check_freeze
from src.models import metanet


def main():
    out=HERE/'control_authority_v1'
    if out.exists():raise ValueError('New output required')
    out.mkdir()
    check_freeze(CAL/'FREEZE.json',CAL/'fit_v2/parameters.json')
    data=ObservationData(CAL/'seed17_observations')
    model=load_base_model(data.geometry)
    fitted=json.loads((CAL/'fit_v2/parameters.json').read_text(encoding='utf-8'))['parameters']
    settings=json.loads(DEFAULT_CONFIG.read_text(encoding='utf-8'))['actuation']['real_world_ramp_metering']
    base_method=ControlAction.uncontrolled
    vsl_rows=[];meter_rows=[]
    for t in (900,1350,1800,2700,3600,7200):
        w=build_window(data,t,'history_forecast')
        for version,overrides in [('baseline',None),('calibrated',fitted)]:
            for road in ('FW_E','FW_W'):
                outcomes={}
                for command in (120.,100.,80.):
                    def action(cfg,road=road,command=command):
                        a=base_method(cfg)
                        heads=cfg.network.freeway_vsl_zone_heads[road]
                        free=cfg.network.freeway_vsl_zone_free
                        for j,h in enumerate(heads):
                            a.vsl[f'{road}__seg{h}']=command if j in free else 120.
                        return a
                    with patch.object(ControlAction,'uncontrolled',staticmethod(action)):
                        pred=model.rollout(w['initial_cells'],w['boundary_steps'],overrides=overrides,
                                           initial_origin_queue=w['initial_origin_queue'],roads=(road,))
                    d=pred['diagnostics']['roads'][0]
                    row={'cutoff_s':t,'version':version,'road':road,'free_zone_vsl':command,
                         'freeway_ttt_veh_h':d['model_residence_10s_veh_h'],
                         'end_freeway_n':d['final_n_veh'],'end_origin_backlog':d['final_origin_queue_veh'],
                         'source_accepted_veh':d['accepted_source_veh'],
                         'off_exit_veh':sum(f['off_departures'] for f in pred['flows']),
                         'terminal_exit_veh':sum(f['terminal_exits'] for f in pred['flows']),
                         'merge_veh':sum(f['ramp_merges'] for f in pred['flows']),
                         'jam_exceedance_count':d['jam_density_exceedance_count']}
                    outcomes[command]=row
                    vsl_rows.append(row)
                for row in outcomes.values():
                    row['delta_freeway_ttt_veh_h']=row['freeway_ttt_veh_h']-outcomes[120.]['freeway_ttt_veh_h']
                    row['delta_merge_veh']=row['merge_veh']-outcomes[120.]['merge_veh']
                    row['delta_exit_veh']=row['off_exit_veh']+row['terminal_exit_veh']-outcomes[120.]['off_exit_veh']-outcomes[120.]['terminal_exit_veh']
                params={} if overrides is None else overrides['by_direction'][road]
                cfg=model._config(road,params)
                initial={r['cell']:r for r in w['initial_cells'] if r['road']==road}
                state=TrafficState.initial(cfg)
                state.time_sec=t
                state.freeway_effective_lanes[road]=list(cfg.network.freeway_segment_lanes[road])
                state.freeway_density[road]=[initial[c]['n_veh']/(cfg.network.freeway_segment_length_km*cfg.network.freeway_segment_lanes[road][c]) for c in range(21)]
                for r in cfg.network.ramps:
                    state.ramp_queue[r]=float(data.boundaries[t,r]['snapshot_n_veh'])
                    cfg.network.ramp_capacity_veh_h[r]=model.ramps[r]['lanes']*float(settings['per_lane_veh_per_cycle']['10'])*3600/settings['cycle_sec']
                results={}
                for g in (10,8):
                    control=base_method(cfg)
                    control.ramp_metering={r:model.ramps[r]['lanes']*float(settings['per_lane_veh_per_cycle'][str(g)])*3600/settings['cycle_sec'] for r in cfg.network.ramps}
                    rates,diag=metanet.compute_ramp_release_flows(state,control,DemandStep({}, {}, {}),cfg,include_current_arrivals=False)
                    results[g]=(control,rates)
                for r in cfg.network.ramps:
                    meter_rows.append({'cutoff_s':t,'version':version,'road':road,'ramp':r,'initial_connector_veh':state.ramp_queue[r],
                        'recent_native_merge_vph':w['boundary_steps'][0]['ramp_release_vph'][r],
                        'g10_service_vph':results[10][0].ramp_metering[r],'g8_service_vph':results[8][0].ramp_metering[r],
                        'g10_query_vph':results[10][1][r],'g8_query_vph':results[8][1][r],
                        'difference_next10s_veh':(results[8][1][r]-results[10][1][r])*cfg.simulation.T_f_h})
    check_freeze(CAL/'FREEZE.json',CAL/'fit_v2/parameters.json')
    result={'scope':'Post-holdout diagnostic only. No refit, no native run, no full Omega/controller decision.',
        'vsl_scope':'450s canonical freeway response with all controllable zones at120/100/80, last recovery zone fixed120; all measured-history ramp/off boundaries held equal. FW residence excludes urban/ramp waits and cannot certify objective improvement.',
        'meter_scope':'Canonical pre-step release query with observed connector stock, actual lane count and existing actuator service table; next10s availability is the model assumption, not measured stop-line readiness. No future arrivals or450s extrapolation. Not a realized native discharge test.',
        'vsl':vsl_rows,'meter_next_step':meter_rows,
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'frozen_definitions_unchanged':True}
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'out':str(out),'vsl_rollouts':len(vsl_rows),'meter_pairs':len(meter_rows)},ensure_ascii=False))
    for row in vsl_rows:
        if row['version']=='calibrated' and row['road']=='FW_E' and row['free_zone_vsl']<120:
            print(json.dumps(row))
    print('calibrated_meter_binding',sum(r['difference_next10s_veh']<-1e-8 for r in meter_rows if r['version']=='calibrated'))

if __name__=='__main__':main()
