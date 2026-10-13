"""Separate elapsed travel and stopped delay using closed, sampled trajectories."""
from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import statistics

from diagnostics.validate_native_signal_record import read_ldp_frames

HERE=Path(__file__).resolve().parent
A=HERE.parent
CACHE=Path('E:/VISSIM_analysis/20261010_sc109_arrival319')
MODEL=Path('E:/VISSIM_analysis/20261010_source_boundary318/forecast2400')
ROOTS={
 'hold':Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold'),
 'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected')}
PINS={}


def read(path, compressed=False):
    path=Path(path);b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if compressed else b)


def unique(rows):
    counts=Counter(r['vehicle'] for r in rows)
    return {r['vehicle']:r for r in rows if counts[r['vehicle']]==1}


def stop_time(track,start,end,threshold):
    """Trapezoidal sampled stopped indicator; not an exact waiting-time measurement."""
    stopped=covered=0.
    for left,right in zip(track,track[1:]):
        dt=right['sec']-left['sec']
        if abs(dt-5)>1e-7:continue
        overlap=max(0.,min(end,right['sec'])-max(start,left['sec']))
        covered+=overlap
        stopped+=overlap*.5*((left['speed']<=threshold)+(right['speed']<=threshold))
    return stopped,covered


def stats(values):
    return dict(n=len(values),mean=statistics.mean(values) if values else None,
                median=statistics.median(values) if values else None,
                minimum=min(values) if values else None,maximum=max(values) if values else None)


