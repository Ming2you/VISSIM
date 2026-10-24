"""One streaming FZP pass: actual sampled crossings after each F_E merge.

The two meter branches have an off-ramp between them, so summed meter flow
divided by a remote section's discharge is not a conserved cohort fraction.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.measure_control_area import read_fzp_frames, sha256


def main():
    run=ROOT/'evaluation/runs/codex_n7_pure_s13_20260910'
    path=next((run/'vissim_eval').glob('*.fzp'))
    network=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    tree=ET.parse(network)
    links={x.attrib['no']:x for x in tree.getroot().find('links')}
    selected={'10639':('70','2',1876.292),'10681':('68','2',2165.429)}
    for connector,(source,target,pos) in selected.items():
        node=links[connector]
        f=node.find('fromLinkEndPt');t=node.find('toLinkEndPt')
        assert f.attrib['lane'].split()[0]==source and t.attrib['lane'].split()[0]==target
        assert abs(float(t.attrib['pos'])-pos)<0.000501
        selected[connector]=(source,target,float(t.attrib['pos']))
        matches=[n.attrib['no'] for n in links.values() if n.find('fromLinkEndPt') is not None and
                 n.find('fromLinkEndPt').attrib['lane'].split()[0]==source and n.find('toLinkEndPt').attrib['lane'].split()[0]==target]
        assert matches==[connector], (source,target,matches)
    sections={'after_'+key:value[2]+1.0 for key,value in selected.items()}
    fw={'74','10699','2','10613','119','10702','24'}
    keep=fw|set(selected)|{'70','68'}
    previous={};counts=defaultdict(Counter);method=Counter();allcounts=Counter()
    for frame in read_fzp_frames(path):
        if frame.time_sec>5250:break
        current={}
        for vehicle_id,v in frame.vehicles.items():
            if v.link not in keep:continue
            prior=previous.get(vehicle_id)
            tag=prior[2] if prior and prior[0] in fw else 'other_or_unseen'
            mode=prior[3] if prior and prior[0] in fw else 'not_F_E'
            entered=None
            if v.link in selected:
                tag=v.link;mode='observed_connector'
            elif v.link=='2' and prior and prior[0] in selected:
                tag=prior[0];mode='observed_connector';entered=selected[tag][2]
            elif v.link=='2' and prior and prior[0] in {'70','68'}:
                tag=next(k for k,spec in selected.items() if spec[0]==prior[0])
                mode='unique_source_target_inferred_connector';entered=selected[tag][2]
            elif v.link in {'74','10699'} or v.link=='2' and v.position_m<selected['10639'][2]:
                tag='upstream_mainline';mode='observed_upstream'
            if v.link=='2' and prior and frame.time_sec>=900:
                for key,cut in sections.items():
                    same=prior[0]=='2' and prior[1]<cut<=v.position_m
                    entry=entered is not None and entered<cut<=v.position_m
                    if same or entry:
                        time_bin=int(frame.time_sec//150)*150
                        if 900<=time_bin<5250:
                            counts[key,time_bin][tag]+=1
                            method[key, 'same_link_bracket' if same else 'merge_entry_bracket']+=1
                            allcounts[key,tag,mode]+=1
            current[vehicle_id]=(v.link,v.position_m,tag,mode)
        previous=current
    result={'window_sec':[900,5250],'section_physical_link':'2','sections_position_m':sections,
        'source_fzp':str(path.relative_to(ROOT)),'source_fzp_sha256':sha256(path),
        'network_sha256':sha256(network),'bin_assignment':'upper observed frame time; at most the 5-second sampling interval timing uncertainty',
        'limitations':['Cohort label uses observed ramp connectors or a verified unique source→target connector skipped between samples. The latter is inference and is separately counted.',
                      'A ramp entry and exit both missed inside one sample can remain unclassified; other_or_unseen is not asserted to be native mainline.',
                      'Ratios describe this controlled trajectory and section. They are not fixed actuator authority or a hypothetical effect of full closure.',
                      '10682 diverges between the two sections, so upstream ramp vehicles that leave before the second section are properly excluded from its ramp cohort.'],
        'by_section':{}}
    for key in sections:
        table=[];total=Counter()
        for t in range(900,5250,150):
            c=counts[key,t];total.update(c)
            table.append({'start_sec':t,'end_sec':t+150,'total_crossings':sum(c.values()),'cohort_counts':dict(c),
                'F_E_ramp_cohort_fraction':sum(c[k] for k in selected)/sum(c.values()) if c else None})
        result['by_section'][key]={'total_crossings':sum(total.values()),'cohort_counts':dict(total),
            'F_E_ramp_cohort_fraction':sum(total[k] for k in selected)/sum(total.values()),
            'methods':{kind:n for (section,kind),n in method.items() if section==key},
            'cohort_assignment_evidence':[{'cohort':tag,'assignment':mode,'count':n} for (section,tag,mode),n in allcounts.items() if section==key],
            'bins':table}
    target=ROOT/'diagnostics/f_merge_actual_share.json'
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({key:{k:v for k,v in value.items() if k!='bins'} for key,value in result['by_section'].items()},indent=2))


if __name__=='__main__':main()
