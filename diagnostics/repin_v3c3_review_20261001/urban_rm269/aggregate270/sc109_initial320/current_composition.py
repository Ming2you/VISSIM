"""Audit known current route loss, independent of future departures."""
from collections import Counter
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308.inputs import inputs,RAW

HERE=Path(__file__).resolve().parent;A=HERE.parent

def main():
    out=HERE/'current_composition.json';assert not out.exists()
    cfg,state,raw,frame,network,inside,lanes=inputs()
    tree=ET.fromstring(network)
    provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    members={'173','174','10280','10281','10285'}
    records=[v for v in raw['vehicle_records']['records'] if str(v['link_no']) in members]
    ready=set()
    for link in members:
        expected=sum(n for key,n in provenance.get(link,{}).items() if key.startswith('movement:'))
        if not expected:continue
        rows=[v for v in records if str(v['link_no'])==link]
        group=set()
        for lane in {v['lane_no'] for v in rows}:
            count=lanes.get((link,str(lane)),0.)
            front=sorted((v for v in rows if v['lane_no']==lane),key=lambda v:-v['position_m'])[:int(count)]
            assert len(front)==count and all(v['stopped'] for v in front)
            group.update(v['veh_no'] for v in front)
        assert len(group)==expected
        ready.update(group)
    current={int(r[0]):r for r in frame['vehicles']}
    rows=[]
    for v in records:
        r=current[v['veh_no']];turn='unknown';path=None
        if all(x is not None for x in r[6:9]):
            assert r[8]=='STATIC'
            dec,rid=str(int(r[6])),str(int(r[7]))
            d=tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{dec}']")
            n=d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{rid}']")
            path=[d.get('link'),*[x.get('key') for x in n.findall('./linkSeq/intObjectRef')],n.get('destLink')]
            assert path.count('173')==1
            connector=path[path.index('173')+1]
            turn={'10285':'through','10286':'left'}[connector]
            index=path.index(str(v['link_no']))
            assert r[9] is None or str(int(r[9]))==path[index+1]
        else:
            assert all(x is None for x in r[6:10])
        rows.append(dict(vehicle=v['veh_no'],link=str(v['link_no']),lane=v['lane_no'],
                         ready=v['veh_no'] in ready,known_turn=turn,current_route=r[6:9],physical_route=path))
    counts={name:dict(Counter(x['known_turn'] for x in rows if x['ready']==flag)) for name,flag in [('ready',True),('residual',False)]}
    before={k:v for k,v in state.urban_movement_queue.items() if k in ('SC109_W_SC108_to_E','SC109_W_SC108_to_N_SC16')}
    fp=RAW.parent/raw['obs150']['frames']['current']['path']
    files=[Path(__file__),RAW,fp,A/'sc12_phase305/current_projection.json',
           A/'citysplit287/forecast2400/initial.pickle',Path(raw['network_path'])]
    # raw network_path can refer to a frozen copy; pin the actually inspected network.
    network_path=HERE.parents[4]/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    files[-1]=network_path
    report=dict(status='confirmed_known_current_turns_lost_in_ready_queue',at_sec=2400,counts=counts,
                original_model_ready=before,vehicles=rows,source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                future_observation_inputs=False,new_predictions=0,new_fits=0,production_changes=0,
                limitation='Unknown current routes remain unknown; current lane alone is not future destination proof. Post-head source ownership remains a separate limitation.')
    assert counts['ready']=={'left':10} and sum(counts['residual'].values())==43
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('CURRENT_TURNS',counts,'MODEL_READY',before)

if __name__=='__main__':main()
