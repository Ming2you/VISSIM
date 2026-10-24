"""Observed/model comparison using completed small replay tables only."""
from pathlib import Path
import csv
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / '.plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def cost(arm, start, field):
    return sum(float(r[field]) for r in rows(BASE / arm / f'replay{start}' / 'comparison_150s.csv'))


plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 11})
fig = plt.figure(figsize=(12, 8), constrained_layout=True)
grid = fig.add_gridspec(2, 2)
data = rows(BASE / 'none/replay1800/comparison_cells_30s.csv')
for col, (direction, cell) in enumerate((('E', 8),)):
    ax = fig.add_subplot(grid[0,col]); sample = [r for r in data if r['direction']==direction and int(r['cell'])==cell]
    t = [float(r['sec'])/60 for r in sample]
    ax.plot(t, [float(r['native_speed_kph']) for r in sample], color='#333333', lw=2, label='VISSIM 실측')
    ax.plot(t, [float(r['predicted_speed_kph']) for r in sample], color='#be4b29', ls='--', lw=2, label='plant 예측')
    ax.set(title=f'무제어 · {direction}{cell} | 1800초 상태에서 450초 예측', xlabel='시뮬레이션 시간 [분]', ylabel='셀 평균속도 [km/h]', ylim=(0,120))
    ax.grid(alpha=.2); ax.legend()
ax = fig.add_subplot(grid[0,1])
paired = {}
for arm in ('none', 'vsl'):
    paired[arm] = {float(r['sec']): r for r in rows(BASE/arm/'replay900/comparison_cells_30s.csv')
                   if r['direction']=='W' and int(r['cell'])==5}
seconds=sorted(paired['none'])
for field, label, color, style in (('native_speed_kph','VISSIM 속도 변화','#333333','-'),
                                  ('predicted_speed_kph','plant 속도 변화','#be4b29','--')):
    values=[float(paired['vsl'][t][field])-float(paired['none'][t][field]) for t in seconds]
    ax.plot([t/60 for t in seconds], values, color=color, ls=style, lw=2, label=label)
ax.axhline(0,color='black',lw=.7); ax.grid(alpha=.2); ax.legend()
ax.set(title='W5 · VSL - 무제어 | 공통900초 상태에서 450초', xlabel='시뮬레이션 시간 [분]', ylabel='제어에 따른 속도 변화 [km/h]')
ax = fig.add_subplot(grid[1,:])
pairs = [('VSL - 무제어\n900–1350초', 'vsl', 'none', 900),
         ('RM - 무제어\n1650–2100초', 'rm', 'none', 1650),
         ('병용 - VSL\n1650–2100초', 'both', 'vsl', 1650)]
actual = [cost(a,t,'native_TTT_veh_h')-cost(b,t,'native_TTT_veh_h') for _,a,b,t in pairs]
predicted = [cost(a,t,'model_TTT_veh_h')-cost(b,t,'model_TTT_veh_h') for _,a,b,t in pairs]
x = np.arange(3)
ax.bar(x-.17, actual, width=.34, label='VISSIM 실측', color='#555555')
ax.bar(x+.17, predicted, width=.34, label='plant 예측', color='#be4b29')
for values, offset in ((actual,-.17),(predicted,.17)):
    for i,v in enumerate(values): ax.text(i+offset,v+.018,f'{v:.3f}',ha='center')
ax.set_xticks(x,[r[0] for r in pairs]); ax.set_ylabel('제어에 따른 TTT 증가 [차량·시간]')
ax.set_title('각 쌍의 동일 초기 상태·이력·직전 명령 확인 후 비교 | 양수는 손해')
ax.axhline(0,color='black',lw=.7); ax.set_ylim(-.03,max(actual)*1.2); ax.legend(); ax.grid(axis='y',alpha=.2)
fig.suptitle('절대 예측 오차와 제어 변경의 효과를 구분')
path=BASE/'review_v1/plant_response.png'
fig.savefig(path,dpi=150)
print(path)
