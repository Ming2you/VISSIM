"""Compare completed observed prefixes; no causal attribution to a single action."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics.summarize_fast_nc import cell_geometry

HERE=Path(__file__).parent
BASE=HERE/'native_windows'

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def values(rows,end,key):return float(rows[end][key]) if end else 0.

def main():
    metrics={tag:load(BASE/tag/'area_metrics.json') for tag in ('nc','cl')}
    areas={tag:{int(float(r['sim_sec'])):r for r in read(BASE/tag/'area_timeseries.csv')} for tag in metrics}
    blocks=[]
    for a in range(0,8850,150):
        b=a+150;row={'start_sec':a,'end_sec':b}
        for tag,t in areas.items():
            for key,col in [('ttt_veh_h','ttt_veh_h_cumulative'),('ttd_veh','ttd_observed_plus_terminal_cumulative')]:
                row[tag+'_'+key]=values(t,b,col)-values(t,a,col)
            row[tag+'_end_n']=int(t[b]['inside_vehicles'])
            for key,col in [('absences','unresolved_inside_disappearances'),('entries','observed_entry_events'),('appeared','appeared_inside_events')]:
                row[tag+'_'+key]=sum(float(t[i][col]) for i in range(a+1,b+1))
        row['control_minus_nc_ttt_veh_h']=row['cl_ttt_veh_h']-row['nc_ttt_veh_h']
        blocks.append(row)
    save(HERE/'actual_policy_windows_150s.csv',blocks)
    phases=[]
    for a,b in [(0,900),(900,1800),(1800,4500),(4500,8100),(8100,8850)]:
        selection=[r for r in blocks if a<=r['start_sec'] and r['end_sec']<=b]
        row={'start_sec':a,'end_sec':b}
        for key in ('nc_ttt_veh_h','cl_ttt_veh_h','nc_ttd_veh','cl_ttd_veh','nc_absences','cl_absences','nc_entries','cl_entries','nc_appeared','cl_appeared'):
            row[key]=sum(r[key] for r in selection)
        row['delta_ttt_veh_h']=row['cl_ttt_veh_h']-row['nc_ttt_veh_h']
        row['reduction_percent']=-100*row['delta_ttt_veh_h']/row['nc_ttt_veh_h']
        phases.append(row)
    _,addresses,_=cell_geometry()
    link_rows=[];group=defaultdict(lambda:defaultdict(float))
    keys=set().union(*(set(m['physical_link_residence']) for m in metrics.values()))
    for k in sorted(keys,key=int):
        n=metrics['nc']['physical_link_residence'].get(k,{})
        c=metrics['cl']['physical_link_residence'].get(k,{})
        inside=n.get('inside',c.get('inside'))
        label='freeway_'+addresses[int(k)][0] if int(k) in addresses else 'urban_and_ramps'
        r={'link':k,'inside_omega':inside,'group':label}
        for tag,point in [('nc',n),('cl',c)]:
            for field in ('ttt_veh_h','slow_veh_h'):r[tag+'_'+field]=point.get(field,0.)
        r['delta_ttt_veh_h']=r['cl_ttt_veh_h']-r['nc_ttt_veh_h']
        r['delta_slow_veh_h']=r['cl_slow_veh_h']-r['nc_slow_veh_h']
        link_rows.append(r)
        if inside:
            for key in ('nc_ttt_veh_h','cl_ttt_veh_h','delta_ttt_veh_h','nc_slow_veh_h','cl_slow_veh_h','delta_slow_veh_h'):group[label][key]+=r[key]
    save(HERE/'physical_link_ttt_delta.csv',link_rows)
    total=sum(v['delta_ttt_veh_h'] for v in group.values())
    assert abs(total-(metrics['cl']['ttt_veh_h']-metrics['nc']['ttt_veh_h']))<1e-7
    cell_summary=[]
    for tag in metrics:
        groups=defaultdict(list)
        for r in read(BASE/tag/'fw_cells_30s.csv'):groups[(r['direction'],int(r['cell']))].append(r)
        for (direction,cell),points in sorted(groups.items()):
            low=[r for r in points if int(r['n'])>=5 and float(r['mean_speed_kph'])<20]
            cell_summary.append({'policy':tag,'direction':direction,'cell_zero_based':cell,'low_speed_samples':len(low),
                                 'first_low_sec':int(low[0]['sec']) if low else None,'last_low_sec':int(low[-1]['sec']) if low else None,
                                 'max_stopped':max(int(r['stopped']) for r in points)})
    save(HERE/'freeway_cell_low_speed.csv',cell_summary)
    mapping=load(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
    pair_counts={tag:defaultdict(int) for tag in metrics}
    for tag in metrics:
        for r in read(BASE/tag/'observed_link_pairs_150s.csv'):
            pair_counts[tag][(int(r['from_link']),int(r['to_link']))]+=int(r['vehicles'])
    ramps=[]
    for r in mapping['ramp_meters']:
        key=int(r['connector']),int(r['to_link'])
        ramps.append({'meter':r['id'],'connector':key[0],'downstream_mainline_link':key[1],
                      'nc_observed_connector_to_mainline_events':pair_counts['nc'][key],
                      'cl_observed_connector_to_mainline_events':pair_counts['cl'][key]})
    inside=[r for r in link_rows if r['inside_omega']]
    report={'schema':'performance-policy-prefix-comparison/v1','interval_sec':[0,8850],
            'whole_native_execution_certified':False,'phases':phases,'groups':dict(group),
            'best_link_residence_reductions':sorted(inside,key=lambda r:r['delta_ttt_veh_h'])[:10],
            'largest_link_residence_increases':sorted(inside,key=lambda r:-r['delta_ttt_veh_h'])[:10],
            'ramp_observed_merges':ramps,'all_cases_same_seed':13,
            'native_warning_coverage':{'nc':'Completed ERR available','cl':'No completed simulation ERR; available baseline_001.err is empty. Do not infer zero removals/missed insertion.'},
            'limits':['E/W cells use0-based indices and30-second snapshots; first low is an observed sample, not a causal wave-speed estimate.',
                      'Policy trajectories diverge after900s. Between-policy increments do not measure the causal effect of one current command.',
                      'Link TTT reductions can reflect arrival/exit/routing changes; road departures exclude unobserved disappearances.',
                      'Ramp events require observed connector→mainline pair and can miss short between-frame connector passages; not desired demand or complete merge count.',
                      'CL error buffer incomplete; TTD excludes unresolved disappearance and censored terminal stock.']}
    (HERE/'native_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# V3와 정본 무제어: 관측0–8850초 사후 대조','',
           '1초 FZP를각각1회읽어기존Ω TTT계산과150초링크회계를대조했다. 이전TTT와일치하고마지막150초외삽은없다. CL중단런의최종신호/오류인증은별도다.','',
           '| 구간(s) | NC TTT | CL TTT | CL−NC(veh·h) | 감소율 |','|---|---:|---:|---:|---:|']
    for r in phases:lines.append(f"| {r['start_sec']}–{r['end_sec']} | {r['nc_ttt_veh_h']:.3f} | {r['cl_ttt_veh_h']:.3f} | {r['delta_ttt_veh_h']:+.3f} | {r['reduction_percent']:.3f}% |")
    lines+=['','| Ω 내부 공간 | NC TTT | CL TTT | CL−NC |','|---|---:|---:|---:|']
    for k,r in sorted(group.items()):lines.append(f"| {k} | {r['nc_ttt_veh_h']:.3f} | {r['cl_ttt_veh_h']:.3f} | {r['delta_ttt_veh_h']:+.3f} |")
    lines+=['','| 동측 cell(0부터번호) | NC 첫 저속(s) | CL 첫 저속(s) | NC/CL 저속표본수 |','|---|---:|---:|---:|']
    for cell in (7,6,5,4,3):
        a,b=[next(r for r in cell_summary if r['policy']==tag and r['direction']=='E' and r['cell_zero_based']==cell) for tag in ('nc','cl')]
        lines.append(f"| {cell} | {a['first_low_sec']} | {b['first_low_sec']} | {a['low_speed_samples']}/{b['low_speed_samples']} |")
    lines+=['','저속은차량5대이상인표본의평균속도20km/h미만이다. 동측E7→E6→E5→E4→E3에서CL의첫저속이더이른패턴을보이나, 특정signal/merge가원인이라는증명은아니다.',
            '','CL은완료시뮬레이션ERR가없고baseline_001.err도0byte이므로삭제0/미삽입0으로판정하지않는다. Ω내미확인소실은NC375/CL348건으로정상TTD에포함하지않았다.',
            '','450초held예측과450초폐루프실측은미래명령이다르므로그차이를동일명령의예측오차로사용하지않는다. 상세150초·링크·관측통과표는같은폴더CSV를참조한다.']
    (HERE/'native_comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'phases':phases,'groups':dict(group),'ramps':ramps},ensure_ascii=False))

if __name__=='__main__':main()
