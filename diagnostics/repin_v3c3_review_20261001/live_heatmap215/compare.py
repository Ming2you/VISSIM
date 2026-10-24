"""Matched-window NC/control observed snapshot figures, no FZP/TTT analysis."""
import hashlib
import json
from pathlib import Path
import numpy as np
from . import plot as p

def main():
    assert not (p.HERE/'comparison.json').exists()
    nc=Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc/decisions_sdmpc31_nc9000_s29')
    proof=p.read(p.HERE.parent/'postrun207/matched_nc.json')
    for source in proof['provenance']:
        assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256']
    assert proof['values']['seed']==29
    assert proof['files']['network']=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    warmup={}
    for t in (1,150,300,450,600,750,900):
        a=p.read(nc/f'state_{t:06d}.json')['vehicle_records']
        b=p.read(p.DECISIONS/f'state_{t:06d}.json')['vehicle_records']
        warmup[t]=a['records']==b['records']
    assert all(warmup.values()),'Warmup snapshots differ; do not label matched'
    p.main(output_dir=p.HERE/'nc',decision_dir=nc,baseline=True)
    data={k:np.load(folder/'snapshot_matrices.npz') for k,folder in (('nc',p.HERE/'nc'),('control',p.HERE))}
    assert np.array_equal(data['nc']['times'],data['control']['times'])
    times=data['nc']['times'];edges=np.r_[times[0],(times[:-1]+times[1:])/2,times[-1]]
    manifest=p.read(p.HERE.parent/'retained10638/candidate_manifest.json')
    geo=p.read(p.ROOT/manifest['sources']['geometry']['path'])
    cmap=p.plt.get_cmap('RdYlBu').copy();cmap.set_bad('#eeeeee')
    for road,label in (('FW_E','동측'),('FW_W','서측')):
        assert np.array_equal(data['nc'][road+'_bounds_m'],data['control'][road+'_bounds_m'])
        fig,axes=p.plt.subplots(2,1,figsize=(13.5,11.5),sharex=True,sharey=True)
        fig.subplots_adjust(left=.09,right=.76,bottom=.14,top=.88,hspace=.22)
        for ax,arm,title in zip(axes,('nc','control'),('무제어 · VSL110','SDMPC + 동측 고정 VSL90' if road=='FW_E' else 'SDMPC · 서측 VSL110 유지')):
            mesh=ax.pcolormesh(edges,data[arm][road+'_bounds_m']/1000,data[arm][road+'_speed'],
                cmap=cmap,vmin=0,vmax=120,shading='flat',rasterized=True)
            ax.set_title(title,fontsize=15,loc='left')
            ax.set(xlim=(1,p.END),ylim=(0,geo['bounds'][road][-1]/1000),ylabel='진입점부터 거리 [km] → 하류')
            ax.axvline(900,color='#333333',ls='--',lw=.9,alpha=.8)
            marks=sorted((b for b in geo['boundaries'] if b['road']==road and b['kind'] in ('ramp','offramp')),key=lambda b:b['chain_pos_m'])
            last=-1
            for b in marks:
                y=b['chain_pos_m']/1000;at=max(y,last+.42);last=at
                ax.axhline(y,color='#293443',lw=.45,alpha=.4,ls='--')
                ax.annotate(f"{b['connector']} {'진입' if b['kind']=='ramp' else '진출'}",xy=(p.END,y),
                    xytext=(p.END+190,at),textcoords='data',fontsize=9.5,va='center',clip_on=False,
                    arrowprops=dict(arrowstyle='-',lw=.6,color='#465566'))
        axes[-1].set_xlabel('시뮬레이션 시간 [초]')
        axes[-1].set_xticks([1,900,1800,2700,3600,4500,5400,6300,7200,p.END])
        axes[-1].tick_params(axis='x',labelsize=10)
        cax=fig.add_axes([.905,.25,.019,.50])
        fig.colorbar(mesh,cax=cax,label='관측 차량 평균속도 [km/h]',extend='max')
        fig.suptitle(f'{label} 본선 | 무제어와 SDMPC 비교',fontsize=19,y=.97)
        fig.text(.09,.92,f'동일 망·수요·seed29 · 1–{p.END:,}초 · 동일 시간·거리·색상 범위',fontsize=12)
        fig.text(.09,.075,'150초 간격 실제 순간 관측 · 시간 평균/5초 FZP가 아님 · 900초 점선: 제어 시작 시점',fontsize=11)
        fig.text(.09,.045,'회색: 관측 차량 없음 · 본선 속도만 표시 · 램프·도시 대기를 포함한 TTT 개선율은 별도 검증',fontsize=11,color='#555555')
        fig.savefig(p.HERE/f'{road}_NC_vs_SDMPC_to{p.END}.png',dpi=150)
        p.plt.close(fig)
    result=dict(passed=True,matched_source_metadata=True,warmup_snapshot_records_exact=warmup,
        same_time_distance_color_scale=True,start_sec=1,end_sec=p.END,TTT_computed=False,FZP_read=False,
        native_full_prefix_verified=False,limitation='Seven warmup snapshots exact; full FZP trajectory prefix remains for completed-run analysis.',
        sources=p.PINS,summary_paths=[str(p.HERE/'nc/summary.json'),str(p.HERE/'summary.json')])
    (p.HERE/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('NC/control figures complete; seven warmup snapshots exact')

if __name__=='__main__':main()
