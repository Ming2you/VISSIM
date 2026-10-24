"""Quick saved-snapshot plot; no live COM, FZP scans or plant calculations."""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
import bisect, ctypes, ctypes.wintypes, hashlib, json
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parents[1]
ROOT=REVIEW.parents[1]
END=4050
OLD=REVIEW/'interim255'
RUN=Path('D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000/sdmpc')
NC=Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc')
NAME='sdmpc31_sdmpc9000_s29'
PINS={}

def read(path):
    raw=path.read_bytes(); PINS[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

def main():
    assert not (HERE/'summary.json').exists(), 'Preserve completed output'
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    k.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    geo=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    prior=read(OLD/'summary.json')
    p=read(RUN/f'run_provenance_{NAME}.json')
    pn=read(NC/'run_provenance_sdmpc31_nc9000_s29.json')
    assert p['seed']==pn['seed']==29 and p['sim_period_sec']==pn['sim_period_sec']==9000
    for key in ['network','control_mapping','vehicle_input_roles','demand_profile','urban_input_gate_map','generated_vbs_config','signal_group_plan']:
        assert p['files'][key]['sha256']==pn['files'][key]['sha256'],key
    assert p['files']['network']['sha256']=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    times=np.array([1]+list(range(150,END+1,150)),dtype=float)
    data={}
    for arm in ('nc','sdmpc'):
        path=OLD/f'{arm}_snapshots.npz'
        PINS[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path) as z:
            use=z['times'][1:]<=END
            assert np.array_equal(z['times'][1:][use],times)
            data[arm]={r:z[r+'_speed'][:,use].copy() for r in ('FW_E','FW_W')}
            for road in data[arm]: assert np.array_equal(z[road+'_bounds_m'],geo['bounds'][road])
    chains={int(x['link']):(road,x['offset_m']) for road,seq in geo['chains'].items() for x in seq}
    counts={r:np.zeros((31,len(times)),dtype=int) for r in ('FW_E','FW_W')}
    sums={r:np.zeros((31,len(times))) for r in counts}
    warmup=[]
    for j,t in enumerate(times):
        path=RUN/f'decisions_{NAME}'/f'state_{int(t):06d}.json'
        state=read(path); v=state['vehicle_records']; rows=v['records']
        assert state['sim_sec']==t==v['paused_at_sim_sec']==v['capture_sim_sec_before']==v['capture_sim_sec_after']
        assert v['complete'] and v['unobservable_count']==0
        assert state['run_provenance']['run_id']==p['run_id']
        assert len(rows)==v['record_count']==state['total_vehicles']==len({x['veh_no'] for x in rows})
        native_counts=Counter(str(x['link_no']) for x in rows)
        assert dict(native_counts)=={str(a):b for a,b in v['full_network_link_counts'].items() if b}
        if t<=900:
            native=read(NC/'decisions_sdmpc31_nc9000_s29'/f'state_{int(t):06d}.json')
            assert rows==native['vehicle_records']['records']
            warmup.append(int(t))
        for x in rows:
            addr=chains.get(int(x['link_no']))
            if addr is None: continue
            road,offset=addr; pos=offset+x['position_m']; bounds=geo['bounds'][road]
            assert bounds[0]<=pos<=bounds[-1]
            c=min(30,bisect.bisect_right(bounds,pos)-1)
            speed=x['speed_kph']; assert np.isfinite(speed) and speed>=0
            counts[road][c,j]+=1; sums[road][c,j]+=speed
        for r in counts:
            raw=[x['speed_kph'] for x in rows if chains.get(int(x['link_no']),(None,))[0]==r]
            assert counts[r][:,j].sum()==len(raw)
            assert abs(sums[r][:,j].sum()-sum(raw))<1e-7
    data['current']={r:np.divide(sums[r],counts[r],out=np.full_like(sums[r],np.nan),where=counts[r]>0) for r in counts}
    np.savez_compressed(HERE/'plot_data.npz',times=times,**{a+'_'+r:z for a,roads in data.items() for r,z in roads.items()},**{r+'_counts':c for r,c in counts.items()})
    draw(data,times,geo)
    summary=dict(end_sec=END,seed=29,current_run=str(RUN),snapshot_times=times.tolist(),warmup_exact=warmup,
                 source='Saved native full-vehicle instantaneous observations every150s; old/NC validated interim255 cache',
                 not_fzp_or_prediction=True,live_process_changed=False,ttt_not_calculated=True,source_sha256=PINS,
                 geometry='31 physical cells; actual distances; mainline only, ramps excluded',
                 limitations=['Sparse instantaneous samples cannot resolve between-sample waves.','Not completed9000 or final performance qualification.'])
    (HERE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='plotted',end_sec=END,snapshots_per_arm=len(times),metadata_and_warmup_passed=True)))

