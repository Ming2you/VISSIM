"""Compare identical native traffic at multiple longitudinal resolutions."""
from pathlib import Path
import json, math, sys
import numpy as np
B=Path(__file__).resolve().parent;H=B.parent;K=H/'cohort_dynamics_20260920'
sys.path.insert(0,str(B));from prepare import save,table
G=json.loads((H/'controller_response_s23_v1/none/geometry.json').read_text())
bins=json.loads((B/'bins.json').read_text());widths=json.loads((H/'lane_group_response_20260919/observations_v1/s23.json').read_text())['geometry']['widths']
params=json.loads((H/'spatial_calibration_20260919/fit_v1/model/segment_params.json').read_text())

def grouping(a,bs):
    a={k:a[k] for k in ('n','mom','slow','stop')}
    out={k:np.zeros((752,len(bs),3)) for k in ('n','mom','slow','stop')}
    for j,b in enumerate(bs):
        c=b['cell'];cursor=0
        for g,w in enumerate(widths[c]):
            span=round(w)
            for k in out:out[k][:,j,g]=a[k][:,j,cursor:cursor+span].sum(axis=1)
            cursor+=span
    return out

def runlength(mask):
    out=np.zeros_like(mask);start=None
    for t,x in enumerate([*mask,False]):
        if x and start is None:start=t
        if not x and start is not None:
            if t-start>=5:out[start:t]=True
            start=None
    return out

def main():
    # This file keeps thresholds explicit; they select visible clusters and
    # are not a capacity-drop rule or fitted plant parameter.
    thresholds=dict(min_bin_vehicles=3,mean_speed_below_kmh=30,min_persistence_s=5,start_s=2400,end_s=2850)
    critical={int(key.split('_S')[1]):r['rho_crit'] for key,r in params['segments'].items() if key.startswith('FW_E_S')} if 'segments' in params else None
    if critical is None:raise ValueError('Read the explicit segment FD schema before evaluating density')
    rows=[];examples=[]
    for arm in ('none_s23','rm_ramp_s23','vsl_s23'):
        coarse=grouping(np.load(B/f'{arm}_0.npz'),bins['0'])
        for size in (250,100,50):
            bs=bins[str(size)];a=grouping(np.load(B/f'{arm}_{size}.npz'),bs)
            for c in (8,9,12,13,14):
                ids=[j for j,b in enumerate(bs) if b['cell']==c]
                cl=(bins['0'][c]['end']-bins['0'][c]['start'])/1000
                for g,w in enumerate(widths[c]):
                    cr=coarse['n'][:,c,g]/(cl*w);cv=np.divide(coarse['mom'][:,c,g],coarse['n'][:,c,g],out=np.full(752,np.nan),where=coarse['n'][:,c,g]>0)
                    clustered=np.zeros(752,dtype=bool);masked=np.zeros(752,dtype=bool);peak=0
                    for j in ids:
                        length=(bs[j]['end']-bs[j]['start'])/1000;n=a['n'][:,j,g]
                        rho=n/(length*w);v=np.divide(a['mom'][:,j,g],n,out=np.full(752,np.nan),where=n>0)
                        slow=(n>=3)&(rho>critical[c])&(v<30)
                        stable=runlength(slow);m=stable&(cr<critical[c])
                        clustered|=stable;masked|=m
                        for ix in np.where(m & (np.arange(752)>=151)&(np.arange(752)<=601))[0]:
                            examples.append(dict(arm=arm,scale_m=size,time_s=int(ix+2249),cell=c,group=g,
                                start_m=bs[j]['start'],end_m=bs[j]['end'],local_n=n[ix],local_v=v[ix],local_rho=rho[ix],
                                cell_rho=cr[ix],cell_v=cv[ix],rho_crit=critical[c],stopped=a['stop'][ix,j,g]))
                    target=slice(151,602)
                    rows.append(dict(arm=arm,scale_m=size,cell=c,group=g,seconds=451,
                        clustered_seconds=int(clustered[target].sum()),masked_seconds=int(masked[target].sum()),
                        cluster_share_pct=float(clustered[target].mean()*100),masked_share_pct=float(masked[target].mean()*100)))
    table(B/'masked_clusters.csv',rows)
    ranked=sorted(examples,key=lambda r:(r['stopped'],r['cell_v']-r['local_v'],r['local_n']),reverse=True)
    chosen=[]
    for r in ranked:
        if r['scale_m']==100 and not any(v['cell']==r['cell'] and v['arm']==r['arm'] for v in chosen):chosen.append(r)
    table(B/'examples.csv',chosen)
    save(B/'spatial_summary.json',dict(thresholds=thresholds,examples=chosen,rows=rows,interpretation='Repeated same-bin physical clusters, not a capacity or causal lever effect.'))
    plot()
    print('Spatial audit complete',chosen[:3],flush=True)

def plot():
    sys.path.insert(0,str(H.parents[2]/'.review-deps'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    plt.rcParams.update({'font.family':'Malgun Gothic','font.size':11,'axes.unicode_minus':False})
    cmap=LinearSegmentedColormap.from_list('speed',['#9a5108','#e8b86a','#f7f4ec','#83b3c8','#18547e']);cmap.set_bad('#eeeeee')
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    for r,(lo,hi,title) in enumerate([(4210,5263,'10643 진출·10639/10681 합류 주변'),(6315,7828,'10481/10483 진출·10490/10484 합류 주변')]):
        for col,size in enumerate((0,50)):
            bs=bins[str(size)];a=np.load(B/f'none_s23_{size}.npz');ids=[j for j,b in enumerate(bs) if lo<=b['start'] and b['end']<=hi]
            n=a['n'][1:751,ids,0].reshape(150,5,len(ids)).sum(axis=1)
            mom=a['mom'][1:751,ids,0].reshape(150,5,len(ids)).sum(axis=1)
            v=np.divide(mom,n,out=np.full_like(mom,np.nan),where=n>0)
            edges=[bs[ids[0]]['start']]+[bs[j]['end'] for j in ids]
            ax=axes[r,col];im=ax.pcolormesh(np.arange(2249.5,3000,5),np.array(edges)/1000,v.T,cmap=cmap,vmin=0,vmax=120,rasterized=True)
            ax.set_title(title+'\n'+('기존 약 500m 셀' if size==0 else '50m 이하 관측 구간'))
            ax.set_xlim(2250,3000);ax.set_xticks([2250,2400,2550,2700,2850,3000]);ax.set_xlabel('시뮬레이션 시간 [s]');ax.set_ylabel('동측 본선 누적 거리 [km]')
            ax.axvline(2400,color='#444444',ls='--',lw=.8)
            for p in G['boundaries']:
                if p['road']=='FW_E' and p['kind'] in ('ramp','offramp') and edges[0]<p['chain_pos_m']<edges[-1]:
                    y=p['chain_pos_m']/1000;ax.axhline(y,color='#333333',lw=.65,ls=':' if p['kind']=='ramp' else '-')
    fig.colorbar(im,ax=axes,label='차량 수로 가중한 속도 [km/h]',shrink=.8)
    fig.suptitle('같은 무제어 차량 기록의 공간 평균 비교 | seed 23 · 1번 차로\n색상은 5초 평균 · 회색은 차량 없음 · 점선=합류, 실선=진출',fontsize=14)
    fig.savefig(B/'space_resolution.png',dpi=160);fig.savefig(B/'space_resolution.pdf');plt.close(fig)

if __name__=='__main__':main()
