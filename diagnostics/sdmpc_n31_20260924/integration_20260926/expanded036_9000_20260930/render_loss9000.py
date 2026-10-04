"""Compact completed-run loss diagnosis, using diagnose_loss9000.py outputs."""
import csv
import json
from collections import defaultdict, Counter
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / 'loss_diagnosis'

def rows(name):
    return list(csv.DictReader((OUT / name).open(encoding='utf-8-sig')))

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def main():
    summary = json.loads((OUT / 'summary.json').read_text(encoding='utf-8'))
    delta = rows('omega_delta_5s.csv')
    cells = rows('physical_cell_snapshots_150s.csv')
    stocks = rows('link_snapshots_150s.csv')
    det = rows('detector_windows_150s.csv')
    greens = rows('native_green_windows_150s.csv')
    after = rows('ramp_posthead_stock.csv')
    errors = rows('saved_one_step_count_errors.csv')
    removals = {}
    for arm in ('nc', 'sdmpc'):
        ee = json.loads((HERE / f'analysis/{arm}/native_errors.json').read_text(encoding='utf-8'))['unique_events']
        removals[arm] = [e for e in ee if e['kind'] == 'lane_change_removal']
    # Verify every available 150s count against its cumulative counter difference.
    by_det = defaultdict(list)
    for r in det:
        by_det[r['arm'], r['dcm_no']].append(r)
    checks = 0
    for rr in by_det.values():
        for a, b in zip(rr, rr[1:]):
            assert int(b['cum_count']) - int(a['cum_count']) == int(b['count'])
            checks += 1
    after = {(x['arm'], float(x['sim_sec']), x['connector']): int(x['posthead_n']) for x in after}
    periods = [(900, 1800), (1800, 2250), (2250, 3300), (3300, 4500), (4500, 6000), (6000, 7500), (7500, 9000)]
    flow_rows = []
    for start, end in periods:
        for arm in ('nc', 'sdmpc'):
            rr = [x for x in det if x['arm'] == arm and start < float(x['sim_sec']) <= end]
            item = {'arm': arm, 'start_s': start, 'end_s': end}
            for role, ref in [('source','FW_E'), ('chain_end','FW_E'), ('through','10481'), ('through','10643'), ('off_entry','10481'), ('off_entry','10643')]:
                item[role+'_'+ref] = sum(int(x['count']) for x in rr if x['role'] == role and x['ref'] == ref)
            for ramp in ('10484','10490','10639','10681'):
                assert not any(e['link'] == ramp for e in removals[arm])
                n = sum(int(x['count']) for x in rr if x['role'] == 'meter_head' and x['link'] == ramp)
                item['head_'+ramp] = n
                item['merge_balance_'+ramp] = n + after[arm,start,ramp] - after[arm,end,ramp]
            flow_rows.append(item)
    n_by = {(r['arm'],float(r['sim_sec']),r['road'],int(r['cell'])): int(r['n']) for r in cells}
    for r in errors:
        assert int(r['actual_n']) == n_by['sdmpc',float(r['target_sec']),r['road'],int(r['cell'])]
    model_examples = [r for r in errors if r['road']=='FW_E' and (float(r['target_sec']),int(r['cell'])) in [(3300,9),(3300,10),(3900,6),(3900,7)]]
    finding = {'detector_count_vs_cumulative_checks': checks, 'all_passed': True,
               'flow_periods': flow_rows,
               'merge_balance_note': 'Head counter + initial minus final posthead connector stock. All four ramps have no native recorded removals. This is conservation-reconstructed discharge to the mainline, not a direct merge-crossing detector or matched-cohort causal estimate.',
               'removals_by_link': {a: dict(Counter(e['link'] for e in rr)) for a,rr in removals.items()},
               'one_step_prediction_examples': model_examples,
               'model_error_note': 'Saved unscaled state_summary, 150s autonomous one-step forecasts under executed commands. No rerun/calibration; not a counterfactual policy comparison.'}
    save('mechanism_evidence.json', finding)
    plt.rcParams.update({'font.family':'Malgun Gothic', 'font.size':11, 'axes.unicode_minus':False,
                         'axes.spines.top':False, 'axes.spines.right':False, 'savefig.facecolor':'white'})
    blue, orange = '#245d89', '#bf591f'
    times = np.array([float(r['sim_sec']) for r in delta])
    tt = np.array([float(r['delta_TTT_veh_h']) for r in delta])
    fig, ax = plt.subplots(2, 1, figsize=(12, 8.6), gridspec_kw={'height_ratios':[1.45,1]}, constrained_layout=True)
    fig.suptitle('이전 9000초 SDMPC: 초기 이득 이후 동측 본선 손실이 누적됨', fontsize=17, fontweight='bold')
    ax[0].plot(times,tt,color=orange,lw=2)
    ax[0].fill_between(times,0,tt,where=tt<0,color=blue,alpha=.18)
    ax[0].axhline(0,color='#444',lw=.8)
    ax[0].annotate('2265초: -21.4',xy=(2265.1,-21.3694),xytext=(1350,-60),arrowprops={'arrowstyle':'-','color':'#555'})
    ax[0].annotate('3325초: 누적 손해 전환',xy=(3325.1,.087),xytext=(3700,-50),arrowprops={'arrowstyle':'-','color':'#555'})
    ax[0].annotate('+326.7 대·시간 (+4.50%)',xy=(9000,326.706),xytext=(6200,345),fontweight='bold')
    ax[0].set(xlim=(0,9200),ylim=(-85,380),xlabel='시뮬레이션 시간 [초]',ylabel='누적 ΔTTT [대·시간]\nSDMPC - 무제어')
    ax[0].set_xticks(range(0,9001,1500));ax[0].grid(alpha=.18)
    labels=['동측 본선','서측 본선','도시·램프 등 나머지 Ω','Ω 전체']
    values=[summary['group_exact_TTT'][k]['delta_TTT_veh_h'] for k in ['FW_E','FW_W','other_Omega']]+[summary['end']['delta_TTT_veh_h']]
    ax[1].barh(labels,values,color=[orange,orange,blue,'#555'],height=.58)
    for j,v in enumerate(values):ax[1].text(v+(6 if v>=0 else -6),j,f'{v:+.1f}',ha='left' if v>=0 else 'right',va='center',fontweight='bold')
    ax[1].axvline(0,color='#444',lw=.8);ax[1].invert_yaxis();ax[1].set(xlim=(-170,500),xlabel='9000초 전체 ΔTTT [대·시간]');ax[1].grid(axis='x',alpha=.18)
    fig.supxlabel('seed 29 · 동일 망/수요 · 기존 native FZP 5초 집계 재사용 · 음수=이득, 양수=손실',fontsize=10)
    fig.savefig(OUT/'loss_overview.png',dpi=160);plt.close(fig)
    selected=sorted({float(r['sim_sec']) for r in cells if float(r['sim_sec'])>=900})
    tm=np.array(selected);xb=np.r_[tm[0]-75,(tm[:-1]+tm[1:])/2,tm[-1]+75]
    geom={int(r['cell']):(float(r['start_m']),float(r['end_m'])) for r in cells if r['road']=='FW_E'}
    y=np.array([geom[0][0]]+[geom[c][1] for c in range(31)])/1000
    speed={a:np.full((31,len(tm)),np.nan) for a in ['nc','sdmpc']}
    number={a:np.zeros((31,len(tm))) for a in ['nc','sdmpc']}
    idx={t:j for j,t in enumerate(tm)}
    for r in cells:
        t=float(r['sim_sec'])
        if r['road']!='FW_E' or t<900:continue
        a,c,j=r['arm'],int(r['cell']),idx[t]
        speed[a][c,j]=float(r['speed_kph']) if r['speed_kph'] else np.nan
        number[a][c,j]=int(r['n'])
    fig, axes=plt.subplots(3,1,figsize=(13,11),sharex=True,sharey=True,constrained_layout=True)
    fig.suptitle('동측 본선: 뒤쪽 병목의 악화와 상류로 확장된 정체',fontsize=17,fontweight='bold')
    for ax,a,title in zip(axes[:2],['nc','sdmpc'],['무제어','SDMPC']):
        im=ax.pcolormesh(xb,y,speed[a],vmin=0,vmax=120,cmap='RdYlBu',shading='flat',rasterized=True)
        ax.set_title(title,loc='left',fontweight='bold')
        fig.colorbar(im,ax=ax,pad=.01,label='순간 평균속도 [km/h]',shrink=.9)
    im=axes[2].pcolormesh(xb,y,number['sdmpc']-number['nc'],vmin=-120,vmax=120,cmap='RdBu_r',shading='flat',rasterized=True)
    axes[2].set_title('셀별 재고 차이: SDMPC - 무제어 (붉은색=추가 체류)',loc='left',fontweight='bold')
    fig.colorbar(im,ax=axes[2],pad=.01,label='재고 차이 [대]',shrink=.9)
    for ax in axes:
        ax.axhline(4.386333,color='#333',ls='--',lw=.6)
        ax.axhline(6.841743,color='#333',ls='--',lw=.6)
        ax.set(xlim=(900,9000),ylim=(0,y[-1]),ylabel='동측 진입점부터 거리 [km]\n상류 → 하류')
    axes[1].text(8400,4.6,'첫 진출부',ha='right',bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'},fontsize=10)
    axes[1].text(8400,7.0,'뒤쪽 분기·차로감소',ha='right',bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'},fontsize=10)
    axes[1].plot([1650,4800],[6.341743,6.341743],color='black',lw=2)
    axes[1].text(4950,6.17,'VSL 100/90 적용 위치·기간',fontsize=9,bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'})
    axes[2].set_xlabel('시뮬레이션 시간 [초]');axes[2].set_xticks([900,1500,2250,3000,4500,6000,7500,9000])
    fig.supxlabel('31개 물리 셀 · 150초 순간 관측(시간평균 아님) · 실제 구간 길이 반영 · 차량 없는 속도 셀은 흰색',fontsize=10)
    fig.savefig(OUT/'east_propagation.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,constrained_layout=True)
    fig.suptitle('40번 링크: 주로 4차로 좌회전 대기가 누적됨',fontsize=16,fontweight='bold')
    lane=rows('urban_lanes_150s.csv')
    for a,color,label in [('nc',blue,'무제어'),('sdmpc',orange,'SDMPC')]:
        rr=[r for r in lane if r['arm']==a and r['link']=='40' and r['lane']=='4' and float(r['sim_sec'])>=900]
        axes[0].plot([float(x['sim_sec']) for x in rr],[int(x['n']) for x in rr],color=color,label=label+' 4차로',lw=2)
        rr=[r for r in lane if r['arm']==a and r['link']=='40' and r['lane']=='3' and float(r['sim_sec'])>=900]
        axes[0].plot([float(x['sim_sec']) for x in rr],[int(x['n']) for x in rr],color=color,ls='--',label=label+' 3차로',lw=1.4)
        gg=[r for r in greens if r['arm']==a and r['sc']=='1001' and r['sg']=='3' and int(r['end_s'])>=900]
        axes[1].step([int(x['end_s']) for x in gg],[int(x['green_s']) for x in gg],where='pre',color=color,label=label+' SG3')
    axes[0].set_ylabel('차로별 재고 [대]');axes[0].legend(ncol=2,loc='upper left');axes[0].grid(alpha=.2)
    axes[1].set(ylabel='직전 150초의 실제 녹색 [초]',xlabel='시뮬레이션 시간 [초]',ylim=(0,45),xlim=(900,9000));axes[1].legend();axes[1].grid(alpha=.2)
    axes[1].set_xticks([900,1500,2250,3000,4500,6000,7500,9000])
    fig.supxlabel('재고: 저장된 차량 관측 · 녹색: native LDP · 녹색 감소만으로 도착량·하류 제약의 영향을 분리할 수 없음',fontsize=10)
    fig.savefig(OUT/'urban40_lane_queue.png',dpi=160);plt.close(fig)
    print(json.dumps({'flow_windows':len(flow_rows),'detector_checks':checks,'saved_prediction_checks':len(errors),'plots':3},ensure_ascii=False))

if __name__=='__main__':
    main()
