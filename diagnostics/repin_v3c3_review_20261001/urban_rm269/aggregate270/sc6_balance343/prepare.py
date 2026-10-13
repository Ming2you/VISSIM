"""Pin SC6 east unique through heads; preserve the existing v11 contract."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
read=lambda p:json.loads(Path(p).read_bytes())
def pin(p):
    p=Path(p);return dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def main():
    from evaluation.controllers import signal_head_observation as observer,vissim_stackelberg_adapter as adapter
    source=A.parent/'sc6_queue/head_resources.json';doc=read(source)
    assert doc['schema']=='physical-head-resource-join/v11'
    network=ROOT/doc['network']['path'];root=ET.fromstring(network.read_bytes())
    proof=A.parent/'sc6_queue/head_lane_support.json';spec=read(proof)['movements']['SC6_E_SC104_to_W_SC5']
    mapping=ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'
    d=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1032']")
    r=d.find("./vehRoutSta/vehicleRouteStatic[@no='3']")
    path=[d.get('link')]+[n.get('key') for n in r.findall('./linkSeq/intObjectRef')]+[r.get('destLink')]
    doc['schema']='physical-head-resource-join/v13'
    doc['resources']['10200']=dict(group='1220021201|p3',
        heads=observer.physical_groups(str(network),adapter.load_signal_group_actuation_plan())[('1220021201','p3')],
        mode='regular_unique',members={'SC6_E_SC104_to_W_SC5':spec['expected_spec']},
        receiver='SC6_to_SC5',target_link=spec['to_link'],proof=pin(proof),
        disjoint_consumers={'SC6_E_SC104_to_N_SC103':dict(
            expected_spec=dict(kind='internal',signal='SC6',phase='SC6_p3',origin='SC104_to_SC6',receiving_link='SC6_to_SC103'),
            path=['1220021201','10142','96'],native_route='1032:3',native_route_path=path,
            destination_mapping=pin(mapping),upstream_of_head=True)})
    out=HERE/'head_resources.json';assert not out.exists()
    out.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PREPARED',out)
if __name__=='__main__':main()
