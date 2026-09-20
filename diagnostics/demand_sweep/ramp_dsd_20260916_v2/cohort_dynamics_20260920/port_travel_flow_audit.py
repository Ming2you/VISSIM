"""Audit the failed port-travel future-speed diagnostic against native fluxes."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e

HERE=Path(__file__).resolve().parent;H=HERE.parent


def main():
    start=2400;result={}
    for arm in ['none','vsl']:
        folder=H/'controller_response_s23_v1/none' if arm=='none' else H/'response_late_s23_v1/observations/vsl'
        data=e.ObservationData(folder)
        pred=e.load(HERE/f'port_travel_speed_oracle_v1/prediction_s23_all_{arm}.json')
        observed=e.rows(folder/'flows_30s.csv')
        rows=[]
        for cell in range(21):
            actual=[r for r in observed if r['road']=='FW_E' and int(r['cell'])==cell and start<float(r['window_end_s'])<=start+450]
            model=[r for r in pred['flows'] if r['road']=='FW_E' and r['cell']==cell]
            x={'cell':cell}
            for field in ['source_admissions','downstream_crossings','off_departures','ramp_merges']:
                x[field]={'actual':sum(float(r[field]) for r in actual),'model':sum(r[field] for r in model)}
            for t in [2430,2550,2850]:
                obs=next(r['n_veh'] for r in data.cells[t] if r['road']=='FW_E' and r['cell']==cell)
                p=next(r['n_veh'] for r in pred['cells'] if r['time_s']==t and r['road']=='FW_E' and r['cell']==cell)
                x['stock_'+str(t)]={'actual':obs,'model':p}
            rows.append(x)
        result[arm]=rows
    delta=[]
    for nc,ctl in zip(result['none'],result['vsl']):
        row={'cell':nc['cell']}
        for field in nc.keys()-{'cell'}:row[field]={kind:ctl[field][kind]-nc[field][kind] for kind in ['actual','model']}
        delta.append(row)
    out=HERE/'port_travel_flow_audit_v1.json'
    e.save(out,{'status':'Future-speed diagnostic, not causal prediction','absolute':result,'delta':delta})
    for row in delta:
        if row['cell'] in [7,8,9,12,13,14,20]:print(row,flush=True)


if __name__=='__main__':main()
