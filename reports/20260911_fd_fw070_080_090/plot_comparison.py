"""Compare the three completed NC conditions using the same reviewed FD extraction."""
from pathlib import Path
import csv
from collections import Counter
import hashlib
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
import numpy as np
import pandas as pd
sys.path.append(str(ROOT/'.review-deps'))
sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(OUT/'.mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from diagnostics.audit_nc5400_native_signals import events

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    plt.rcParams.update({'font.family':'Malgun Gothic','font.size':10,'axes.unicode_minus':False,
                         'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold',
                         'grid.color':'#e3e7ea','grid.linewidth':.7,'axes.edgecolor':'#aab2b8'})
    points=[];metrics=[];checks={};source_files=[]
    for pct in (70,80,90):
        case=f'fw{pct:03d}_urban050'
        run=ROOT/f'evaluation/runs/fast_nc_{case}_s13_v1'
        result=ROOT/f'diagnostics/demand_sweep/{case}/results'
        figures=ROOT/'reports/20260911_fd_mfd_fw070_urban050' if pct==70 else OUT/f'fw{pct:03d}'
        receipt=load(run/'run.json');summary=load(result/'summary.json');valid=load(figures/'validation.json')
        assert receipt['completed'] and receipt['exit_code']==0 and receipt['terminal_sec']==5400 and not receipt['owned_native_alive']
        assert summary['status']=='complete' and valid['all_5400_frames'] and valid['omega_stock_exact_all_seconds']
        with (run/'readback.csv').open(newline='',encoding='ascii') as f:
            rb=list(csv.DictReader(f))
        for r in rb:
            try:
                assert abs(float(r['expected'])-float(r['actual'])) <= .001+abs(float(r['expected']))*1e-6
            except ValueError:
                assert r['expected']==r['actual']
        counts=pd.Series([r['kind'] for r in rb]).value_counts().to_dict()
        assert counts['demand']==204 and counts['vsl']==528 and counts['meter']==16
        prepared=Path(receipt['prepared'])
        with (prepared/'demand.csv').open(encoding='ascii',newline='') as stream:
            expected={(r['input_no'],r['time_int']):float(r['volume_vph']) for r in csv.DictReader(stream)}
        actual_demand=[r for r in rb if r['kind']=='demand']
        assert Counter((r['no'],r['time_int']) for r in actual_demand)==Counter({key:1 for key in expected})
        assert all(abs(float(r['expected'])-expected[r['no'],r['time_int']])<1e-7 for r in actual_demand)
        with (prepared/'controls.csv').open(encoding='ascii',newline='') as stream:
            controls=list(csv.DictReader(stream))
        vsl_expected={(r['no'],cls):2 for r in controls if r['kind']=='vsl' for cls in ('10','20','30','70')}
        meter_expected={(r['no'],'1'):2 for r in controls if r['kind']=='meter'}
        assert Counter((r['no'],r['time_int']) for r in rb if r['kind']=='vsl')==Counter(vsl_expected)
        assert Counter((r['no'],r['time_int']) for r in rb if r['kind']=='meter')==Counter(meter_expected)
        assert all(float(r['actual'])==120 for r in rb if r['kind']=='vsl')
        assert all(r['actual']=='GREEN' for r in rb if r['kind']=='meter')
        lsa=events(run/'vissim_eval/baseline_001.lsa')
        checks[case]=dict(completed=True,readback_counts=counts,readbacks_match=True,readback_identities_and_prepared_demand_join=True,native_lsa=lsa,
                          fd_validation_file=str(figures/'validation.json'))
        data=pd.read_csv(figures/'freeway_fd_points.csv')
        data=data[data.window_sec==60].copy();data['freeway_percent']=pct
        assert len(data)==3780
        points.append(data)
        unfinished=summary['unfinished_inputs']
        for direction in ('E','W'):
            a=data[data.direction==direction]
            slow=a[(a.speed_kph<30)&(a.n_veh>=5)]
            tail=a[a.start_sec==5340]
            metrics.append(dict(freeway_percent=pct,urban_percent=50,direction=direction,
                max_density_veh_km_lane=a.k_veh_km_lane.max(),max_observed_flow_veh_h_lane=a.q_veh_h_lane.max(),
                min_occupied_cell_speed_kph=a.loc[a.n_veh>=5,'speed_kph'].min(),
                slow_cell_minutes=len(slow),affected_slow_cells=','.join(str(x) for x in sorted(slow.cell.unique())),
                first_slow_start_sec=None if slow.empty else int(slow.start_sec.min()),
                last_slow_end_sec=None if slow.empty else int(slow.end_sec.max()),
                final_slow_cells=int(((tail.speed_kph<30)&(tail.n_veh>=5)).sum()),
                omega_ttt_veh_h=summary['ttt_veh_h'],omega_ttd_events=summary['td_observed_plus_terminal_canonical'],
                native_removals=summary['native_removals'],unknown_inside_disappearances=summary['unknown_inside_disappearances'],
                unfinished_input_event_count=len(unfinished),unfinished_input_vehicles=sum(int(e['remaining_vehicles']) for e in unfinished),
                unfinished_input_events_json=json.dumps(unfinished,ensure_ascii=False),
                omega_end_vehicles=summary['censored_end_n']))
        source_files += [run/'run.json',run/'readback.csv',result/'summary.json',figures/'freeway_fd_points.csv',figures/'validation.json']
    reference=checks['fw070_urban050']['native_lsa']['event_sha256']
    for case,check in checks.items():
        check['native_signal_events_exact_to_fw070']=check['native_lsa']['event_sha256']==reference
        check['native_meter_groups_recorded']=[key for key in check['native_lsa']['group_event_counts'] if int(key.split(':')[0])>=9101]
        check['meter_verification_scope']='Initial/terminal COM GREEN readbacks pass. Equal native LSA contains only initial t1 OFF for meters; no COM GREEN transition proof.'
    data=pd.concat(points,ignore_index=True)
    data.to_csv(OUT/'fd_points_60s_comparison.csv',index=False)
    table=pd.DataFrame(metrics)
    table.to_csv(OUT/'comparison_metrics.csv',index=False)
    norm=Normalize(0,90);cmap=plt.get_cmap('viridis')
    xmax=np.ceil(data.k_veh_km_lane.max()/10)*10
    ymax=np.ceil(data.q_veh_h_lane.max()/250)*250
    def finish(fig,name):
        for extension in ('png','svg','pdf'):
            fig.savefig(OUT/f'{name}.{extension}',dpi=180,bbox_inches='tight',facecolor='white')
        plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(16.8,9.5),sharex=True,sharey=True,layout='constrained')
    for j,pct in enumerate((70,80,90)):
        for i,direction in enumerate(('E','W')):
            ax=axes[i,j];a=data[(data.freeway_percent==pct)&(data.direction==direction)]
            ax.scatter(a.k_veh_km_lane,a.q_veh_h_lane,c=a.minute,norm=norm,cmap=cmap,s=11,alpha=.62,linewidths=0,rasterized=True)
            ax.set(title=f'고속도로 {pct}% · FW_{direction}',xlim=(0,xmax),ylim=(0,ymax))
            ax.grid(True);ax.set_axisbelow(True)
            if j==0: ax.set_ylabel(('동행' if i==0 else '서행')+' q [veh/h/lane]')
            if i==1: ax.set_xlabel('밀도 k [veh/km/lane]')
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=axes,shrink=.8,label='시뮬레이션 시간 [min]')
    fig.suptitle('고속도로 입력 70% · 80% · 90% — 관측 FD 비교\n도시 50% 고정 · 무제어 · seed 13 · 5400초 | 약 513m × 60초 평균 · 모든 패널 동일 축',fontsize=15)
    finish(fig,'freeway_fd_70_80_90')
    fig,axes=plt.subplots(2,3,figsize=(16.8,9.1),sharex=True,sharey=True,layout='constrained')
    speed_cmap=plt.get_cmap('viridis').copy();speed_cmap.set_bad('#eceff2')
    for j,pct in enumerate((70,80,90)):
        for i,direction in enumerate(('E','W')):
            ax=axes[i,j];a=data[(data.freeway_percent==pct)&(data.direction==direction)].copy()
            a.loc[a.n_veh<5,'speed_kph']=np.nan
            v=a.pivot(index='cell',columns='minute',values='speed_kph').to_numpy()
            im=ax.imshow(v,origin='lower',aspect='auto',extent=(0,90,-.5,20.5),cmap=speed_cmap,vmin=0,vmax=120,interpolation='nearest')
            ax.set(title=f'고속도로 {pct}% · FW_{direction}',yticks=range(0,21,2),xticks=range(0,91,15))
            if i==1: ax.set_xlabel('시뮬레이션 시간 [min]')
            if j==0: ax.set_ylabel('구간 번호: 0 상류 → 20 하류')
    fig.colorbar(im,ax=axes,shrink=.8,label='구간 평균 속도 [km/h]')
    fig.suptitle('고속도로 입력 변화에 따른 혼잡 발생·전파·회복\n도시 50% · 60초 평균 | 회색: 평균 차량 수 5대 미만 · 색상 범위 0–120 km/h',fontsize=15)
    finish(fig,'freeway_speed_70_80_90')
    physical_valid=all(check['native_signal_events_exact_to_fw070'] for check in checks.values())
    proof=dict(status='rendered_pending_visual_review' if physical_valid else 'FAIL_native_signal_comparison',conditions=checks,
               recorded_signal_comparison_valid=physical_valid,
               meter_lsa_transition_verification='INCOMPLETE: SG identity presence is not COM GREEN execution proof',
               sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in source_files+[Path(__file__)]},
               figure_scope='Same60-second trapezoids, geometry and FD domain exclusions as reviewed70percent extraction',
               no_controller_changes=True)
    (OUT/'validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(table.drop(columns='unfinished_input_events_json').to_string(index=False))
    print('Native signal event equality:',{k:v['native_signal_events_exact_to_fw070'] for k,v in checks.items()})
    if not physical_valid:
        raise SystemExit('Native signal event differences require diagnosis before interpreting the demand comparison')

if __name__=='__main__':
    main()
