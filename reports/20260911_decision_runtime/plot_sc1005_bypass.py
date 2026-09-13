"""Static figure from completed native balances and pinned model diagnostics."""
from pathlib import Path
import json
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
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,
    'font.size':11,'savefig.facecolor':'white'})
load=lambda name:json.loads((D/name).read_text(encoding='utf-8'))
native=load('open1350_sc1005_departures_v1.json')
comparison=load('open1350_model_native_comparison_v1.json')
probe=load('sc1005_bypass_model_probe_v1.json')
assert native['completed'] and native['all_link_frame_balances_zero']
assert comparison['completed'] and probe['completed'] and probe['baseline_response_exact']
exits=native['exits_by_next_link']['403']
right=exits['10565']+exits['58'];left=exits['10570']
assert right+left==native['links']['403']['observed_exits']
fig,axes=plt.subplots(1,2,figsize=(15,6.6),gridspec_kw={'width_ratios':[1.15,1]})
ax=axes[0];ax.set(xlim=(0,10),ylim=(0,8));ax.axis('off')
def box(x,y,text,color='#e9eef3'):
    ax.text(x,y,text,ha='center',va='center',bbox={'boxstyle':'round,pad=.65',
        'facecolor':color,'edgecolor':'#596b7a'},fontsize=11)
def arrow(start,end,label,color='#315874'):
    ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','lw':2,'color':color})
    ax.text((start[0]+end[0])/2,(start[1]+end[1])/2+.22,label,
        color=color,ha='center',fontsize=10)
box(2,6.5,'도로403\n실제 재고 8 → 15대')
box(7.5,6.5,'2·3차로 / SG7\n녹색 69초 / 450초','#e7f1e9')
box(7.5,4.55,'10570 → 도로61')
box(2,3.9,'1차로 / 신호 없음\n10565 → 도로58','#fff1d9')
box(2,1.65,'10498 → 도로52\n→ SC1004 → 램프 분기')
arrow((3.45,6.5),(5.65,6.5),f'{left}대')
arrow((7.5,5.85),(7.5,5.13),'')
arrow((2,5.8),(2,4.62),f'{right}대', '#b46d14')
arrow((2,3.15),(2,2.45),'')
ax.text(5.8,2.2,'현재 모델은 신호 없는 우회전도\nSC1005_p1 녹색에 종속시킴',
    color='#a74632',ha='center',fontsize=12)
model_release=probe['arms']['baseline']['area']['flow_counts']['movement:SC1005_N_SC105_to_W_SC1004']
ax.text(5.8,1.25,f'실제 방출 {right}대 / 모델 {model_release:.2f}대',ha='center',fontweight='bold')
ax.set_title('실제 신호 차로와 우회전 경로는 분리됨',fontweight='bold',pad=15)
rows=comparison['ramps'];labels=[r['ramp'].removeprefix('RM_C') for r in rows]
y=np.arange(len(rows));ax=axes[1]
ax.barh(y-.18,[r['native_merge'] for r in rows],height=.34,label='VISSIM 실제',color='#39789c')
ax.barh(y+.18,[r['model_merge'] for r in rows],height=.34,label='현재 모델',color='#d99948')
ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlabel('450초 동안 실제/예측 본선 합류 [veh]')
ax.set_ylabel('물리 램프 connector');ax.grid(axis='x',alpha=.22);ax.set_axisbelow(True)
ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False,loc='lower right')
ax.set_title('같은 무제어 명령의 8개 램프 응답',fontweight='bold',pad=15)
fig.suptitle('고속도로 80% · 도시 50% · seed 13 | 900–1350초 사후 진단',fontsize=16,y=.97)
fig.text(.04,.035,'왼쪽은 연결 관계를 보여주는 모식도이며 지도 축척이 아님. 우회전 57대는 403→10565 관측 53대 + 1초 사이 connector를 건너뛴 403→58 관측 4대.\n'
    '도로58 유입 58대에는 시작 시 connector 재고 1대가 포함됨. 오른쪽 합류는 Ω 내부 이동으로 TTD에 포함하지 않음.',fontsize=9,color='#4d5963')
fig.tight_layout(rect=(.02,.1,.99,.92))
for suffix in ('png','svg'):
    path=OUT/f'SC1005_BYPASS_AND_RAMP450.{suffix}'
    if path.exists():raise FileExistsError(path)
    fig.savefig(path,dpi=160)
print(OUT/'SC1005_BYPASS_AND_RAMP450.png')
