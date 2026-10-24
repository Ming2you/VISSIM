"""Check native same-10s passage without using future rows as model inputs."""
from pathlib import Path
import json,math,time,hashlib,statistics
HERE=Path(__file__).resolve().parent.parent;ROOT=HERE.parents[3];H=HERE.parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
out=Path(__file__).resolve().parent/'passage_audit.json';assert not out.exists()
cache=load(HERE/'branch_flux_audit_v1/native_none.json')
native={r['time_s']:r for r in cache['rows']}
geom=load(H/'controller_response_s23_v1/none/geometry.json')
cell=next(c for c in geom['cells'] if c['road']=='FW_E' and c['cell']==8)
branch=next(p for p in geom['boundaries'] if p['connector']==10643)
a,b=cell['start_m'],branch['chain_pos_m'];shift=b-branch['from_pos_m']
path=ROOT/cache['source']['path'];before=path.stat()
assert (before.st_size,before.st_mtime_ns)==(cache['source']['bytes'],cache['source']['mtime_ns'])
assert cache['source']['sha256']==load(HERE/'route_state_native_v1/none_s23/analysis/result.json')['new_fzp_sha256']
previous={};entered={};events=[];samples=[];checked=0;started=time.perf_counter()
def process(t,current):
    global previous,checked
    if 2400<=t<=2850:
        counts=[sum(a<=v[1]<b and min(v[0]-1,2)==g for v in current.values()) for g in range(3)]
        assert counts==native[t]['counts']['pre'],(t,counts,native[t]['counts']['pre'])
        checked+=3
    for vid,new in current.items():
        old=previous.get(vid)
        if old is None:continue
        if old[1]<a<=new[1]<b:
            entered[vid]=dict(vehicle=vid,entry_interval_s=[t-1,t],entry_lane=new[0],changed=old[0]!=new[0],
                              observations=[[t-1,*old],[t,*new]])
        elif vid in entered:
            entered[vid]['observations'].append([t,*new])
            entered[vid]['changed']|=old[0]!=new[0]
        if old[1]<b<=new[1] and vid in entered:
            event=entered.pop(vid);entry=event['entry_interval_s'][1]
            if entry>2400 and t<=2850:
                event.update(exit_interval_s=[t-1,t],same10s=math.ceil((entry-2400)/10)==math.ceil((t-2400)/10),
                             sampled_travel_s=t-entry)
                events.append(event)
    previous=current
last=None;frame={};lines=0
with path.open('rb') as stream:
    for line in stream:
        if not line[:1].isdigit():continue
        time_field=line.split(b';',1)[0];t=int(float(time_field))
        if t<2399:continue
        if t>2850:break
        if last is not None and last!=t:
            assert t==last+1;process(last,frame);frame={}
        last=t;lines+=1
        p=line.rstrip(b'\r\n').split(b';')
        if p[2]!=b'2':continue
        x=float(p[4])+shift
        if a-50<=x<=b+50:frame[int(p[1])]=(int(p[3]),x,float(p[6]))
assert last==2850;process(last,frame)
after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
free=[v for v in events if v['entry_lane']>=3 and not v['changed']]
same=[v for v in free if v['same10s']]
violations=[]
for end in range(2410,2851,10):
    n0=native[end-10]['counts']['pre'][2];rows=[native[t] for t in range(end-9,end+1)]
    cross=sum(r['terms']['pre'][2].get('cross',0) for r in rows)
    lateral=sum(r['terms']['pre'][2].get('lateral',0) for r in rows)
    if cross>n0:violations.append(dict(end_s=end,start_n=n0,cross=cross,net_lateral=lateral))
result=dict(status='COMPLETE',source=cache['source'],source_identity='Prior full SHA256 reused; size/mtime unchanged, all1353 current pre-group counts match cached full-hash extraction.',
    geometry=dict(start_m=a,branch_m=b,length_m=b-a),information_scope='Future native rows are validation labels only; no prediction was rerun or conditioned on them.',
    observed_frames=checked//3,matched_group_counts=checked,window_numeric_rows=lines,
    unchanged_lane3or4_passages=len(free),within_same10s=len(same),sampled_travel_median_s=statistics.median(v['sampled_travel_s'] for v in free),
    strict_model_start_stock_sending_violations=len(violations),violations=violations,
    examples=same[:20],elapsed_s=time.perf_counter()-started,qualified=False,new_native_runs=0,
    conclusion='These unchanged-lane vehicles enter and leave the176m pre-branch section within one model step. A sending rule using only start-of-step stock cannot represent these specific passages, independent of FD fitting. This is not proof that time refinement alone fixes RM/VSL net gain.')
with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
print(json.dumps({k:v for k,v in result.items() if k not in ('examples','violations','source')},indent=2))
