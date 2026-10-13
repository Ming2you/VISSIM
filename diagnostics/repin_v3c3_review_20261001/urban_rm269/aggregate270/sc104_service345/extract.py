"""One completed FZP past-prefix read, head crossings qualified by actual LDP.

Neither future observations nor held-out throughput is a model input.
Five-second crossing brackets touching amber/red stay explicitly ambiguous.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,time,xml.etree.ElementTree as ET
from diagnostics.validate_native_signal_record import read_ldp_frames
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc104_arrival344.candidate import PATH,NET_SHA
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
FZP=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/vissim_eval/sdmpc31_g_2400_hold_s29_001.fzp')
LDP=FZP.with_name('sdmpc31_g_2400_hold_s29_104_001.ldp')
NET=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
def crossed(a,b,heads):
    # Tuples: time,id,link,lane,pos,route_decision,route_no.
    if not 0<b[0]-a[0]<=5.001:return False
    if a[5:]!=(1095,1):return False
    i,j=PATH.index(str(a[2])),PATH.index(str(b[2]));h=PATH.index('1220061200')
    before=i<h or (i==h and a[3] in heads and a[4]<heads[a[3]])
    after=j>h or (j==h and b[3] in heads and b[4]>=heads[b[3]])
    return before and after
def main():
    assert not (HERE/'past_head.json').exists()
    start=time.perf_counter();root=ET.fromstring(NET.read_bytes())
    assert hashlib.sha256(NET.read_bytes()).hexdigest()==NET_SHA
    hs=[h for h in root.findall('./signalHeads/signalHead') if h.get('sg')=='104 6']
    assert len(hs)==4 and all(h.get('lane').split()[0]=='1220061200' for h in hs)
    heads={int(h.get('lane').split()[1]):float(h.get('pos')) for h in hs}
    ld=read_ldp_frames({104:LDP},{104:list(range(1,9))},1795,2400)
    before=FZP.stat();last={};events=[];cols=None;visited=0;used=0;prefix=hashlib.sha256()
    with FZP.open('rb') as f:
        for line in f:
            if line.startswith(b'$VEHICLE:'):
                cols=line.decode('utf8').strip().split(':',1)[1].split(';');continue
            if cols is None or not line.strip():continue
            fields=line.strip().split(b';');t=float(fields[0]);visited+=1
            if t>=2400:break
            prefix.update(line)
            if t<1795:continue
            used+=1;link=int(fields[cols.index('LANE\\LINK\\NO')])
            if str(link) not in PATH:continue
            def num(name):return int(float(fields[cols.index(name)] or b'-1'))
            rec=(t,num('NO'),link,num('LANE\\INDEX'),float(fields[cols.index('POS')]),num('ROUTDECNO'),num('ROUTENO'))
            old=last.get(rec[1]);last[rec[1]]=rec
            if old and crossed(old,rec,heads):
                stamps=range(math.floor(old[0])+1,math.ceil(t)+1)
                green=all(ld['frames'][x]['104:6']=='GREEN' for x in stamps)
                events.append(dict(vehicle=rec[1],low=old[0],high=t,all_green=green,from_link=old[2],to_link=link))
    assert cols and (before.st_size,before.st_mtime_ns)==(FZP.stat().st_size,FZP.stat().st_mtime_ns)
    assert len({e['vehicle'] for e in events})==len(events)
    windows=[]
    for lo,hi in ((1800,2100),(2100,2400)):
        ev=[e for e in events if lo<=e['low'] and e['high']<=hi]
        green=sum(ld['frames'][s]['104:6']=='GREEN' for s in range(lo+1,hi+1))
        qualified=sum(e['all_green'] for e in ev)
        windows.append(dict(start=lo,end=hi,green_sec=green,known_crossings=len(ev),
            all_green_crossings=qualified,ambiguous=len(ev)-qualified,observed_rate_veh_h=qualified*3600/green))
    result=dict(status='complete_past_prefix_service_audit',source=str(FZP),source_size=before.st_size,
        source_mtime_ns=before.st_mtime_ns,past_data_prefix_sha256=prefix.hexdigest(),read_until_sec=2400,
        lines_visited=visited,window_rows=used,events=events,windows=windows,
        lower_observed_rate=min(w['observed_rate_veh_h'] for w in windows),
        source_pins={str(NET):NET_SHA,**{p:v['sha256'] for p,v in ld['pins'].items()},
            str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        wall_sec=time.perf_counter()-start,created_utc=datetime.now(timezone.utc).isoformat(),
        limitations=['Observed green throughput, not identified saturation flow.',
            'Five-second ambiguous crossings excluded from rate numerator.',
            'Only past data before2400; future140 is validation only.',
            'No production adoption or native performance claim.'])
    (HERE/'past_head.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','windows','lower_observed_rate','wall_sec')},indent=2))
if __name__=='__main__':main()
