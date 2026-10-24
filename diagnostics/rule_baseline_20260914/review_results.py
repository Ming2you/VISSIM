"""Small post-run aggregation and figures from the existing native summaries."""
from pathlib import Path
import csv
import json
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARMS = ('none', 'vsl', 'rm', 'both')
LABELS = ('무제어', 'VSL', 'RM', 'VSL + RM')


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def save_csv(path, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    sys.path.insert(0, str(HERE / '.plot-deps'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False,
                         'font.size': 11, 'figure.dpi': 150})
    out = HERE / 'review_v1'
    out.mkdir(exist_ok=False)
    mapping = json.loads((ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text(encoding='utf-8'))
    mainline = {str(x) for v in mapping['freeway_model_links'].values() for x in v['chain_links']}
    connectors = {str(r['connector']) for r in mapping['ramp_meters']}
    metrics, times, cells, ramp_totals, congestion = [], {}, {}, [], []
    for arm in ARMS:
        native = HERE / arm / 'native'
        area = json.loads((native / 'area_metrics.json').read_text(encoding='utf-8'))
        proof = json.loads((native / 'summary.json').read_text(encoding='utf-8'))
        rows = read(native / 'area_timeseries.csv'); times[arm] = rows
        at = {int(float(r['sim_sec'])): r for r in rows}
        links = read(native / 'links_150s.csv')
        result = {'arm': arm, 'TTT_0_3000_veh_h': area['ttt_veh_h'],
                  'TTT_900_3000_veh_h': float(at[3000]['ttt_veh_h_cumulative']) - float(at[900]['ttt_veh_h_cumulative']),
                  'TTD_0_3000_events': area['ttd_observed_plus_terminal_events'],
                  'TTD_900_3000_events': int(at[3000]['ttd_observed_plus_terminal_cumulative']) - int(at[900]['ttd_observed_plus_terminal_cumulative']),
                  'end_omega_n': area['censored_last_observed_inside_vehicles'],
                  'native_removed_vehicles': proof['native_removals'],
                  'unresolved_inside_disappearances': area['unresolved_inside_disappearances']}
        for group in ('mainline', 'onramp_connector', 'urban_and_other'):
            selected = [r for r in links if r['inside_omega'] == 'True' and
                        ('mainline' if r['link'] in mainline else 'onramp_connector' if r['link'] in connectors else 'urban_and_other') == group]
            result[group + '_TTT_veh_h'] = math.fsum(float(r['ttt_veh_h']) for r in selected)
            result[group + '_stopped_veh_h'] = math.fsum(float(r['stopped_veh_h']) for r in selected)
        assert math.isclose(sum(result[g+'_TTT_veh_h'] for g in ('mainline','onramp_connector','urban_and_other')), result['TTT_0_3000_veh_h'], abs_tol=1e-7)
        metrics.append(result)
        ramps = read(native / 'ramps_150s.csv')
        for mid in sorted({r['ramp'] for r in ramps}):
            selected = [r for r in ramps if r['ramp'] == mid and int(r['start_sec']) >= 900]
            ramp_totals.append({'arm': arm, 'ramp': mid, 'merges_900_3000': sum(int(r['observed_connector_to_mainline']) for r in selected),
                'connector_TTT_900_3000_veh_h': math.fsum(float(r['connector_ttt_veh_h']) for r in selected),
                'connector_stop_900_3000_veh_h': math.fsum(float(r['connector_stopped_veh_h']) for r in selected),
                'max_connector_n': max(int(r['connector_end_n']) for r in selected),
                'end_connector_n': int(selected[-1]['connector_end_n']),
                'approach_all_destinations_TTT_900_3000_veh_h': math.fsum(float(r['approach_all_destinations_ttt_veh_h']) for r in selected)})
        cells[arm] = read(native / 'fw_cells_30s.csv')
        for direction in ('E', 'W'):
            for cell in range(21):
                selected = [r for r in cells[arm] if r['direction'] == direction and int(r['cell']) == cell]
                flags = [int(r['n']) >= 5 and float(r['mean_speed_kph'] or 999) < 40 for r in selected]
                onset = next((int(selected[i]['sec']) for i in range(len(flags)-2) if all(flags[i:i+3])), None)
                tail = [r for r in selected if int(r['sec']) > 2700 and int(r['n']) > 0]
                congestion.append({'arm': arm, 'direction': direction, 'cell': cell,
                    'first_three_samples_below40_sec': onset,
                    'samples_below40_nge5': sum(flags), 'max_stopped': max(int(r['stopped']) for r in selected),
                    'tail2700_3000_vehicle_weighted_speed_kph': sum(int(r['n'])*float(r['mean_speed_kph']) for r in tail)/sum(int(r['n']) for r in tail) if tail else None})
    for row in metrics:
        row['TTT_change_percent'] = 100*(row['TTT_0_3000_veh_h']/metrics[0]['TTT_0_3000_veh_h']-1)
        row['TTT_controlled_window_change_percent'] = 100*(row['TTT_900_3000_veh_h']/metrics[0]['TTT_900_3000_veh_h']-1)
    for name, rows in (('performance', metrics), ('ramps', ramp_totals), ('congestion', congestion)):
        save_csv(out / (name+'.csv'), rows)
    (out / 'summary.json').write_text(json.dumps({'performance': metrics,
        'scope': '0–3000s seed13; same common history to900s; stopped is speed<=1km/h; connector-only ramp costs exclude shared approach traffic.',
        'congestion_rule': 'Three consecutive30s samples with mean speed<40km/h and at least5 vehicles; descriptive threshold, not a calibrated capacity criterion.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    colors = ('#444444', '#c85f28', '#227ca8', '#8758a5')
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)
    baseline = {int(float(r['sim_sec'])): float(r['ttt_veh_h_cumulative']) for r in times['none']}
    for arm, label, color in zip(ARMS, LABELS, colors):
        rows = times[arm]; x = [float(r['sim_sec'])/60 for r in rows]
        axes[0].plot(x, [int(r['inside_vehicles']) for r in rows], label=label, color=color, lw=1.5)
        axes[1].plot(x, [float(r['ttt_veh_h_cumulative'])-baseline[int(float(r['sim_sec']))] for r in rows], label=label, color=color, lw=1.5)
    for ax in axes:
        ax.axvline(15, color='#888888', ls='--', lw=1); ax.set_xlabel('시뮬레이션 시간 [분]'); ax.grid(alpha=.2)
    axes[0].set_ylabel('Ω 내부 차량 수 [대]'); axes[1].set_ylabel('무제어 대비 누적 TTT 증가 [차량·시간]')
    axes[0].legend(); axes[1].axhline(0, color='black', lw=.7)
    fig.suptitle('고속도로80% · 도시50% · seed13 · 100km/h 기준 | 제어 시작15분')
    fig.savefig(out/'native_performance.png'); plt.close(fig)
    fig, axes = plt.subplots(4, 2, figsize=(12, 10), constrained_layout=True, sharex=True, sharey=True)
    for i, (arm, label) in enumerate(zip(ARMS, LABELS)):
        for j, direction in enumerate(('E', 'W')):
            matrix = np.full((21, 100), np.nan)
            for r in cells[arm]:
                if r['direction'] == direction and int(r['n']) >= 5:
                    matrix[int(r['cell']), int(r['sec'])//30-1] = float(r['mean_speed_kph'])
            im = axes[i,j].imshow(matrix, origin='lower', aspect='auto', extent=(0,50,-.5,20.5), cmap='RdYlGn', vmin=0, vmax=100, interpolation='nearest')
            axes[i,j].axvline(15, color='black', ls='--', lw=.8)
            axes[i,j].set_title(label+' · '+('동측' if direction=='E' else '서측'))
            axes[i,j].set_yticks([0,5,8,10,15,20]); axes[i,j].set_ylabel('모델 셀 번호 (흐름 → 증가)')
    for ax in axes[-1]: ax.set_xlabel('시뮬레이션 시간 [분]')
    fig.colorbar(im, ax=axes, label='실측 셀 평균속도 [km/h]', shrink=.85)
    fig.suptitle('실제 혼잡의 발생·전파 | 30초 표본, 차량5대 미만은 공백')
    fig.savefig(out/'native_spacetime.png'); plt.close(fig)
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == '__main__':
    main()
