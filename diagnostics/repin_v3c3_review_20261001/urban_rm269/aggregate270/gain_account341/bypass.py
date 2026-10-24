"""Geometry and native red-crossing evidence; shared lane is not free capacity."""
from pathlib import Path
import json,subprocess,xml.etree.ElementTree as ET
from diagnostics.validate_native_signal_record import read_ldp_frames
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gain_account341 import audit
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.city_loss322.audit import RUNS

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
M='SC6_E_SC104_to_N_SC103'

def main():
    assert not (HERE/'bypass.json').exists()
    netpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    root=ET.fromstring(audit.raw(netpath));links={l.get('no'):l for l in root.findall('./links/link')}
    node=links['10142'];frm=node.find('fromLinkEndPt');source,lane=frm.get('lane').split();lane=int(lane);pos=float(frm.get('pos'))
    assert source=='1220021201' and lane==1 and len(node.findall('./lanes/lane'))==1
    heads=[dict(h.attrib) for h in root.findall('./signalHeads/signalHead') if h.get('lane')==f'{source} {lane}']
    assert heads and all(float(h['pos'])>pos and h['sg']=='6 6' for h in heads)
    assert not any(h.get('lane').split()[0]=='10142' for h in root.findall('./signalHeads/signalHead'))
    sharing=[]
    for k,l in links.items():
        f=l.find('fromLinkEndPt')
        if f is None or k=='10142' or f.get('lane').split()[0]!=source:continue
        lo=int(f.get('lane').split()[1])
        if lane in range(lo,lo+len(l.findall('./lanes/lane'))):sharing.append(dict(connector=k,position=float(f.get('pos')),to_link=l.find('toLinkEndPt').get('lane')))
    assert sharing
    path='diagnostics/sdmpc_n31_20260924/urban/unsignalized_turns_v3c3_20261001.json'
    blob=subprocess.check_output(['git','show','bd39205:'+path],cwd=ROOT)
    claude=json.loads(blob);found=[]
    def collect(v):
        if isinstance(v,dict):
            if v.get('movement')==M:found.append(v)
            for x in v.values():collect(x)
        elif isinstance(v,list):
            for x in v:collect(x)
    collect(claude)
    assert any(v.get('reason')=='shared_source_lane' and v.get('connector')=='10142' for v in found)
    topology=audit.read(A/'exit_timing309/assessment.json')['native_observed_pair_topology']
    native={}
    for arm,folder in RUNS.items():
        stem=folder.name.removeprefix('decisions_')
        ld=read_ldp_frames({6:folder.parent/'vissim_eval'/f'{stem}_6_001.ldp'},{6:list(range(1,9))},2400,2850)
        audit.PINS.update({p:x['sha256'] for p,x in ld['pins'].items()})
        events=audit.read(Path('E:/VISSIM_analysis/20261010_exit_timing309')/(arm+'.json.gz'))['events']
        counts={'green_interval':0,'red_interval':0,'mixed_or_uncertain_interval':0};samples=[]
        for e in events:
            if e['kind']!='observed_exit' or not 2400<=e['mid_sec']<2850:continue
            mapping=topology[e['from_link']+'->'+e['to_link']]
            if mapping['edge']!=[source,'10142']:continue
            # Expand the midpoint by3s for the5s observation bracket. Only
            # classify red/green when all sampled states throughout agree.
            times=range(int(e['mid_sec'])-3,int(e['mid_sec'])+4)
            phases={ld['frames'][t]['6:6'] for t in times if t in ld['frames']}
            covered=all(t in ld['frames'] for t in times)
            category=('red_interval' if covered and phases=={'RED'} else
                      'green_interval' if covered and phases=={'GREEN'} else 'mixed_or_uncertain_interval')
            counts[category]+=1
            if category=='red_interval' and len(samples)<5:samples.append(e)
        assert sum(counts.values())==56
        native[arm]=dict(**counts,total=sum(counts.values()),red_examples=samples)
    result=dict(status='shared_lane_prehead_bypass_verified',movement=M,
        geometry=dict(source=source,lane=lane,connector='10142',departure_pos=pos,heads=heads,
            distance_before_head=min(float(h['pos']) for h in heads)-pos,shared_connectors=sharing),
        claude=dict(commit='bd39205',path=path,rows=found),native=native,source_pins=audit.PINS,
        conclusion='Direct green-only gating is inconsistent with red passage, but unrestricted unsignalized flow ignores shared through-lane blockage.',
        constraints=['Keep current lane/route, actual accepted flow, receiving and mass conservation.',
          'No coefficient fitting, new forecast, AD, native, FZP scan or production change.',
          'Red samples identify absence of a direct signal gate; they do not identify saturation flow or prove no blockage.',
          'Historical Claude network differs; local geometry and native behavior were checked on current pinned network.'])
    (HERE/'bypass.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('SC6_PREHEAD',result['geometry'])
    print('RED_PASSAGE',{a:{k:v for k,v in r.items() if k!='red_examples'} for a,r in native.items()})

if __name__=='__main__':main()
