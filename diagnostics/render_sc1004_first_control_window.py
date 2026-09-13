"""Plot actual service windows and queues from the bounded first-window audit."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    directory = ROOT / 'diagnostics/sc1004_first_control_window'
    evidence = directory / 'diagnosis.json'
    doc = json.loads(evidence.read_text(encoding='utf-8'))
    inputs = [evidence]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True,
                             sharey='row', constrained_layout=True)
    for col, (label, filename) in enumerate((('NC', 'NC_timeseries.csv'),
                                            ('beta300', 'beta300_timeseries.csv'))):
        path = directory / filename
        inputs.append(path)
        with path.open(encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        times = [int(r['sec']) for r in rows]
        if times != list(range(900, 1051)):
            raise ValueError('Expected every native integer frame from 900 to 1050')
        windows = doc['runs'][label]['green_windows']
        top, bottom = axes[:, col]
        for start, end in windows['1004:2']:
            top.axvspan(start, end, color='#2d9d74', alpha=.13, lw=0)
        top.step(times, [int(r['71_stopped']) for r in rows], where='post',
                 color='#343d4b', label='All stopped vehicles on road 71')
        top.step(times, [int(r['lane3_near20_stopped']) for r in rows],
                 where='post', color='#ba4a3a', label='Lane 3 stopped, last 20 m')
        for start, end in windows['1004:5']:
            top.plot([start, end], [34, 34], color='#ba8627', lw=5,
                     solid_capstyle='butt')
        top.set(ylim=(-.5, 38), ylabel='Stopped vehicles', title=label)
        top.text(.02, .97, 'Shading: SG2 GREEN | amber bar: SG5 GREEN',
                 transform=top.transAxes, va='top', fontsize=9)
        if label == 'beta300':
            top.annotate('4725 blocks lane 3\n929–973 s; removed by VISSIM',
                         xy=(947, 3), xytext=(912, 20), fontsize=9,
                         arrowprops={'arrowstyle': '->', 'color': '#ba4a3a'})
        for start, end in windows['105:4']:
            bottom.axvspan(start, end, color='#2d9d74', alpha=.13, lw=0)
        bottom.step(times, [int(r['420_stopped']) for r in rows], where='post',
                    color='#c36b28', label='Road 420 stopped')
        bottom.step(times, [int(r['1220007200_stopped']) for r in rows],
                    where='post', color='#5c609b', label='Downstream 1220007200 stopped')
        bottom.set(ylim=(-1, 50), ylabel='Stopped vehicles', xlabel='Simulation time (s)')
        bottom.text(.02, .97, 'Shading: downstream SC105 SG4 GREEN',
                    transform=bottom.transAxes, va='top', fontsize=9)
        for ax in (top, bottom):
            ax.set(xlim=(900, 1050), xticks=[900, 930, 960, 990, 1020, 1050])
            ax.grid(axis='y', alpha=.2)
    axes[0, 0].legend(loc='upper left', bbox_to_anchor=(0, .84), fontsize=9)
    axes[1, 0].legend(loc='upper left', bbox_to_anchor=(0, .87), fontsize=9)
    fig.suptitle('More GREEN did not guarantee more discharge\n'
                 'Completed matched 1,050 s runs, seed 13 | 1 s records | stopped speed <= 1 km/h',
                 fontsize=14)
    outputs = []
    for ext in ('png', 'svg'):
        path = directory / ('service_and_queues.' + ext)
        fig.savefig(path, dpi=160)
        outputs.append(path)
    plt.close(fig)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    proof = {'schema': 'first-window-service-queue-plot/v1',
             'inputs': {p.relative_to(ROOT).as_posix(): digest(p) for p in inputs},
             'producer_sha256': digest(Path(__file__)),
             'outputs': {p.relative_to(ROOT).as_posix(): digest(p) for p in outputs},
             'stopped_threshold_kph_inclusive': 1,
             'scope': 'Observed queue counts and actual GREEN intervals. Both green and offset changed; this is not a single-lever causal experiment.'}
    (directory / 'service_and_queues_provenance.json').write_text(
        json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'outputs': [str(p) for p in outputs]}))


if __name__ == '__main__':
    main()
