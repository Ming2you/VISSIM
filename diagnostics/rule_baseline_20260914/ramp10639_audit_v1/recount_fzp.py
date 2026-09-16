"""Independent raw FZP recount. Does not import the prior native parser/accountant."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def write_csv(path, rows, fields=None):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)


def run(arm):
    name={'none':'rule100_none3000_s13_v1','rm':'rule100_rm3000_s13_v2'}[arm]
    directory=OUT/('raw_'+arm)
    assert not directory.exists(), 'Preserve previous audit'
    mapping=json.loads((ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text(encoding='utf-8-sig'))
    meters={int(r['connector']):r for r in mapping['ramp_meters']}
    selected=meters[10639]
    assert (int(selected['from_link']),int(selected['to_link']))==(70,2)
    pairs={(int(r['from_link']),int(r['to_link'])):c for c,r in meters.items()}
    files=list((ROOT/'evaluation/runs'/name/'vissim_eval').glob('*.fzp'))
    assert len(files)==1
    fzp=files[0];stat=(fzp.stat().st_size,fzp.stat().st_mtime_ns)
    digest=hashlib.sha256();header=None;prev={};origins={};paths={};events=[];jumps=[];raw=[];targets=set();counts=Counter()
    rows=0;last_sec=0;frames=set();start=time.perf_counter()
    with fzp.open('rb') as f:
        for line_no,line in enumerate(f,1):
            digest.update(line)
            if line.startswith(b'$VEHICLE:'):
                header=line.decode('ascii').strip().split(':',1)[1].split(';')
                indexes={k:header.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED')}
                continue
            if header is None or not line.strip() or line.startswith((b'*',b'$')):continue
            fields=line.strip().split(b';')
            assert len(fields)==len(header)
            sec=float(fields[indexes['SIMSEC']]);vid=int(fields[indexes['NO']]);link=int(fields[indexes['LANE\\LINK\\NO']])
            lane=int(fields[indexes['LANE\\INDEX']]);pos=float(fields[indexes['POS']]);speed=float(fields[indexes['SPEED']])
            assert sec>=last_sec and sec.is_integer()
            last_sec=sec;frames.add(int(sec));rows+=1
            row=(sec,link,lane,pos,speed,line_no,line.decode('ascii').strip())
            old=prev.get(vid)
            if old is None:
                origins[vid]={'first_sec':sec,'first_link':link,'first_pos_m':pos};paths[vid]=[(sec,link)]
            elif old[1]!=link:
                paths[vid].append((sec,link))
                if old[1] in meters or link in meters:
                    c=old[1] if old[1] in meters else link
                    spec=meters[c]
                    kind='merge' if old[1]==c and link==int(spec['to_link']) else 'entry' if link==c and old[1]==int(spec['from_link']) else 'other_transition'
                    e={'ramp':c,'kind':kind,'vehicle_id':vid,'before_sec':old[0],'after_sec':sec,'gap_sec':sec-old[0],
                       'before_link':old[1],'after_link':link,'before_lane':old[2],'after_lane':lane,
                       'before_pos_m':old[3],'after_pos_m':pos,'before_line':old[5],'after_line':line_no,
                       'origin_link':origins[vid]['first_link'],'origin_first_sec':origins[vid]['first_sec']}
                    events.append(e)
                    if c==10639:
                        raw.append(dict(e,before_raw=old[6],after_raw=row[6]))
                if (old[1],link) in pairs:
                    jumps.append({'vehicle_id':vid,'before_sec':old[0],'after_sec':sec,'from_link':old[1],'to_link':link,'candidate_ramp':pairs[old[1],link]})
            if link==10639:
                targets.add(vid);counts[int(sec)]+=1
            prev[vid]=row
    assert frames==set(range(1,3001))
    assert stat==(fzp.stat().st_size,fzp.stat().st_mtime_ns)
    summaries=[]
    for c in meters:
        es=[e for e in events if e['ramp']==c]
        def amount(kind,a,b):return sum(e['kind']==kind and a<e['after_sec']<=b for e in es)
        merges=[e for e in es if e['kind']=='merge' and 900<e['after_sec']<=3000]
        summaries.append({'arm':arm,'ramp':c,'entry_900_3000':amount('entry',900,3000),'merge_900_3000':len(merges),
            'merge_unique_vehicles_900_3000':len({e['vehicle_id'] for e in merges}),
            'merge_mean_vph_900_3000':len(merges)*3600/2100,
            'merge_0_900':amount('merge',0,900),'merge_0_3000':amount('merge',0,3000),
            'merge_gap_not1':sum(e['gap_sec']!=1 for e in merges),
            'possible_parent_link_jump_900_3000':sum(e['candidate_ramp']==c and 900<e['after_sec']<=3000 for e in jumps)})
    selected_events=[e for e in events if e['ramp']==10639]
    intervals=[{'start_sec':a,'end_sec':a+150,
        'entries':sum(e['kind']=='entry' and a<e['after_sec']<=a+150 for e in selected_events),
        'merges':sum(e['kind']=='merge' and a<e['after_sec']<=a+150 for e in selected_events),
        'start_n':counts[a],'end_n':counts[a+150]} for a in range(0,3000,150)]
    for r in intervals:assert r['start_n']+r['entries']-r['merges']==r['end_n'],r
    directory.mkdir()
    write_csv(directory/'all_ramp_counts.csv',summaries)
    write_csv(directory/'ramp10639_intervals.csv',intervals)
    write_csv(directory/'ramp10639_raw_crossings.csv',raw)
    write_csv(directory/'all_ramp_crossings.csv',events)
    origin=Counter(e['origin_link'] for e in selected_events if e['kind']=='merge' and 900<e['after_sec']<=3000)
    proof={'schema':'independent-raw-fzp-crossings/v1','arm':arm,'run':name,'fzp':str(fzp),'fzp_sha256':digest.hexdigest(),
        'header':header,'rows':rows,'frames':len(frames),'window':'after_sec>900 and <=3000; one-second crossing brackets retained',
        'target_geometry':selected,'all_ramps':summaries,'ramp10639_counts_at900_3000':[counts[900],counts[3000]],
        'ramp10639_max_n_900_3000':max(counts[s] for s in range(900,3001)),
        'ramp10639_origin_first_link_merges_900_3000':dict(origin),
        'crossings_at900':[e for e in selected_events if e['kind']=='merge' and e['after_sec']==900],
        'parent_jumps':jumps,'elapsed_sec':time.perf_counter()-start,
        'limitations':['First observed source link is not a route-choice probability or desired-demand count.',
                       'Does not count intended vehicles that never reach the connector.',
                       'Raw one-second records independently parsed, not previous aggregate CSV reused.']}
    (directory/'summary.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    (directory/'ramp10639_vehicle_paths.json').write_text(json.dumps({str(v):{'origin':origins[v],'path':paths[v]} for v in sorted(targets)},indent=2),encoding='utf-8')
    print(json.dumps({'arm':arm,'total_8_merge_900_3000':sum(r['merge_900_3000'] for r in summaries),
        'ramp10639':next(r for r in summaries if r['ramp']==10639),'source_link_counts':dict(origin),'end_n':counts[3000],
        'rows':rows,'elapsed_sec':proof['elapsed_sec']},ensure_ascii=False),flush=True)


if __name__=='__main__':run(sys.argv[1])
