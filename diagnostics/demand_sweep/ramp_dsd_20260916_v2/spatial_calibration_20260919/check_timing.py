"""Separate a service integration correction from FD calibration."""
import copy
import statistics
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919.calibrate import *

def main():
    out=HERE/'timing_v2';out.mkdir(exist_ok=False)
    results={}
    for base_name,source in [('base',BASE),('spatial',HERE/'fit_v1/model')]:
        dest=out/('model_'+base_name);dest.mkdir()
        for filename in ['config.json','selected_parameters.json','port_profile.json']:
            document=e.load(source/filename)
            if filename=='config.json':document['freeway']['physical_offramp_interval_service']=True
            write(dest/filename,document)
        rows=[]
        for seed,folder in [(13,H/'controller_response_4500_v1/none'),(23,H/'controller_response_s23_v1/none'),
                            (33,H/'state_response_20260919/native_s33_v1/observations/none')]:
            data,model,profile,windows=setup(folder,dest/'config.json')
            params=e.load(dest/'selected_parameters.json')['parameters']
            old=e.load_base_model(data.geometry,source/'config.json')
            err_before=[];err_after=[];drain_before=[];drain_after=[];ss=[];numeric_matches=0
            for t,w in windows.items():
                prior=e.simulate(old,w,params);new=e.simulate(model,w,params)
                if prior['cells']==new['cells'] and prior['flows']==new['flows']:numeric_matches+=1
                for pred,errors,drains in [(prior,err_before,drain_before),(new,err_after,drain_after)]:
                    for r in pred['ports']:
                        c=r['connector'];ts=int(r['time_s'])
                        if ts % 30:continue
                        errors.append(r['n_veh']-len(data.port_cohorts[str(ts)][c]))
                    # Same 450s physical port inventory area, all8 ports.
                    parts=direction_parts(data,model,t,pred)
                    actual=direction_parts(data,model,t)
                    drains.append(sum(parts[road]['off']-actual[road]['off'] for road in model.roads))
                ss.append(e.score_rollout(data,t,new,'FW_E'))
            rows.append({'seed':seed,'no_control':summary(ss),
                'off_stock_mae_before':statistics.mean(map(abs,err_before)),
                'off_stock_mae_after':statistics.mean(map(abs,err_after)),
                'off_ttt_mae_before':statistics.mean(map(abs,drain_before)),
                'off_ttt_mae_after':statistics.mean(map(abs,drain_after)),
                'identical_freeway_state_and_flow_windows':numeric_matches})
        results[base_name]=rows
        print(base_name,rows,flush=True)
    write(out/'results.json',results)

if __name__=='__main__':main()
