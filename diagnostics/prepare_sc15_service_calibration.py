"""SC15-only offline queued-discharge prior with two excluded time holdouts."""
from collections import defaultdict
from pathlib import Path
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
HOLDOUTS=[(900,1350),(2700,3150)]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def blocks_from_rows(headways,crossings,holdouts=HOLDOUTS):
    """Join consecutive qualified gaps; bound the block by its two endpoints."""
    groups=defaultdict(list);excluded=[]
    for h in headways:
        if str(h['queued_after_third_departure']) not in ('True','true','1'):continue
        key=(h['input_no'],int(h['previous_vehicle_id']));last=(h['input_no'],int(h['vehicle_id']))
        prev,cur=crossings[key],crossings[last]
        lo,hi=float(prev['lower_sec']),float(cur['upper_sec'])
        if any(lo<=end and hi>=start for start,end in holdouts):excluded.append(h);continue
        groups[(h['input_no'],float(h['green_start_sec']))].append((h,prev,cur))
    blocks=[]
    for (no,green),rows in sorted(groups.items()):
        rows.sort(key=lambda item:float(item[2]['linear_estimate_sec']));current=[]
        def append():
            if not current:return
            first,last=current[0][1],current[-1][2]
            ids=[int(first['vehicle_id'])]+[int(row[2]['vehicle_id']) for row in current]
            blocks.append({'input_no':no,'green_start_sec':green,'gap_count':len(current),'vehicle_ids':ids,
                'first_crossing_lower_sec':float(first['lower_sec']),'first_crossing_upper_sec':float(first['upper_sec']),
                'last_crossing_lower_sec':float(last['lower_sec']),'last_crossing_upper_sec':float(last['upper_sec']),
                'duration_lower_sec':float(last['lower_sec'])-float(first['upper_sec']),
                'duration_upper_sec':float(last['upper_sec'])-float(first['lower_sec']),
                'linear_estimate_duration_sec':float(last['linear_estimate_sec'])-float(first['linear_estimate_sec'])})
        for row in rows:
            if current and int(current[-1][2]['vehicle_id'])!=int(row[1]['vehicle_id']):append();current=[]
            current.append(row)
        append()
    return blocks,excluded

def main():
    headpath=ROOT/'diagnostics/native_sc15_head_crossings.csv';gappath=ROOT/'diagnostics/native_sc15_headways.csv'
    crossings={(r['input_no'],int(r['vehicle_id'])):r for r in csv.DictReader(headpath.open(encoding='utf-8'))}
    headways=list(csv.DictReader(gappath.open(encoding='utf-8')));blocks,excluded=blocks_from_rows(headways,crossings)
    original=json.loads((ROOT/'diagnostics/native_sc15_source_discharge.json').read_text(encoding='utf-8'))
    result={'schema':'native-fixed-service-calibration/v1','purpose':'Opt-in SC15-only queued-discharge lower-rate prior; no global capacity replacement',
        'seed':13,'calibration_scope':'Seed13 fit outside two excluded time holdouts; not an independent-seed validation',
        'excluded_time_holdouts_sec':HOLDOUTS,'seed14_validation':'pending','selected_estimator':'sum_gap_count / sum_block_duration_upper_sec * 3600',
        'method':'Consecutive same-GREEN headway blocks, each gap after third departure with observed stopped queue throughout intervening integer frames; use endpoint time brackets once per block.',
        'network_sha256':original['source_sha256'][str(Path('network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'))],
        'sig_sha256':original['source_sha256'][str(Path('network/real_world_gaepo_modi/개포동 test-bed11.sig'))],
        'fzp':original['fzp'],'inputs':{},'excluded_qualified_gap_counts':{},
        'limitations':['Bounds describe one-second crossing-time uncertainty for these sampled discharge blocks, not confidence bounds on a population saturation flow.',
            'The selected lower rate is conservative with respect to these timing intervals; residual downstream interference can still reduce observed discharge.',
            'Whole GREEN averages and stochastic desired-volume averages are not used as saturation estimators.',
            'The two time holdouts belong to the same seed13 trajectory; seed14 remains an independent validation requirement.']}
    for no,source,decision,group,head in [('1086','343','1099','5','110501'),('1087','341','1100','1','110101')]:
        own=[b for b in blocks if b['input_no']==no];gaps=sum(b['gap_count'] for b in own);upper=sum(b['duration_upper_sec'] for b in own);lower=sum(b['duration_lower_sec'] for b in own);linear=sum(b['linear_estimate_duration_sec'] for b in own)
        if gaps<=0 or lower<=0:raise ValueError('Insufficient bounded queued-discharge evidence')
        result['inputs'][no]={'physical_source':source,'native_decision':decision,'controller':'15','signal_group':group,'head':head,'lanes':1,
            'blocks':own,'gap_count':gaps,'duration_upper_sum_sec':upper,'duration_lower_sum_sec':lower,'linear_estimate_duration_sum_sec':linear,
            'selected_service_veh_h':gaps/upper*3600,'measurement_rate_lower_veh_h':gaps/upper*3600,
            'measurement_rate_upper_veh_h':gaps/lower*3600,'linear_estimate_rate_veh_h':gaps/linear*3600}
        result['excluded_qualified_gap_counts'][no]=sum(h['input_no']==no for h in excluded)
    sources=[Path(__file__),headpath,gappath,ROOT/'diagnostics/native_sc15_source_discharge.json']
    result['source_sha256']={str(p.relative_to(ROOT)):sha(p) for p in sources}
    out=ROOT/'diagnostics/native_sc15_service_calibration.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for no,decision in [('1086','1099'),('1087','1100')]:
        doc=json.loads((ROOT/f'diagnostics/route_choice_corridor_{decision}_ver2.json').read_text(encoding='utf-8'))
        doc['native_fixed_service']['calibrated_discharge']={'path':str(out.relative_to(ROOT)),'sha256':sha(out),'input_no':no}
        target=ROOT/f'diagnostics/route_choice_corridor_{decision}_sc15_calibrated.json';target.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({no:{k:v for k,v in row.items() if k!='blocks'} for no,row in result['inputs'].items()}))

if __name__=='__main__':main()
