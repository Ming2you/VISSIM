"""Saved cross-sectional lane evidence around the actual diverge; targets only."""
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
PINS={}


def read(path):
    path=Path(path);blob=path.read_bytes()
    PINS[str(path)]=hashlib.sha256(blob).hexdigest()
    return json.loads(blob)


def main():
    assert not (OUT/'approach_lane_evidence.json').exists()
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    contract=read(ROOT/'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
    mapping_path=ROOT/contract['mapping']['path'];mapping=read(mapping_path)
    assert PINS[str(mapping_path)]==contract['mapping']['sha256']
    runtime=route.compile_inventory(contract,mapping)
    network=ROOT/contract['network']['path'];blob=network.read_bytes()
    PINS[str(network)]=hashlib.sha256(blob).hexdigest()
    assert PINS[str(network)]==contract['network']['sha256']
    tree=ET.fromstring(blob)
    geometry={}
    for no in (2,10613,10481,119):
        link=tree.find(f"./links/link[@no='{no}']")
        nlanes=len(link.findall('./lanes/lane'))
        source=link.find('fromLinkEndPt');dest=link.find('toLinkEndPt')
        geometry[str(no)]=dict(lanes=nlanes,source=None if source is None else dict(source.attrib),destination=None if dest is None else dict(dest.attrib))
    assert geometry['10613']['source']['lane']=='2 2' and geometry['10613']['lanes']==3
    assert geometry['10481']['source']['lane']=='2 1' and geometry['10481']['lanes']==2
    cases={
        'hold':Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29'),
        'single90':Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/vsl90/decisions_sdmpc31_g_2250_vsl90_s29'),
        'selected':Path('D:/VISSIM_runs/20261016_vsl_multizone2250_repaired_s29/selected/decisions_sdmpc31_g_2250_selected_s29')}
    observed=read(OUT/'summary.json')['native_snapshots']
    rows=[]
    for name,folder in cases.items():
        for step,t in enumerate((2250,2400,2550,2700)):
            raw=read(folder/f'state_{t:06d}.json')
            assert raw['vehicle_records']['complete'] and raw['sim_sec']==t
            groups=defaultdict(list)
            for v in raw['vehicle_records']['records']:
                link=str(v['link_no'])
                if link not in runtime['physical']:continue
                fw,_,cell=route._position(runtime,link,v['position_m'])
                if fw=='FW_E' and 14<=cell<=18:
                    assert link=='2' and int(v['lane_no']) in (1,2,3,4)
                    groups[(cell,int(v['lane_no']))].append(v)
            for cell in range(14,19):
                assert sum(len(groups[(cell,lane)]) for lane in (1,2,3,4))==observed[name][step]['n']['FW_E'][cell]
                for lane in (1,2,3,4):
                    vehicles=groups[(cell,lane)]
                    speeds=[v['speed_kph'] for v in vehicles]
                    mean=math.fsum(speeds)/len(speeds) if speeds else None
                    rows.append(dict(case=name,time_sec=t,cell=cell,lane=lane,n=len(speeds),
                                     speed_mean=mean,speed_sd=(math.fsum((v-mean)**2 for v in speeds)/len(speeds))**.5 if speeds else None,
                                     n_under40=sum(v<40 for v in speeds),n_stopped=sum(v['stopped'] for v in vehicles)))
    for path in (Path(__file__),Path(route.__file__)):
        PINS[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    for path,h in PINS.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h
    result=dict(status='completed_cross_sectional_lane_audit',geometry=geometry,rows=rows,source_pins=PINS,
                new_native=0,new_forecasts=0,new_fzp_scans=0,production_edits=0,
                limitations=['Lane1 has no through continuation; lane2 has both through and exit connectivity. Connectivity is not observed route intent or observed lane-changing frequency.',
                             '150s snapshots are cross-sections, not individual vehicle acceleration or exact inter-snapshot lane changes.',
                             'The aggregate lane-drop term is not proved erroneous solely by diverge connectivity.'])
    (OUT/'approach_lane_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'geometry':geometry,'rows':len(rows),'selected_end18':[r for r in rows if r['cell']==18 and r['time_sec']==2700]},indent=2))


if __name__=='__main__':main()
