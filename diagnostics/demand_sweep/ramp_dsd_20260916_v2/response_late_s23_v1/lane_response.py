"""Post-run lane statistics missing from the aggregate observer. No live COM."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
OUT=HERE/'lane_response_v1'
LINKS={2,119,10681,10702,10613}
STATIONS={2:[2000.,2400.,3900.],119:[500.]}


def scan(name,path):
    stats=collections.defaultdict(lambda:[0,0.,0.,0,0,0])
    crossings=collections.Counter()
    previous={}; frame={}; now=None; digest=hashlib.sha256(); count=0
    def consume(sec,current,previous):
        if sec<1200:return
        bucket=(sec-1)//150*150
        for no,(link,lane,pos,speed) in current.items():
            key=(bucket,link,lane,int(max(0.,pos)//100)*100)
            s=stats[key];s[0]+=1;s[1]+=speed;s[2]+=speed*speed;s[3]+=speed<5
            old=previous.get(no)
            if old and old[0]==link:
                s[4]+=old[1]!=lane
                s[5]+=speed-old[3]<-7.2
                for station in STATIONS.get(link,[]):
                    if old[2]<station<=pos:crossings[bucket,link,station,lane]+=1
    with path.open('rb') as stream:
        for raw in stream:
            digest.update(raw)
            if raw.startswith(b'$VEHICLE:'):
                assert raw.strip()==b'$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM'
                break
        else:raise ValueError('Header absent')
        for raw in stream:
            digest.update(raw);count+=1
            p=raw.split(b';')
            assert len(p)==9 and raw.endswith(b'\n')
            sec=int(float(p[0]))
            if now is not None and sec!=now:
                assert sec==now+1
                consume(now,frame,previous);previous=frame;frame={}
            now=sec
            link=int(p[2])
            if sec>=1199 and link in LINKS:
                no=int(p[1]);assert no not in frame
                frame[no]=(link,int(p[3]),float(p[4]),float(p[6]))
        consume(now,frame,previous)
    assert now==4500
    with (OUT/(name+'_lane150.csv')).open('x',newline='',encoding='utf-8') as stream:
        w=csv.writer(stream);w.writerow(['start_s','link','lane','start_m','n_mean','speed_mean_kmh','speed_sd_kmh','stopped_veh_s','lane_changes','braking_steps'])
        for key,(n,v,v2,stop,lc,brake) in sorted(stats.items()):
            w.writerow([*key,n/150,v/n,math.sqrt(max(0.,v2/n-(v/n)**2)),stop,lc,brake])
    with (OUT/(name+'_stations150.csv')).open('x',newline='',encoding='utf-8') as stream:
        w=csv.writer(stream);w.writerow(['start_s','link','station_m','lane','vehicles'])
        for key,n in sorted(crossings.items()):w.writerow([*key,n])
    return {'file':str(path),'sha256':digest.hexdigest(),'rows':count,'end_s':now,
        'scope':'150s x100m x lane; snapshot occupancy and speed moments; braking is >7.2km/h one-second drop; lane changes same-link only'}


def main():
    OUT.mkdir(exist_ok=False)
    evidence={}
    for name,path in [('s13_none',H/'rules_4500_v1/run_none/vissim_eval/baseline_001.fzp'),
                      ('s23_none',H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp'),
                      ('s23_vsl',HERE/'run_vsl/vissim_eval/baseline_001.fzp')]:
        evidence[name]=scan(name,path)
        print(name,'complete',flush=True)
    (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')


if __name__=='__main__':main()
