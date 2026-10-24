"""Read one bounded past slice of a closed FZP for typed head support.

Only1790<=t<2400, source1220012103 and connectors10241/10242 are retained.
Exact head times/greens come from that same closed run's MER and signal log.
Future observations are not used. All-source FZP scans/TTT analysis are absent.
"""
import bisect,ctypes,hashlib,importlib.util,json,sys,time
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from evaluation.controllers import obs150_signal_clock as clock
from qualify_native2400 import validate_scope
loader=importlib.util.spec_from_file_location('heads',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS={'SC12_W':1220012103}
FOLDER=a.NATIVE/'hold'/'decisions_sdmpc31_g_2400_hold_s29'
FZP=a.NATIVE/'hold/vissim_eval/sdmpc31_g_2400_hold_s29_001.fzp'

def extract():
    assert not (HERE/'past_fzp_slice.json').exists(),'Do not reread completed extraction'
    meta=FZP.stat();kept=[];digest=hashlib.sha256();total=0
    with FZP.open('rb') as f:
        while True:
            line=f.readline()
            if not line:raise ValueError('Missing vehicle header')
            if line.startswith(b'$VEHICLE:'):
                columns=line.decode('ascii').strip().split(':',1)[1].split(';');begin=f.tell();break
        assert columns[:5]==['SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS']
        assert all(c in columns for c in ('ROUTDECNO','ROUTENO','ROUTDECTYPE','NEXTLINK\\NO'))
        # Find an earlier complete row, then scan only the bounded time window.
        lo,hi=begin,meta.st_size
        while hi-lo>1048576:
            f.seek((lo+hi)//2);f.readline();pos=f.tell();line=f.readline()
            sec=float(line.split(b';',1)[0])
            if sec<1790:lo=pos
            else:hi=pos
        f.seek(lo);first=f.tell();last_time=-1
        while True:
            pos=f.tell();line=f.readline()
            if not line:break
            fields=line.rstrip(b'\r\n').split(b';');sec=float(fields[0])
            assert sec>=last_time;last_time=sec
            if sec>=2400:break
            if sec<1790:continue
            digest.update(line);total+=1
            if int(fields[2]) not in (1220012103,10241,10242):continue
            def value(c):return fields[columns.index(c)].decode('ascii').strip()
            kept.append(dict(time_sec=sec,vehicle_id=int(fields[1]),link=int(fields[2]),lane=int(fields[3]),position_m=float(fields[4]),
                route_decision=value('ROUTDECNO'),route=value('ROUTENO'),route_type=value('ROUTDECTYPE'),next_link=value('NEXTLINK\\NO')))
        last=pos
    end=FZP.stat();assert (meta.st_size,meta.st_mtime_ns)==(end.st_size,end.st_mtime_ns)
    result=dict(source=str(FZP),source_size=meta.st_size,source_mtime_ns=meta.st_mtime_ns,read_byte_start=first,read_byte_end=last,
        time_window=[1790,2400],cutoff_exclusive=True,scanned_rows_in_window=total,kept_rows=kept,
        all_rows_in_window_sha256=digest.hexdigest(),scope='Closed past only; selected physical links; no performance scan or full-file hash')
    (HERE/'past_fzp_slice.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
    return result

def main():
    assert not (HERE/'typed_support_v3.json').exists()
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    validate_scope(a.read(H/'native2400_analysis/summary.json'),a.read(H/'native2400_analysis/observed_input_qualification.json'))
    a.read(H/'native2400_analysis/runtime_closure.json')
    tr=ET.fromstring(a.pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    decisions={d.get('no'):d for d in tr.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    assert not any(d.get('link')=='1220012103' for d in decisions.values())
    head=tr.find("./signalHeads/signalHead[@no='50201']");assert head.get('lane')=='1220012103 2' and head.get('sg')=='12 5'
    started=time.perf_counter()
    cached=HERE/'past_fzp_slice.json'
    first=a.read(HERE/'typed_support.json')
    assert hashlib.sha256(cached.read_bytes()).hexdigest()==first['source_pins'][str(cached)]
    slice_doc=json.loads(a.pin(cached))
    current=FZP.stat()
    assert (current.st_size,current.st_mtime_ns)==(slice_doc['source_size'],slice_doc['source_mtime_ns'])
    by_vehicle=defaultdict(list)
    for r in slice_doc['kept_rows']:by_vehicle[r['vehicle_id']].append(r)
    rows=[]
    for end in (1950,2100,2250,2400):
        raw=a.read(FOLDER/f'state_{end:06}.json');physical,events=a.heads_and_entries(FOLDER,end)
        obs=next(x for x in physical['SC12_W']['rows'] if x['head_id']=='50201')
        log=raw['obs150']['signal_log'];scoped={**log,'scs':['12'],'start':{k:v for k,v in log['start'].items() if k.startswith('12-')},'events':[e for e in log['events'] if e[1]=='12']}
        intervals=clock.windows(scoped,{},raw['obs150']['window'])['12-5']
        assert intervals['complete'] and intervals['native_sec']==0
        typed=[];untyped=[];outside_green=0
        for lane,veh,t in events['SC12_W']:
            if lane!=2:continue
            if not any(lo<t<hi for lo,hi in intervals['green']):outside_green+=1;continue
            prior=[r for r in by_vehicle[veh] if r['time_sec']<=t]
            r=prior[-1] if prior else None
            valid=r and 0<=t-r['time_sec']<=5.1 and r['link']==1220012103 and r['position_m']<float(head.get('pos'))
            if valid:
                # Actual NextLink and an independently decoded active static route must agree.
                valid=r['route_type']=='Static' and r['route_decision'] not in ('','0') and r['next_link']=='10242'
            route=None
            if valid:
                d=decisions[str(int(float(r['route_decision'])))];native=d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(float(r['route']))}']")
                path=[d.get('link')]+[x.get('key') for x in native.findall('./linkSeq/intObjectRef')]+[native.get('destLink')]
                valid=path.count('1220012103')==1
                if valid:idx=path.index('1220012103');valid=path[idx+1:idx+3]==['10242','1220015100']
                route=f'{r["route_decision"]}:{r["route"]}'
            proof='active_static_route_and_next_link' if valid else None
            post=None
            if not valid and r and r['link']==1220012103 and r['position_m']<float(head.get('pos')):
                candidates=[x for x in by_vehicle[veh] if x['link']==10242 and t<x['time_sec']<2400
                    and abs(x['time_sec']-r['time_sec']-5)<1e-7]
                if candidates:
                    post=candidates[0];valid=True;proof='observed_adjacent_source_to_connector_frames'
            if valid:typed.append(dict(vehicle_id=veh,head_time_sec=t,prior=r,observed_current_route=route,proof=proof,post_connector=post))
            else:untyped.append(veh)
        assert len(typed)+len(untyped)+outside_green==sum(1 for lane,veh,t in events['SC12_W'] if lane==2)
        rows.append(dict(start_sec=end-150,end_sec=end,green_sec=sum(hi-lo for lo,hi in intervals['green']),head_total=obs['crossings'],
            typed_count=len(typed),typed_witnesses=typed,untyped_ids=untyped,outside_green=outside_green))
    pools=[]
    for pair in (rows[:2],rows[2:]):
        count=sum(r['typed_count'] for r in pair);green=sum(r['green_sec'] for r in pair)
        pools.append(dict(start_sec=pair[0]['start_sec'],end_sec=pair[-1]['end_sec'],count=count,green_sec=green,
            eligible=count>=5 and green>=30,rate_veh_h=3600*count/green))
    supported=all(x['eligible'] for x in pools)
    a.pin(Path(__file__))
    doc=dict(status='complete_past_typed_discharge_support',cutoff_sec=2400,rows=rows,pools=pools,
        selected_support_veh_h=min(x['rate_veh_h'] for x in pools) if supported else None,source_pins=a.PINS,
        estimator='Minimum of two fixed adjacent300s pools of typed10242 vehicles crossing the source head during actual green. A current static route plus NextLink or adjacent5s source-to-connector frames qualify. At least5known vehicles and30green seconds per pool.',
        new_predictions=0,new_native=0,bounded_closed_fzp_reads=0,reused_slice=True,wall_sec=time.perf_counter()-started,
        parser_correction='FZP serializes Static while COM frame uses STATIC. First unqualified report preserved; exact cached past slice reused without another raw read.',
        limitations=['Typed subset uses current chosen route/NextLink or directly sampled connector transition, not a full detector census at connector10242.',
            'A partial achieved flow support estimate, not proof of future saturation; unknown routes and red/amber/transition events are excluded.',
            'No source observation at or after2400 was used for this rate. The four2400future/3300validation outcomes are not inputs.'])
    (HERE/'typed_support_v3.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('rows',[(r['end_sec'],r['typed_count'],r['green_sec']) for r in rows]);print('pools',pools,'selected',doc['selected_support_veh_h'],'wall',doc['wall_sec'])

if __name__=='__main__':main()
