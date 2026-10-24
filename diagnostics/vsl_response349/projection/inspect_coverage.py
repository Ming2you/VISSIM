import json,pickle,xml.etree.ElementTree as ET
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc105_initial340 import candidate as terminal
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as gate
BASE=Path('E:/VISSIM_analysis/20261011_vsl_response349')
out={}
for name,component in [('window2250',terminal),('window4500',gate),('optimized3300',terminal)]:
    folder=BASE/f'projection_{name}_v2'
    label='gate' if component is gate else 'terminal'
    path=folder/f'{label}_initialization_inputs.pickle'
    if not path.exists():continue
    cfg,state,raw,frame,net,lanes=pickle.loads(path.read_bytes())
    root=ET.fromstring(net);movements=component.MOVS if component is gate else component.MOVES
    keys={'storage:'+component.TARGET,*('movement:'+m for m in movements)}
    prov=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    owners={k:v for k,v in prov.items() if any(v.get(key,0)>0 for key in keys)}
    rows=[]
    for row in frame['vehicles']:
        link=str(int(row[1]))
        if link not in owners:continue
        native=None
        if row[6] is not None:
            d=root.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{int(row[6])}']")
            r=d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(row[7])}']")
            full=[d.get('link'),*[n.get('key') for n in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
            native=full[full.index(link):]
        rows.append(dict(id=row[0],link=link,lane=row[2],pos=row[3],speed=row[4],native=native))
    out[name]=dict(owners=owners,vehicles=rows)
print(json.dumps(out,indent=2))
