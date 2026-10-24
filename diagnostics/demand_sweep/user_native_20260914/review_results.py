"""Post-run figures and compact tables; reads derived CSVs, never opens VISSIM."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results_v1'


def read(name):
    with (RESULTS / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    ramps = defaultdict(list)
    for r in read('ramps_150s.csv'):
        ramps[r['connector']].append(r)
    table = []
    for connector, rows in ramps.items():
        table.append(dict(connector=connector,
            total_merges=sum(int(r['observed_connector_to_mainline']) for r in rows),
            merges_900_3000=sum(int(r['observed_connector_to_mainline']) for r in rows
                if int(r['start_sec']) >= 900 and int(r['end_sec']) <= 3000),
            peak_150s_rate_vph=max(int(r['observed_connector_to_mainline']) * 24 for r in rows),
            max_150s_snapshot_connector_n=max(int(r['connector_end_n']) for r in rows),
            end_connector_n=int(rows[-1]['connector_end_n']),
            stopped_veh_h=sum(float(r['connector_stopped_veh_h']) for r in rows)))
    area = read('area_timeseries.csv')
    selected_area = [r for r in area if int(float(r['sim_sec'])) in (900,1800,2700,3600,4500,5400,7200,8100,9000)]
    cells = read('fw_cells_30s.csv')
    cell_groups = defaultdict(list)
    for r in cells:
        cell_groups[(r['direction'], int(r['cell']))].append(r)
    summaries = []
    for (direction, cell), rows in sorted(cell_groups.items()):
        run = []
        onset = None
        for r in rows:
            eligible = int(r['n']) >= 5 and r['mean_speed_kph'] != ''
            if eligible and float(r['mean_speed_kph']) < 30:
                run.append(int(r['sec']))
                if onset is None and run[-1] - run[0] >= 120:
                    onset = run[0]
            else:
                run = []
        tail = [r for r in rows if int(r['sec']) > 8100 and int(r['n']) >= 5]
        summaries.append(dict(direction=direction, cell=cell+1,
            first_120s_span_congested_sample=onset,
            last_900s_eligible_samples=len(tail),
            last_900s_sample_mean_speed=(sum(float(r['mean_speed_kph']) for r in tail)/len(tail) if tail else None),
            final_sample_n=int(rows[-1]['n']),
            final_sample_speed=(float(rows[-1]['mean_speed_kph']) if rows[-1]['mean_speed_kph'] else None)))
    output = dict(ramps=table, area_checkpoints=selected_area, cells=summaries,
        definitions={'congestion':'n>=5 and mean speed<30 km/h at consecutive 30-second snapshots spanning at least 120 seconds (5 samples); not continuous proof',
        'peak_ramp_rate':'150-second observed connector-to-mainline count multiplied by 24; not saturation capacity',
        'connector_inventory':'All vehicles on physical connector, including moving vehicles; shared urban approach excluded',
        'stopped':'speed<=1 km/h', 'cell_speed':'Instantaneous vehicle mean at each 30-second snapshot, not 30-second average'})
    (HERE / 'RESULTS_COMPACT.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')

    sys.path.insert(0, str(HERE.parents[1] / 'rule_baseline_20260914' / '.plot-deps'))
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'Malgun Gothic', 'axes.unicode_minus':False, 'font.size':11})
    fig, axes = plt.subplots(2, 1, figsize=(14, 8.2), sharex=True, layout='constrained')
    for ax, direction, title in zip(axes, ('E','W'), ('동측 FW-E','서측 FW-W')):
        grid = np.full((21, 300), np.nan)
        for r in cells:
            if r['direction'] == direction and int(r['n']) >= 5 and r['mean_speed_kph']:
                grid[int(r['cell']), int(r['sec'])//30-1] = float(r['mean_speed_kph'])
        cmap = plt.get_cmap('RdYlBu').copy()
        cmap.set_bad('#eeeeee')
        im = ax.imshow(grid, origin='lower', aspect='auto', extent=(0,150,.5,21.5), vmin=0, vmax=120, cmap=cmap, interpolation='nearest')
        ax.set_yticks([1,4,7,10,13,16,19,21])
        ax.set_ylabel('셀 번호 (진행 방향 → 증가)')
        ax.set_title(title, loc='left', weight='bold')
        ax.axvline(90, color='black', linestyle='--', alpha=.55)
    axes[-1].set_xlabel('시뮬레이션 시간 [분]')
    fig.colorbar(im, ax=axes, label='순간 셀 평균 속도 [km/h] · 5대 미만 회색', shrink=.9)
    fig.suptitle('사용자 수정망 · 저장 교통 설정 유지 · seed 13 · 9000초\n30초 간격 FZP 표본 | 90분 이후에도 저장 수요 계속 유입', fontsize=16)
    fig.savefig(HERE/'freeway_speed.png', dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True, layout='constrained')
    axes[0].plot([float(r['sim_sec'])/60 for r in area], [int(r['inside_vehicles']) for r in area], color='#243b53')
    axes[0].set_ylabel('Ω 내부 차량 [대]')
    axes[0].set_title('제어 영역 재고', loc='left', weight='bold')
    for connector in ('10482','10681','10639','10644'):
        rows = ramps[connector]
        axes[1].plot([int(r['end_sec'])/60 for r in rows], [int(r['observed_connector_to_mainline'])*24 for r in rows], label=connector)
        axes[2].plot([int(r['end_sec'])/60 for r in rows], [int(r['connector_end_n']) for r in rows], label=connector)
    axes[1].set_ylabel('본선 합류 [대/h]')
    axes[1].set_title('실제 합류량 · 150초 집계 (용량 측정값 아님)', loc='left', weight='bold')
    axes[2].set_ylabel('Connector 차량 [대]')
    axes[2].set_title('150초 경계 재고 · 주행 차량 포함, 상류 접근도로 제외', loc='left', weight='bold')
    axes[2].set_xlabel('시뮬레이션 시간 [분]')
    axes[1].legend(ncol=4)
    for ax in axes:
        ax.grid(alpha=.2)
        ax.axvline(90, color='black', linestyle='--', alpha=.45)
    fig.suptitle('사용자 수정망 · 9000초 무제어 결과\n미터 8개 native OFF | 원본 수요·경로·신호·희망속도 유지', fontsize=16)
    fig.savefig(HERE/'inventory_ramps.png', dpi=160)
    plt.close(fig)
    print(json.dumps(dict(ramps=table,area_checkpoints=selected_area),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
