"""Reproduce the rejected lane hypothesis without installing a controller path."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.response_late_s23_v1.lane_boundary_candidate import LaneResolvedRampBoundary
import canonical_harness


def main():
    out=HERE/'lane_candidate_v1'
    params=e.load(HERE.parent/'controller_response_4500_v1/model_v4/selected_parameters.json')['parameters']
    checked=[]
    for name,folder in [('early13','controller_response_4500_v1/none'),('late23','controller_response_s23_v1/none')]:
        data=e.ObservationData(HERE.parent/folder)
        model=e.load_base_model(data.geometry,HERE.parent/'controller_response_4500_v1/model_v4/config.json')
        for arm in ['none','rm_ramp','vsl','both']:
            window=e.load(out/f'{name}_{arm}_window.json')
            original=canonical_harness.PhysicalRampBoundary
            def factory(**kwargs):
                if 'lane_arrival_shares' in kwargs:return LaneResolvedRampBoundary(**kwargs)
                return original(**kwargs)
            canonical_harness.PhysicalRampBoundary=factory
            try:pred=json.loads(json.dumps(e.simulate(model,window,params)))
            finally:canonical_harness.PhysicalRampBoundary=original
            old=e.load(out/f'{name}_{arm}_prediction.json')
            for key in ['cells','flows','ports','ramps','local_ramp_audit']:
                assert pred[key]==old[key],(name,arm,key)
            checked.append(name+'_'+arm)
    path=out/'standalone_replay_check.json'
    path.write_text(json.dumps({'passed':True,'checked':checked,'scope':'All physical outputs; experimental config provenance intentionally differs'},indent=2),encoding='utf-8')
    print('Exact candidate physical-output replay PASS:',len(checked))


if __name__=='__main__':main()
