"""Plot actual commands beside observed bottleneck states, without a model run."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source = folder / 'comparison.json'
    doc = json.loads(source.read_text(encoding='utf-8'))
    if not doc['common_window_comparison_ready']:
        raise ValueError('A matched, completed common window is required')
    target = doc['runs']['target']
    if target['actuation']['status'] != 'pass' or doc['source_changes']:
        raise ValueError('Actual command/readback and source consistency must pass')
    start, end = doc['common_completed_window_sec']
    commands = [c for c in target['commands'] if
                c['positive_control_duration_sec'] > 0 and start <= c['sim_sec'] < end]
    if not commands or commands[0]['sim_sec'] != start:
        raise ValueError('The plotted interval must start at a recorded command')
    input_paths = [source, folder/'cell_curves.csv', folder/'road_curves.csv', Path(__file__)]
    before = {str(p): sha(p) for p in input_paths}
    def read(name):
        with (folder/name).open(encoding='utf-8', newline='') as stream:
            return list(csv.DictReader(stream))
    cells, roads = read('cell_curves.csv'), read('road_curves.csv')
    plotted = []
    fig, axes = plt.subplots(3, 2, figsize=(13.2, 10.8), sharex=True, layout='constrained')
    colors = ['#146b75', '#ad542a', '#555fa5', '#686868']
    def record(panel, name, x, y, unit, kind):
        if not x or len(x) != len(y) or any(not math.isfinite(float(v)) for v in x+y):
            raise ValueError(f'Invalid plot data: {panel}/{name}')
        plotted.extend({'panel':panel, 'series':name, 'sim_sec':t,
                        'value':v, 'unit':unit, 'kind':kind} for t, v in zip(x, y))
    def observed(ax, rows, select, series, key, unit, panel, color):
        selected = sorted((r for r in rows if select(r) and start <= float(r['sim_sec']) <= end),
                          key=lambda r: float(r['sim_sec']))
        x = [float(r['sim_sec']) for r in selected]
        y = [float(r[key]) for r in selected]
        if len(x) != len(set(x)):
            raise ValueError(f'Duplicate observed timestamps: {series}')
        record(panel, series, x, y, unit, 'observed_30s')
        ax.plot([t/60 for t in x], y, label=series, color=color, lw=1.5)
    # Read the comparison's explicit CSV schema, preserving zeros/empty-cell masks.
    def is_target(row):
        return row['run'] == 'target'
    for index, color in zip((8, 7, 6), colors):
        observed(axes[0, 0], cells,
                 lambda r, i=index: is_target(r) and r['model_link']=='FW_E' and int(r['index'])==i and float(r['count'])>0,
                 f'E{index}', 'mean_speed_kph', 'km/h', 'cell_speed', color)
    for link, color in zip(('10639', '10682', '420'), colors):
        observed(axes[0, 1], roads, lambda r, link=link: is_target(r) and r['link']==link,
                 link, 'stopped_count', 'vehicles', 'stopped_stock', color)
    x = [float(c['sim_sec']) for c in commands] + [float(end)]
    def stepped(ax, name, values, unit, panel, color):
        y = values + [values[-1]]
        record(panel, name, x, y, unit, 'held_actual_command')
        ax.step([t/60 for t in x], y, where='post', label=name, color=color, lw=1.5)
    for zone, color in zip(('RW_FW_E_S0', 'RW_FW_E_S2', 'RW_FW_E_S5', 'RW_FW_E_S7'), colors):
        values=[]
        for command in commands:
            rates={float(v['speed_kph']) for k,v in command['signature'].items()
                   if k.startswith('vsl:'+zone+':')}
            if len(rates)!=1:
                raise ValueError(f'{zone}: missing or differing lane DSD values')
            values.append(rates.pop())
        stepped(axes[1,0], zone.replace('RW_FW_', ''), values, 'km/h', 'vsl', color)
    for link, color in zip(('10639','10681'), colors):
        values=[float(c['signature']['ramp:RM_C'+link]['green_sec']) for c in commands]
        stepped(axes[1,1], link, values, 'seconds_per_10s_cycle', 'meter_green', color)
    for phase, color in zip(('p1','p2','p3','p4'), colors):
        values=[float(c['signature']['signal:1004'][phase+'_green']) for c in commands]
        stepped(axes[2,0], phase, values, 'seconds', 'SC1004_green', color)
    for signal, color in zip(('1004','1001'), colors):
        values=[float(c['signature']['signal:'+signal]['offset_sec']) for c in commands]
        stepped(axes[2,1], 'SC'+signal, values, 'seconds', 'offset', color)
    titles = ['Observed eastbound cell speed', 'Observed stopped vehicles (unfiltered)',
              'Executed eastbound VSL settings', 'Executed F east meter GREEN',
              'Executed SC1004 phase GREEN', 'Executed signal offsets']
    units = ['km/h', 'Vehicles', 'km/h', 'GREEN seconds / 10s cycle', 'GREEN seconds', 'Offset seconds']
    for ax, title, unit in zip(axes.flat, titles, units):
        ax.set_title(title, fontsize=11)
        ax.set_ylabel(unit)
        ax.grid(alpha=.18)
        ax.legend(fontsize=8, ncol=2, loc='best')
        ax.set_xlim(start/60, end/60)
    axes[0,0].set_ylim(0,125)
    axes[1,0].set_ylim(0,125)
    axes[1,1].set_ylim(-.3,10.5)
    for ax in axes[2,:]:ax.set_xlabel('Simulation minute')
    fig.suptitle('F east bottleneck: observed traffic and the commands actually applied', fontsize=14)
    stem=folder/'lever_timeline'
    fig.savefig(stem.with_suffix('.png'),dpi=160)
    fig.savefig(stem.with_suffix('.svg'))
    plt.close(fig)
    with stem.with_suffix('.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(plotted[0]));writer.writeheader();writer.writerows(plotted)
    ET.parse(stem.with_suffix('.svg'))
    after={str(p):sha(p) for p in input_paths}
    if before != after:raise ValueError('Source changed while plotting')
    metadata={'source_sha256':before,'common_window_sec':[start,end],
              'plotted_rows':len(plotted),'completed_command_intervals':len(commands),
              'svg_parse':'PASS','finite_values':'PASS','source_unchanged':True,
              'visual_review':'pending',
              'limits':'Selected F east bottleneck views; other actuators remain in comparison.json. '
              'DSD/SG readback verifies commands, not vehicle compliance. Coincident changes do not isolate lever effects. '
              'The final zero-duration command is excluded; end values only draw the preceding hold interval.'}
    stem.with_name(stem.name+'_provenance.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return metadata


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path)
    print(json.dumps(render(p.parse_args().folder)))
