"""Replay the configured physical observer through2400, no model forecast."""
from pathlib import Path
from copy import deepcopy
import hashlib,importlib.util,json,pickle,sys
HERE=Path(__file__).resolve().parent;A=HERE.parent
def main():
    config=json.loads((A/'flow279/config_10686_free.json').read_bytes())
    config['urban']['capacity']['head_resource_contract']=(HERE/'head_resources.json').relative_to(HERE.parents[4]).as_posix()
    cfg_path=HERE/'config.json';assert not cfg_path.exists()
    cfg_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    source=json.loads((A/'transfer331/build2400_v2/summary.json').read_bytes())['source']
    out=HERE/'canonical2400';assert not out.exists()
    sys.argv=['verify.py','--at','2400','--out',str(out),'--no-prediction','--cold-prices',
        '--tuning',str(cfg_path),'--decisions',source]
    spec=importlib.util.spec_from_file_location('head343_bootstrap',A.parents[1]/'urban260/verify.py')
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,physical_ramp_branches as ramps,sdmpc_pfo
    from ..sc12_phase305.candidate import hook
    from ..corridor339.runtime import source_hooks
    from ..sc12_initial306.state_check import equal
    original=adapter.main;captured={}
    def wrapped():
        bound,forecast=ramps.configure_operating_bounds,adapter.demand_from_state
        def capture(s,c,r):captured.update(state=s,cfg=c);return bound(s,c,r)
        def demand(*a,**kw):
            value=forecast(*a,**kw);captured['forecast']=value;return value
        ramps.configure_operating_bounds=capture;adapter.demand_from_state=demand
        def audit(*args):
            bc,bs,bf=pickle.loads((A/'transfer331/build2400_v2/canonical.pickle').read_bytes())
            cfg,state,forecast=captured['cfg'],captured['state'],captured['forecast']
            changed={k:dict(old=bc.network.movement_capacity_by_movement_veh_h[k],new=value)
                     for k,value in cfg.network.movement_capacity_by_movement_veh_h.items()
                     if value!=bc.network.movement_capacity_by_movement_veh_h[k]}
            compare=deepcopy(cfg)
            for name in ('head_service_resources','movement_capacity_by_movement_veh_h'):
                setattr(compare.network,name,deepcopy(getattr(bc.network,name)))
            checks=dict(other_cfg_equal=equal(compare,bc),state_equal=equal(state,bs),forecast_equal=equal(forecast,bf))
            record=dict(status='complete_canonical_head_history_replay',checks=checks,capacity_changes=changed,
                physical_observation=cfg.network.head_service_resources['observations']['10200'],
                predictions=0,native=0,optimizer=0,goal_complete=False)
            (out/'assessment.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
            (out/'initial.pickle').write_bytes(pickle.dumps((cfg,state,forecast),protocol=5))
            print(json.dumps(record,indent=2),flush=True)
            assert all(checks.values()),checks
            raise v.Done()
        sdmpc_pfo.solve=audit
        return original()
    adapter.main=wrapped
    with source_hooks(),hook('source_path_current_physical_speed'):v.main()
if __name__=='__main__':main()
