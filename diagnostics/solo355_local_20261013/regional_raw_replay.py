
"""Replay canonical preparation from a cached validated merged observation.

Injection begins AFTER obs150 collection/transport validation. Closed own head
service history and VSL cohorts are reused from the capture. Current physical
projection, reactive guards, local cfg and the canonical adapter cut run afresh.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
os.environ.update(RW_OFFSET_WRITER='experiment',RW_MAINLINE_SG_ONLY='1',RW_RAMP_AMBER_SEC='0')
import argparse,copy,json,pickle
from pathlib import Path
from unittest.mock import patch
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import runtime_setup,lane_plant_runtime,vsl_exposure_history,sdmpc
from evaluation.controllers.sdmpc_regional_context import prepare
from diagnostics.solo355_local_20261013.regional_context_probe import inputs,token,canonical,evaluate

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',required=True,choices=('freeway_only','urban_only'))
    p.add_argument('--variant',choices=('base','opposite','own','opposite_stock'),default='base')
    p.add_argument('--capture',default='D:/VISSIM_analysis/20261013_solo355_local/projected.pkl')
    p.add_argument('--output',required=True)
    p.add_argument('--evaluate',action='store_true')
    a=p.parse_args()
    x=pickle.loads(Path(a.capture).read_bytes());old,state,forecast,history,mapping=x['args']
    raw=copy.deepcopy(x['obs']['merged']);observation=copy.deepcopy(x['obs']['observation'])
    fw_links={int(k) for k in x['obs']['geometry']['addresses']}
    fw_links.update(int(row['connector']) for row in old.cfg.network.physical_ramp_branches['ramps'].values())
    altered=[]
    if a.variant in ('opposite','own'):
        own_fw=a.mode=='freeway_only'
        selected_fw=own_fw if a.variant=='own' else not own_fw
        for row in raw['vehicle_records']['records']:
            if (int(row['link_no']) in fw_links)==selected_fw:
                row['speed_kph']=max(1.,float(row['speed_kph'])*0.63)
                altered.append(row['veh_no'])
        for frame in observation['frames']:
            for i,row in enumerate(frame['vehicles']):
                if (int(row[1]) in fw_links)==selected_fw:
                    changed=list(row);changed[4]=max(1.,float(row[4])*0.63);frame['vehicles'][i]=changed
    if a.variant == 'opposite_stock':
        selected_fw = a.mode == 'urban_only'
        eligible = [v for v in raw['vehicle_records']['records']
                    if (int(v['link_no']) in fw_links) == selected_fw]
        victim = next((v for v in eligible if v['stopped']), eligible[0])
        altered.append(victim['veh_no'])
        records = raw['vehicle_records']
        records['records'] = [v for v in records['records'] if v['veh_no'] != victim['veh_no']]
        for k in ('collection_count_before','collection_count_after','record_count'):
            records[k] -= 1
        link = str(victim['link_no'])
        for table, key, delta in (
                (records,'full_network_link_counts',1),
                (records,'full_network_link_stopped_counts',int(victim['stopped'])),
                (raw['local_observation'],'link_counts',1),
                (raw['local_observation'],'link_stopped_counts',int(victim['stopped']))):
            if link in table.get(key,{}): table[key][link] -= delta
        raw['local_observation']['observed_vehicle_count'] -= 1
        bins=raw['local_observation']['queue_bins']
        key=link+'|'+str(victim['lane_no'])+'|'+str(int(victim['position_m']//raw['local_observation']['queue_bin_m']))
        if key in bins:
            bins[key][0]-=1;bins[key][1]-=int(victim['stopped'])
        for frame in observation['frames']:
            frame['vehicles']=[v for v in frame['vehicles'] if v[0]!=victim['veh_no']]
    config=json.loads(Path('diagnostics/solo355_local_20261013/'+a.mode+'_config.json').read_text(encoding='utf-8'))
    adapter.install_config_switches(config)
    calibration=json.loads(Path('evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json').read_text(encoding='utf-8-sig'))
    calibration=adapter.deep_update(calibration,config.get('calibration_override',{}))
    detector=json.loads(Path(config['detector_mapping_json']).read_text(encoding='utf-8-sig'))
    detector,_=adapter.filter_midblock_links_from_detector_mapping(detector,config)
    from src.models.state import TrafficState
    cfg=adapter.build_config(Path('vendor/NumSim-mine'),150.,8100.,'integrated',calibration,config,
        local_observation=True,flagship=True)
    def observed(context,unused):return copy.deepcopy(raw),copy.deepcopy(observation)
    def vsl_history(context,observed_raw,current,current_cfg):
        current._component_vsl_exposure=copy.deepcopy(state._component_vsl_exposure)
        return {'qualification_cached_own_vsl_history':True}
    original_capacity=adapter.install_measured_movement_capacity
    def service_history(current_cfg,*args,**kw):
        result=original_capacity(current_cfg,*args,**kw)
        # These are established own-head passage/exposure histories, fixed in
        # both variants; no capture-derived traffic STATE is reused below.
        for field in ('head_free_service','head_service_resources','sc1001_shared_observation'):
            setattr(current_cfg.network,field,copy.deepcopy(getattr(old.cfg.network,field)))
        current_cfg.network.movement_capacity_by_movement_veh_h.update(copy.deepcopy(old.cfg.network.movement_capacity_by_movement_veh_h))
        return dict(result,qualification_cached_own_head_history=True)
    with patch.object(lane_plant_runtime,'observe_state',observed),patch.object(
            vsl_exposure_history,'initialize',vsl_history),patch.object(
            adapter,'install_measured_movement_capacity',service_history):
        current,detector,metadata=runtime_setup.configure_runtime(adapter,cfg,config,mapping,raw,
            x['kwargs']['previous_path'],detector,calibration,TrafficState,controller_variant='wu-link')
    cfg.mpc.phase_price_exchange_steps_sec=copy.deepcopy(old.cfg.mpc.phase_price_exchange_steps_sec)
    sdmpc.configure(config,cfg);sdmpc.install_cost_ownership(cfg,detector)
    private=copy.copy(old);private.cfg=cfg;private.nash_solver=copy.copy(old.nash_solver);private.nash_solver.cfg=cfg
    private.leader=type(old.leader)(cfg)
    current_forecast=adapter.demand_from_state(raw,cfg,type(forecast[0]),len(forecast),calibration,detector)
    bootstrap=dict(x['kwargs']['worker_bootstrap'],detector_mapping=detector,runtime_sources={})
    local=prepare(private,current,current_forecast,history,mapping,
        derived=current._regional_boundary_observation,bootstrap=bootstrap)
    prepared=inputs(local,x)
    result=dict(mode=a.mode,variant=a.variant,altered_records=len(altered),native_runs=0,full_selections=0,
        injection_boundary='validated cached merged raw/derived observation before canonical configure_runtime',
        fixed_own_history=('head passage/exposure service supports','VSL cohort history'),
        upstream_transport_revalidated=False,complete_context_sha256=token(prepared.view))
    out=Path(a.output)
    out.with_suffix('.pkl').write_bytes(pickle.dumps(dict(local=local,view=prepared.view,x=x),protocol=5))
    if a.evaluate:result['evaluation']=evaluate(prepared,x)
    out.write_text(json.dumps(canonical(result),indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='evaluation'}),flush=True)

if __name__=='__main__':main()
