"""Ablate arrival timing and independently qualified ramp receiving nodes."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.calibrate_ramps import *
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919 import calibrate as spatial

def main():
    out=HERE/'arrival_v1';out.mkdir(exist_ok=False)
    spatial.BASE=BASE
    selected=e.load(HERE/'local_v1/selected.json')
    variants=[('wave',[],True),('gap84',['RM_C10484'],False),
        ('gap84_wave',['RM_C10484'],True),('gapboth_wave',TARGETS,True)]
    for name,nodes,wave in variants:
        result=out/name;result.mkdir();modeldir=result/'model';modeldir.mkdir()
        cfg=e.load(BASE/'config.json')
        for mid in nodes:
            tc,tf=selected[mid]['gap']
            cfg['freeway']['physical_ramp_receiving_nodes'][mid]={'critical_gap_sec':tc,
                'followup_sec':tf,'lane_arrival_history_sec':150}
        if wave:cfg['freeway']['physical_ramp_arrival_profile']={'history_sec':150,'ramps':TARGETS}
        write(modeldir/'config.json',cfg)
        for f in ['selected_parameters.json','port_profile.json']:write(modeldir/f,e.load(BASE/f))
        spatial.evaluate(result,modeldir)
        print('VARIANT COMPLETE',name,flush=True)

if __name__=='__main__':main()
