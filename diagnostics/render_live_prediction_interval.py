"""Render a validated live interval audit; never run a model or simulator."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    source = args.report.resolve()
    raw = source.read_bytes()
    data = json.loads(raw)
    if not (data['replay_matches_executed_model'] and data['executed_command_audit_valid']
            and not data['source_changes_during_audit']):
        raise ValueError('A verified executed-model/command interval is required')
    destination = source.with_name(source.stem+'_figure')
    if any(destination.with_suffix(suffix).exists() for suffix in ('.png', '.svg', '.csv')):
        raise ValueError('Refusing to overwrite an existing figure')
    residence = data['comparison']['residence']
    keys = ['freeway', 'urban_and_ramps', 'omega']
    labels = ['Freeway', 'Urban + ramps', 'Total area']
    pred = [residence[k]['model_veh_h'] for k in keys]
    obs = [residence[k]['physical_veh_h'] for k in keys]
    stock_keys = [k+'_veh' for k in keys]
    stocks = [data['model']['final'][k] for k in stock_keys]
    physical = [data['comparison']['final_fzp'][k] for k in stock_keys]
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':11, 'svg.fonttype':'none'})
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.1), gridspec_kw={'width_ratios':[1.25, 1.25, .85]})
    rows = []
    for ax, title, unit, modeled, measured, digits in [
        (axes[0], 'Residence over the interval', 'Vehicle-hours', pred, obs, 2),
        (axes[1], 'Stock at the interval end', 'Vehicles', stocks, physical, 0),
    ]:
        xx = np.arange(3)
        for shift, values, label, color in [(-.19, modeled, 'Model', '#ce7527'), (.19, measured, 'Physical', '#247da8')]:
            bars = ax.bar(xx+shift, values, .36, label=label, color=color)
            ax.bar_label(bars, labels=[f'{v:.{digits}f}' for v in values], padding=4, fontsize=10)
            rows.extend({'panel':title, 'category':k, 'series':label, 'value':v, 'unit':unit}
                        for k,v in zip(keys, values))
        ax.set_xticks(xx, labels, fontsize=10)
        ax.set_ylim(0, max(modeled+measured)*1.20)
        ax.set_title(title, loc='left', weight='bold', pad=25)
        ax.set_ylabel(unit)
    ax = axes[2]
    td = data['model']['metrics']['ttd_veh']
    observed = data['physical']['totals']['observed_exit_veh']
    inferred = data['physical']['totals']['terminal_inferred_exit_veh']
    ax.bar(0, td, .55, color='#ce7527')
    ax.bar(1, observed, .55, color='#247da8')
    ax.bar(1, inferred, .55, bottom=observed, color='#acd1e2', edgecolor='#247da8', hatch='///')
    ax.text(0, td+14, f'{td:.1f}', ha='center')
    ax.text(1, observed+inferred+14, f'{observed+inferred:.0f}', ha='center')
    ax.text(1, observed/2, f'{observed}\nobserved', ha='center', va='center', color='white')
    ax.text(1, observed+inferred/2, f'{inferred}\ninferred', ha='center', va='center', fontsize=10)
    ax.set_xticks([0,1], ['Model', 'Physical'])
    ax.set_ylim(0, max(td,observed+inferred)*1.20)
    ax.set_title('Outward crossings (TTD)', loc='left', weight='bold', pad=25)
    ax.set_ylabel('Vehicle crossing events')
    rows.extend({'panel':'Outward crossings', 'category':k, 'series':s, 'value':v, 'unit':'Vehicle events'}
                for k,s,v in [('modeled','Model',td),('observed','Physical',observed),('terminal inferred','Physical',inferred)])
    for ax in axes:
        ax.yaxis.grid(True, color='#e3e7eb')
        ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
    start,end = data['interval_sec']
    fig.suptitle('Applied commands pass; freeway prediction error remains', x=.06, y=.96, ha='left', fontsize=19, weight='bold')
    fig.text(.06,.885, f'Actual source-aware MPC | {start}–{end} s | seed 13 | all four control vectors held in the replay', fontsize=11, color='#46515b')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper right', bbox_to_anchor=(.97,.86), ncol=2, frameon=False)
    axes[0].text(0,1.02, f"Freeway error +{residence['freeway']['error_veh_h']:.2f}; urban/ramps {residence['urban_and_ramps']['error_veh_h']:.2f}", transform=axes[0].transAxes, fontsize=10)
    axes[1].text(0,1.02, 'Physical: native 1 s vehicle-record phase', transform=axes[1].transAxes, fontsize=10)
    fig.text(.06,.105, 'Area = controlled freeway + protected urban network. Physical residence uses trapezoidal integration of complete 1 s records.', fontsize=10)
    unknown = data['physical']['totals'].get('unresolved_inside_disappearance_veh',0)
    fig.text(.06,.069, f'Terminal departures are inferred separately; {unknown} unresolved disappearances receive no exit credit. One interval is not full-run performance.', fontsize=10)
    fig.subplots_adjust(left=.06, right=.97, top=.72, bottom=.25, wspace=.30)
    for suffix in ('.png','.svg'):
        fig.savefig(destination.with_suffix(suffix), dpi=170, facecolor='white')
    plt.close(fig)
    with destination.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    evidence = {'source':str(source.relative_to(ROOT)), 'source_sha256':hashlib.sha256(raw).hexdigest(),
                'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'plotted_values':len(rows),
                'qa':'Inspect the exported PNG before delivery.'}
    destination.with_name(destination.name+'_provenance.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    print(str(destination.with_suffix('.png')))


if __name__ == '__main__':
    main()
