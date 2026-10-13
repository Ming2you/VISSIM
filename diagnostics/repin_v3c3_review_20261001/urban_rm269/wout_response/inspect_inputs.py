"""Inventory closed, already recorded W_out boundary evidence."""
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.controllers import obs150_contract as oc
n=json.loads((H/'sc1_supply/forecast2400/network.json').read_bytes())
spec=n['known_legsplit_routes']
print('spec',json.dumps(spec,ensure_ascii=False))
folder=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')
raw=json.loads((folder/'state_002550.json').read_bytes());b=oc.load_bundle(raw)
detectors,_=oc.read_detector_csv(b.obs['detector_config']['path'],b.obs['detector_config']['sha256'])
print('frame_fields',oc.FRAME_ROW_FIELDS)
print('detectors',[d._asdict() if hasattr(d,'_asdict') else vars(d) for d in detectors if d.link in (68,121,10625,10629,10633,10681,10646,10773,10682)])
tree=ET.parse(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx')
for link in tree.findall('./links/link'):
    a,z=link.find('fromLinkEndPt'),link.find('toLinkEndPt')
    if a is not None and ({a.get('lane').split()[0],z.get('lane').split()[0]} & {'68','121'}):
        print('edge',link.get('no'),a.attrib,z.attrib)
