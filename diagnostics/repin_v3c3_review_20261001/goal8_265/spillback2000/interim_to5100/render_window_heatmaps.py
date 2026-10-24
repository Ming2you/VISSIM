"""Render this requested interim comparison from saved aggregates, not live FZP."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
summary = json.loads((HERE / 'summary.json').read_text(encoding='utf8'))
geo = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json').read_text(encoding='utf8'))
data = {arm: np.load(HERE / f'{arm}_snapshots.npz') for arm in ('nc', 'sdmpc')}
end = summary['end_sec']
times = data['nc']['times']
assert np.array_equal(times, data['sdmpc']['times'])
assert end == times[-1] == 5100
previous_nc = np.load(HERE.parent.parent / 'interim_verified_to6150/nc_snapshots.npz')
assert np.array_equal(data['nc']['stocks'], previous_nc['stocks'][:len(times)])
assert np.array_equal(data['nc']['cumulative_ttt'], previous_nc['cumulative_ttt'][:len(times)])
for arm in data:
    stock = data[arm]['stocks']
    total = np.trapezoid(stock[:, :3].sum(axis=1), times) / 3600
    assert abs(total - summary['comparison_veh_h']['Omega'][arm]) < 1e-8
    assert abs(sum(summary['comparison_veh_h'][part][arm] for part in ('FW_E', 'FW_W', 'Omega_other')) - total) < 1e-8

plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False,
                     'font.size': 12, 'figure.facecolor': 'white'})
samples = times[1:]
edges = np.r_[samples[0], (samples[:-1] + samples[1:]) / 2, samples[-1]]
cmap = plt.get_cmap('RdYlBu').copy()
cmap.set_bad('#e4e4e4')
for road, label in [('FW_E', '동측'), ('FW_W', '서측')]:
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 10.4), sharex=True, sharey=True)
    fig.subplots_adjust(left=.085, right=.765, bottom=.18, top=.85, hspace=.25)
    titles = ['무제어 · VSL110', 'SDMPC · 병목 VSL90: 1800–5700초' if road == 'FW_E' else 'SDMPC · 서측 VSL110 유지']
    for ax, arm, title in zip(axes, ('nc', 'sdmpc'), titles):
        speed = data[arm][road + '_speed']
        assert speed.shape == (31, len(samples))
        mesh = ax.pcolormesh(edges, np.array(geo['bounds'][road]) / 1000, speed,
                             cmap=cmap, vmin=0, vmax=120, shading='flat')
        ax.set(xlim=(1, end), ylim=(0, geo['bounds'][road][-1] / 1000),
               ylabel='진입점부터 거리 [km] → 하류')
        ax.set_title(title, fontsize=15, loc='left')
        if arm == 'sdmpc':
            ax.axvline(900, ls=':', color='#222222', lw=1.1)
            ax.axvline(1800, ls='--', color='#222222', lw=1.1)
        last = -1
        marks = sorted([b for b in geo['boundaries'] if b['road'] == road and b['kind'] in ('ramp', 'offramp')], key=lambda b: b['chain_pos_m'])
        for b in marks:
            y = b['chain_pos_m'] / 1000
            at = max(y, last + .45)
            last = at
            ax.axhline(y, color='#293443', lw=.45, alpha=.45, ls='--')
            ax.annotate(f"{b['connector']} {'진입' if b['kind'] == 'ramp' else '진출'}",
                        xy=(end, y), xytext=(end + 125, at), fontsize=9.5, va='center',
                        clip_on=False, arrowprops=dict(arrowstyle='-', lw=.6, color='#465566'))
    axes[-1].set_xlabel('시뮬레이션 시간 [초]')
    axes[-1].set_xticks([1, 900, 1800, 2700, 3600, 4500, end])
    axes[-1].tick_params(axis='x', labelsize=10)
    cax = fig.add_axes([.91, .28, .018, .47])
    fig.colorbar(mesh, cax=cax, label='관측 차량 평균속도 [km/h]', extend='max')
    fig.suptitle(f'{label} 본선 | 무제어 vs 현재 SDMPC 런', fontsize=19, y=.97)
    fig.text(.085, .917, f'동일 망·FW80/도시90·seed29 · 1–{end:,}초 · 31개 물리 셀', fontsize=12)
    fig.text(.085, .107, '150초 간격 순간 관측 · 연속 궤적 또는 150초 평균이 아님 · 회색: 관측 차량 없음', fontsize=10.8)
    fig.text(.085, .073, '제어 패널 세로선: 900초 SDMPC 시작(점선), 1800초 동측 병목 VSL 시작(파선)', fontsize=10.8)
    fig.text(.085, .039, '동측 병목 VSL은 시간창 밖 110km/h · 전체 런은 진행 중 · 두 조건 색상 범위 동일', fontsize=10.8, color='#555555')
    fig.savefig(HERE / f'{road}_NC_vs_SDMPC_to{end}.png', dpi=150)
    plt.close(fig)

(HERE / 'readout_validation.json').write_text(json.dumps({
    'status': 'passed', 'cutoff': end, 'prior_nc_prefix_exact': True,
    'independent_trapezoid_and_component_sums_passed': True,
    'vsl_schedule_label': 'bottleneck 90 for 1800 <= t < 5700, otherwise 110',
    'read_live_fzp': False, 'simulation_changed': False,
    'nature': '150-second snapshot interim estimate, not native performance verification'
}, indent=2) + '\n', encoding='utf8')
print('Snapshot calculations checked; both heatmaps rendered with the current VSL schedule.')
