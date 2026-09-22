"""Plot the frozen literature-term candidate against the same saved native data."""
import sys
import numpy as np
import calibrate as c
from prepare import save
sys.path.insert(0,str(c.ROOT/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

O=c.B/'literature_v2'
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
with np.load(c.O/'observed_none.npz') as f:obs={k:f[k] for k in f.files}
before=c.predicted(c.load(c.B/'refined_guard1_none.json'))
after=c.predicted(c.load(O/'lit_all_terms_width_corrected/refined_guard1_none.json'))
t=np.arange(15)*30+2415.5
fig,axes=plt.subplots(2,2,figsize=(13,7.6),sharex=True,layout='constrained')
tail={}
for col,(label,parents) in enumerate([('10643·10681 주변',[8,9]),('10481·10490·10484 주변',[12,13,14])]):
    cells=[i for i,p in enumerate(c.PARENTS) if p in parents];tail[label]={}
    for values,name,color,style in [(obs,'VISSIM 실측','#222222','-'),(before,'기존 모델','#c77729','--'),(after,'요청 항 포함 최선 후보','#147d92','-')]:
        n=values['n'][:,cells].sum(axis=(1,2));mom=values['mom'][:,cells].sum(axis=(1,2))
        speed=np.divide(mom,n,out=np.zeros_like(n),where=n>0)
        tail[label][name]=dict(n_veh=float(n[-1]),speed_kmh=float(speed[-1]))
        axes[0,col].plot(t,speed,style,color=color,label=name,lw=2,marker='o',ms=3)
        axes[1,col].plot(t,n,style,color=color,lw=2,marker='o',ms=3)
    axes[0,col].set_title(label,fontweight='bold');axes[0,col].set_ylim(0,125)
    axes[1,col].set_xlabel('시뮬레이션 시간 [s]')
    for ax in axes[:,col]:
        ax.axvspan(2700,2850,color='#dbe3ef',alpha=.65)
        ax.axvline(2700,color='#667788',lw=1);ax.set_xlim(2400,2850);ax.grid(alpha=.25)
    axes[0,col].text(.98,.97,'음영: 적합 제외 후반',transform=axes[0,col].transAxes,ha='right',va='top',fontsize=10)
axes[0,0].set_ylabel('구역 차량 가중 평균속도 [km/h]')
axes[1,0].set_ylabel('구역 평균 차량 수 [veh]')
axes[0,0].legend(loc='lower left',fontsize=10)
fig.suptitle('합류·분기 경계 / 진출부 차로 감소 / 비대칭 anticipation 재보정\n무제어 seed23 · 2400초에서 450초 연속 예측 · 30초 평균',fontsize=15)
fig.savefig(O/'profiles.png',dpi=170);fig.savefig(O/'profiles.pdf')
save(O/'profile_tail.json',dict(interval_sec=[2821,2850],regions=tail))
print(tail)
