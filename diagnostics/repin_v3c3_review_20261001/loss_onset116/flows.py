"""Conserved native port decomposition; finalized ERR is post-hoc evidence only."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import audit as a
sys.path.insert(0,str(a.ROOT))
from diagnostics.capture_native_runtime_errors import parse_bytes

def main():
    assert not (a.HERE/'flow_summary.json').exists()
    fluxes=a.proof.function(a.ROOT/'evaluation/controllers/vsl_exposure_history.py','cell_fluxes')
    rows=[];per_port=[];all_flux=[];pins={}
    def read(p):
        data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest()
        return json.loads(data)
    for arm,run in a.runs.items():
        error=run/'network'/f'sdmpc31_{arm}9000_s29_001.err'
        data=error.read_bytes();pins[str(error)]=hashlib.sha256(data).hexdigest()
        parsed=parse_bytes(data);assert not parsed['unparsed_removal_lines']
        losses=[x for x in parsed['events'] if x['kind']=='lane_change_removal']
        old=read(a.dec[arm]/'lane_observations/frame_000900.json')
        for t in range(1050,7051,150):
            new=read(a.dec[arm]/f'lane_observations/frame_{t:06d}.json')
            d=read(a.dec[arm]/f'obs150/derived_{t:06d}.json')
            removed=[r for r in losses if t-150<r['time_sec']<=t]
            counts=lambda f,link:sum(z[1]==int(link) for z in f['vehicles'])
            for road in ('FW_E','FW_W'):
                _,bins,_=a.bin_frame(a.geometry,old['vehicles'],road,drop_before_start=True)
                n0=list(map(len,bins))
                _,bins,_=a.bin_frame(a.geometry,new['vehicles'],road,drop_before_start=True)
                n1=list(map(len,bins))
                merges=[0]*31;exits=[0]*31;deleted=[0]*31
                for b in a.geometry['boundaries']:
                    if b['road']!=road or b['kind'] not in ('ramp','offramp'):continue
                    link=b['connector']
                    if b['kind']=='offramp':
                        amount=d['boundaries']['off_entry:'+str(link)]['cross'];exits[b['from_cell']]+=amount
                    else:
                        amount=(d['boundaries']['ramp_arrival:RM_C'+str(link)]['cross']
                            +counts(old,link)-counts(new,link)-sum(r['link']==int(link) for r in removed))
                        merges[b['to_cell']]+=amount
                    assert amount>=0
                    per_port.append(dict(arm=arm,start_s=t-150,end_s=t,road=road,kind=b['kind'],connector=link,vehicles=amount))
                for r in removed:
                    _,bins,_=a.bin_frame(a.geometry,[[r['vehicle_id'],r['link'],1,r['position_m'],0,1]],road,drop_before_start=True)
                    for i,z in enumerate(bins):deleted[i]+=len(z)
                entry=d['boundaries']['source:'+road]['cross'];terminal=d['boundaries']['chain_end:'+road]['cross']
                through=fluxes(n0,n1,entry,merges,exits,deleted,terminal)
                row=dict(arm=arm,start_s=t-150,end_s=t,road=road,n0=sum(n0),n1=sum(n1),
                    entry=entry,merges=sum(merges),off=sum(exits),deleted=sum(deleted),terminal=terminal)
                row['residual']=row['n0']+entry+row['merges']-row['off']-row['deleted']-terminal-row['n1']
                assert row['residual']==0
                rows.append(row)
                for i,value in enumerate(through):all_flux.append(dict(arm=arm,start_s=t-150,end_s=t,road=road,cell=i,through=value))
            old=new
    periods=[]
    for start,end in ((900,1500),(1500,2250),(2250,3150),(3150,4800),(4800,7050),(900,7050)):
        for road in ('FW_E','FW_W'):
            period=dict(start_s=start,end_s=end,road=road,arms={})
            for arm in a.runs:
                subset=[r for r in rows if r['arm']==arm and r['road']==road and start<=r['start_s'] and r['end_s']<=end]
                period['arms'][arm]={k:sum(r[k] for r in subset) for k in ('entry','merges','off','deleted','terminal')}
                period['arms'][arm].update(n0=subset[0]['n0'],n1=subset[-1]['n1'])
            period['delta']={k:period['arms']['sdmpc'][k]-period['arms']['nc'][k] for k in period['arms']['nc']}
            period['ramp_delta']={str(b['connector']):sum((1 if r['arm']=='sdmpc' else -1)*r['vehicles'] for r in per_port
                if r['connector']==b['connector'] and start<=r['start_s'] and r['end_s']<=end)
                for b in a.geometry['boundaries'] if b['road']==road and b['kind']=='ramp'}
            periods.append(period)
    a.write('native_port_intervals.csv',per_port);a.write('native_road_balances.csv',rows);a.write('native_internal_crossings.csv',all_flux)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
    a.save('flow_pins.json',pins)
    result=dict(status='PASS',validated_road_intervals=len(rows),validated_cell_intervals=len(all_flux),periods=periods,
        scope='Native actual flows, closed-loop paths; no isolated control counterfactual or future data in model',
        terminal_notes='FinalERR posthoc losses subtracted, never counted as normal exits',sources_unchanged=True)
    a.save('flow_summary.json',result)
    print(json.dumps([p for p in periods if p['road']=='FW_E'],indent=2))

if __name__=='__main__':main()
