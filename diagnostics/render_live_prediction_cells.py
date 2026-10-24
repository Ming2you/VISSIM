"""Plot recorded E8/E9 traffic against an audited held-command prediction."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from diagnostics.audit_area_live_actuation import read_csv_prefix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--title', default='Predicted and observed congestion in E8/E9')
    parser.add_argument('--speed-max', type=float, default=130.0)
    args = parser.parse_args()
    source = args.report.resolve()
    raw = source.read_bytes(); data = json.loads(raw)
    if not (data['replay_matches_executed_model'] and data['executed_command_audit_valid'] and not data['source_changes_during_audit']):
        raise ValueError('Verified executed-model/command evidence is required')
    start,end = data['interval_sec']
    trace = source.with_name(source.stem+'_cell_trace.csv')
    with trace.open(encoding='utf-8-sig') as stream:
        model = list(csv.DictReader(stream))
    observed_path = ROOT/'evaluation/runs'/data['run']/('bottleneck_segments_'+data['run']+'.csv')
    observed,evidence = read_csv_prefix(observed_path,end)
    destination = source.with_name(source.stem+'_local_cells')
    if any(destination.with_suffix(ext).exists() for ext in ('.png','.svg','.csv')):
        raise ValueError('Refusing to overwrite a previous figure')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
    fig,axes = plt.subplots(2,2,figsize=(12,8),sharex=True)
    rows=[]
    for col,cell in enumerate((8,9)):
        pred=[r for r in model if r['link']=='FW_E' and int(r['cell_index_zero_based'])==cell]
        physical=[r for r in observed if r['model_link']=='FW_E' and int(r['segment_index'])==cell and start<=float(r['sim_sec'])<=end]
        if [float(r['sim_sec']) for r in physical] != list(range(start,end+1,30)):
            raise ValueError('Complete 30-second observation grid required')
        if [float(r['sim_sec']) for r in pred] != list(range(start,end+1,10)):
            raise ValueError('This figure expects the audited 10-second model grid')
        for row,(predkey,obskey,label) in enumerate((('speed_kph','mean_speed_kph','Speed (km/h)'),('count_veh','count','Vehicles in cell'))):
            ax=axes[row,col]
            for seq,key,name,color,marker in ((pred,predkey,'Model','#ce7527',None),(physical,obskey,'Physical','#247da8','o')):
                xx=[float(r['sim_sec']) for r in seq]; yy=[float(r[key]) for r in seq]
                ax.plot(xx,yy,label=name,color=color,lw=2.3,marker=marker,ms=4)
                rows.extend({'cell':cell,'sim_sec':t,'metric':label,'series':name,'value':v} for t,v in zip(xx,yy))
            ax.set_ylabel(label);ax.set_xlim(start,end);ax.set_ylim(bottom=0)
            ax.grid(True,color='#e3e7eb');ax.spines[['top','right']].set_visible(False)
            ax.set_xticks(list(range(start,end+1,30)))
        axes[0,col].set_title(f'E{cell}  |  '+('4.108–4.622 km' if cell==8 else '4.622–5.135 km'),loc='left',weight='bold',pad=14)
        speed_values = [float(r['speed_kph']) for r in pred] + [float(r['mean_speed_kph']) for r in physical]
        if not args.speed_max > max(speed_values):
            raise ValueError('Speed axis must include every plotted speed')
        axes[0,col].set_ylim(0,args.speed_max)
        axes[1,col].set_xlabel('Simulation time (s)')
    fig.suptitle(args.title,x=.08,y=.96,ha='left',fontsize=19,weight='bold')
    fig.text(.08,.91,f'Actual command at {start} s held in the replay  |  seed 13  |  E9 contains diverge 10682',fontsize=11,color='#46515b')
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='upper right',bbox_to_anchor=(.96,.89),ncol=2,frameon=False)
    fig.text(.08,.05,'Same physical cell boundaries and paused observations. Model: 10 s; physical: 30 s samples. This is prediction error, not a capacity estimate.',fontsize=9.5)
    fig.subplots_adjust(left=.08,right=.96,top=.80,bottom=.14,wspace=.23,hspace=.28)
    for ext in ('.png','.svg'):fig.savefig(destination.with_suffix(ext),dpi=170,facecolor='white')
    plt.close(fig)
    with destination.with_suffix('.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    provenance={'report_sha256':hashlib.sha256(raw).hexdigest(),'cell_trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),
                'observed_prefix':evidence,'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'values':len(rows),'title':args.title,'speed_axis_max_kph':args.speed_max,
                'qa':'Inspect the exported PNG before delivery.'}
    destination.with_name(destination.name+'_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(str(destination.with_suffix('.png')))


if __name__=='__main__':main()
