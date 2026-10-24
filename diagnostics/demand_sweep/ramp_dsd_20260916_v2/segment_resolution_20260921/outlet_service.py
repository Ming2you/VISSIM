"""Identify off-ramp service separately from demand-limited observed throughput."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,sys,statistics,math
import vsl_strength as s
c=s.c;B=s.B;K=s.K;ROOT=s.ROOT;O=B/'outlet_service_v1'
PORTS={10682:(121,118.4461500324946),10483:(124,201.15015124303818)}


def extract():
    path=K/'route_state_native_v1/vsl_s23/run_retry1/vissim_eval/baseline_001.fzp'
    expected=c.load(K/'route_state_native_v1/vsl_s23/analysis/result.json')['new_fzp_sha256']
    digest=hashlib.sha256();frames={};stamp=path.stat();selected={10682,10483,121,124,123,125}
    with path.open('rb') as stream:
        for line in stream:
            digest.update(line)
            if not line[:1].isdigit():continue
            header=line.split(b';',4);t=float(header[0])
            if not 2250<=t<=3000:continue
            assert t.is_integer();frame=frames.setdefault(str(int(t)),[])
            link=int(header[2])
            if link not in selected:continue
            a=line.rstrip(b'\r\n').split(b';')
            frame.append([int(a[1]),link,int(a[3]),float(a[4]),float(a[6]),float(a[10])])
    assert digest.hexdigest()==expected and len(frames)==751
    assert (stamp.st_size,stamp.st_mtime_ns)==(path.stat().st_size,path.stat().st_mtime_ns)
    s.save(O/'local_native.json',dict(frames=frames,source=str(path.relative_to(ROOT)),sha256=expected,
        future_records='Times after each forecast cutoff are scoring only; truncate before estimator.'))
    print('Local native extracted',flush=True)


def estimate(frames,cutoff):
    assert set(frames)==set(range(cutoff-150,cutoff+1)),'Only contiguous past150s accepted'
    geometry=c.load(B.parent/'controller_response_s23_v1/none/geometry.json')
    lengths={p['connector']:p['length_m'] for p in geometry['boundaries'] if p['connector'] in PORTS}
    bytime={t:{r[0]:r for r in rows} for t,rows in frames.items()};result={}
    for off,(down,entry) in PORTS.items():
        service=[];previous_departure=None;last_waiting=None;opportunity=[];unknown=[]
        for t in range(cutoff-149,cutoff+1):
            before,now=bytime[t-1],bytime[t]
            port=sorted((r for r in before.values() if r[1]==off),key=lambda r:-r[3])
            head=port[0] if port else None
            departures=[vid for vid,r in before.items() if r[1]==off and vid in now and now[vid][1]!=off]
            unknown.extend((t,vid) for vid,r in before.items() if r[1]==off and vid not in now)
            near=[r for r in before.values() if r[1]==down and r[2]==1 and entry-20<=r[3]<=entry+50]
            opportunity.append(dict(time_s=t,queue_head=head[0] if head else None,
                head_distance=lengths[off]-head[3] if head else None,head_speed=head[4] if head else None,
                receiving_lane1_n=len(near),receiving_lane1_slow=sum(r[4]<5 for r in near),departures=len(departures)))
            for vid in departures:
                if previous_departure is not None:
                    first=bytime[previous_departure].get(vid)
                    service.append(dict(time_s=t,vehicle=vid,headway_s=t-previous_departure,
                        following_at_previous_departure=first is not None and first[1]==off,
                        previous_distance_m=lengths[off]-first[3] if first and first[1]==off else None,
                        previous_speed_kmh=first[4] if first and first[1]==off else None))
                previous_departure=t
        assert not unknown,('Unexplained off-ramp disappearance',off,unknown)
        # Diagnose estimator support before choosing a service law. Queue
        # criteria are explicit sensitivity bands, not production constants.
        bands=[]
        for distance,speed in ((15,10),(30,10),(30,20),(50,20)):
            samples=[r['headway_s'] for r in service if r['following_at_previous_departure'] and r['previous_distance_m']<=distance and r['previous_speed_kmh']<=speed and r['headway_s']>0]
            bands.append(dict(max_distance_m=distance,max_speed_kmh=speed,count=len(samples),headways=samples,
                mean=statistics.mean(samples) if samples else None,median=statistics.median(samples) if samples else None))
        result[str(off)]=dict(departures=sum(r['departures'] for r in opportunity),headways=service,queue_bands=bands,
            opportunity=opportunity,zero_head_seconds=sum(r['queue_head'] is None for r in opportunity),
            receiving_slow_seconds=sum(r['receiving_lane1_slow']>0 for r in opportunity))
    return result


def inspect():
    raw=c.load(O/'local_native.json');results={}
    for cutoff in (2400,2550):
        past={int(t):rows for t,rows in raw['frames'].items() if cutoff-150<=int(t)<=cutoff}
        results[str(cutoff)]=estimate(past,cutoff)
    s.save(O/'service_support.json',dict(cutoffs=results,fitted=False,future_inputs=False))
    for t,ports in results.items():
        for off,r in ports.items():print(json.dumps(dict(cutoff=t,off=off,departures=r['departures'],zero_head_seconds=r['zero_head_seconds'],receiving_slow_seconds=r['receiving_slow_seconds'],bands=r['queue_bands'])))


def compare():
    results={};exact=0;effective=0;west=0;forecasts=0;pins=[]
    reference=c.load(s.v.O/'vr_hadi_fd_cap_r2_validation/effective_config.json')
    reference={r['arm']:r for r in reference}
    for filename in ('protocol.json',):
        for path,h in c.load(O/filename)['source_pins'].items():
            p=ROOT/path
            if p==Path(__file__):p=O/'source_before_compare.py.txt'
            assert s.sha(p)==h;pins.append(dict(path=path,resolved=str(p.relative_to(ROOT)),sha256=h))
    for name,start in [('outlet_default2400',2400),('outlet_10682_2400',2400),('outlet_10682_2550',2550),('outlet_both_2400',2400),('outlet_both_2550',2550)]:
        spec=c.load(O/(name+'.json'));cases={};folder=O/name
        receipt=c.load(folder/'refined_guard1_receipt.json');assert receipt['completed'] and receipt['runner_sha256']==s.sha(B/'run.py')
        for row in c.load(folder/'effective_config.json'):assert row==reference[row['arm']];effective+=1
        for arm in spec['arms']:
            p=s.f.load_prediction(folder/f'refined_guard1_{arm}.json');numerics=c.screen(p);assert numerics['passed'];forecasts+=1
            ref=s.f.load_prediction((s.v.O/'vr_hadi_fd_cap_r2_validation' if start==2400 else B/'vsl_restart_v1/restart_both2550')/f'refined_guard1_{arm}.json')
            if name=='outlet_default2400':assert p==ref;exact+=1
            for field in ('cells','flows','ports','ramps'):
                assert [r for r in p[field] if r['road']=='FW_W']==[r for r in ref[field] if r['road']=='FW_W']
            west+=1
            costs=dict(mainline=sum(r['n_veh']*5/3600 for r in p['lane_groups']['FW_E'] if r['time_s']%5==0),
                on=sum(r['end']['connector_veh']*5/3600 for r in p['ramps'] if r['road']=='FW_E' and r['end_sec']%5==0),
                off=sum(r['n_veh']*5/3600 for r in p['ports'] if r['road']=='FW_E' and r['time_s']%5==0))
            cases[arm]=dict(costs=costs,numerics=numerics)
            if start==2400 and arm=='none':cases[arm].update(train=c.score(p),late=c.score(p,10,15))
            if spec.get('diagnostic_off_service'):
                recorded=c.load(folder/f'off_service_{arm}.json');assert recorded['optimistic_free_outlet']
                assert {r['connector'] for r in recorded['ports']}==set(spec['diagnostic_off_service']['connectors'])
                assert all(r['diagnostic_vph']>max(r['previous_vph']) for r in recorded['ports'])
        for arm,row in cases.items():
            if arm=='none':continue
            row['delta']={k:v-cases['none']['costs'][k] for k,v in row['costs'].items()};row['delta']['total']=sum(row['delta'].values())
        results[name]=cases
    core=c.load(B/'distribution_response_v1/verification.json')['core_hashes_unchanged']
    for path,h in core.items():assert s.sha(ROOT/path)==h
    assert s.sha(O/'before_run.py.txt')==c.load(B/'vsl_restart_v1/completion.json')['source_pins'][str((B/'run.py').relative_to(ROOT))]
    s.save(O/'results_final.json',results)
    s.save(O/'verification.json',dict(forecasts_completed=forecasts,default_entire_json_exact=exact,effective_configs_checked=effective,
        west_predictions_exact=west,source_pins=pins,core4_hashes_unchanged=core,new_native=0,future_inputs=False,production_adopted=False,qualified=False))
    print(json.dumps(dict(forecasts=forecasts,default_exact=exact,west_exact=west,effective=effective,
        vsl_delta={name:rows['vsl']['delta']['total'] for name,rows in results.items()}),indent=2))


if __name__=='__main__':{'extract':extract,'inspect':inspect,'compare':compare}[sys.argv[1]]()
