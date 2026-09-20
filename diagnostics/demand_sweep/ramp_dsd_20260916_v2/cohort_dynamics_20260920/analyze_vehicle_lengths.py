"""Exact observation-repeat gate, then separate bodies from stopped gaps."""
from pathlib import Path
import sys
from collections import Counter
import hashlib
import statistics
import itertools
import argparse
from datetime import datetime
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_entry_space_audit import quantiles

HERE=Path(__file__).resolve().parent


def analyze_route_state(case,run_name):
    bank=HERE/'route_state_native_v1'/case;run=bank/run_name
    receipt=e.load(run/'run.json');protocol=e.load(bank/'protocol.json')
    assert receipt['completed'] and receipt['terminal_sec']==3000 and e.load(run/'fixed_validation.json')['passed']
    # Defer the large scan until BOTH sequential native recordings have finished.
    for name in ('none_s23','vsl_s23'):
        candidates=[p for p in (HERE/'route_state_native_v1'/name).glob('run*/run.json') if e.load(p)['completed']]
        assert len(candidates)==1,('Native recording not uniquely complete',name)
    reference=e.ROOT/protocol['reference_run']/'vissim_eval/baseline_001.fzp'
    source=run/'vissim_eval/baseline_001.fzp';out=bank/'analysis';out.mkdir(exist_ok=False)
    files=[reference,source];stats=[p.stat() for p in files];hashes=[hashlib.sha256(),hashlib.sha256()];headers={}
    def lines(path,index):
        with path.open('rb') as f:
            for line in f:
                hashes[index].update(line)
                if line.startswith(b'$VEHICLE:'):
                    headers[index]=line.split(b':',1)[1].strip().rstrip(b';').decode('ascii').split(';')
                if line[:1].isdigit():
                    fields=line.rstrip(b'\r\n').split(b';')
                    if len(fields)==len(headers[index])+1 and fields[-1]==b'':fields.pop()
                    yield fields
    prefix=hashlib.sha256();prefix_rows=0;count=0;last=None;frame=[];frames=[];known_routes=Counter();kinds=Counter()
    selected={10643,126,10641,10700,71};columns=['vehicle','link','lane','position_m','speed_kmh','length_m',
        'route_decision','route_number','route_type','next_link','current_lane_change_destination',
        'lane_change','interaction_state','interaction_target_type','interaction_target_number']
    def integer(v):return int(v) if v else None
    def finish(t,rows):
        if t is not None and (t in (900,1650) or 2250<=t<=2850):frames.append(dict(time_s=t,vehicles=rows))
    try:
        for old,new in itertools.zip_longest(lines(reference,0),lines(source,1)):
            assert old is not None and new is not None,('FZP row count differs',count)
            assert len(old)==10 and len(new)==20,(count,len(old),len(new),headers)
            assert old==new[:10],('First physical divergence',count,old,new[:10])
            count+=1;t=int(float(new[0]))
            if t<=2400:prefix.update(b';'.join(new)+b'\n');prefix_rows+=1
            if t!=last:finish(last,frame);frame=[];last=t
            link=int(new[2])
            if link not in selected or not (t in (900,1650) or 2250<=t<=2850):continue
            length=float(new[10]);assert 0<length<30
            row=[int(new[1]),link,int(new[3]),float(new[4]),float(new[6]),length,
                integer(new[11]),integer(new[12]),new[13].decode('ascii') or None,
                integer(new[14]),integer(new[15]),new[16].decode('ascii'),new[17].decode('ascii'),
                new[18].decode('ascii') or None,integer(new[19])]
            frame.append(row);kinds[row[8]]+=1
            if row[6] is not None:known_routes[f'{row[6]}-{row[7]}']+=1
        finish(last,frame)
        assert last==3000
        for p,s in zip(files,stats):
            after=p.stat();assert (s.st_size,s.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        assert headers[1][10:]==protocol['fields_added']
        assert any(r[6]==1126 and r[7]==1 and r[1]==10643 for f in frames if f['time_s']==2400 for r in f['vehicles'])
        # Match local positions/inventories previously extracted from the old FZP.
        prior=e.load(HERE/'off_urban_entrance_state_v1'/('s23_none.json' if case=='none_s23' else 's23_vsl.json'))
        original={f['time_s']:f['vehicles'] for f in prior['frames']};frame_checks=0
        for f in frames:
            if f['time_s'] in original:
                assert sorted([r[0],r[1],r[2],r[3],r[4]] for r in f['vehicles'])==original[f['time_s']]
                frame_checks+=1
        assert frame_checks==451
        e.save(out/'frames.json',dict(columns=columns,frames=frames,source_fzp=str(source.relative_to(e.ROOT)),
            interpretation='Each row is measured at its own time. Truncate at forecast cutoff; future routes/interaction states are labels only.'))
        e.save(out/'result.json',dict(passed=True,all_original_ten_columns_exact_rows=count,
            reference_sha256=hashes[0].hexdigest(),new_fzp_sha256=hashes[1].hexdigest(),
            full_twenty_column_prefix_through2400_sha256=prefix.hexdigest(),prefix_rows=prefix_rows,
            headers=headers,native_validation_passed=True,local_frame_checks=frame_checks,
            route_types=dict(kinds),observed_routes=dict(known_routes),
            source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),bank/'protocol.json',run/'run.json',run/'fixed_validation.json',out/'frames.json']},
            caveats=['Empty route/next-link attributes mean unavailable or unassigned, never a zero-demand destination.',
                'DestLane is the current lane-change destination, not necessarily the final connector access lane.',
                'Interaction fields describe the preceding simulation step according to the installed documentation.',
                'This deterministic observation repeat is not an independent gain validation seed.']))
        print(case,'original10 fields exact:',count,'; local frames:',frame_checks,'; route types:',dict(kinds),flush=True)
    except Exception as error:
        e.save(out/'failure.json',dict(error=repr(error),compared_rows=count,last_time=last,headers=headers))
        raise


