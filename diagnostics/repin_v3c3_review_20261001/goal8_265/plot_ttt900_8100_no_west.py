"""Reproduce the requested warmup-excluded TTT curves from native stock counts."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import StrMethodFormatter

HERE = Path(__file__).resolve().parent
BASE = HERE / 'current_native_analysis_to8100'
REF = json.loads((HERE / 'warmup_excluded900_8100_no_west.json').read_bytes())
OUT = HERE / 'ttt900_8100_no_west'
OUT.mkdir(exist_ok=True)


def stock_frames(path):
    """Read only time/link columns; reconcile every frame against the audited stock."""
    columns = None
    stamp = None
    counts = Counter()
    with path.open(encoding='utf-8-sig', errors='replace') as stream:
        for line in stream:
            if line.startswith('$VEHICLE:'):
                columns = [s.strip().upper() for s in line.split(':', 1)[1].split(';')]
                ti, li = columns.index('SIMSEC'), columns.index('LANE\\LINK\\NO')
                continue
            if line.startswith(('*', '$')) or not line.strip():
                continue
            assert columns is not None
            row = line.split(';')
            assert len(row) == len(columns)
            t = float(row[ti])
            if stamp is not None and t != stamp:
                assert t > stamp
                yield stamp, counts
                counts = Counter()
            if t > 8100:
                return
            stamp = t
            counts[str(int(row[li]))] += 1
    if stamp is not None and stamp <= 8100:
        yield stamp, counts


def extract(arm):
    record = REF['arms'][arm]
    path = Path(record['fzp_source'])
    assert path.stat().st_size == record['fzp_size'], 'Native source changed'
    for name, digest in REF['source_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    metrics = json.loads((BASE / arm / 'area_metrics.json').read_bytes())
    geo_path = next(Path(p) for p in REF['source_sha256'] if p.endswith('geometry.json'))
    geo = json.loads(geo_path.read_bytes())
    west = {str(cell['link']) for cell in geo['chains']['FW_W']}
    inside = {link for link, row in metrics['physical_link_residence'].items() if row['inside']}
    with (BASE / arm / 'area_timeseries.csv').open(encoding='utf-8-sig', newline='') as stream:
        audited = {float(r['sim_sec']): r for r in csv.DictReader(stream)}
    times, stocks, west_stocks = [0.], [0.], [0.]
    native_rows = 0
    for t, counts in stock_frames(path):
        assert t in audited and audited[t]['source'] == 'fzp'
        total_inside = sum(n for link, n in counts.items() if link in inside)
        west_n = sum(counts[link] for link in west)
        assert total_inside == int(audited[t]['inside_vehicles']), (arm, t)
        assert sum(counts.values()) == int(audited[t]['network_vehicles'])
        times.append(t)
        stocks.append(total_inside - west_n)
        west_stocks.append(west_n)
        native_rows += sum(counts.values())
    assert native_rows == metrics['sampling']['fzp_rows']
    assert len(times) - 1 == metrics['sampling']['fzp_snapshots']
    assert abs(times[-1] - 8095.1) < 1e-6
    times.append(8100.)
    stocks.append(stocks[-1])
    west_stocks.append(west_stocks[-1])
    t, n = np.array(times), np.array(stocks)
    # Check the whole curve against the previous independent domain totals.
    total = np.sum((n[:-1] + n[1:]) * np.diff(t) / 7200)
    expected = record['without_west'] + record['warmup_0_900']['FW_E'] + record['warmup_0_900']['urban_ramps']
    assert abs(total - expected) < 1e-7, (arm, total, expected)
    cut_t = np.r_[900., t[t > 900]]
    cut_n = np.r_[np.interp(900., t, n), n[t > 900]]
    cumulative = np.r_[0., np.cumsum((cut_n[:-1] + cut_n[1:]) * np.diff(cut_t) / 7200)]
    assert abs(cumulative[-1] - record['without_west']) < 1e-7
    assert np.all(np.diff(cumulative) >= 0)
    return cut_t, cut_n, cumulative, native_rows


def main():
    curves = {}
    for arm in ('nc', 'sdmpc'):
        curves[arm] = extract(arm)
        print(f'{arm}: {curves[arm][3]} native rows; final TTT={curves[arm][2][-1]:.8f}', flush=True)
    t = curves['nc'][0]
    assert np.array_equal(t, curves['sdmpc'][0])
    nc, control = curves['nc'][2], curves['sdmpc'][2]
    gain = nc[-1] - control[-1]
    reduction = 100 * gain / nc[-1]
    with (OUT / 'cumulative_ttt.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['sim_sec', 'nc_vehicles', 'control_vehicles', 'nc_cumulative_ttt_veh_h', 'control_cumulative_ttt_veh_h', 'nc_minus_control_veh_h'])
        writer.writerows(zip(t, curves['nc'][1], curves['sdmpc'][1], nc, control, nc-control))
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none'})
    fig, ax = plt.subplots(figsize=(12.5, 7.1))
    fig.subplots_adjust(left=.10, right=.90, top=.82, bottom=.19)
    fig.text(.10, .94, 'Cumulative TTT', fontsize=22, weight='bold', color='#20252B')
    fig.text(.10, .888, '900–8100 s  |  Eastbound freeway + urban roads and ramps  |  Seed 29', fontsize=12, color='#555B62')
    ax.plot(t, nc, color='#62676F', lw=2.3, ls='--', label='No control')
    ax.plot(t, control, color='#0072B2', lw=2.5, label='SDMPC + fixed VSL90')
    ax.fill_between(t, control, nc, color='#0072B2', alpha=.07)
    ax.scatter([8100, 8100], [nc[-1], control[-1]], color=['#62676F', '#0072B2'], s=28, zorder=4, clip_on=False)
    for value, color, yoff in [(nc[-1], '#62676F', 7), (control[-1], '#0072B2', -9)]:
        ax.annotate(f'{value:,.2f}', (8100, value), xytext=(9, yoff), textcoords='offset points', color=color, fontsize=12, va='center', annotation_clip=False)
    ax.text(.57, .38, f'TTT reduction: {reduction:.2f}%\n{gain:,.2f} veh·h', transform=ax.transAxes, color='#0072B2', fontsize=15, linespacing=1.7)
    ax.set(xlim=(900, 8100), ylim=(0, 6000), xlabel='Simulation time [s]', ylabel='Cumulative TTT [veh·h]')
    ax.set_xticks(np.arange(900, 8101, 900))
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
    ax.grid(axis='y', color='#DFE3E8', lw=.7)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_color('#8F969E')
    ax.legend(loc='upper left', frameon=False, fontsize=12)
    fig.text(.10, .070, 'Westbound mainline excluded; all ramps in Ω retained. Cumulative TTT starts at zero at 900 s.', fontsize=9.2, color='#5B6168')
    fig.text(.10, .042, '5 s native samples; last 4.9 s held constant. Unequal vehicle removals and outside-Ω costs are not corrected.', fontsize=9.2, color='#5B6168')
    fig.savefig(OUT / 'cumulative_ttt.png', dpi=200, facecolor='white')
    fig.savefig(OUT / 'cumulative_ttt.svg', facecolor='white')
    plt.close(fig)
    report = {'start_sec': 900, 'end_sec': 8100, 'excluded': REF['excluded'], 'unit': 'veh*h', 'nc': float(nc[-1]), 'control': float(control[-1]), 'reduction_percent': float(reduction), 'reduction_veh_h': float(gain), 'curves_start_at_zero': True, 'native_rows': {a: curves[a][3] for a in curves}, 'all_frames_match_audited_omega_stock': True, 'final_totals_match_previous_domain_calculation': True, 'source': str(HERE / 'warmup_excluded900_8100_no_west.json')}
    (OUT / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
