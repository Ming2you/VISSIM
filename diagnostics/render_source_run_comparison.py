"""Render completed-prefix observations and actual command changes."""
from pathlib import Path
import argparse,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.review-deps'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read_csv(path):
    with path.open(encoding='utf-8') as stream:return list(csv.DictReader(stream))
def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('directory',type=Path)
    ap.add_argument('--queue-links',nargs=6,default=('10639','10682','40','420','70','71'))
    ap.add_argument('--queue-smoothing-samples',type=int,default=5)
    args=ap.parse_args(argv);directory=(ROOT/args.directory).resolve()
    if args.queue_smoothing_samples<1:ap.error('Queue smoothing must use at least one sample')
    if (ROOT/'diagnostics').resolve() not in directory.parents:ap.error('Render input/output must stay under diagnostics')
    path=directory/'comparison.json';report=json.loads(path.read_text(encoding='utf-8'));created=[]
    if not report.get('common_window_comparison_ready'):
        print(json.dumps({'status':'pending','reason':'No common completed comparison window; no chart invented.'}));return 0
    start,end=report['common_completed_window_sec'];cells=read_csv(directory/'cell_curves.csv');roads=read_csv(directory/'road_curves.csv')
    times=sorted({float(r['sim_sec']) for r in cells if start<=float(r['sim_sec'])<=end});xs=np.array(times)/60
    fig,axes=plt.subplots(2,2,figsize=(13,8),sharex=True,sharey=True,constrained_layout=True)
    for axis,(model,label) in zip(axes.flat,[('FW_E','reference'),('FW_E','target'),('FW_W','reference'),('FW_W','target')]):
        selected=[r for r in cells if r['run']==label and r['model_link']==model and start<=float(r['sim_sec'])<=end]
        indices=sorted({int(r['index']) for r in selected});z=np.full((len(indices),len(times)),np.nan);lookup={t:i for i,t in enumerate(times)}
        for row in selected:
            if float(row['count'])>0:z[indices.index(int(row['index'])),lookup[float(row['sim_sec'])]]=float(row['mean_speed_kph'])
        image=axis.imshow(z,origin='lower',aspect='auto',interpolation='nearest',cmap='RdYlGn',vmin=0,vmax=120,
            extent=[(times[0]-15)/60,(times[-1]+15)/60,min(indices)-.5,max(indices)+.5])
        axis.set(title=f'{label}: {model}',ylabel='Cell index (upstream = 0)',xlabel='Simulation minute',xlim=(start/60,end/60))
    fig.colorbar(image,ax=axes.ravel().tolist(),label='Mean measured speed (km/h); empty cells masked',shrink=.8)
    fig.suptitle('Observed freeway congestion on the common completed window')
    for suffix in ('png','svg'):
        destination=directory/f'freeway_comparison.{suffix}';fig.savefig(destination,dpi=150);created.append(destination)
    plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,9),sharex=True,constrained_layout=True)
    for axis,link in zip(axes.flat,args.queue_links):
        for label,color in [('reference','#646a73'),('target','#247a83')]:
            series=sorted([r for r in roads if r['run']==label and r['link']==link and start<=float(r['sim_sec'])<=end],key=lambda r:float(r['sim_sec']))
            if not series:raise ValueError('Requested queue link has no observed data: '+link)
            values=[float(r['stopped_count']) for r in series];n=args.queue_smoothing_samples
            smoothed=[sum(values[max(0,i-n+1):i+1])/min(i+1,n) for i in range(len(values))]
            axis.plot([float(r['sim_sec'])/60 for r in series],smoothed,label=label,color=color,lw=1.5)
        axis.set(title=f'Physical link {link}',ylabel='Stopped vehicles',xlabel='Simulation minute',xlim=(start/60,end/60));axis.grid(alpha=.2)
        peak=max((max(line.get_ydata(),default=0) for line in axis.lines),default=0)
        axis.set_ylim(0,max(1,peak*1.05))
    title=('Observed stopped stock: individual 30-second samples' if args.queue_smoothing_samples==1 else
           f'Observed stopped stock: trailing {args.queue_smoothing_samples} 30-second samples')
    axes[0,0].legend(frameon=False);fig.suptitle(title)
    for suffix in ('png','svg'):
        destination=directory/f'queue_comparison.{suffix}';fig.savefig(destination,dpi=150);created.append(destination)
    plt.close(fig)
    commands=report['runs']['target'].get('commands',[]);commands=[r for r in commands if start<=r['sim_sec']<end]
    if commands:
        fig,axes=plt.subplots(4,1,figsize=(12,8),sharex=True,constrained_layout=True)
        for axis,lever in zip(axes,('VSL','RM','green','offset')):
            counts=[len(r['lever_changes'][lever]) for r in commands]
            axis.bar([r['sim_sec']/60 for r in commands],counts,width=2.2,color='#247a83')
            axis.set_ylabel(f'{lever}\nchanged fields');axis.grid(axis='y',alpha=.2);axis.set_ylim(0,max(1,max(counts)*1.2));axis.set_xlim(start/60,end/60)
            if not any(counts):axis.text(.5,.5,'No command changes',transform=axis.transAxes,ha='center',color='#606873')
        axes[-1].set_xlabel('Decision simulation minute');fig.suptitle('Actual CSV command changes versus preceding command; zero is legitimate')
        for suffix in ('png','svg'):
            destination=directory/f'command_changes.{suffix}';fig.savefig(destination,dpi=150);created.append(destination)
        plt.close(fig)
    sources=[Path(__file__),path,directory/'road_curves.csv',directory/'cell_curves.csv']
    proof={'schema':'source-run-comparison-plot/v1','window_sec':[start,end],
        'queue_links':args.queue_links,'queue_smoothing_samples':args.queue_smoothing_samples,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in created},
        'interpretation':'Observed spatial association, not an isolated causal effect. Command changes count actual CSV fields; readback validation is in comparison.json.'}
    (directory/'plot_provenance.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'rendered','artifacts':[p.name for p in created]}));return 0

if __name__=='__main__':raise SystemExit(main())