def main():
    assert not (HERE/'diagnosis.json').exists()
    synthetic=[{'sec':t,'speed':0} for t in (0,5,10,15,20)]
    assert stop_time(synthetic,2.5,16,5)==(13.5,13.5)
    assert stop_time([dict(x,speed=50) for x in synthetic],2.5,16,5)==(0.,13.5)
    chain=read(A/'exit_timing309/sc109_chain.json')
    done=read(CACHE/'completion.json')
    for p,h in done['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    arms={}
    for arm,root in ROOTS.items():
        path=Path(done['arms'][arm]['cache']);cache=read(path,True)
        assert PINS[str(path)]==done['arms'][arm]['sha256']
        heads=chain['head_events'][arm];down=unique(heads['SC109_W_p3'])
        up={key:unique(heads[key]) for key in ('SC108_W_p3','SC108_side_p3')}
        journeys=[]
        for vehicle,exit in down.items():
            sources=[(key,rows[vehicle]) for key,rows in up.items() if vehicle in rows and rows[vehicle]['time']<exit['time']]
            if exit['category']=='initial_local':source,start='initial_local',2400.
            elif len(sources)==1:source,start=sources[0][0],sources[0][1]['time']
            else:continue
            track=cache['tracks'].get(str(vehicle),[])
            stopped,coverage=stop_time(track,start,exit['time'],5)
            stop1,coverage1=stop_time(track,start,exit['time'],1)
            elapsed=exit['time']-start
            assert coverage<=elapsed+1e-7 and 0<=stop1<=stopped<=coverage+1e-7
            journeys.append(dict(vehicle=vehicle,source=source,category=exit['category'],
                start_sec=start,head_sec=exit['time'],elapsed_sec=elapsed,stopped_le5_sec=stopped,
                stopped_le1_sec=stop1,nonstopped_le5_sec=elapsed-stopped,
                virtual_ready_le5_sec=exit['time']-stopped,
                uncovered_sec=max(0.,elapsed-coverage)))
        complete=[r for r in journeys if r['uncovered_sec']<1e-7]
        ldp=next(root.glob('vissim_eval/*_109_001.ldp'))
        PINS[str(ldp)]=hashlib.sha256(ldp.read_bytes()).hexdigest()
        frames=read_ldp_frames({109:ldp},{109:list(range(1,9))},2400,2850)['frames']
        green=[t for t in range(2400,2850) if frames[t]['109:2']=='GREEN']
        intervals=[]
        for t in green:
            if intervals and intervals[-1][1]==t:intervals[-1][1]=t+1
            else:intervals.append([t,t+1])
        response=read(MODEL/(arm+'.response.json.gz'),True)
        move='movement:SC109_W_SC108_to_E'
        departure=[r for r in response['transfers'] if r['source']==move and r['target']!=move]
        arrival=[r for r in response['transfers'] if r['source']=='storage:SC108_to_SC109' and r['target']==move]
        def bins(rows):return [sum(r['vehicles'] for r in rows if t<=r['start_sec']<t+150) for t in (2400,2550,2700)]
        arms[arm]=dict(journeys=journeys,complete_journeys=len(complete),
            rejected_incomplete=len(journeys)-len(complete),native_head_counts150=chain['native_head_summary'][arm]['SC109_W_p3']['count150'],
            model_departures150=bins(departure),model_arrivals150=bins(arrival),
            native_green_intervals=intervals,native_green_seconds150=[sum(t<=g<t+150 for g in green) for t in (2400,2550,2700)],
            groups={key:{field:stats([r[field] for r in complete if r['source']==key])
                         for field in ('elapsed_sec','stopped_le5_sec','stopped_le1_sec','nonstopped_le5_sec')}
                    for key in ('initial_local','SC108_W_p3','SC108_side_p3')},
            virtual_ready_completed_cohorts150=[sum(t<=r['virtual_ready_le5_sec']<t+150 for r in complete) for t in (2400,2550,2700)],
            model_queue150=[next(r['model_stock_veh'][move] for r in response['residence'] if r['stage']=='urban' and r['end_sec']==t) for t in (2550,2700,2850)])
    paired={}
    for source in ('initial_local','SC108_W_p3','SC108_side_p3'):
        byarm={arm:{r['vehicle']:r for r in rows['journeys'] if r['source']==source and r['category']!='absent_initial' and r['uncovered_sec']<1e-7}
               for arm,rows in arms.items()}
        common=sorted(set(byarm['hold'])&set(byarm['city']))
        rows=[]
        for veh in common:
            hold,city=byarm['hold'][veh],byarm['city'][veh]
            d={key:city[key]-hold[key] for key in ('start_sec','head_sec','elapsed_sec','stopped_le5_sec','stopped_le1_sec','nonstopped_le5_sec','virtual_ready_le5_sec')}
            assert abs(d['head_sec']-d['start_sec']-d['stopped_le5_sec']-d['nonstopped_le5_sec'])<1e-7
            rows.append(dict(vehicle=veh,**d))
        paired[source]=dict(count=len(rows),mean_delta={k:statistics.mean(r[k] for r in rows) if rows else None for k in ('start_sec','head_sec','stopped_le5_sec','stopped_le1_sec','nonstopped_le5_sec','virtual_ready_le5_sec')},rows=rows)
    for rel in ('diag_c3_r2/U7.md','impl/STAGE3.md'):
        p=A.parent.parent/'upstream_worklog/02_urban_b2'/rel
        PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(status='complete_sc109_arrival_and_stopped_delay_diagnostic',arms=arms,paired_initial_cohorts=paired,
        source_pins=PINS,goal_complete=False,production_adopted=False,
        budget=dict(forecasts=0,optimizer=0,native=0,source_fzp_passes=2,fits=0),
        limits=['Future observed trajectories are diagnosis only; never prediction features.',
                'Head-to-head completed journeys are survivor-conditioned; common initial IDs are paired but do not cover the whole control effect.',
                'Stopped duration is a5s sampled indicator estimate; virtual ready=head time minus stopped duration is a point-queue proxy, not observed queue-arrival time.',
                'Partial final trajectories are excluded from travel-time statistics, never treated as normal exits.',
                'Observed p3 through head and model approach-arrival quantities have different cohort coverage. Do not equate their totals.',
                'Two fresh closed-file passes were needed because prior cache did not retain post2400 positions; no prior extraction or prediction repeated.'])
    (HERE/'diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PAIRED',json.dumps({k:{f:v[f] for f in ('count','mean_delta')} for k,v in paired.items()}))
    for arm,r in arms.items():print(arm,json.dumps({k:r[k] for k in ('groups','native_head_counts150','model_departures150','model_arrivals150','native_green_intervals','native_green_seconds150','model_queue150','virtual_ready_completed_cohorts150')}))


if __name__=='__main__':main()
