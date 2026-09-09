"""Plot the frozen first-interval evidence without running a traffic model."""
from pathlib import Path
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    source = ROOT / 'diagnostics/live_beta0_interval_prediction.json'
    raw = source.read_bytes()
    data = json.loads(raw)
    assert data['valid_source_freeze'] and not data['source_changes_during_probe']
    residence = data['comparison']['residence_decomposition']
    model_ttt = [residence['freeway_model_veh_h'], residence['remaining_omega_model_veh_h']]
    observed_ttt = [residence['freeway_physical_veh_h'], residence['remaining_omega_physical_veh_h']]
    model_ttt.append(sum(model_ttt))
    observed_ttt.append(sum(observed_ttt))
    model_flows = [sum(row[key] for row in data['model']['freeway_mass_balance'].values()) for key in
                   ('mainline_admitted_veh', 'ramp_merge_veh', 'offramp_exit_veh', 'terminal_exit_veh')]
    observed_flows = [sum(row[key] for row in data['physical']['freeway_chain_stock_and_flow'].values()) for key in
                      ('appeared_veh', 'observed_entry_veh', 'observed_exit_veh', 'disappeared_veh')]
    speed_rows = [next(row for row in data['cells_1050'] if row['link'] == 'FW_E' and row['cell'] == cell)
                  for cell in (8, 9)]
    panels = [
        ('Residence', 'Vehicle-hours over 150 s', ['Freeway', 'Other control\narea', 'Total control\narea'], model_ttt, observed_ttt, 2),
        ('Freeway stock and flows', 'Vehicles over 150 s', ['Mainline\nentry', 'Ramp\nmerge', 'Off-ramp\nentry', 'Terminal\nexit'], model_flows, observed_flows, 1),
        ('Local speeds at 1050 s', 'km/h', ['E8', 'E9'], [r['predicted_speed_kph'] for r in speed_rows],
         [r['observed_speed_kph'] for r in speed_rows], 1),
    ]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.titlesize': 14,
                         'axes.labelsize': 11, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.2), gridspec_kw={'width_ratios': [1.2, 1.5, .85]})
    rows = []
    for ax, (title, unit, labels, predictions, observations, precision) in zip(axes, panels):
        xs, width = np.arange(len(labels)), .36
        for shift, values, label, color in [(-width / 2, predictions, 'Model', '#db7c28'),
                                             (width / 2, observations, 'Physical', '#247da8')]:
            bars = ax.bar(xs + shift, values, width, label=label, color=color)
            ax.bar_label(bars, labels=[f'{value:.{precision}f}' for value in values], padding=4, fontsize=10)
            rows.extend({'panel': title, 'category': category.replace('\n', ' '), 'series': label,
                         'unit': unit, 'value': value} for category, value in zip(labels, values))
        ax.set_xticks(xs, labels)
        ax.set_ylabel(unit)
        ax.set_title(title, loc='left', pad=27, weight='bold')
        ax.set_ylim(0, max(predictions + observations) * 1.19)
        ax.yaxis.grid(True, color='#e3e7eb', linewidth=.8)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    error = (model_ttt[-1] / observed_ttt[-1] - 1) * 100
    axes[0].text(0, 1.02, f'Total error +{error:.2f}%; component errors offset', transform=axes[0].transAxes, fontsize=10)
    model_delta = model_flows[0] + model_flows[1] - model_flows[2] - model_flows[3]
    observed_delta = observed_flows[0] + observed_flows[1] - observed_flows[2] - observed_flows[3]
    axes[1].text(0, 1.02, f'Stock change: model +{model_delta:.1f}, physical +{observed_delta:.0f}',
                 transform=axes[1].transAxes, fontsize=10)
    axes[2].text(0, 1.02, 'Same cell and endpoint', transform=axes[2].transAxes, fontsize=10)
    fig.suptitle('Aggregate residence agreement conceals flow and local speed errors', x=.06, y=.965,
                 ha='left', fontsize=19, weight='bold')
    fig.text(.06, .885, 'Executed beta0 command at 900 s  |  prediction and observation: 900–1050 s  |  seed 13',
             fontsize=12, color='#46515b')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper right', bbox_to_anchor=(.96, .90), ncol=2, frameon=False)
    fig.text(.06, .105, 'Residence and flow: complete 1 s vehicle records. Terminal exits are bounded inferences. Speed: paused COM at 1050 s.', fontsize=10)
    fig.text(.06, .071, 'Native records and paused COM differ slightly in timing. The run stopped at its next decision; these are interval checks, not full-run performance or capacity estimates.', fontsize=10)
    fig.subplots_adjust(left=.06, right=.97, top=.74, bottom=.24, wspace=.30)
    destination = ROOT / 'diagnostics/first_interval_prediction'
    fig.savefig(destination.with_suffix('.png'), dpi=170, facecolor='white')
    fig.savefig(destination.with_suffix('.svg'), facecolor='white')
    plt.close(fig)
    with destination.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    provenance = {'source': str(source.relative_to(ROOT)), 'source_sha256': hashlib.sha256(raw).hexdigest(),
                  'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'csv_sha256': hashlib.sha256(destination.with_suffix('.csv').read_bytes()).hexdigest(),
                  'values': len(rows), 'model_stock_change_veh': model_delta, 'physical_stock_change_veh': observed_delta,
                  'scope': data['method'], 'qa': 'Inspect the exported PNG before delivery.'}
    destination.with_name(destination.name + '_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'png': str(destination.with_suffix('.png')), 'plotted_values': len(rows)}))


if __name__ == '__main__':
    main()
