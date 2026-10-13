"""Past-only achieved GREEN throughput floor, not fitted saturation capacity."""
from pathlib import Path
import hashlib
import json
import math
import pickle
import xml.etree.ElementTree as ET

from evaluation.controllers import obs150_contract as oc
from diagnostics.validate_native_signal_record import read_ldp_frames

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
FOLDER=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')
PINS={}


def raw(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b


def main():
    assert not (HERE/'support.json').exists()
    cfg,_,_=pickle.loads(raw(A/'citysplit287/forecast2400/initial.pickle'))
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree=ET.fromstring(raw(network))
    heads=[h.attrib for h in tree.findall('./signalHeads/signalHead') if h.get('lane').split()[0]=='21']
    assert len(heads)==2 and {h['sg'] for h in heads}=={'108 2'}
    assert {h['lane'] for h in heads}=={'21 1','21 2'}
    connector=next(x for x in tree.findall('./links/link') if x.get('no')=='10112')
    assert connector.find('fromLinkEndPt').get('lane').split()[0]=='21'
    assert connector.find('toLinkEndPt').get('lane').split()[0]=='174'
    route=cfg.network.control_area_routes['movement:SC108_W_to_E_SC109']
    assert len(route['physical_turns'])==1 and route['physical_turns'][0]['connector']=='10112'
    ldp_path=FOLDER.parent/'vissim_eval/sdmpc31_g_2400_hold_s29_108_001.ldp'
    raw(ldp_path)
    clock=read_ldp_frames({108:ldp_path},{108:list(range(1,9))},1800,2400)['frames']
    blocks=[]
    for end in (1950,2100,2250,2400):
        state=json.loads(raw(FOLDER/f'state_{end:06}.json'))
        b=oc.load_bundle(state);w=oc.assign_window(b.obs,b.mer_rows)
        dets,_=oc.read_detector_csv(b.obs['detector_config']['path'],b.obs['detector_config']['sha256'])
        raw(b.obs['detector_config']['path']);raw(FOLDER/b.obs['mer']['chunk'])
        wanted=[d for d in dets if d.role=='head' and d.link==21 and oc.parse_head_ref(d.ref)[2]=='2']
        assert len(wanted)==2
        known=[(r.veh,r.t_entry) for d in wanted for r in w.entries[d.dcp_no]]
        # Drop both one-second switch boundaries: no ambiguous-state events fitted.
        eligible_seconds=[t for t in range(end-150,end) if clock[t]['108:2']=='GREEN' and clock[t+1]['108:2']=='GREEN']
        eligible=set(eligible_seconds)
        ev=[(v,t) for v,t in known if t<2400 and math.floor(t) in eligible]
        assert eligible_seconds
        blocks.append(dict(start=end-150,end=end,green_interior_sec=len(eligible),known_head_count=len(known),
            eligible_count=len(ev),unresolved_tail=sum(w.tails[d.dcp_no] for d in wanted),
            achieved_rate_veh_h=len(ev)*3600/len(eligible),eligible_events=ev))
    # A single pooled, achieved-throughput floor; not a grid or future loss fitting.
    rate=sum(r['eligible_count'] for r in blocks)*3600/sum(r['green_interior_sec'] for r in blocks)
    old=cfg.network.movement_capacity_by_movement_veh_h['SC108_W_to_E_SC109']
    raw(Path(__file__))
    result=dict(status='past_only_service_floor',cutoff_sec=2400,training_window=[1800,2400],movement='SC108_W_to_E_SC109',
        old_rate_veh_h=old,achieved_floor_veh_h=rate,blocks=blocks,heads=heads,
        physical_route=dict(from_link='21',connector='10112',to_link='174',phase='SC108_p3'),source_pins=PINS,
        future_inputs=False,fzp_scans=0,native_runs=0,
        limitations=['Achieved GREEN-only flow is a lower bound on capacity, not a saturated-service estimate.',
                     'No queued-prefix evidence is assumed. Idle green is included and can make this floor conservative.',
                     'One existing seed/past window; requires separate forward response checks.'])
    (HERE/'support.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PAST',old,rate,[(r['start'],r['eligible_count'],r['green_interior_sec']) for r in blocks])


if __name__=='__main__':main()
