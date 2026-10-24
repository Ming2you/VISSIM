"""Summarize the closed 8100s native audit; reuse metrics, never rescan FZP."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=HERE/'current_native_analysis_to8100'
read=lambda p:json.loads(p.read_bytes())
def main():
    out=HERE/'native8100_diagnosis.json'
    assert not out.exists(), 'Preserve completed diagnosis'
    summary=read(BASE/'summary.json')
    assert summary['end_sec']==8100 and summary['counterfactual_valid']
    geo=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    chains={str(x['link']):road for road,chain in geo['chains'].items() for x in chain}
    groups={};tables={};removals={};metrics={};pins={}
    for arm in ('nc','sdmpc'):
        folder=BASE/arm
        metrics[arm]=read(folder/'area_metrics.json')
        physical=metrics[arm]['physical_link_residence']
        groups[arm]=dict.fromkeys(('FW_E','FW_W','urban_ramps','outside'),0.)
        for link,row in physical.items():
            group=chains.get(link,'urban_ramps' if row['inside'] else 'outside')
            assert group=='outside' or row['inside']
            groups[arm][group]+=row['ttt_veh_h']
        assert abs(sum(v for k,v in groups[arm].items() if k!='outside')-metrics[arm]['ttt_veh_h'])<1e-7
        events=read(folder/'native_errors.json')['unique_events']
        deleted=[e for e in events if e['kind']=='lane_change_removal']
        assert all(0<=e['time_sec']<=8100 for e in deleted)
        removals[arm]=dict(count=len(deleted),by_link=dict(Counter(e['link'] for e in deleted)),
            by_route=dict(Counter(f"{e['link']}|{e['route_decision']}:{e['route_index']}" for e in deleted)),
            all_deleted_max_remaining_residence_veh_h=sum((8100-e['time_sec'])/3600 for e in deleted),
            inside_deleted_count=sum(physical[e['link']]['inside'] for e in deleted))
        with (folder/'area_timeseries.csv').open(encoding='utf-8-sig',newline='') as f:
            tables[arm]=[{k:float(v) for k,v in r.items() if k!='source'} for r in csv.DictReader(f)]
        for p in (folder/'area_metrics.json',folder/'native_errors.json',folder/'execution.json',folder/'area_timeseries.csv'):
            pins[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    link_deltas=[]
    links=set(metrics['nc']['physical_link_residence'])|set(metrics['sdmpc']['physical_link_residence'])
    for link in links:
        rows=[metrics[a]['physical_link_residence'].get(link,dict(ttt_veh_h=0.,slow_veh_h=0.)) for a in ('nc','sdmpc')]
        inside=next(r['inside'] for r in rows if 'inside' in r)
        link_deltas.append(dict(link=link,inside=inside,group=chains.get(link,'urban_ramps' if inside else 'outside'),
            nc=rows[0]['ttt_veh_h'],sdmpc=rows[1]['ttt_veh_h'],delta=rows[1]['ttt_veh_h']-rows[0]['ttt_veh_h'],
            slow_delta=rows[1]['slow_veh_h']-rows[0]['slow_veh_h'],
            removed_nc=removals['nc']['by_link'].get(link,0),removed_sdmpc=removals['sdmpc']['by_link'].get(link,0)))
    domain=[]
    for group in groups['nc']:
        a,b=groups['nc'][group],groups['sdmpc'][group]
        domain.append(dict(group=group,nc=a,sdmpc=b,delta=b-a,reduction_percent=100*(a-b)/a))
    a,b=[summary['arms'][arm]['TTT_0_8100_veh_h'] for arm in ('nc','sdmpc')]
    times=[r['sim_sec'] for r in tables['nc']]
    assert times==[r['sim_sec'] for r in tables['sdmpc']]
    windows=[]
    previous=[0.,0.]
    for end in (900,1800,2700,3600,4500,5400,6300,7200,8100):
        # Interpolate the already-integrated 5s series, not a new trajectory metric.
        import numpy as np
        totals=[float(np.interp(end,times,[r['ttt_veh_h_cumulative'] for r in tables[arm]])) for arm in ('nc','sdmpc')]
        inc=[totals[i]-previous[i] for i in range(2)]
        windows.append(dict(start=end-900,end=end,nc=inc[0],sdmpc=inc[1],delta=inc[1]-inc[0]))
        previous=totals
    result=dict(analysis_end_sec=8100,omega_reduction_percent=100*(a-b)/a,target_met=False,
        domain=domain,time_windows=windows,removals=removals,
        largest_inside_losses=sorted([r for r in link_deltas if r['inside']],key=lambda r:r['delta'],reverse=True)[:15],
        largest_inside_gains=sorted([r for r in link_deltas if r['inside']],key=lambda r:r['delta'])[:15],
        source_pins=pins,limitations=[
            'Deletion future residence ceiling is a sensitivity bound, not a counterfactual reconstruction or correction.',
            'Outside observed residence excludes vehicles not yet inserted; input waiting at8100 is unavailable.',
            'Unresolved disappearances remain unqualified normal exits; use the native summary counts.',
            'Time-window totals interpolate the cumulative5s series; domain totals reuse the full sampled integration.'])
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('omega_reduction_percent','domain','removals','largest_inside_losses')},ensure_ascii=False))
if __name__=='__main__':main()
