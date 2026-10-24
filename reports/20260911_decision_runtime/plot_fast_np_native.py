"""Completed native road52 arrivals, discharge and SG6 windows; no model/COM calls."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / '.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

D = ROOT / 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
load = lambda name: json.loads((D / name).read_text(encoding='utf-8'))
traffic = load('fast_np_sc1004_arrivals450_v1.json')
qualified = load('fast_np_native_qualification_v1.json')
assert qualified['completed'] and qualified['native_execution_passed']
assert qualified['warmup_prefix']['all_raw_data_rows_equal']
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic', 'axes.unicode_minus':False, 'font.size':11})
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True,
                         gridspec_kw={'height_ratios':[2, 2, 1.7, 1]})
for index, (key, label, color) in enumerate((('baseline', '기준', '#38799a'),
                                           ('selected', '선택 명령', '#b95b38'))):
    rows = traffic[key]['bins30s']
    times = sorted(map(int, rows))
    for ax, field, descriptor in ((axes[0], 'observed_entries', '도착'),
                                  (axes[1], 'observed_exits', '방출')):
        values = [rows[str(t)].get('52', {}).get(field, 0) for t in times]
        ax.step([*times, 1350], [*values, values[-1]], where='post', color=color,
                label=f'{label}: {sum(values)}대', lw=1.8)
        ax.set_ylabel(f'52번 도로 {descriptor}\n[veh / 30s]')
        ax.legend(frameon=False, loc='upper left')
    stopped = [rows[str(t)].get('52', {}).get('stopped_vehicle_seconds_lt5', 0)/30 for t in times]
    axes[2].plot([t+15 for t in times], stopped, 'o-', color=color, markersize=4, label=label)
    windows = qualified['sc1004'][key]['native_green_windows']['6']
    axes[3].broken_barh([(w['first_native_green_frame_sec'],
                         w['last_native_green_frame_sec']-w['first_native_green_frame_sec']+1)
                        for w in windows], (1-index-.28, .56), facecolors=color)
axes[2].set_ylabel('저속 차량 수\n30초 평균 [veh]')
axes[3].set_yticks([1, 0], ['기준 SG6', '선택 명령 SG6'])
axes[3].set_ylim(-.55, 1.55)
axes[3].set_xlabel('시뮬레이션 시각 [s]')
axes[3].set_xlim(900, 1350)
axes[1].annotate('선택 명령: 마지막 90초 방출 0대', xy=(1300, .1), xytext=(1090, 5),
                 arrowprops={'arrowstyle':'->', 'color':'#b95b38'}, color='#b95b38')
for ax in axes:
    ax.grid(axis='x', alpha=.22)
    ax.spines[['top','right']].set_visible(False)
fig.suptitle('SC1004: 도착 차량군과 녹색 시각이 어긋난 실제 응답', fontsize=17, y=.985)
fig.text(.09, .947, '80/50 · seed13 · 900초까지 전체 FZP 행 일치 · 900-1350초 고정 명령 재생', fontsize=11)
fig.text(.09, .018, '상단은 52번 도로 전체, 하단 SG6는 1·2·3차로 신호. 4차로는 SG1이므로 집계 범위가 다름.\n'
         '저속: 5km/h 미만. 신호는 native LDP의 GREEN 1초 표본 범위. GNE 인증·폐루프 성능 검증은 아님.',
         fontsize=9, color='#4d5963')
fig.tight_layout(rect=(.01, .067, .99, .932))
for suffix in ('png', 'svg'):
    fig.savefig(Path(__file__).with_name('FAST_NP_NATIVE450.'+suffix), dpi=160, facecolor='white')
print(Path(__file__).with_name('FAST_NP_NATIVE450.png'))
