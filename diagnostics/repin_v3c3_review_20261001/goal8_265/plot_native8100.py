"""Plot only the audited native8100 cumulative metrics; no FZP reread."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE/'current_native_analysis_to8100'
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
arrays={}
for arm,label,color in [('nc','무제어','#555555'),('sdmpc','SDMPC + 고정 VSL90','#1875b8')]:
    with (BASE/arm/'area_timeseries.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    t=np.array([float(r['sim_sec']) for r in rows])
    y=np.array([float(r['ttt_veh_h_cumulative']) for r in rows]);arrays[arm]=(t,y)
    axes[0].plot(t,y,label=f'{label}: {y[-1]:,.1f} 차량·시간',color=color,lw=1.8)
assert np.array_equal(arrays['nc'][0],arrays['sdmpc'][0])
delta=arrays['sdmpc'][1]-arrays['nc'][1]
axes[1].plot(t,delta,color='#1875b8',lw=1.8,label='SDMPC - 무제어')
axes[1].axhline(0,color='#777777',lw=.7)
axes[1].fill_between(t,delta,0,where=delta<0,color='#1875b8',alpha=.12)
axes[0].set_ylabel('Ω 누적 TTT [차량·시간]');axes[1].set_ylabel('누적 TTT 차이 [차량·시간]')
axes[1].set_xlabel('시뮬레이션 시간 [초]')
for ax in axes:
    ax.grid(alpha=.2);ax.legend(loc='upper left');ax.set_xlim(0,8100)
axes[1].set_xticks(np.arange(0,8101,900))
fig.suptitle('FW80 · 도시90 · seed29 · Ω701 · 0–8100초\n관측 TTT 5.32% 감소 — 8% 목표 미달',fontsize=15)
fig.supxlabel('native FZP 5초 간격 적분 · 마지막 4.9초 재고 유지\n삭제 233→403대, Ω 밖 체류 1,588.8→1,719.9 차량·시간: 개선의 한계로 별도 보고',fontsize=10)
fig.savefig(HERE/'TTT_native_to8100.png',dpi=160)
plt.close(fig)
