"""Prepare one cached lane-specific junction diagnostic, no fitted coefficient."""
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]


def main():
    assert not (HERE/'profiles.json').exists()
    source=R/'lane_interaction110/frames.json.gz'
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    data=json.loads(gzip.decompress(source.read_bytes()))
    links={int(x.get('no')):x for x in ET.fromstring(network.read_bytes()).findall('./links/link')}
    exit_pos=float(links[10483].find('fromLinkEndPt').get('pos'))
    merge_pos=float(links[10490].find('toLinkEndPt').get('pos'))
    face=data['bounds_m'][21]-data['offsets_m']['119']
    assert exit_pos<face<merge_pos
    assert links[10483].find('fromLinkEndPt').get('lane')==links[10490].find('toLinkEndPt').get('lane')=='119 1'
    result={};observations={}
    for arm in ('release','release_vsl90'):
        frames=data['cases'][arm]['frames'];profile={}
        groups={False:Counter(),True:Counter()}
        for i,f in enumerate(frames):
            t=round(f['t']-.1);rows=f['rows']
            blocked=any(r['link']==119 and r['lane']==1 and r['speed']<5
                and r['pos']-float(r['LENGTH'])<=exit_pos<=r['pos'] for r in rows.values())
            through=[r for r in rows.values() if r['cell']==20 and r['NEXTLINK\\NO']=='10702']
            in_lane=sum(r['lane']==1 for r in through)
            share=in_lane/len(through) if through else 0.
            profile[str(t)]=dict(blocked=blocked,through_n=len(through),through_lane1_n=in_lane,through_lane1_share=share)
            assert 0<=share<=1
            if i==len(frames)-1:continue
            nxt=frames[i+1]['rows'];g=groups[blocked];g['intervals']+=1
            for vid,r in rows.items():
                z=nxt.get(vid)
                if r['link']==119 and z and z['link']==119 and r['pos']<face<=z['pos']:
                    g['mainline_crossings']+=1
                    g['lane1_crossings']+=int(r['lane']==1)
            g['through_stock_samples']+=len(through);g['lane1_through_stock_samples']+=in_lane
        result[arm]=profile
        observations[arm]={str(b):dict(g,
            mean_mainline_crossings_per5s=g['mainline_crossings']/g['intervals'],
            mean_lane1_crossings_per5s=g['lane1_crossings']/g['intervals']) for b,g in groups.items()}
    assert result['release']['2700']==result['release_vsl90']['2700']
    protocol=dict(previous_turn='PROGRESS122: corrected fixed-parameter inference; no assertion of a calibrated performance ceiling.',
        hypothesis='A body blocking the shared lane constrains through sending as well as exit entry; test its physical gain path with fixed cell parameters before deciding a calibration design.',
        exact_geometry=dict(link=119,exit10483_m=exit_pos,cell20_21_face_m=face,merge10490_m=merge_pos),
        equations=['S_through_new20=(1-blocked*observed_current_lane1_through_share)*S_through_old20',
            'S_exit10483=min(original_sending,original_storage_supply) when open;0 when blocked',
            'Original accepted flows, class conservation, speed update and urban/ramp waiting remain active.'],
        profile_holding_sec=5,phase_offset_sec=.1,autonomous=False,
        future_observation_inputs=['body-block binary','current cell20 through-population share in lane1'],
        fitted_parameters=0,budget=dict(new450=2,reused_baseline450=2,reused_branch_only450=2,native=0,fzp=0),
        inference_limits=['Conditional fixed-parameter test only. Not a calibrated structure or ceiling on dynamics-plus-cell recalibration.',
            'Population share approximates within-cell shared-lane service share; not a calibrated capacity or exact flow share.',
            'A5s snapshot of blocked body does not prove continuous closure for5s; no future MER flow is forced.',
            'Mainline point crossings are observed adjacent-frame lower bounds, including lane changes between snapshots.',
            'Old121 field after_merge_face actually lies1.407m BEFORE the merge and1.407m AFTER the exit. Values preserved; name corrected here.'],
        source_sha={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,network,R/'junction_release121/probe.py')})
    for name,obj in [('profiles.json',result),('protocol.json',protocol),('observations.json',observations)]:
        (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(geometry=protocol['exact_geometry'],observations=observations),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
