"""Align completed native SG6 head departures by the first GREEN sample."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

D=ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
report=json.loads((D/'fast_np_native_startup450_v2.json').read_text(encoding='utf-8'))
assert report['completed']
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
fig,axes=plt.subplots(1,2,figsize=(12,5),gridspec_kw={'width_ratios':[1,1.25]})
for arm,label,palette in (('baseline','기준',['#88afc4','#447e9c','#154c68']),
                          ('selected','변경',['#deb29e','#bb7859','#8d4326'])):
    data=report['arms'][arm]
    for i,w in enumerate(data['green_windows']):
        if w['right_censored']:
            continue
        start=w['first_native_green_frame_sec']
        lag=sorted(w['observed_head_departure_lags_sec'])
        n=sum(v['upstream_n'] for v in data['pre_green_lane_snapshots'][str(start-1)].values())
        for ax in axes:
            ax.step([0,*lag,45],[0,*range(1,len(lag)+1),len(lag)],where='post',
                    color=palette[i],ls='-' if arm=='baseline' else '--',lw=1.7,
                    label=f'{label} {start}초 · 시작 전 {n}대')
axes[0].set_xlim(0,10)
axes[0].set_ylim(0,13)
axes[0].set_title('출발 초기 10초')
axes[1].set_xlim(0,45)
axes[1].set_ylim(0,27)
axes[1].set_title('녹색 전체: 도착량·초기 재고는 서로 다름')
axes[1].legend(frameon=False,fontsize=9,loc='upper left')
for ax in axes:
    ax.set_xlabel('native GREEN 첫 기록 이후 시간 [s]')
    ax.set_ylabel('SG6 누적 정지선 통과 [veh]')
    ax.grid(alpha=.2)
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('녹색 시작을 정렬하면 초기 방출은 비슷하다',fontsize=17,y=.99)
fig.text(.08,.025,'1초 FZP/LDP 기록. 정지선→도로 이탈은 관측된 차량 모두 0–1초. 1350초 시작 녹색은 종료로 잘려 제외.\n'
         '시작 전 차량 수는 SG6 차로의 정지선 상류 재고이며 모두 정지 차량은 아님. 포화 방출률 동치 검증은 아님.',fontsize=9,color='#4d5963')
fig.tight_layout(rect=(.01,.13,.99,.92))
for suffix in ('png','svg'):
    fig.savefig(Path(__file__).with_name('FAST_NP_GREEN_ALIGNED.'+suffix),dpi=160,facecolor='white')
print(Path(__file__).with_name('FAST_NP_GREEN_ALIGNED.png'))
