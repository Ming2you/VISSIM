"""Native SG7 timing, departures and stopped inventory in two completed runs."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

D=ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
OUT=Path(__file__).resolve().parent
load=lambda name:json.loads((D/name).read_text(encoding='utf-8'))
baseline=load('open1350_sc1004_corridor_v1.json')
changed=load('sc1005_shift1350_native450_v1.json')
assert baseline['completed'] and changed['completed'] and changed['warmup_rows_exact_through900']
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True,gridspec_kw={'height_ratios':[3,2,1]})
for i,(name,color,doc) in enumerate((('기준','#39789c',baseline),('p1 +3초 / p2 -3초','#bd683b',changed))):
    signal=doc['signals']['1005']
    crossings=sorted(row['interval_sec'][1] for row in signal['head_crossings'] if row['sg']==7)
    axes[0].step([900,*crossings,1350],[0,*range(1,len(crossings)+1),len(crossings)],
        where='post',label=f'{name}: {len(crossings)}대',color=color,lw=2)
    times=sorted(map(int,signal['bins30s']))
    stopped=[signal['bins30s'][str(t)]['7'].get('upstream_stopped_vehicle_seconds_lt5',0)/30 for t in times]
    axes[1].plot(np.array(times)+15,stopped,'o-',color=color,lw=1.7,markersize=4,label=name)
    windows=signal['native_green_windows']['7']
    axes[2].broken_barh([(w['first_native_green_frame_sec'],w['last_native_green_frame_sec']-w['first_native_green_frame_sec']+1) for w in windows],
        (1-i-.28,.56),facecolors=color)
    first=next(row for row in signal['head_crossings'] if row['vehicle']==977)
    axes[0].annotate(f"차량977 통과 {first['interval_sec'][1]}초",
        xy=(first['interval_sec'][1],1),xytext=(970,7+11*i),color=color,
        arrowprops={'arrowstyle':'->','color':color},fontsize=10)
axes[0].set_ylabel('SG7 누적 정지선 통과 [veh]')
axes[0].legend(frameon=False,loc='upper left')
axes[1].set_ylabel('상류 저속 차량 수\n30초 평균 [veh]')
axes[2].set_yticks([1,0],['기준: 23초 녹색','변경: 20초 녹색'])
axes[2].set_xlabel('시뮬레이션 시각 [s]')
axes[2].set_ylim(-.55,1.55)
axes[2].set_xlim(900,1350)
for ax in axes:
    ax.grid(axis='x',alpha=.2)
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('SC1005 SG7: 녹색 시작 3초 지연의 실제 응답',fontsize=17,y=.98)
fig.text(.1,.925,'80/50 · seed13 · 같은 1350초 실행 · 900초까지 전체 FZP 행 일치 · native LDP/1초 FZP',fontsize=11)
fig.text(.1,.025,'저속은 5km/h 미만으로, 대기열 길이와 다름. 하단은 native GREEN 기록의 1초 표본 범위.\n'
    '신호 없는 우회전은 57대로 동일하며 이 SG7 그래프에 포함하지 않음. 진단용 신호 변경이며 GNE 선택 결과가 아님.',fontsize=9,color='#4d5963')
fig.tight_layout(rect=(.02,.075,.99,.91))
for suffix in ('png','svg'):
    path=OUT/f'SC1005_SHIFT_NATIVE450.{suffix}'
    fig.savefig(path,dpi=160,facecolor='white')
print(OUT/'SC1005_SHIFT_NATIVE450.png')
