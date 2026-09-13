"""Render the source-specific holdout comparison from pinned audit artifacts."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    data=json.loads((ROOT/'diagnostics/native_sc15_service_holdout.json').read_text(encoding='utf-8'))
    labels=[];flows={'Physical':[],'Inherited model':[],'SC15 prior':[]};stocks={k:[] for k in flows}
    for r in data['rows']:
        for no in ('1086','1087'):
            labels.append(f"{r['start_sec']}–{r['start_sec']+450}s\nInput {no}")
            flows['Physical'].append(r['measured'][no]['source_departures_veh']);stocks['Physical'].append(r['measured'][no]['final_source_n_veh'])
            for title,mode in [('Inherited model','inherited'),('SC15 prior','calibrated')]:
                source=r['cases'][mode]['sources'][no];flows[title].append(sum(source['accepted_by_receiver_veh'].values()));stocks[title].append(source['final_veh'])
    fig,axes=plt.subplots(2,1,figsize=(10.6,7.4),sharex=True,gridspec_kw={'hspace':.24})
    colors=['#48505b','#c96450','#267f82'];width=.24
    for axis,values,title in [(axes[0],flows,'Source departures during 450 seconds'),(axes[1],stocks,'Source vehicles at the end of 450 seconds')]:
        for i,(label,ys) in enumerate(values.items()):
            x=[j+(i-1)*width for j in range(len(labels))];bars=axis.bar(x,ys,width,label=label,color=colors[i])
            axis.bar_label(bars,labels=[f'{y:.1f}' if label!='Physical' else str(int(y)) for y in ys],fontsize=9,padding=3)
        axis.set_ylabel('Vehicles');axis.set_title(title,loc='left',fontsize=12);axis.grid(axis='y',alpha=.2);axis.set_axisbelow(True)
        axis.spines[['top','right']].set_visible(False);axis.set_ylim(0,max(max(y) for y in values.values())*1.22)
    axes[0].legend(frameon=False,ncol=3,loc='upper left');axes[1].set_xticks(range(len(labels)),labels,fontsize=10)
    fig.suptitle('SC15 service correction: two excluded time holdouts',x=.08,ha='left',fontsize=16,fontweight='bold')
    fig.text(.08,.022,'Same seed13, same held action. Fit excludes both shown intervals. Actual stochastic arrivals differ from the model mean.\nSC15-only prior: SG5 1305 veh/h; SG1 1220.34 veh/h. No global capacity change. Seed14 validation pending.',fontsize=9,color='#40464e')
    fig.subplots_adjust(left=.08,right=.98,top=.88,bottom=.16)
    png=ROOT/'diagnostics/native_sc15_service_holdout.png';svg=png.with_suffix('.svg');fig.savefig(png,dpi=160);fig.savefig(svg);plt.close(fig)
    paths=[Path(__file__),ROOT/'diagnostics/native_sc15_service_holdout.json',ROOT/'diagnostics/native_sc15_service_calibration.json',png,svg]
    proof={'schema':'sc15-service-plot/v1','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'units':'Both panels count vehicles; bars distinguish observations from predictions. No performance reduction percentage is implied.'}
    (ROOT/'diagnostics/native_sc15_plot_provenance.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(str(png))

if __name__=='__main__':main()
