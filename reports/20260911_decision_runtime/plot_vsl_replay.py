"""Completed native VSL replay: cached observations only, no COM or FZP scan."""
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
proof = load('vsl100_e0_native_qualification_v1.json')
comparison = load('vsl100_e0_comparison_v1.json')
assert proof['completed'] and proof['warmup_prefix']['all_raw_data_rows_equal']
assert comparison['completed']
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 11})
fig, axes = plt.subplots(2, 2, figsize=(13, 8))
boundaries = []
for name, label, color in [('open1350_area450_v1', '기준 VSL 120', '#39789c'),
                           ('vsl100_e0_area450_v1', '동측 첫 구역 VSL 100', '#bd683b')]:
    summary = load(name + '/summary.json')
    road = next(row for row in summary['all_physical_link_summaries'] if row['link_or_cell'] == '74')
    snapshots = sorted(road['snapshots'].values(), key=lambda row: row['sec'])
    times = [row['sec'] for row in snapshots]
    axes[0, 0].plot(times, [row['mean_speed_kph'] for row in snapshots], 'o-', color=color, label=label, ms=4)
    axes[0, 1].plot(times, [row['n'] for row in snapshots], 'o-', color=color, label=label, ms=4)
    boundaries.append(load(name + '/boundary_metrics.json')['time_rows'])
assert [r['sim_sec'] for r in boundaries[0]] == [r['sim_sec'] for r in boundaries[1]]
times = [900, *[r['sim_sec'] for r in boundaries[0]]]
delta = [0, *[b['ttd_observed_plus_terminal_cumulative'] - a['ttd_observed_plus_terminal_cumulative']
             for a, b in zip(*boundaries)]]
axes[1, 0].step(times, delta, where='post', color='#835490', lw=1.8)
axes[1, 0].axhline(0, color='#697581', lw=.8)
axes[1, 0].text(.035, .055, '종료: -9대', transform=axes[1, 0].transAxes, fontsize=11)
physical = sorted([r for r in comparison['spatial'] if r['link_or_cell'].isdigit()],
                  key=lambda r: abs(r['residence_veh_h'][2]), reverse=True)[:6]
physical.reverse()
values = [r['residence_veh_h'][2] for r in physical]
axes[1, 1].barh([r['link_or_cell'] for r in physical], values,
               color=['#bd683b' if v > 0 else '#39789c' for v in values])
axes[1, 1].axvline(0, color='#697581', lw=.8)
axes[0, 0].set(title='동측 진입부 74번 도로', ylabel='차량 평균 속도 [km/h]')
axes[0, 1].set(title='같은 도로의 재고', ylabel='차량 수 [veh]')
axes[1, 0].set(title='Ω 누적 TTD 변화: VSL100 - 기준', ylabel='유출 사건 차이 [veh]')
axes[1, 1].set(title='물리 도로별 체류 변화 상위 6개', xlabel='VSL100 - 기준 [veh·h]', ylabel='도로 번호')
axes[0, 0].legend(frameon=False, fontsize=10, loc='lower left')
for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
    ax.set_xlim(900, 1350)
    ax.set_xlabel('시뮬레이션 시각 [s]')
for ax in axes.flat:
    ax.grid(alpha=.18)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
fig.suptitle('VSL 전달은 정상 · 이 구간의 교통 결과는 악화', fontsize=19, y=.985)
fig.text(.065, .925, '80/50 · seed13 · 동일 1350초 실행 · 기준과 900초까지 FZP 939,080행 일치', fontsize=11)
fig.text(.065, .02, '상단은 30초 간격 순간 관측. 제한속도 설정은 별도의 적용 시 readback으로 확인.\n'
         'Ω TTT +0.6093veh·h / TTD -9대 / 진입 2166대로 동일 / 사라짐 12대씩 TTD 제외. GNE 선택 명령이 아닌 재생 검증.',
         fontsize=9, color='#4d5963')
fig.tight_layout(rect=(.025, .07, .99, .91), h_pad=2.0, w_pad=2.0)
for ext in ('png', 'svg'):
    fig.savefig(Path(__file__).with_name('VSL_REPLAY_NATIVE450.' + ext), dpi=160, facecolor='white')
print(Path(__file__).with_name('VSL_REPLAY_NATIVE450.png'))