def draw(data,times,geo):
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':12,'figure.facecolor':'white'})
    cmap=plt.get_cmap('RdYlBu').copy(); cmap.set_bad('#e4e4e4')
    edges=np.r_[times[0],(times[:-1]+times[1:])/2,times[-1]]
    for road,label in [('FW_E','동측'),('FW_W','서측')]:
        fig,axes=plt.subplots(3,1,figsize=(13.5,12),sharex=True,sharey=True)
        fig.subplots_adjust(left=.085,right=.765,bottom=.12,top=.89,hspace=.29)
        titles=['무제어','수정 전 SDMPC + 동측 고정 VSL90','수정 후 SDMPC + 동측 고정 VSL90 · 현재 런']
        for ax,arm,title in zip(axes,['nc','sdmpc','current'],titles):
            mesh=ax.pcolormesh(edges,np.array(geo['bounds'][road])/1000,data[arm][road],cmap=cmap,vmin=0,vmax=120,shading='flat')
            ax.set(xlim=(1,END),ylim=(0,geo['bounds'][road][-1]/1000),ylabel='진입점부터 거리 [km] → 하류')
            ax.set_title(title,loc='left',fontsize=14)
            ax.axvline(900,ls='--',color='#333333',lw=.9)
            ax.axvline(3600,ls=':',color='#222222',lw=1.2)
            last=-1
            for b in sorted([b for b in geo['boundaries'] if b['road']==road and b['kind'] in ('ramp','offramp')],key=lambda b:b['chain_pos_m']):
                y=b['chain_pos_m']/1000; at=max(y,last+.72);last=at
                ax.axhline(y,color='#293443',lw=.45,alpha=.45,ls='--')
                ax.annotate(f"{b['connector']} {'진입' if b['kind']=='ramp' else '진출'}",xy=(END,y),xytext=(END+85,at),fontsize=9.5,va='center',clip_on=False,arrowprops=dict(arrowstyle='-',lw=.6,color='#465566'))
        axes[-1].set_xlabel('시뮬레이션 시간 [초]')
        axes[-1].set_xticks([1,900,1800,2700,3600,4050])
        cax=fig.add_axes([.91,.25,.018,.48]);fig.colorbar(mesh,cax=cax,label='관측 차량 평균속도 [km/h]',extend='max')
        fig.suptitle(f'{label} 본선 속도 | 무제어 · 수정 전 · 현재',fontsize=19,y=.97)
        fig.text(.085,.925,'동일 망·수요·seed29 · 1–4,050초 중간 관측 · 31개 물리 셀',fontsize=12)
        fig.text(.085,.062,'150초 간격 순간 관측 · 시간 평균/연속 궤적 아님 · 900초 제어 시작 / 세로 점선 3,600초',fontsize=10.5)
        fig.text(.085,.036,'회색: 관측 차량 없음 · 세 조건 동일 색상 범위 · 현재 9000초 런은 진행 중',fontsize=10.5,color='#555555')
        fig.savefig(HERE/f'{road}_comparison_to4050.png',dpi=140);plt.close(fig)


def redraw():
    geo=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    with np.load(HERE/'plot_data.npz') as z:
        times=z['times']
        data={a:{r:z[a+'_'+r] for r in ('FW_E','FW_W')} for a in ('nc','sdmpc','current')}
        draw(data,times,geo)

if __name__=='__main__':
    import sys
    redraw() if '--redraw' in sys.argv else main()
