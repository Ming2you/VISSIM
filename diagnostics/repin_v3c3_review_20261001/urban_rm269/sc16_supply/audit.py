"""Bounded SC16-to-SC12 source diagnosis; no fit, forecast or native run."""
import ctypes,gzip,hashlib,importlib.util,json,sys
from collections import Counter,defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
loader=importlib.util.spec_from_file_location('closed_sc16_heads',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS=dict(SC16_W=1210009700,SC16_E=1220011200,SC16_S=1210009503,SC12_S=1210012700)
def main():
    out=HERE/'assessment.json';assert not out.exists()
    k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    from qualify_native2400 import validate_scope
    validate_scope(a.read(H/'native2400_analysis/summary.json'),a.read(H/'native2400_analysis/observed_input_qualification.json'))
    net=a.read(H/'sc12w_service/forecast2400_checked/network.json')
    past={}
    for end in (1950,2100,2250,2400):past[str(end)],_=a.heads_and_entries(a.ORIGINAL,end)
    tree=ET.fromstring(a.pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    geometry={label:[dict(head_id=x.get('no'),lane=x.get('lane'),pos=x.get('pos'),sg=x.get('sg')) for x in tree.findall('./signalHeads/signalHead') if x.get('lane').split()[0]==str(link)] for label,link in a.LINKS.items()}
    result={}
    for arm in ('hold','selected'):
        folder=a.NATIVE/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        events=defaultdict(list);blocks=[]
        for end in (2250,2400,2550,2700,2850):
            physical,observed=a.heads_and_entries(folder,end)
            for source,rows in observed.items():
                for lane,veh,t in rows:events[source].append((lane,veh,t))
            if end>2400:blocks.append(dict(start_sec=end-150,heads=physical))
        downstream=defaultdict(list)
        for lane,veh,t in events['SC12_S']:downstream[veh].append(t)
        paths=[]
        for source in ('SC16_W','SC16_E','SC16_S'):
            for lane,veh,t in events[source]:
                future=[z for z in downstream[veh] if t<z and z>2400]
                if future:paths.append(dict(source=source,lane=lane,vehicle_id=veh,source_sec=t,downstream_sec=min(future),travel_sec=min(future)-t))
        response=json.loads(gzip.decompress(a.pin(H/'sc12w_service/forecast2400_checked'/(arm+'.response.json.gz'))))
        for block in blocks:
            t=block['start_sec'];transfers=[r for r in response['transfers'] if t<=r['start_sec']<t+150]
            incoming=Counter();heads=Counter()
            for r in transfers:
                if r['target']=='storage:SC16_to_SC12' and r['source']!=r['target']:incoming[r['source'] or r['route_key']]+=r['vehicles']
                for label in ('SC16_W','SC16_E','SC16_S'):
                    if (r['source'] or '').startswith('movement:'+label+'_') and r['target']!=r['source']:heads[label]+=r['vehicles']
            block['model_to_SC12_by_source']=dict(incoming);block['model_aggregate_source_departures']=dict(heads)
        result[arm]=dict(blocks=blocks,path_witnesses=paths,
            two_head_source_paths_with_both_passages_in450=dict(Counter(p['source'] for p in paths if p['source_sec']>2400)),
            paths_with_source_before_initial_state=dict(Counter(p['source'] for p in paths if p['source_sec']<=2400)))
    inputs={m:dict(spec=v,rate=net['movement_capacity_by_movement_veh_h'][m],physical_turn=net['control_area_routes']['movement:'+m]) for m,v in net['urban_movements'].items() if m.startswith(('SC16_W_','SC16_E_'))}
    for f in [Path(__file__),H.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md',H.parent/'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md']:a.pin(f)
    doc=dict(status='complete_source_diagnosis',past=past,geometry=geometry,model_inputs=inputs,arms=result,
        new_forecasts=0,new_native=0,coefficient_fits=0,fzp_scans=0,
        limitations=['Head total is not a turn count when a lane has competing connectors.',
            'Two-head identity is a realized path witness, not a unique direct connector count or a complete source census.',
            'A past achieved rate must not be called universal saturation; actual queues and finite receiving must be retained.',
            'Source amounts and downstream arrival times are separate; no future data substituted into prediction.'],source_pins=a.PINS)
    out.write_text(json.dumps(doc,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    for end,groups in past.items():print('past',end,{k:[(r['lane'],r['crossings'],r.get('green_sec')) for r in v['rows']] for k,v in groups.items() if k in ('SC16_W','SC16_E')})
    for arm,x in result.items():
        print(arm,'paths',x['two_head_source_paths_with_both_passages_in450'])
        for row in x['blocks']:print(row['start_sec'],{k:(v['crossings'],row['model_aggregate_source_departures'].get(k)) for k,v in row['heads'].items() if k in ('SC16_W','SC16_E','SC16_S')})
if __name__=='__main__':main()
