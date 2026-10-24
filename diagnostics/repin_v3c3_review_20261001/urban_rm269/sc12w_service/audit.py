"""Past-only typed SC12 west turn service support; no future validation fit."""
import hashlib,importlib.util,json,sys
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from evaluation.controllers import obs150_signal_clock as clock
loader=importlib.util.spec_from_file_location('head_reader',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS={'SC12_W':1220012103}

def main():
    assert not (HERE/'evidence.json').exists(),'No evidence overwrite'
    tree=ET.fromstring(a.pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    decisions={d.get('no'):d for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    assert not any(d.get('link')=='1220012103' for d in decisions.values())
    head=tree.find("./signalHeads/signalHead[@no='50201']")
    assert head.get('lane')=='1220012103 2' and head.get('sg')=='12 5'
    output=[]
    for end in (1950,2100,2250,2400):
        start=end-150
        before=a.read(a.ORIGINAL/f'state_{start:06}.json');after=a.read(a.ORIGINAL/f'state_{end:06}.json')
        info=before['obs150']['frames']['current'];p=a.ORIGINAL/info['path'];b=a.pin(p)
        assert a.PINS[str(p)]==info['sha256'];frame=json.loads(b)
        assert frame['complete'] and frame['time_s']==start and frame['run_id']==before['run_provenance']['run_id']
        vehicles={v[0]:v for v in frame['vehicles']};assert len(vehicles)==len(frame['vehicles'])==info['vehicles']
        physical,events=a.heads_and_entries(a.ORIGINAL,end)
        obs=next(r for r in physical['SC12_W']['rows'] if r['head_id']=='50201')
        log=after['obs150']['signal_log']
        scoped={**log,'scs':['12'],'start':{k:v for k,v in log['start'].items() if k.startswith('12-')},'events':[e for e in log['events'] if e[1]=='12']}
        intervals=clock.windows(scoped,{},after['obs150']['window'])['12-5']
        assert intervals['complete'] and intervals['native_sec']==0
        assert sum(hi-lo for lo,hi in intervals['green'])==obs['green_sec']
        typed=[];untyped=[]
        for lane,veh,t in events['SC12_W']:
            if lane!=2:continue
            # Require a non-boundary event, not the ambiguous exact switch slot.
            if not any(lo<t<hi for lo,hi in intervals['green']):continue
            v=vehicles.get(veh)
            valid=v and v[1]==1220012103 and v[3]<float(head.get('pos')) and v[6] is not None and v[8]=='STATIC'
            route=None
            if valid:
                assert float(v[6]).is_integer() and float(v[7]).is_integer()
                d=decisions[str(int(v[6]))];r=d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(v[7])}']")
                path=[d.get('link')]+[n.get('key') for n in r.findall('./linkSeq/intObjectRef')]+[r.get('destLink')]
                valid=path.count('1220012103')==1
                if valid:
                    idx=path.index('1220012103');valid=path[idx+1:idx+3]==['10242','1220015100']
                if valid:route=f'{int(v[6])}:{int(v[7])}'
            if valid:typed.append(dict(vehicle_id=veh,head_time_sec=t,frame_sec=start,frame_link=v[1],frame_lane=v[2],frame_position_m=v[3],route=route))
            else:untyped.append(veh)
        assert len(typed)<=obs['qualified_crossings']
        output.append(dict(start_sec=start,end_sec=end,green_sec=obs['green_sec'],qualified_all_head=obs['qualified_crossings'],
            typed_direct_turn_veh=len(typed),typed_witnesses=typed,unresolved_or_other_turn_ids=untyped))
    pools=[]
    for pair in (output[:2],output[2:]):
        green=sum(r['green_sec'] for r in pair);count=sum(r['typed_direct_turn_veh'] for r in pair)
        pools.append(dict(start_sec=pair[0]['start_sec'],end_sec=pair[-1]['end_sec'],green_sec=green,typed_count=count,
            eligible=green>=30 and count>=5,achieved_lower_support_veh_h=3600*count/green))
    eligible=all(p['eligible'] for p in pools)
    doc=dict(status='complete_past_only_typed_support',cutoff_sec=2400,rows=output,pools=pools,
        selected_support_veh_h=min(p['achieved_lower_support_veh_h'] for p in pools) if eligible else None,
        estimator='Minimum of two predeclared adjacent two-window pools; typed count / complete actual green exposure;30s and5typed vehicles per pool.',
        scope='Chosen direct route in preceding complete snapshot on the same source link, no intervening decision, actual later source-head passage in green. No downstream future witness is used.',
        limitations=['Achieved lower support of a route-qualified subset is not a universal saturation rate.',
            '10242 has no connector detector. Null/missing route and future arrivals remain untyped, never assigned to northbound.',
            'Other post-head movements can use the same lane; a candidate must retain one physical phase service pool, finite receiving, and source stocks.'],
        new_forecasts=0,native_runs=0,source_pins=a.PINS)
    a.pin(Path(__file__))
    (HERE/'evidence.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('rows',[(r['end_sec'],r['green_sec'],r['typed_direct_turn_veh'],r['qualified_all_head']) for r in output]);print('pools',pools,'selected',doc['selected_support_veh_h'])

if __name__=='__main__':main()
