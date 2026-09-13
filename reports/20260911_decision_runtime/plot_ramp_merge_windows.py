"""Plot three already completed native/model windows; no simulation or FZP scan."""
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
doc = json.loads((D / 'ramp_merge_three_windows_v1.json').read_text())
assert doc['completed'] and doc['native_total_450'] == 301
font_manager.fontManager.addfont('C:/Windows/Fonts/malgun.ttf')
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False,
                     'font.size': 10})
fig, axes = plt.subplots(2, 4, figsize=(14, 8), sharex=True, sharey=True)
for ax, row in zip(axes.flat, doc['rows']):
    ax.plot(range(3), row['native_merges150'], 'o-', color='#28688e', lw=2,
            label='실제 VISSIM')
    ax.plot(range(3), row['model_merges150']['original'], 's--', color='#b36139',
            label='현재 모형', lw=1.7, markersize=5)
    ax.plot(range(3), row['model_merges150']['sc1005_unsignalized_only'], 'x:',
            color='#407c4c', label='SC1005 신호 종속만 수정한 모형', lw=1.7, markersize=7)
    ax.set_title(f"램프 {row['connector']}", fontweight='bold')
    ax.set_xticks(range(3), ['900–1050', '1050–1200', '1200–1350'], rotation=15)
    ax.set_ylim(0, 30)
    ax.grid(alpha=.2)
    ax.spines[['top', 'right']].set_visible(False)
for ax in axes[:, 0]:
    ax.set_ylabel('150초 본선 합류량 [veh]')
for ax in axes[1, :]:
    ax.set_xlabel('집계 구간 [s]')
fig.suptitle('8개 램프: 합계가 가리는 시간대별 합류 예측 오차', fontsize=18, y=.985)
fig.legend(*axes[0, 0].get_legend_handles_labels(), loc='upper center',
           bbox_to_anchor=(.5, .947), ncol=3, frameon=False)
fig.text(.06, .865, '고속도로 80% · 도시 50% · seed 13 · 동일 명령 · 모형은 900초에서 450초 예측', fontsize=11)
fig.text(.06, .037,
         '8개 램프 × 3구간의 MAE: 현재 5.83 → SC1005 수정 5.71 veh/구간. 실제 합류 301대는 Ω 내부 이동이며 TTD가 아님.\n'
         '인접한 세 구간의 단일 예측 비교이며, 첨두·회복 대표 상태 검증이나 controller의 교통 개선 결과가 아님.',
         fontsize=10, color='#49565f')
fig.tight_layout(rect=(.015, .09, .995, .845))
for suffix in ('png', 'svg'):
    fig.savefig(Path(__file__).with_name(f'RAMP_MERGE_WINDOWS.{suffix}'), dpi=160, facecolor='white')
print(Path(__file__).with_name('RAMP_MERGE_WINDOWS.png'))
