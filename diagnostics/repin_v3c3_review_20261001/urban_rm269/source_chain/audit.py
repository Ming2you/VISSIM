"""Closed native head/stock evidence versus saved native-beta predictions.

Native control volumes end at actual lane-specific stoplines. Their inferred
net inflow is entries minus unobserved losses, not an independent inflow count.
Model origins can include longer upstream corridors: do not equate footprints.
"""
import ctypes
import gzip
import importlib.util
import json
from collections import Counter,defaultdict
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
from evaluation.controllers import physical_movement_routes as routes
spec=importlib.util.spec_from_file_location('closed_head_reader',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
a.LINKS.update(SC16_S=1210009503,SC109_W=173,SC109_E=1220000704)
read=a.read

def main():
    assert not (HERE/'assessment.json').exists()
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    config=read(H/'native_beta/config.json')
    doc,native,edges=routes.load_evidence(config['urban']['movements']['physical_route_topology'])
    tree=ET.fromstring(a.pin(ROOT/doc['network']['path']))
    links={n.get('no'):n for n in tree.findall('./links/link')}
    head_nodes=tree.findall('./signalHeads/signalHead')
    volumes={}
    for group,label in [('SC12_S_SC16','SC12_S'),('SC16_S_SC109','SC16_S')]:
        g=doc['native_choice_groups'][group]
        footprint=set()
        for rid in g['route_to_movement']:
            path=native[rid]['path'];footprint.update(path[:path.index(g['stopline'])+1])
        cuts={int(n.get('lane').split()[1]):float(n.get('pos')) for n in head_nodes if n.get('lane').split()[0]==g['stopline']}
        assert len(cuts)==4
        exits=[]
        for k,node in links.items():
            frm=node.find('fromLinkEndPt')
            if frm is None:continue
            road,lane=frm.get('lane').split(); pos=float(frm.get('pos'))
            if road in footprint and k not in footprint:
                assert road==g['stopline'] and pos>cuts[int(lane)],(label,k,road,pos)
                exits.append(k)
        assert len(exits)==3
        volumes[label]=dict(links=sorted(footprint),stopline=g['stopline'],head_cuts=cuts,downstream_connectors=exits)

    def inventory(raw,label):
        v=volumes[label];counts=Counter();stopped=Counter()
        for r in raw['vehicle_records']['records']:
            link=str(r['link_no'])
            if link not in v['links']:continue
            if link==v['stopline'] and r['position_m']>v['head_cuts'][int(r['lane_no'])]:continue
            counts[link]+=1
            stopped[link]+=int(r['stopped'])
        return dict(total=sum(counts.values()),stopped=sum(stopped.values()),by_link=dict(counts))

    observed={}
    for arm in ('hold','selected'):
        folder=a.NATIVE/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        frames={t:read(folder/f'state_{t:06}.json') for t in (2400,2550,2700,2850)}
        rows=[]
        for end in (2550,2700,2850):
            heads,_=a.heads_and_entries(folder,end)
            balance={}
            for label in volumes:
                start_stock,end_stock=inventory(frames[end-150],label),inventory(frames[end],label)
                head=heads[label]['crossings']
                balance[label]=dict(start_stock=start_stock,end_stock=end_stock,head_departures=head,
                    inferred_net_entries_minus_losses=end_stock['total']-start_stock['total']+head)
            rows.append(dict(start_sec=end-150,heads={k:v for k,v in heads.items() if k in ('SC16_S','SC12_S','SC6_S','SC109_W','SC109_E')},balance=balance))
        observed[arm]=rows

    network=read(H/'native_beta/init2400_checked/network.json')
    origins=dict(SC16_S='SC109_to_SC16',SC12_S='SC16_to_SC12',SC6_S='SC12_to_SC6')
    interests={m for m in network['urban_movements'] if m.startswith(('SC16_S_','SC12_S_','SC6_S_','SC109_W_','SC109_E_'))}
    model={}
    for arm in ('hold','selected'):
        response=json.loads(gzip.decompress(a.pin(H/'native_beta/forecast2400_checked'/(arm+'.response.json.gz'))))
        stock=read(H/'native_beta/forecast2400_checked'/(arm+'.json'))
        resources=defaultdict(dict)
        for r in response['resource_allocations']:
            if r['resource'] in interests and r['kind'] in ('urban_movement_stock','urban_movement_intended_limit'):
                resources[r['resource'],r['start_sec']][r['kind']]=r
        rows=[]
        for j,start in enumerate((2400,2550,2700)):
            incoming={g:Counter() for g in origins}
            for t in response['transfers']:
                if start<=t['start_sec']<start+150:
                    for g,o in origins.items():
                        if t['target']=='storage:'+o and t['source']!=t['target']:
                            incoming[g][t['source'] or 'exogenous_boundary']+=t['vehicles']
            minima={}
            for m in sorted(interests):
                sums=Counter(); peak=0.
                for (name,t),kinds in resources.items():
                    if name!=m or not start<=t<start+150:continue
                    q=kinds['urban_movement_stock']['available_veh'];r=kinds['urban_movement_intended_limit']
                    request,accepted=r['available_veh'],r['accepted_total_veh']
                    assert -1e-8<=accepted<=request+1e-8 and request<=q+1e-8
                    peak=max(peak,q);sums['requested_veh']+=request;sums['accepted_veh']+=accepted
                    if request>1e-8:
                        sums['positive_requests']+=1
                        sums['ready_stock_bound']+=int(abs(request-q)<=1e-8)
                        sums['below_ready_stock']+=int(request<q-1e-8)
                        sums['later_receiver_limited']+=int(accepted<request-1e-8)
                minima[m]=dict(sums,peak_ready_veh=peak,rate_veh_h=network['movement_capacity_by_movement_veh_h'][m])
            rows.append(dict(start_sec=start,incoming_by_source={g:dict(v) for g,v in incoming.items()},minima=minima,
                local_balance={g:stock['local'][g]['bins'][j] for g in origins}))
        model[arm]=rows
        del response
    for p in (Path(__file__),H.parent/'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md'):a.pin(p)
    out=dict(status='complete_read_only_diagnosis',physical_volumes=volumes,native=observed,model=model,
        source_pins=a.PINS,new_forecasts=0,native_runs=0,fzp_scans=0,future_inputs=False,
        limitations=['Derived net entries subtract any unobserved deletion/loss; do not call them directly measured arrivals.',
          'Model origins include upstream and half-connector inventories; native RD-to-head stocks use explicit physical boundaries. Do not compute stock errors between them.',
          'SC109 shared head passages are not turn-specific SC109-to-SC16 flows.',
          'Ready-stock-bound and below-stock requests distinguish supply from request constraints only; red phases are not failures.'])
    (HERE/'assessment.json').write_text(json.dumps(out,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    for arm,rows in observed.items():
        for j,row in enumerate(rows):
            print(arm,row['start_sec'], {g:dict(actual_head=row['heads'][g]['crossings'],predicted_head=round(model[arm][j]['local_balance'][g]['outgoing_veh'],2),native_net_entries=row['balance'].get(g,{}).get('inferred_net_entries_minus_losses'),model_incoming=round(model[arm][j]['local_balance'][g]['incoming_veh'],2)) for g in origins})
    print('DONE: no new forecasts/native/FZP; pins',len(a.PINS))

if __name__=='__main__':main()
