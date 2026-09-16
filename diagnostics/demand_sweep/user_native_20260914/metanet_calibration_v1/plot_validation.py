"""Display frozen seed17 predictions; does not fit parameters or change scoring."""
import csv
import json
import math
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from boundary_factory import ObservationData
from evaluate import check_freeze


def main():
    check_freeze(HERE/'FREEZE.json',HERE/'fit_v2/parameters.json')
    data=ObservationData(HERE/'seed17_observations')
    result=json.loads((HERE/'seed17_evaluation_v1/evaluation.json').read_text(encoding='utf-8'))
    if result['failures']: raise ValueError('Inspect failed predictions before plotting')
    with (HERE/'seed17_evaluation_v1/predicted_cells_30s.csv').open(encoding='utf-8',newline='') as f:
        raw=list(csv.DictReader(f))
    obs={(t,r['road'],r['cell']):r for t,rows in data.cells.items() for r in rows}
    pred={(r['mode'],r['version'],int(r['cutoff_s']),r['road'],int(float(r['time_s'])),int(r['cell'])):
          {k:float(r[k]) for k in ('v_kmh','n_veh','rho_veh_per_km_lane')} for r in raw}
    out=HERE/'figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
    times=list(range(930,9001,30));cutoffs=result['cutoffs_s']
    fig,axes=plt.subplots(3,2,figsize=(15,10),sharex=True,sharey=True,layout='constrained')
    labels=['VISSIM 관측','기존 METANET · 450초 예측','seed13 보정 · 450초 예측']
    for column,road in enumerate(('FW_E','FW_W')):
        for row,version in enumerate((None,'baseline','calibrated')):
            matrix=[]
            for cell in range(21):
                values=[]
                for t in times:
                    cutoff=900+((t-901)//450)*450
                    r=obs[t,road,cell] if version is None else pred['history_forecast',version,cutoff,road,t,cell]
                    values.append(r['v_kmh'] if r['n_veh']>=5 else np.nan)
                matrix.append(values)
            ax=axes[row,column]
            im=ax.pcolormesh(np.arange(900,9001,30)/60,np.arange(.5,22,1),np.array(matrix),
                             cmap='RdYlGn',vmin=0,vmax=150,shading='flat',rasterized=True)
            if row>0:
                for t in cutoffs[1:]: ax.axvline(t/60,color='white',lw=.35,alpha=.45)
            ax.set_title(('동측 FW-E' if column==0 else '서측 FW-W')+' | '+labels[row],fontsize=12)
            ax.set_yticks([1,5,10,14,18,21]);ax.set_ylabel('셀 번호 (1 → 21 하류)')
            if row==2:ax.set_xlabel('시뮬레이션 시간 [min]')
    fig.colorbar(im,ax=axes,label='셀 평균 속도 [km/h]',fraction=.025,pad=.015)
    fig.suptitle('동측 본선 입력 ×0.8 · 미사용 seed17 검증\n과거 150초 경계 관측만 사용 | 450초마다 새 예측 시작, 지평 내부 상태 재설정 없음',fontsize=15)
    fig.savefig(out/'seed17_speed_space_time.png',dpi=150);plt.close(fig)
    colors={'baseline':'#b76932','calibrated':'#2768ad','persistence':'#777777'}
    names={'baseline':'기존 모델','calibrated':'seed13 보정','persistence':'현재 상태 유지'}
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    metric_rows=[]
    for col,road in enumerate(('FW_E','FW_W')):
        for version in ('baseline','calibrated','persistence'):
            metrics={'speed':[],'density':[]}
            for lead in range(30,451,30):
                es=[];er=[]
                for cutoff in cutoffs:
                    for c in range(21):
                        o=obs[cutoff+lead,road,c]
                        p=obs[cutoff,road,c] if version=='persistence' else pred['history_forecast',version,cutoff,road,cutoff+lead,c]
                        er.append(p['rho_veh_per_km_lane']-o['rho_veh_per_km_lane'])
                        if o['n_veh']>=5 and o['v_kmh'] is not None and p['v_kmh'] is not None:
                            es.append(p['v_kmh']-o['v_kmh'])
                for name,errors in [('speed',es),('density',er)]:
                    val=math.sqrt(sum(e*e for e in errors)/len(errors))
                    metrics[name].append(val)
                    metric_rows.append(dict(road=road,version=version,lead_s=lead,metric=name,rmse=val,count=len(errors)))
            for row,name in enumerate(('speed','density')):
                ax=axes[row,col];ax.plot(range(30,451,30),metrics[name],color=colors[version],label=names[version],lw=2)
                ax.grid(alpha=.2);ax.set_xlabel('예측 시작 이후 [s]')
                ax.set_ylabel('속도 RMSE [km/h]' if name=='speed' else '밀도 RMSE [veh/km/lane]')
                ax.set_title(('동측' if col==0 else '서측')+' · '+('속도' if name=='speed' else '밀도'))
    axes[0,0].legend();fig.suptitle('seed17 · 18개 시작 시점 전체의 예측 오차\n실제 미래 경계 정보를 사용하지 않은 예측',fontsize=15)
    fig.savefig(out/'seed17_error_by_lead.png',dpi=150);plt.close(fig)
    with (out/'error_by_lead.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(metric_rows[0]));w.writeheader();w.writerows(metric_rows)
    fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
    for row,cutoff in enumerate((1350,3600,7200)):
        tt=list(range(cutoff,cutoff+451,30))
        series=[('VISSIM','#202020',None,None,'-'),('기존 모델','#b76932','history_forecast','baseline','-'),
                ('보정 모델','#2768ad','history_forecast','calibrated','-'),
                ('보정 + 미래 경계 제공 (진단)','#67a4bb','conditioned_diagnostic','calibrated','--')]
        for label,color,mode,version,style in series:
            vel=[];counts=[]
            for t in tt:
                cells=[obs[t,'FW_E',c] if mode is None or t==cutoff else pred[mode,version,cutoff,'FW_E',t,c] for c in range(21)]
                vel.append(cells[13]['v_kmh']);counts.append(sum(r['n_veh'] for r in cells))
            for col,values in enumerate((vel,counts)):
                axes[row,col].plot(np.array(tt)-cutoff,values,label=label,color=color,ls=style,lw=2)
        for col in range(2):
            ax=axes[row,col];ax.grid(alpha=.2);ax.set_xlabel('예측 시작 이후 [s]')
            ax.set_title(f'{cutoff}초 시작 | '+('동측 E14 속도' if col==0 else '동측 본선 차량 수'))
            ax.set_ylabel('속도 [km/h]' if col==0 else '차량 수 [veh]')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=2,fontsize=10)
    fig.suptitle('seed17 · 사전에 고른 3개 예측 구간\nE14 병목 반응과 동측 차량 보존을 함께 비교',fontsize=15)
    fig.savefig(out/'seed17_450s_examples.png',dpi=150);plt.close(fig)
    check_freeze(HERE/'FREEZE.json',HERE/'fit_v2/parameters.json')
    print(json.dumps({'figures':str(out),'parameters_retuned':False}))

if __name__=='__main__':main()
