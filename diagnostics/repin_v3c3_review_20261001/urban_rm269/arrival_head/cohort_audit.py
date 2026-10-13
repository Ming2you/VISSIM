"""Current-cohort ETA vs closed future crossings: one-sided timing diagnostic.

Future crossings are validation targets only. Crossing time includes signal and
queue wait, so an earlier modeled ready-time is not itself an arrival error.
"""
import ctypes,hashlib,importlib.util,json,math,sys
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
loader=importlib.util.spec_from_file_location('closed_heads',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS={'SC6_S':1210018302,'SC101_S':1220011503}
read=a.read

def main():
    out=HERE/'cohort_assessment.json';assert not out.exists()
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    contract=read(HERE/'contract.json')
    net=ET.fromstring(a.pin(ROOT/contract['network']['path']))
    links={e.get('no'):e for e in net.findall('./links/link')}
    def length(e):
        pts=[[float(n.get(c,'0')) for c in ('x','y','zOffset')] for n in e.findall('./geometry/linkPolyPts/linkPolyPoint')]
        return sum(math.dist(x,y) for x,y in zip(pts,pts[1:]))
    lengths={k:length(e) for k,e in links.items()}
    rows=[]
    for at,arm in ((2400,'hold'),(2400,'selected'),(3300,'applied')):
        folder=a.ORIGINAL if arm=='applied' else a.NATIVE/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        raw=read(folder/f'state_{at:06}.json')
        # Uses the same queue walk as production, with the pinned geometry.
        with patch.object(adapter,'_link_lengths_m',return_value=lengths):
            q=adapter._contiguous_stopline_queue(raw,per_lane=True)
        events=defaultdict(list)
        for end in range(at+150,at+(150 if arm=='applied' else 450)+1,150):
            _,ev=a.heads_and_entries(folder,end)
            for group,items in ev.items():events[group].extend(items)
        local=[]
        for source,group in (('SC12_to_SC6','SC6_S'),('SC1_to_SC101','SC101_S')):
            spec=contract['sources'][source];link=spec['link']
            vs=[v for v in raw['vehicle_records']['records'] if str(v['link_no'])==link]
            ready=set()
            for lane in {v['lane_no'] for v in vs}:
                n=q.get((link,str(lane)),0.)
                assert n==int(n)
                front=sorted((v for v in vs if v['lane_no']==lane),key=lambda v:-v['position_m'])[:int(n)]
                assert len(front)==n and all(v['stopped'] for v in front)
                ready.update(v['veh_no'] for v in front)
            meanspeed=sum(v['speed_kph'] for v in vs)/len(vs) if vs else contract['speed_floor_kph']
            eta={}
            for v in vs:
                if v['veh_no'] in ready:continue
                candidates=[]
                for m,r in spec['movements'].items():
                    c=links[r['connector']];start=c.find('fromLinkEndPt');pos=float(start.get('pos'))
                    first=int(start.get('lane').split()[1]);lanes=range(first,first+len(c.findall('./lanes/lane')))
                    if v['lane_no'] in lanes and v['position_m']<=pos+1e-6:
                        t=(pos-v['position_m'])/(max(v['speed_kph'],meanspeed,contract['speed_floor_kph'])/3.6)
                        candidates.append(max(1,math.ceil(t)))
                assert candidates,(at,group,v)
                eta[v['veh_no']]=dict(old=105 if v['stopped'] else 15,kinematic_min=min(candidates),kinematic_max=max(candidates),stopped=v['stopped'])
            observed={}
            for lane,id,t in sorted(events[group],key=lambda v:v[2]):
                if id in eta and id not in observed:observed[id]=t-at
            matched=[dict(veh_no=id,crossing_delay_sec=t,**eta[id]) for id,t in observed.items()]
            metrics={}
            for method in ('old','kinematic_min','kinematic_max'):
                late=[max(0.,r[method]-r['crossing_delay_sec']) for r in matched]
                metrics[method]=dict(arrival_after_actual_crossing_count=sum(x>1e-7 for x in late),
                    sum_proven_late_sec=sum(late),max_proven_late_sec=max(late,default=0.))
            local.append(dict(source=source,link=link,current_residual_veh=len(eta),matched_later_head_veh=len(matched),
                no_observed_head_within_window=len(eta)-len(matched),metrics=metrics,matched_vehicles=matched))
        rows.append(dict(at=at,arm=arm,cohorts=local))
    for p in (Path(__file__),ROOT/'evaluation/controllers/observation_projection.py',
        H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md'):a.pin(p)
    out.write_text(json.dumps(dict(status='complete',rows=rows,source_pins=a.PINS,
        new_forecasts=0,fzp_scans=0,future_used_as_model_input=False,
        limitations=['Early modeled readiness cannot be validated directly with crossing times that contain waiting.',
            'Unmatched vehicles may turn before a detector or cross after the observed window; do not treat them as stopped or lost.',
            'Lane-based route ambiguity is bounded by min/max ETA; no unrecorded current destination is invented.']),indent=2)+'\n',encoding='utf8')
    print(json.dumps([dict(at=r['at'],arm=r['arm'],cohorts=[{k:v for k,v in c.items() if k!='matched_vehicles'} for c in r['cohorts']]) for r in rows]))

if __name__=='__main__':main()
