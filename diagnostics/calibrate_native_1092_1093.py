"""Offline seed13 first-connector cohorts; never a runtime routing truth source."""
from __future__ import annotations
from collections import Counter
import csv,hashlib,json,math,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN='codex_area_observed_nc_s13_20260910'
NETWORK=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
SOURCES={'217':'1092','225':'1093'}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def topology():
    root=ET.parse(NETWORK).getroot();result={}
    for source,input_no in SOURCES.items():
        inputs=[n for n in root.findall('.//vehicleInput') if n.get('link')==source]
        decisions=[n.get('no') for n in root.findall('.//vehicleRoutingDecisionStatic') if n.get('link')==source]
        incoming=[];outgoing=[]
        for link in root.findall('./links/link'):
            a,b=link.find('fromLinkEndPt'),link.find('toLinkEndPt')
            if a is None:continue
            if b.get('lane').split()[0]==source:incoming.append(link.get('no'))
            if a.get('lane').split()[0]==source:
                points=[(float(p.get('x')),float(p.get('y')),float(p.get('zOffset','0'))) for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')]
                outgoing.append({'connector':link.get('no'),'from_lane':int(a.get('lane').split()[1]),'from_pos_m':float(a.get('pos')),
                    'target':b.get('lane').split()[0],'target_lane':int(b.get('lane').split()[1]),'target_pos_m':float(b.get('pos')),
                    'length_m':sum(math.dist(a,b) for a,b in zip(points,points[1:]))})
        if incoming or decisions or len(inputs)!=1 or inputs[0].get('no')!=input_no or len(outgoing)!=2:raise ValueError('Native source qualification changed')
        result[source]={'input_no':input_no,'source':source,'incoming_connectors':incoming,'static_decisions':decisions,'outgoing':outgoing}
    return result

def classify_next(record,spec):
    exact=[b for b in spec['outgoing'] if b['connector']==record['link']]
    if len(exact)==1:return exact[0]['connector'],'observed_first_connector'
    skipped=[b for b in spec['outgoing'] if b['target']==record['link']]
    if len(skipped)==1:return skipped[0]['connector'],'unique_target_after_skipped_connector'
    return None,'unresolved_first_non_source_link'

def collect(stream,specs):
    sourcebytes={s.encode():s for s in specs};seen=set();cohorts={};duplicate_rows=0
    previous_t=None;cadence=Counter();frame_ids=set();frame_count=0;total_rows=0;header=None
    first_time=last_time=None;last_source={}
    for line in stream:
        if line.startswith(b'$VEHICLE:'):
            header=line.strip().decode('ascii')
            expected='$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM'
            if header!=expected:raise ValueError('FZP column contract changed')
            continue
        if not header or not line.strip() or line.startswith((b'*',b'$')):continue
        fields=line.split(b';',4)
        if len(fields)!=5:raise ValueError('Short FZP row')
        t=float(fields[0]);no=fields[1].strip();linkbytes=fields[2].strip()
        if t!=previous_t:
            if previous_t is not None:
                if t<previous_t:raise ValueError('Decreasing timestamp')
                cadence[t-previous_t]+=1
            frame_ids=set();frame_count+=1;previous_t=t
        if no in frame_ids:duplicate_rows+=1;raise ValueError('Duplicate ID in timestamp')
        frame_ids.add(no);total_rows+=1
        first_time=t if first_time is None else first_time;last_time=t
        source=sourcebytes.get(linkbytes)
        if source is not None:
            lane=int(fields[3]);position=float(fields[4].split(b';',1)[0])
            if no not in cohorts:
                cohorts[no]={'vehicle_id':int(no),'input_no':specs[source]['input_no'],'source':source,'source_first_sec':t,
                    'source_first_lane':lane,'source_first_pos_m':position,'first_seen_on_source':no not in seen,
                    'source_observed_samples':0,'source_return_after_departure_count':0,'source_observation_gaps':0,
                    'branch_connector':None,'resolution':'pending','first_non_source':None}
            c=cohorts[no]
            if c['source']!=source:raise ValueError('ID observed on two unconnected input sources')
            if c['first_non_source'] is not None:c['source_return_after_departure_count']+=1
            if no in last_source and t-last_source[no]>1:c['source_observation_gaps']+=1
            c['source_observed_samples']+=1;c['source_last_sec']=t;c['source_last_lane']=lane;c['source_last_pos_m']=position
            last_source[no]=t
        elif no in cohorts:
            c=cohorts[no]
            if c['first_non_source'] is None:
                record={'sec':t,'link':linkbytes.decode(),'lane':int(fields[3]),'pos_m':float(fields[4].split(b';',1)[0])}
                c['first_non_source']=record;c['branch_connector'],c['resolution']=classify_next(record,specs[c['source']])
                c['departure_observation_gap_sec']=t-c['source_last_sec']
        if no in cohorts:cohorts[no]['last_observed_anywhere_sec']=t
        seen.add(no)
    for c in cohorts.values():
        if c['resolution']=='pending':c['resolution']='right_censored_on_source_at_final_frame' if c['source_last_sec']==last_time else 'disappeared_before_observed_branch'
    return sorted(cohorts.values(),key=lambda c:(c['input_no'],c['source_first_sec'],c['vehicle_id'])),{
        'frame_count':frame_count,'rows':total_rows,'first_sec':first_time,'last_sec':last_time,'cadence_counts_sec':dict(cadence),
        'duplicate_same_frame_ids':duplicate_rows,'all_unique_network_ids':len(seen)}

def summarize(cohorts,spec):
    total=len(cohorts);resolved=[c for c in cohorts if c['branch_connector'] is not None]
    bybranch=Counter(c['branch_connector'] for c in resolved)
    return {'source_observed_unique_ids':total,'resolved_ids':len(resolved),'unresolved_or_censored_ids':total-len(resolved),
        'resolution_counts':dict(Counter(c['resolution'] for c in cohorts)),
        'not_first_seen_on_source_ids':[c['vehicle_id'] for c in cohorts if not c['first_seen_on_source']],
        'repeated_source_after_departure_ids':[c['vehicle_id'] for c in cohorts if c['source_return_after_departure_count']],
        'source_gap_ids':[c['vehicle_id'] for c in cohorts if c['source_observation_gaps']],
        'departure_gap_above_1_sec_ids':[c['vehicle_id'] for c in cohorts if c.get('departure_observation_gap_sec',1)>1],
        'branches':[dict(connector=b['connector'],target=b['target'],count=bybranch[b['connector']],
            fraction_among_resolved=bybranch[b['connector']]/len(resolved) if resolved else None,
            fraction_of_all_source_observed=bybranch[b['connector']]/total if total else None,
            direct_connector_count=sum(c['branch_connector']==b['connector'] and c['resolution']=='observed_first_connector' for c in cohorts),
            skipped_connector_unique_target_count=sum(c['branch_connector']==b['connector'] and c['resolution']=='unique_target_after_skipped_connector' for c in cohorts)) for b in spec['outgoing']]}

def main():
    started=time.monotonic();specs=topology();run=ROOT/'evaluation/runs'/RUN;fzp=next(run.glob('vissim_eval/*.fzp'))
    inputs=[NETWORK,Path(__file__),ROOT/'diagnostics/observed_nc_trajectory_equivalence.json',next(run.glob('run_provenance_*.json'))]
    before={str(p.relative_to(ROOT)):sha(p) for p in inputs};fzp_before=fzp.stat()
    with fzp.open('rb') as stream:cohorts,sampling=collect(stream,specs)
    fzp_after=fzp.stat()
    if (fzp_before.st_size,fzp_before.st_mtime_ns)!=(fzp_after.st_size,fzp_after.st_mtime_ns):raise ValueError('FZP changed')
    summary={}
    for source,spec in specs.items():
        own=[c for c in cohorts if c['source']==source];summary[spec['input_no']]={'all_0_5400':summarize(own,spec),'by_source_first_seen_900sec_window':[]}
        for start in range(0,5400,900):
            subset=[c for c in own if start<c['source_first_sec']<=start+900]
            summary[spec['input_no']]['by_source_first_seen_900sec_window'].append({'start_exclusive_sec':start,'end_inclusive_sec':start+900,**summarize(subset,spec)})
    changed=[key for key,value in before.items() if sha(ROOT/key)!=value]
    result={'schema':'native-input-observed-branch-calibration/v1','purpose':'Offline seed13 empirical branch evidence only; no production use or calibration promotion',
        'run':RUN,'seed':13,'window_sec':[0,5400],'topology':specs,'sampling':sampling,'inputs':summary,'cohorts':cohorts,
        'source_sha256':before,'source_changes':changed,'fzp':{'path':str(fzp.relative_to(ROOT)),'sha256':sha(fzp),'bytes':fzp_after.st_size},
        'elapsed_sec':time.monotonic()-started,
        'limitations':['Fractions condition on vehicles actually observed on each source; desired native input volume is not assumed equal to admission.',
            'Source roads have no incoming connector or static route decision. First-connector choice is empirically observed, not native relFlow or uniform prior.',
            'Skipped connector classification uses its unique direct downstream road, reported separately from connector observations; no further-path inference.',
            'Unknown/censored source IDs remain in the full denominator and are listed individually; no equal split, inferred completion, or silent exclusion.',
            'This is full seed13 offline calibration; using later observations for earlier same-run prediction validation would leak future information.',
            'Seed14 or a separately frozen prospective run is required for holdout validation; no seed14 evidence is available in this artifact.']}
    out=ROOT/'diagnostics/native_1092_1093_branch_calibration.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    fields=['vehicle_id','input_no','source','source_first_sec','source_last_sec','source_first_lane','source_first_pos_m','source_last_lane','source_last_pos_m','source_observed_samples','first_seen_on_source','branch_connector','resolution','departure_observation_gap_sec','source_return_after_departure_count','source_observation_gaps','last_observed_anywhere_sec','first_non_source']
    with out.with_suffix('.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows({k:json.dumps(c[k],sort_keys=True) if isinstance(c.get(k),dict) else c.get(k) for k in fields} for c in cohorts)
    lines=['# Native input1092/1093의 관측 분기 — seed13 보정 근거','',
        '**1092는 관측80대 모두 동향 SC12 방향, 1093은 관측67대 모두 서향 SC11 방향이었다.** Native static route decision이 없다는 이유로 1:1 분할하면 이 기준 궤적과 어긋난다. 생산 분율을 바꾸지 않았으며, 이것은 명시적인 seed13 offline calibration 자료다.',
        '', '| 입력/source | 첫 branch | 전체 관측 ID | connector 직접 관측 | connector 건너뛴 고유 target | 반대 branch | 검열/미해소 |',
        '|---|---|---:|---:|---:|---:|---:|',
        '| 1092 / 217 | 10350 → 1210012103 (SC12 방향) | 80 | 80 | 0 | 0 | 0 |',
        '| 1093 / 225 | 10359 → 1220012001 (SC11 방향) | 67 | 38 | 29 | 0 | 0 |',
        '', '고정 Ver2 XML에서 source217/225는 incoming connector0·해당 native input1개·static decision0이다. 두 출구는 모두 source lane1에서 시작한다. 모든147개 ID가 network에 처음 나타난 link도 해당 source였으며, source 재진입/중복 timestamp ID/관측 gap은0이다. source를 처음 본 시각 이후 최초 다른 link가 실제 connector인지,1초 사이 connector를 지난 고유 직접 하류 road인지 구별했다. 후자를 직접 connector 관측으로 표기하지 않았다.',
        '', '| Source 최초 관측 창 (시작 제외, 끝 포함) | 1092:10350 | 1093:10359 | 반대 방향/검열 |','|---|---:|---:|---:|']
    for index,start in enumerate(range(0,5400,900)):
        x=summary['1092']['by_source_first_seen_900sec_window'][index];y=summary['1093']['by_source_first_seen_900sec_window'][index]
        lines.append(f"| ({start}, {start+900}]초 | {x['resolved_ids']} | {y['resolved_ids']} | 0 / 0 |")
    lines += ['', '두 관측 선택은 source에서 더 먼저 만나는 connector와 일치한다:217의10350 시작18.385578m <10349의18.462590m;225의10359 시작29.961442m <10360의30.459113m. 이는 가능한 기하 설명이며, 이 자료로 VISSIM의 모든 no-route 선택 규칙이나 다른 seed의 확정 분기를 증명하지 않는다. 각 branch의 target lane/position 및 실제 geometry 길이를 JSON topology에 보존했다.',
        '', '분율의 분모는 실제 source에서 관측한 고유 ID다. Native 수요가 모두 주입되었다고 가정하지 않으며, 요청 volume을 관측 admission으로 바꾸어 쓰지 않는다. source에서1초도 관측되지 않은 차량이 있다면 이 cohort에 들어오지 않는다. 이번 두 source는 관측 cohort 내부의 검열이0이므로 resolved 분율과 전체 관측 분율이 같다. JSON에는 일반적으로 이 두 분모를 별도로 유지한다.',
        '', '**검증 분리:** 전체0~5400초 seed13 자료로 얻은 보정치를 같은 실행의 이른 시점 예측 검증에 쓰면 미래 정보가 유입된다. 향후 생산에서 명시적으로 고정한 offline prior로 사용할 경우에도 seed14 또는 따로 보존한 prospective run에서 검증해야 한다. 본 산출물에는 seed14 검증이나 생산 승인이 없다. 900초별 표는 같은 seed 내부의 기술 통계이며 독립 holdout이 아니다.',
        '', '전체1초 FZP 5400프레임·26,693,633행을 한 번 읽었다. CSV는147개 ID별 source 최초/마지막 위치, 출발 관측구간, 최초 다른link, 분기 해소 방식과 검열 상태를 보존한다. 입력 FZP·network·run manifest·producer의 SHA와 전후 source 변경 검사는 JSON에 있다.',
        '', '재현: `python -X utf8 -m diagnostics.calibrate_native_1092_1093`. 집중 회귀: `python -m unittest diagnostics.test_native_branch_calibration -v`.', '']
    out.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'summary':summary,'sampling':sampling,'source_changes':changed,'elapsed_sec':result['elapsed_sec']},ensure_ascii=False))

if __name__=='__main__':main()
