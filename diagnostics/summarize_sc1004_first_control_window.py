"""Summarize pinned selected frames only; never reopen native FZP."""
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagnostics/sc1004_first_control_window'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    if (OUT/'followup_evidence.json').exists():raise ValueError('Preserve prior result')
    diagnosis=load(OUT/'diagnosis.json')
    result={'schema':'sc1004-window-followup/v1','diagnosis_sha256':sha(OUT/'diagnosis.json'),
            'producer_sha256':sha(__file__),'runs':{}}
    for label,run in diagnosis['runs'].items():
        cache=Path(run['fzp']['selected_cache'])
        if sha(cache)!=run['fzp']['selected_cache_sha256']:raise ValueError('Selected frames changed')
        with gzip.open(cache,'rt',encoding='utf-8') as stream:frames=json.load(stream)
        raw_path=ROOT/'evaluation/runs'/run['run']/('decisions_'+run['run'])/'state_001050.json'
        raw=load(raw_path)
        raw_heads=[h for h in raw['local_observation']['signal_observation_window']['heads'] if h['link']=='71']
        raw_summary={sg:{'green_sec':next(h['green_sec'] for h in raw_heads if h['sg']==sg),
            'qualified_crossings':sum(h['qualified_crossings'] for h in raw_heads if h['sg']==sg)} for sg in ('2','5')}
        for sg,r in raw_summary.items():
            if r['green_sec']!=run['sg71_summary'][sg]['green_sec'] or r['qualified_crossings']!=run['sg71_summary'][sg]['qualified_head_crossings']:
                raise ValueError('Independent COM/FZP head evidence differs')
        before=len(run['endpoint71']['900']);after=len(run['endpoint71']['1050'])
        departures=[e for e in run['road_exits'] if e['link']==71]
        residual=before+len(run['arrivals71'])-len(departures)-after
        if residual!=0:raise ValueError('Observed source stock did not close')
        paths=[]
        for history in run['selected_endpoint_histories']['end420_stopped']:
            rows=history['samples'];changes=[r for i,r in enumerate(rows) if i==0 or r[1]!=rows[i-1][1]]
            previous=[r[1] for r in changes]
            source='127' if 127 in previous else '329' if 329 in previous else '72' if 72 in previous else 'unresolved'
            paths.append({'vehicle':history['vehicle'],'source_evidence':source,
                'ordered_observed_path':[[r[0],r[1]] for r in changes],
                'arrival420_sec':next(r[0] for r in rows if r[1]==420),
                'first_stopped420_sec':history['first_stopped_sec_by_link']['420'],'final_record':rows[-1]})
        blocker=[[int(t),*row['4725']] for t,row in frames.items() if '4725' in row]
        lane3_green_stopped=[r for r in blocker if r[1]==71 and r[2]==3 and r[4]<=1 and any(a<=r[0]<b for a,b in run['green_windows']['1004:2'])]
        connector={}
        for link in (10643,10682):
            enter=exit_=0
            for sec in range(900,1050):
                old,new=frames[str(sec)],frames[str(sec+1)]
                enter+=sum(row[0]==link and (no not in old or old[no][0]!=link) for no,row in new.items())
                exit_+=sum(row[0]==link and (no not in new or new[no][0]!=link) for no,row in old.items())
            connector[str(link)]={'observed_entries':enter,'observed_exits':exit_,'inference':'none; 1s same-ID connector presence transitions only'}
        arrival_bins=[{'start':a,'end':b,'arrivals':sum(a<=e['lower_sec']<b for e in run['arrivals71'])}
            for a,b in ((900,945),(945,966),(966,975),(975,991),(991,1020),(1020,1045),(1045,1050))]
        result['runs'][label]={'raw1050_sha256':sha(raw_path),'raw_head71':raw_summary,
            'stock71':{'initial':before,'arrivals':len(run['arrivals71']),'departures':len(departures),'final':after,'residual':residual,
                       'final_stopped':sum(row['record'][3]<=1 for row in run['endpoint71']['1050'])},
            'origins71':dict(Counter(e['origin_evidence'] for e in run['arrivals71'])),
            'destinations71':dict(Counter(str(e['to']) for e in departures)),
            'arrival_bins':arrival_bins,'connector_transitions':connector,
            'lane3_blocker4725_samples':blocker,'lane3_blocker_green_stopped_seconds':len(lane3_green_stopped),
            'cohort420':paths,'cohort420_by_source':dict(Counter(r['source_evidence'] for r in paths))}
    run=ROOT/'evaluation/runs'/diagnosis['runs']['beta300']['run']
    error=run/'vissim_simulation_001.err';text=error.read_bytes().decode('cp949')
    lines=[row.strip() for row in text.splitlines() if re.search(r'vehicle 4725\b',row)]
    if len(lines)!=1:raise ValueError('Expected exact independent native removal warning')
    network=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx';tree=ET.parse(network).getroot()
    decision=next(d for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic') if d.get('no')=='1126')
    route=next(r for r in decision.findall('./vehRoutSta/vehicleRouteStatic') if r.get('no')=='1')
    result['native_removal4725']={'source_path':str(error),'sha256':sha(error),'verbatim_warning':lines[0],
        'native_decision':dict(decision.attrib),'chosen_route':dict(route.attrib),
        'chosen_path':[decision.get('link'),*[n.get('key') for n in route.findall('./linkSeq/intObjectRef')],route.get('destLink')],
        'network_sha256':sha(network),
        'scope':'Native warning timestamps deletion at973; FZP last observation is973 and first absence974. This event is a removal, not a completed outward crossing.'}
    (OUT/'followup_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:{'stock71':v['stock71'],'connectors':v['connector_transitions'],'cohort420':v['cohort420_by_source'],
                         'blocker_green_stopped':v['lane3_blocker_green_stopped_seconds']} for k,v in result['runs'].items()}))


if __name__=='__main__':main()
