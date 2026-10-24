"""One bounded plot of completed native snapshots while FZP is buffered."""
import bisect
import ctypes
import ctypes.wintypes
import hashlib
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=Path('D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000')
DECISIONS=RUN/'sdmpc/decisions_sdmpc31_sdmpc9000_s29'
END=8250
PINS={}

def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

def main(*,output_dir=HERE,decision_dir=DECISIONS,baseline=False):
    output_dir.mkdir(exist_ok=True)
    assert not (output_dir/'summary.json').exists(),'Preserve a completed snapshot'
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    manifest=read(HERE.parent/'retained10638/candidate_manifest.json')
    p=ROOT/manifest['sources']['geometry']['path'];geometry=read(p)
    assert PINS[str(p)]==manifest['sources']['geometry']['sha256']
    chains={int(x['link']):(road,x['offset_m']) for road,chain in geometry['chains'].items() for x in chain}
    times=[1]+list(range(150,END+1,150))
    count={r:np.zeros((31,len(times)),dtype=int) for r in ('FW_E','FW_W')}
    sums={r:np.zeros_like(m,dtype=float) for r,m in count.items()}
    total_rows=0;overshoots=[];checks=[]
    for ti,t in enumerate(times):
        state=read(decision_dir/f'state_{t:06d}.json');v=state['vehicle_records']
        assert state['sim_sec']==t==v['paused_at_sim_sec']==v['capture_sim_sec_before']==v['capture_sim_sec_after']
        assert v['complete'] and len(v['records'])==v['record_count'] and v['unobservable_count']==0
        assert len({x['veh_no'] for x in v['records']})==len(v['records'])
        total_rows+=len(v['records'])
        for x in v['records']:
            address=chains.get(int(x['link_no']))
            if address is None:continue
            road,offset=address;position=offset+x['position_m'];bounds=geometry['bounds'][road]
            assert len(bounds)==32 and np.isfinite(x['speed_kph']) and x['speed_kph']>=0
            if position<bounds[0] or position>bounds[-1]:overshoots.append(dict(time=t,road=road,position=position))
            cell=min(30,max(0,bisect.bisect_right(bounds,position)-1))
            count[road][cell,ti]+=1;sums[road][cell,ti]+=x['speed_kph']
        for road in count:
            direct=[x['speed_kph'] for x in v['records'] if chains.get(int(x['link_no']),(None,))[0]==road]
            assert len(direct)==int(count[road][:,ti].sum())
            assert abs(sum(direct)-float(sums[road][:,ti].sum()))<1e-7
        # Independently check several actual cell means with direct interval membership.
        if t in (150,2700,5400,END):
            for road in count:
                for cell in (10,19,20,21,23,24):
                    lo,hi=geometry['bounds'][road][cell:cell+2]
                    selected=[x['speed_kph'] for x in v['records'] if int(x['link_no']) in chains
                        and chains[int(x['link_no'])][0]==road and lo<=chains[int(x['link_no'])][1]+x['position_m']<hi]
                    assert len(selected)==count[road][cell,ti]
                    assert abs(sum(selected)-sums[road][cell,ti])<1e-7
                    checks.append(dict(time=t,road=road,cell=cell,n=len(selected)))
    speed={r:np.divide(sums[r],count[r],out=np.full_like(sums[r],np.nan),where=count[r]>0) for r in count}
    np.savez_compressed(output_dir/'snapshot_matrices.npz',times=times,
        **{r+'_speed':speed[r] for r in count},**{r+'_count':count[r] for r in count},
        **{r+'_bounds_m':geometry['bounds'][r] for r in count})
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':12,
        'axes.titlesize':16,'figure.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
    cmap=plt.get_cmap('RdYlBu').copy();cmap.set_bad('#eeeeee')
    edges=np.r_[times[0],(np.array(times[:-1])+np.array(times[1:]))/2,times[-1]]
    for road,label in (('FW_E','동측'),('FW_W','서측')):
        fig,ax=plt.subplots(figsize=(13.5,6.8))
        fig.subplots_adjust(left=.09,right=.76,bottom=.20,top=.83)
        mesh=ax.pcolormesh(edges,np.array(geometry['bounds'][road])/1000,speed[road],
            cmap=cmap,vmin=0,vmax=120,shading='flat',rasterized=True)
        ax.set(xlim=(1,END),ylim=(0,geometry['bounds'][road][-1]/1000),
            xlabel='시뮬레이션 시간 [초]',ylabel='본선 진입점부터 거리 [km]  → 하류')
        ax.set_xticks([1,900,1800,2700,3600,4500,5400,6300,7200,END])
        ax.tick_params(axis='x',labelsize=10)
        ax.axvline(900,color='#333333',ls='--',lw=1,alpha=.8)
        bounds=sorted((b for b in geometry['boundaries'] if b['road']==road and b['kind'] in ('ramp','offramp')),
                      key=lambda b:b['chain_pos_m'])
        positions=[]
        for b in bounds:
            y=b['chain_pos_m']/1000
            positions.append(max(y,positions[-1]+.42 if positions else y))
        for b,ytext in zip(bounds,positions):
            y=b['chain_pos_m']/1000
            ax.axhline(y,color='#293443',lw=.55,alpha=.4,ls='--')
            ax.annotate(f"{b['connector']} {'진입' if b['kind']=='ramp' else '진출'}",xy=(END,y),
                xytext=(END+190,ytext),textcoords='data',fontsize=10,va='center',clip_on=False,
                arrowprops=dict(arrowstyle='-',lw=.6,color='#465566'))
        ax.text(900+90,ax.get_ylim()[1]-.22,'900초 비교 기준' if baseline else '900초 제어 시작',fontsize=10,va='top',
                bbox=dict(fc='white',ec='none',alpha=.85,pad=2))
        cax=fig.add_axes([.905,.23,.019,.54])
        fig.colorbar(mesh,cax=cax,label='관측 차량 평균속도 [km/h]',extend='max')
        policy='고정 VSL90' if road=='FW_E' else '서측 VSL110 유지'
        title=f'무제어 (VSL110) | {label} 본선' if baseline else f'SDMPC + {policy} | {label} 본선'
        fig.suptitle(title,fontsize=19,y=.96)
        fig.text(.09,.875,f'seed 29 · 실제 관측 1–{END:,}초 · 31개 물리 셀',fontsize=12)
        fig.text(.09,.095,'150초 간격 순간 관측을 인접 시점 중간까지 표시 · 시간 평균이나 연속 궤적이 아님',fontsize=11)
        fig.text(.09,.06,'회색: 관측 차량 없음 · 진입/진출 표시는 본선 접속 위치 · 램프 자체 속도는 제외',fontsize=11,color='#555555')
        fig.savefig(output_dir/f'{road}_snapshot_to{END}.png',dpi=160)
        plt.close(fig)
    summary=dict(source='complete native COM vehicle snapshots, not plant predictions or FZP',
        start_sec=1,end_sec=END,times=times,interval_sec=150,first_sample_exception_sec=1,
        rows=total_rows,geometry_physical_cells_per_road=31,overshoots=overshoots,
        sample_checks=checks,source_sha256=PINS,
        temporal_display='Nearest sampled instant; edge midpoint rectangles, no averaging/interpolation',
        empty_cell_policy='masked grey, not speed0',TTT_computed=False,FZP_read=False,
        simulations_started=0,model_or_live_files_changed=False,
        plotted_speed_range=[0,120],above_120_color_saturated_with_colorbar_extension=True)
    (output_dir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=True,snapshots=len(times),rows=total_rows,
        checked_cells=len(checks),overshoots=len(overshoots),files=[str(output_dir/f'{r}_snapshot_to{END}.png') for r in count])))

if __name__=='__main__':main()