def records(path,sha):
    with path.open('rb') as stream:
        for line in stream:
            sha.update(line)
            if line[:1].isdigit():yield line.rstrip(b'\r\n;').split(b';')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--route-state',action='store_true')
    ap.add_argument('--case',choices=['none_s23','vsl_s23'],default='none_s23');ap.add_argument('--run',default='run_retry1');args=ap.parse_args()
    if args.route_state:return analyze_route_state(args.case,args.run)
    bank=HERE/'vehicle_lengths_native_v1';run=bank/'run_retry';receipt=e.load(run/'run.json')
    assert receipt['completed'] and receipt['terminal_sec']==3000
    validation=e.load(run/'fixed_validation.json')
    assert validation['passed']
    out=bank/'analysis';out.mkdir(exist_ok=False)
    reference=HERE/'native_v1/none_s23/run/vissim_eval/baseline_001.fzp'
    source=run/'vissim_eval/baseline_001.fzp';before=source.stat()
    hashes=[hashlib.sha256(),hashlib.sha256()]
    root=ET.parse(bank/'source/baseline.inpx').getroot()
    behavior=next(x for x in root.findall('./drivingBehaviors/drivingBehavior') if x.get('no')=='1')
    gap=float(behavior.get('w74ax'));assert gap==1.5
    links={int(x.get('no')):x for x in root.findall('./links/link')}
    assert links[10643].get('linkBehavType')==links[71].get('linkBehavType')=='1'
    link_behavior=next(x for x in root.findall('./linkBehaviorTypes/linkBehaviorType') if x.get('no')=='1')
    assert link_behavior.get('drivBehavDef')=='1' and not list(link_behavior)
    length=318.99832762775236
    count=0;last=None;frame=[];frames=[];pairs=[];meta={};types=Counter();seen_off=set()
    def finish(t,rows):
        if t is None or not 900<=t<=3000:return
        frames.append({'time_s':t,'vehicles':rows})
        if not 1800<=t<2850:return
        for lane in (1,2):
            ordered=sorted((p,vid,v,size,kind) for vid,l,p,v,size,kind in rows if l==lane)
            for follower,leader in zip(ordered,ordered[1:]):
                if follower[2]<1 and leader[2]<1:
                    gross=leader[0]-follower[0];net=gross-leader[3]
                    pairs.append({'time_s':t,'lane':lane,'leader':leader[1],'follower':follower[1],
                        'leader_type':leader[4],'leader_length_m':leader[3],
                        'front_spacing_m':gross,'net_gap_m':net})
    for old,new in itertools.zip_longest(records(reference,hashes[0]),records(source,hashes[1])):
        assert old is not None and new is not None,'FZP record count changed'
        assert len(old)==10 and len(new)==12
        assert old==new[:10],('First physical divergence',count,old[:7],new[:7])
        count+=1;t=int(float(new[0]));vid=int(new[1]);link=int(new[2]);size=float(new[10]);kind=int(new[11])
        assert 0<size<30 and kind>0
        if t!=last:
            finish(last,frame);frame=[];last=t
        if link==10643:
            if vid in meta:assert meta[vid]==[size,kind]
            meta[vid]=[size,kind];seen_off.add(vid);types[kind]+=1
            frame.append([vid,int(new[3]),float(new[4]),float(new[6]),size,kind])
    finish(last,frame)
    after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert last==3000
    original=e.load(HERE/'native_v1/none_s23/run/run.json')
    assert original['completed']
    summaries={}
    for lane in (1,2):
        sample=[]
        for row in frames:
            if not 1800<=row['time_s']<2850:continue
            vehicles=sorted((p,v,size,kind) for vid,l,p,v,size,kind in row['vehicles'] if l==lane)
            n=len(vehicles);body=sum(v[2] for v in vehicles)
            nominal=length-6*n;occupied=body+gap*n
            sample.append({'time_s':row['time_s'],'n':n,'body_length_m':body,
                'heavy_n':sum(v[3]==200 for v in vehicles),'nominal_free_m':nominal,
                'body_plus_standstill_gap_free_m':length-occupied,
                'entry_near_stopped':bool(vehicles and vehicles[0][0]<6 and vehicles[0][1]<5)})
        queued=[r for r in sample if r['entry_near_stopped']]
        lane_pairs=[p for p in pairs if p['lane']==lane]
        summaries[str(lane)]={'samples':len(sample),'near_entry_stopped_samples':len(queued),
            'mean_stock':statistics.mean(r['n'] for r in sample),
            'heavy_share_of_vehicle_seconds':sum(r['heavy_n'] for r in sample)/sum(r['n'] for r in sample),
            'mean_body_length_m':sum(r['body_length_m'] for r in sample)/sum(r['n'] for r in sample),
            'near_entry_free_space_mean_m':{key:statistics.mean(r[key] for r in queued)
                for key in ('nominal_free_m','body_plus_standstill_gap_free_m')} if queued else {},
            'stopped_pair_gap_by_leader_type':{str(kind):{'n':len(selected),
                'front_spacing_m':quantiles([r['front_spacing_m'] for r in selected]),
                'net_gap_m':quantiles([r['net_gap_m'] for r in selected])}
                for kind in (100,150,200) if (selected:=[p for p in lane_pairs if p['leader_type']==kind])},
            'rows':sample}
    e.save(out/'frames.json',{'source_fzp':str(source.relative_to(e.ROOT)),'frames':frames,'vehicle_metadata':meta})
    e.save(out/'stopped_pairs.json',pairs)
    e.save(out/'result.json',{'completed':True,'all_original_ten_columns_exact_rows':count,
        'native_validation_passed':True,'reference_sha256':hashes[0].hexdigest(),'new_fzp_sha256':hashes[1].hexdigest(),
        'summaries':summaries,'standstill_distance_from_inpx_m':gap,'unique_off_vehicles':len(seen_off),
        'runtime_s':(datetime.fromisoformat(receipt['finished'])-datetime.fromisoformat(receipt['started'])).total_seconds(),
        'scope':'Native observation repeat, not independent benefit validation; bodies+standstill gap are a physical occupancy diagnostic, not a calibrated dynamic receiving capacity.',
        'caveat':'Front-crossing vehicle counts include partially entered/exited bodies; changing lanes also complicates one-lane occupancy. Negative reserved free space is retained, never resolved by deleting vehicles.'})
    print('exact rows',count,flush=True)
    for lane,row in summaries.items():print(lane,{k:v for k,v in row.items() if k!='rows'},flush=True)


if __name__=='__main__':main()
