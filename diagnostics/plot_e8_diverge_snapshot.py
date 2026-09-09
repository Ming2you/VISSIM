"""Export exact common-time vehicle positions around the E9 diverge."""
from pathlib import Path
import bisect
import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / '.review-deps')]
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from diagnostics.probe_e8_lane_receiving import IndexedFzp, RUNS


def main():
    contract_path = ROOT / 'diagnostics/e8_diverge_snapshot_chart.json'
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    mapping_path = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    network_path = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))['freeway_model_links']['FW_E']
    offsets = dict(zip(mapping['chain_links'], mapping['chain_offsets_m']))
    bounds = mapping['segment_bounds_m']
    low, split, high = [bounds[i] for i in (8, 9, 10)]
    network = ET.parse(network_path).getroot()
    nodes = {}
    for number, role in (('10639', 'merge'), ('10682', 'diverge'), ('10681', 'merge')):
        node = network.find(f'./links/link[@no="{number}"]')
        endpoint = node.find('fromLinkEndPt' if role == 'diverge' else 'toLinkEndPt')
        nodes[number] = offsets[int(endpoint.get('lane').split()[0])] + float(endpoint.get('pos'))
    rows, sources = [], {}
    for label, run in RUNS.items():
        files = list((ROOT / 'evaluation/runs' / run / 'vissim_eval').glob('*.fzp'))
        if len(files) != 1:
            raise ValueError(f'Expected one native FZP for {run}')
        reader = IndexedFzp(files[0])
        try:
            vehicles = reader.snapshot(contract['time_sec'])
            for vehicle, (link, lane, pos, speed) in vehicles.items():
                if link not in offsets:
                    continue
                chain = offsets[link] + pos
                if low <= chain < high:
                    cell = bisect.bisect_right(bounds, chain) - 1
                    rows.append(dict(run_label=label, run=run, seed=13, sim_sec=contract['time_sec'],
                        vehicle_id=vehicle, physical_link=link, lane=lane, local_pos_m=pos,
                        chain_pos_m=chain, cell=cell, speed_kph=speed,
                        speed_class='stopped' if speed < 5 else 'slow' if speed < 30 else 'moving'))
            sources[label] = dict(path=str(files[0]), file_bytes=files[0].stat().st_size,
                                  bytes_read=reader.bytes_read, **reader.selected[str(contract['time_sec'])])
        finally:
            reader.handle.close()
    if len(rows) < 8 or any(row['lane'] not in (1, 2, 3, 4) for row in rows):
        raise ValueError('Insufficient or unexpected lane observations')
    output = ROOT / 'diagnostics/e8_diverge_snapshot_3301'
    with output.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.edgecolor': '#70757B', 'text.color': '#252B32'})
    fig, axes = plt.subplots(4, 1, figsize=contract['footprint_inches'], sharex=True)
    fig.subplots_adjust(left=.09, right=.98, top=.80, bottom=.155, hspace=.57)
    titles = {'NC': 'No control', 'n7': 'Pure n7', 'zero': 'Fixed greens · zero offset',
              'offset10': 'Same fixed greens · relative offset10'}
    for ax, label in zip(axes, RUNS):
        group = [row for row in rows if row['run_label'] == label]
        for lane in (1, 2, 3, 4):
            ax.axhline(lane, color='#E0E3E6', lw=.8, zorder=0)
        for category in ('moving', 'slow', 'stopped'):
            selected = [row for row in group if row['speed_class'] == category]
            style = (dict(marker='o', s=16, color='#3B6FA0', linewidths=0) if category == 'moving'
                     else dict(marker='o', s=23, facecolors='none', edgecolors='#C97932', linewidths=.9) if category == 'slow'
                     else dict(marker='x', s=24, color='#C97932', linewidths=1.0))
            ax.scatter([row['chain_pos_m'] / 1000 for row in selected], [row['lane'] for row in selected], **style)
        ax.axvline(split / 1000, color='#6A7077', ls=':', lw=1)
        for number, position in nodes.items():
            ax.axvline(position / 1000, color='#343B43' if number == '10682' else '#9BA1A7',
                       lw=1.1 if number == '10682' else .8, ls='-' if number == '10682' else '--')
        n8 = sum(row['cell'] == 8 for row in group)
        n9 = sum(row['cell'] == 9 for row in group)
        ax.set_title(f'{titles[label]}     E8: {n8} vehicles   |   E9: {n9} vehicles', loc='left', fontsize=11, pad=9)
        ax.set(ylim=(.6, 4.4), yticks=[1, 2, 3, 4], ylabel='Lane', xlim=(low / 1000, high / 1000))
    axes[-1].set_xlabel('FW_E chain position [km]  →  direction of travel', labelpad=9)
    fig.suptitle('Vehicle positions and speeds around the 10682 diverge', x=.09, ha='left', y=.97, fontsize=18)
    fig.text(.09, .925, 'Exact snapshot: 3301 s · seed 13 · each mark is one observed mainline vehicle', fontsize=11)
    legend = [Line2D([], [], color='#C97932', marker='x', ls='', label='<5 km/h'),
              Line2D([], [], color='#C97932', marker='o', markerfacecolor='none', ls='', label='5–30 km/h'),
              Line2D([], [], color='#3B6FA0', marker='o', ls='', label='≥30 km/h'),
              Line2D([], [], color='#6A7077', ls=':', lw=1, label='E8 / E9 cell boundary')]
    fig.legend(handles=legend, loc='upper left', bbox_to_anchor=(.085, .908), ncol=4, frameon=False)
    # Two node names are only 11 m apart; use separate annotation heights.
    axis_top = axes[0]
    for number, text, y in [('10639', '10639 merge', 1.53), ('10682', '10682 diverge', 1.29),
                             ('10681', '10681 merge', 1.53)]:
        axis_top.annotate(text, xy=(nodes[number]/1000, 1.02), xycoords=('data', 'axes fraction'),
            xytext=(nodes[number]/1000, y), textcoords=('data', 'axes fraction'),
            ha='center', fontsize=9, arrowprops=dict(arrowstyle='-', color='#70757B', lw=.7), annotation_clip=False)
    fig.text(.09, .055, 'NC vs n7 compares whole policies; the bottom pair isolates relative offset with identical fixed greens.', fontsize=9)
    fig.text(.09, .033, 'Fixed greens originate from the earlier audit-affected n7 run. Instantaneous positions do not estimate discharge capacity.', fontsize=9)
    for suffix in ('.png', '.svg'):
        fig.savefig(output.with_suffix(suffix), dpi=170, facecolor='white')
    plt.close(fig)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    provenance = {'contract': contract, 'sources': sources, 'row_count': len(rows),
                  'network_sha256': sha(network_path), 'mapping_sha256': sha(mapping_path),
                  'plot_script_sha256': sha(Path(__file__)), 'csv_sha256': sha(output.with_suffix('.csv')),
                  'nodes_chain_m': nodes, 'cell_bounds_m': [low, split, high]}
    output.with_name(output.name + '_provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'image': str(output.with_suffix('.png')), 'rows': len(rows),
                      'bytes_read': sum(item['bytes_read'] for item in sources.values())}))


if __name__ == '__main__':
    main()
