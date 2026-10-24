"""One physical two-lane head resource, existing causal four-window support."""
import copy,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    p=HERE/name;assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    base=H/'native_beta/config.json'; cfg=read(base)
    old=ROOT/cfg['urban']['capacity']['head_resource_contract'];doc=read(old)
    assert doc['schema']=='physical-head-resource-join/v11' and '10286' not in doc['resources']
    initial=H/'native_beta/init2400_checked/network.json';net=read(initial)
    name='SC109_W_SC108_to_N_SC16';spec=net['urban_movements'][name]
    expected={k:spec[k] for k in ('kind','signal','phase','origin','receiving_link')}
    authority={'network':{k:{'movement:'+name if k=='control_area_routes' else name:net[k]['movement:'+name if k=='control_area_routes' else name]}
                   for k in ('urban_movements','control_area_routes')}}
    save('authority.json',authority)
    pin=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
    proof=dict(schema='head-queue-lane-support/v1',network=doc['network'],authority=pin(HERE/'authority.json'),
        movements={name:dict(expected_spec=expected,from_link='173',connector='10286',to_link='1220009502',lanes=[4,5])},
        scope='Service ownership only. Existing queue projection is retained. No turn/seed/time bonus or fitted rate.')
    save('lane_support.json',proof)
    tree=ET.parse(ROOT/doc['network']['path'])
    heads=[]
    for n in tree.findall('./signalHeads/signalHead'):
        if n.get('no') in ('1090501','1090502'):
            link,lane=n.get('lane').split();sc,sg=n.get('sg').split()
            heads.append(dict(head_id=n.get('no'),link=link,lane=int(lane),position_m=float(n.get('pos')),sc=sc,sg=sg))
    assert len(heads)==2 and {n['lane'] for n in heads}=={4,5}
    doc['schema']='physical-head-resource-join/v12'
    doc['resources']['10286']=dict(group='173|p4',heads=heads,mode='regular_unique',members={name:expected},
        receiver='SC109_to_SC16',target_link='1220009502',green_exposure_windows=4,proof=pin(HERE/'lane_support.json'))
    doc['scope']+=' Add SC109 west-left two-lane10286 only, reusing four past windows and unchanged exposure/count thresholds.'
    save('head_resources.json',doc)
    cfg['urban']['capacity']['head_resource_contract']=(HERE/'head_resources.json').relative_to(ROOT).as_posix()
    save('config.json',cfg)
    core=ROOT/'evaluation/controllers/head_service_resources.py'
    (HERE/'head_service_resources.before.py.txt').write_bytes(core.read_bytes())
    save('plan.json',dict(status='prepared_not_validated',reason='Past24/26/28/23sec green excluded by30sec single-window threshold; native future15-18left vehicles versus model4.6-4.8 with ready queue and no downstream rejection.',
        max_forecasts=3,new_full_selections=0,native_runs=0,coefficients_fitted=0,
        evaluation=['Two canonical initialization2400/3300, only observed service changes',
          'Two fixed450 actual commands2400 and one actual first150 at3300; reuse native and prior model outputs'],
        preserve=['Same demand, initial physical inventory,450horizon,Omega701TTT,terminalOFF,actual commands,NP/NUF caps',
          'No active frozen native queue changes; no fitting from future head counts'],
        source_pins={str(p):sha(p) for p in (Path(__file__),base,old,initial,H/'source_chain/assessment.json',
            HERE/'authority.json',HERE/'lane_support.json',HERE/'head_resources.json',HERE/'config.json')}))
    print('Prepared one SC109 west-left resource; coefficients/native/forecasts0.')

if __name__=='__main__':main()
