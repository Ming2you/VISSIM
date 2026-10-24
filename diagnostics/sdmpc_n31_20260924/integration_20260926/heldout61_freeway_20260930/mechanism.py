"""Read-only accounting of the completed seed61 forecasts and cached observations.

No raw FZP scan, model rollout, coefficient fitting, or simulator invocation.
"""
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
T0=2670.1
END=3120.1
TIMES=[round(T0+i,6) for i in range(0,451,30)]

def read(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def integral(values):return sum((values[a]+values[b])*(b-a)/7200 for a,b in zip(TIMES,TIMES[1:]))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    summary=load(HERE/'prediction_summary.json')
    native=load(HERE/'native_summary.json')
    output=[];pins={};max_residual=0
    for row in summary['rows']:
        family,arm=row['family'],row['arm']
        paths={key:HERE/'observations'/arm/(key+'_30s.csv') for key in ('cells','flows','ports')}
        cells=read(paths['cells']);flows=read(paths['flows']);ports=read(paths['ports'])
        cells=[r for r in cells if r['road']=='FW_E' and T0<=float(r['time_s'])<=END]
        flows=[r for r in flows if r['road']=='FW_E' and T0<float(r['window_end_s'])<=END]
        ports=[r for r in ports if r['road']=='FW_E' and T0<=float(r['window_end_s'])<=END]
        pred_path=HERE/family/(arm+'_prediction.json.gz')
        with gzip.open(pred_path,'rt',encoding='utf-8') as f:pred=json.load(f)
        pins.update({str(p):sha(p) for p in (*paths.values(),pred_path)})
        start=sum(float(r['n_veh']) for r in cells if float(r['time_s'])==T0)
        ledger={};finals={}
        for basis,rows,terminal in (('actual',flows,'terminal_exits_inferred'),('predicted',pred['flows'],'terminal_exits')):
            terms={}
            for key,field,sign in (('source','source_admissions',1),('merge','ramp_merges',1),('off','off_departures',-1),('terminal',terminal,-1)):
                terms[key]=sign*sum(float(r[field])*(END-(float(r['window_start_s'])+float(r['window_end_s']))/2)/3600 for r in rows)
            reconstruction=start*(END-T0)/3600+sum(terms.values())
            error=abs(reconstruction-row[basis+'_main']);assert error<1e-8,(family,arm,basis,error)
            max_residual=max(max_residual,error);ledger[basis]=terms
            cs=cells if basis=='actual' else pred['cells']
            finals[basis]=sum(float(r['n_veh']) for r in cs if float(r['time_s'])==END)
        component={};ramps={}
        for basis in ('actual','predicted'):
            stocks={'on':{},'off':{}}
            for t in TIMES:
                native_rows=[r for r in ports if float(r['window_end_s'])==t]
                actual_on=sum(float(r['end_n_veh']) for r in native_rows if r['kind']=='ramp')
                actual_off=sum(float(r['end_n_veh']) for r in native_rows if r['kind']=='offramp')
                if basis=='actual' or t==T0:
                    stocks['on'][t]=actual_on;stocks['off'][t]=actual_off
                else:
                    stocks['on'][t]=sum(r['end']['connector_veh'] for r in pred['ramps'] if float(r['end_sec'])==t)
                    stocks['off'][t]=sum(r['n_veh'] for r in pred['ports'] if float(r['time_s'])==t)
            component[basis]={k:integral(v) for k,v in stocks.items()}
            error=abs(sum(component[basis].values())-row[basis+'_ports']);assert error<1e-8,(basis,arm,'ports',error)
        for rid in row['actual_merges']:
            connector=rid.split('C')[-1]
            ar=[r for r in ports if r['connector']==connector and float(r['window_end_s'])>T0]
            pr=[r for r in pred['ramps'] if r['ramp']==rid]
            ramps[rid]={'actual_arrivals':sum(float(r['arrivals_veh']) for r in ar),
                        'predicted_requested':sum(r['requested_arrivals_veh'] for r in pr),
                        'predicted_admitted':sum(r['admitted_arrivals_veh'] for r in pr),
                        'actual_merges':row['actual_merges'][rid],'predicted_merges':row['predicted_merges'][rid]}
        spatial=[]
        for c in range(17,26):
            actual=[r for r in cells if int(r['cell'])==c and float(r['time_s'])>T0]
            predicted=[r for r in pred['cells'] if int(r['cell'])==c]
            assert len(actual)==len(predicted)==15
            spatial.append(dict(cell=c,actual_v=sum(float(r['v_kmh']) for r in actual)/15,
                predicted_v=sum(float(r['v_kmh']) for r in predicted)/15,
                actual_mean_n=sum(float(r['n_veh']) for r in actual)/15,
                predicted_mean_n=sum(float(r['n_veh']) for r in predicted)/15))
        errors=[e for r in native['rows'] if r['arm']==arm for e in r['native_error_events']
                if e['kind']=='lane_change_removal' and T0<float(e.get('time_sec',-1))<=END]
        output.append(dict(family=family,arm=arm,ledger=ledger,final_n=finals,connector_cost=component,ramps=ramps,spatial=spatial,
            native_component_unresolved_absences=sum(float(r['unresolved_absences_veh']) for r in ports if float(r['window_end_s'])>T0),
            network_removal_events=len(errors),removal_links=sorted({e['link'] for e in errors})))
    for family in ('baseline','candidate'):
        rows=[r for r in output if r['family']==family];base=rows[0]
        for r in rows:
            r['delta_ledger']={b:{k:r['ledger'][b][k]-base['ledger'][b][k] for k in r['ledger'][b]} for b in ('actual','predicted')}
            r['delta_connector_cost']={b:{k:r['connector_cost'][b][k]-base['connector_cost'][b][k] for k in ('on','off')} for b in ('actual','predicted')}
            r['delta_final_n']={b:r['final_n'][b]-base['final_n'][b] for b in ('actual','predicted')}
    result=dict(rows=output,input_pins=pins,max_ttt_reconstruction_error=max_residual,refit=False,
        notes=['30s snapshot trapezoid cost decomposed with interval-midpoint flow weights; accounting, not causal attribution.',
               'Spatial speed/stock are arithmetic means of15 sampled30s end states, not native acceleration or vehicle-weighted speed.',
               'Connector costs exclude upstream urban approaches. All-network removal events do not count as TTD.'])
    target=HERE/'mechanism_summary.json';assert not target.exists()
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'completed':True,'cached_rows':len(output),'max_ttt_error':max_residual,'new_rollouts':0,'refit':False}))

if __name__=='__main__':main()
