"""One low-priority451-frame census of two long urban corridors; no FZP scan."""
import ctypes,hashlib,json,time
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
F=Path('E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
GROUPS={
    'SC105_to_SC1005':{10661,10669,10671,1220006403,10655,412,10651,10652,410,10654,408,10647,10648,409,10649,403},
    '52_58_internal_bridge':{52,58,10498},
}
PINS={}

def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)

def main():
    out=HERE/'native_census.json';assert not out.exists()
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent))
    k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    raw=read(F/'state_003300.json');folder=Path(raw['lane_plant_observation']['directory'])
    run_id=raw['lane_plant_observation']['run_id']
    netpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    data=netpath.read_bytes();PINS[str(netpath)]=hashlib.sha256(data).hexdigest()
    tree=ET.fromstring(data);edges={};inputs={int(x.get('link')) for x in tree.findall('./vehicleInputs/vehicleInput')}
    for x in tree.findall('./links/link'):
        a,b=x.find('fromLinkEndPt'),x.find('toLinkEndPt')
        if a is not None and b is not None:
            edges[int(x.get('no'))]=(int(a.get('lane').split()[0]),int(b.get('lane').split()[0]))
    # Groups have no source input and are long corridors. An observed change
    # between adjacent complete frames is an entry/exit, not a stopped queue.
    assert all(not(group & inputs) for group in GROUPS.values())
    report={name:dict(links=sorted(group),initial=None,final=None,blocks=[],inflow=Counter(),outflow=Counter(),
        unresolved=[],boundary_stock={}) for name,group in GROUPS.items()}
    previous=None;start=time.perf_counter();total_bytes=0
    for t in range(3300,3751):
        path=folder/f'frame_{t:06}.json';total_bytes+=path.stat().st_size;frame=read(path)
        assert frame['schema']=='lane-plant-frame/v1' and frame['complete'] and frame['time_s']==t and frame['run_id']==run_id
        current={int(v[0]):int(v[1]) for v in frame['vehicles']}
        assert len(current)==len(frame['vehicles'])
        for name,group in GROUPS.items():
            row=report[name];ids={vid for vid,link in current.items() if link in group}
            if t==3300:
                row['initial']=len(ids);row['boundary_stock'][str(t)]=len(ids);continue
            before={vid for vid,link in previous.items() if link in group}
            block=(t-3301)//150
            if len(row['blocks'])<=block:row['blocks'].append(dict(start_sec=3300+block*150,initial=len(before),inflow=Counter(),outflow=Counter(),unresolved=[]))
            item=row['blocks'][block]
            for direction,vehicles in (('inflow',ids-before),('outflow',before-ids)):
                for vid in vehicles:
                    source,target=previous.get(vid),current.get(vid)
                    if source is None or target is None:
                        event=dict(time=t,vehicle=vid,direction=direction,source=source,target=target)
                        item['unresolved'].append(event);row['unresolved'].append(event)
                    else:
                        key=str(source)+'->'+str(target)
                        item[direction][key]+=1;row[direction][key]+=1
            item['final']=len(ids);row['final']=len(ids)
            if t%150==0:row['boundary_stock'][str(t)]=len(ids)
        previous=current
        if t%150==0:print('CENSUS_SEC',t,flush=True)
    for row in report.values():
        row['unresolved_count']=len(row['unresolved'])
        for item in row['blocks']:
            item['residual']=item['final']-item['initial']-sum(item['inflow'].values())+sum(item['outflow'].values())
        row['residual']=row['final']-row['initial']-sum(row['inflow'].values())+sum(row['outflow'].values())
        assert row['residual']==0 and not row['unresolved'] and all(x['residual']==0 for x in row['blocks']),row
    result=dict(status='complete',groups=report,wall_sec=time.perf_counter()-start,frames=451,bytes_read=total_bytes,
        source_pins=PINS,new_predictions=0,new_native_runs=0,
        limitations=['One-second sample transitions can miss a complete unobserved in-and-out traversal. These long groups have no vehicle inputs; compare their exits with independent native heads.',
            'Physical group boundaries include internal connectors; they are not the original52+58-only metric or a change to Omega701.',
            'Future observed flow is diagnostic only; no forecast input or saturation-rate replacement.'])
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print('CENSUS_COMPLETE',result['wall_sec'],[(k,sum(v['inflow'].values()),sum(v['outflow'].values())) for k,v in report.items()],flush=True)

if __name__=='__main__':main()
