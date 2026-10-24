"""Postrun-only recovery comparison at5400/7200/9000 with exact original FZP prefix checks."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
import numpy as np
import pandas as pd
sys.path.append(str(ROOT/'.review-deps'))
os.environ['MPLCONFIGDIR']=str(OUT/'.mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def save(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def data_start(stream):
    for line in stream:
        if line.startswith(b'$VEHICLE:'):
            return stream.tell(),line
    raise ValueError('Missing native FZP header')

def exact_prefix(old,new):
    # Compare raw rows in blocks: no parsing or reconstructed-field equivalence.
    h=hashlib.sha256();total=0;rows=0;first_diff=None
    with old.open('rb') as a,new.open('rb') as b:
        pa,ha=data_start(a);pb,hb=data_start(b)
        assert ha==hb
        while chunk:=a.read(1024*1024):
            other=b.read(len(chunk))
            if chunk!=other and first_diff is None:
                at=next((i for i,(x,y) in enumerate(zip(chunk,other)) if x!=y),min(len(chunk),len(other)))
                first_diff=total+at
            total+=len(chunk);rows+=chunk.count(b'\n');h.update(chunk)
        next_row=b.readline().decode('ascii').rstrip()
    result=dict(exact=first_diff is None,original_payload_bytes=total,original_rows=rows,
                original_payload_sha256=h.hexdigest(),next_extended_row=next_row,first_difference_payload_byte=first_diff)
    if first_diff is None:
        assert next_row.startswith('5401.00;'), 'Original payload did not end at exact extended5400 boundary'
    else:
        with old.open('rb') as a,new.open('rb') as b:
            a.seek(pa+max(0,first_diff-150));b.seek(pb+max(0,first_diff-150))
            result['first_difference_context']={'original':a.read(350).decode('ascii'),'extended':b.read(350).decode('ascii')}
    return result

def lsa_prefix(path,end=5400):
    h=hashlib.sha256();rows=0;last=0;first=None
    with path.open('rb') as f:
        for raw in f:
            try:
                sec=float(raw.split(b';',1)[0].strip())
            except ValueError:
                continue
            assert np.isfinite(sec) and sec>=last, 'Invalid or nonmonotonic native LSA time'
            if sec>end: break
            if first is None: first=sec
            h.update(raw);rows+=1;last=sec
    assert rows>0 and first==1 and last==end, 'Missing native LSA boundary coverage'
    return dict(sha256=h.hexdigest(),rows=rows,first_sec=first,last_sec=last)

def main():
    checkpoint=[];roads=[];area_windows=[];source_entries=[];cells=[];proof={}
    for pct in (80,90):
        case=f'fw{pct:03d}_urban050'
        run=ROOT/f'evaluation/runs/fast_nc_{case}_s13_9000_v1'
        original=ROOT/f'evaluation/runs/fast_nc_{case}_s13_v1'
        result=ROOT/f'diagnostics/demand_sweep/{case}_cooldown9000/results'
        figures=OUT/f'fw{pct:03d}'
        receipt=load(run/'run.json');summary=load(result/'summary.json');fdproof=load(figures/'validation.json')
        assert receipt['completed'] and receipt['exit_code']==0 and receipt['terminal_sec']==9000 and not receipt['owned_native_alive']
        assert summary['terminal_sec']==9000 and summary['status']=='complete' and fdproof['all_requested_frames']
        prefix=exact_prefix(original/'vissim_eval/baseline_001.fzp',run/'vissim_eval/baseline_001.fzp')
        old_lsa=lsa_prefix(original/'vissim_eval/baseline_001.lsa');new_lsa=lsa_prefix(run/'vissim_eval/baseline_001.lsa')
        before=ROOT/f'diagnostics/demand_sweep/{case}/prepared'
        after=Path(receipt['prepared'])
        assert all((before/n).read_bytes()==(after/n).read_bytes() for n in ('demand.csv','controls.csv','route_checks.csv'))
        with (run/'readback.csv').open(encoding='ascii',newline='') as f: rb=list(csv.DictReader(f))
        for r in rb:
            if r['kind']=='meter': assert r['expected']==r['actual']=='GREEN'
            else: assert abs(float(r['expected'])-float(r['actual']))<=.001+abs(float(r['expected']))*1e-6
        tails=[r for r in rb if r['kind']=='tail_demand']
        with (after/'demand.csv').open(encoding='ascii',newline='') as f:
            desired={r['input_no']:float(r['volume_vph']) for r in csv.DictReader(f) if r['time_int']=='1-6'}
        assert Counter(r['no'] for r in tails)==Counter({no:2 for no in desired})
        assert all(r['time_int']=='1-6' and abs(float(r['expected'])-desired[r['no']])<1e-7 for r in tails)
        counts=Counter(r['kind'] for r in rb)
        assert counts['demand']==204 and counts['vsl']==528 and counts['meter']==16 and counts['tail_demand']==68
        fd=pd.read_csv(figures/'freeway_fd_points.csv');fd=fd[fd.window_sec==60].copy();fd['freeway_percent']=pct
        assert len(fd)==6300
        cells.append(fd)
        snap=pd.read_csv(result/'fw_cells_30s.csv')
        area=pd.read_csv(result/'area_timeseries.csv')
        road=pd.read_csv(result/'road_windows_900s.csv')
        inputs=pd.read_csv(result/'source_inputs_900s.csv')
        for sec in (5400,7200,9000):
            for direction in ('E','W'):
                a=fd[(fd.direction==direction)&(fd.end_sec==sec)]
                s=snap[(snap.direction==direction)&(snap.sec==sec)]
                slow=a[(a.speed_kph<30)&(a.n_veh>=5)]
                checkpoint.append(dict(freeway_percent=pct,sim_sec=sec,direction=direction,
                    stock_at_checkpoint=int(s.n.sum()),stopped_at_checkpoint=int(s.stopped.sum()),
                    slow60_cell_count=len(slow),slow60_cells=','.join(str(x) for x in slow.cell),
                    minimum60_speed_kph=float(a.loc[a.n_veh>=5,'speed_kph'].min()),
                    omega_stock=int(area.loc[area.sim_sec==sec,'inside_vehicles'].iloc[0])))
        for start,end in ((5400,7200),(7200,9000),(5400,9000)):
            aa=area[(area.sim_sec>start)&(area.sim_sec<=end)]
            initial=area.loc[area.sim_sec==start].iloc[0];terminal=area.loc[area.sim_sec==end].iloc[0]
            area_windows.append(dict(freeway_percent=pct,start_sec=start,end_sec=end,
                initial_omega_n=int(initial.inside_vehicles),end_omega_n=int(terminal.inside_vehicles),
                ttt_veh_h=float(terminal.ttt_veh_h_cumulative-initial.ttt_veh_h_cumulative),
                ttd_events=int(terminal.ttd_observed_plus_terminal_cumulative-initial.ttd_observed_plus_terminal_cumulative),
                observed_entries=int(aa.observed_entry_events.sum()),appeared_inside=int(aa.appeared_inside_events.sum()),
                unresolved_absences=int(aa.unresolved_inside_disappearances.sum())))
            for link in (2,127,329,10682,10639,10681,71):
                rr=road[(road.link==link)&(road.start_sec>=start)&(road.end_sec<=end)].sort_values('start_sec')
                assert len(rr)==(end-start)//900 and rr.closure.eq(0).all()
                roads.append(dict(freeway_percent=pct,start_sec=start,end_sec=end,link=link,
                    initial_n=int(rr.iloc[0].initial_n),end_n=int(rr.iloc[-1].end_n),end_stopped=int(rr.iloc[-1].end_stopped),
                    arrivals=int(rr.entry.sum()),normal_other_link_exits=int(rr.normal_other_link_exit.sum()),
                    normal_exit_minus_entry=int(rr.normal_other_link_exit.sum()-rr.entry.sum()),
                    absent=int(rr.absent.sum()),matched_native_removal=int(rr.matched_native_removal.sum())))
            observed=inputs[(inputs.input_no==1098)&(inputs.start_sec>=start)&(inputs.end_sec<=end)]
            source_entries.append(dict(freeway_percent=pct,input_no=1098,start_sec=start,end_sec=end,
                desired_vph=desired['1098'],expected_vehicles=desired['1098']*(end-start)/3600,
                first_observed_insertions=int(observed.first_observed_insertions.sum())))
        recovery={}
        for direction in ('E','W'):
            d=fd[(fd.direction==direction)&(fd.end_sec>5400)]
            low=d[(d.speed_kph<30)&(d.n_veh>=5)]
            last=5400 if low.empty else int(low.end_sec.max())
            recovery[direction]=dict(last_low_speed_window_end=last,clear_minutes_after_last_low=(9000-last)/60,
                                      any_low_speed_after5400=not low.empty)
        proof[str(pct)]=dict(completed=True,terminal_sec=9000,original_fzp_prefix=prefix,
            lsa5400_exact=old_lsa==new_lsa,lsa5400_before=old_lsa,lsa5400_extended=new_lsa,
            demand_controls_routes_bytes_unchanged=True,tail_demand_34_inputs_checked_before_and_after=True,
            readbacks_match=True,readback_counts=dict(counts),recovery=recovery,
            native_removals=summary['native_removals'],unknown_inside_disappearances=summary['unknown_inside_disappearances'],
            native_reported_uninserted=sum(int(e['remaining_vehicles']) for e in summary['unfinished_inputs']),
            reported_uninserted_not_actual_source_backlog_proof=True,
            source_fzp_sha256=summary['fzp']['file_sha256'],run_receipt=receipt)
    for name,rows in (('checkpoints',checkpoint),('road_recovery_windows',roads),('area_windows',area_windows),('post5400_source_entries',source_entries)):
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)
    prefix_ok=all(x['original_fzp_prefix']['exact'] and x['lsa5400_exact'] for x in proof.values())
    save(OUT/'validation.json',dict(status='data_complete_pending_figures' if prefix_ok else 'prefix_equivalence_failed',conditions=proof,
         original_prefix_exact=all(x['original_fzp_prefix']['exact'] for x in proof.values()),
         lsa5400_prefix_exact=all(x['lsa5400_exact'] for x in proof.values()),
         limitations=['Native LSA does not show COM GREEN meter transitions; initial/terminal readbacks only.',
                     'No native uninserted warning does not establish zero unmet input demand for a MAX interval.']))
    assert all(x['original_fzp_prefix']['exact'] and x['lsa5400_exact'] for x in proof.values()), 'Prefix comparison failed; preserve and diagnose'
    render(pd.concat(cells),pd.DataFrame(checkpoint))
    print(pd.DataFrame(checkpoint).to_string(index=False))
    print(json.dumps({pct:x['recovery'] for pct,x in proof.items()},ensure_ascii=False))

def render(fd,checkpoints):
    plt.rcParams.update({'font.family':'Malgun Gothic','font.size':11,'axes.unicode_minus':False,
                         'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold'})
    def finish(fig,name):
        for ext in ('png','svg','pdf'): fig.savefig(OUT/f'{name}.{ext}',dpi=175,bbox_inches='tight',facecolor='white')
        plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(14,9),sharex=True,sharey=True,layout='constrained')
    cmap=plt.get_cmap('viridis').copy();cmap.set_bad('#eceff2')
    for j,pct in enumerate((80,90)):
        for i,direction in enumerate(('E','W')):
            ax=axes[i,j];a=fd[(fd.freeway_percent==pct)&(fd.direction==direction)].copy()
            a.loc[a.n_veh<5,'speed_kph']=np.nan
            grid=a.pivot(index='cell',columns='minute',values='speed_kph').to_numpy()
            im=ax.imshow(grid,origin='lower',aspect='auto',extent=(0,150,-.5,20.5),cmap=cmap,vmin=0,vmax=120,interpolation='nearest')
            for minute in (90,120): ax.axvline(minute,color='white',lw=2,ls='--')
            ax.set(title=f'고속도로 {pct}% · 도시 50% · FW_{direction}',xticks=range(0,151,15),yticks=range(0,21,2))
            if i==1: ax.set_xlabel('시간 [min] · 90=5400초 / 120=7200초 / 150=9000초')
            if j==0: ax.set_ylabel('구간: 0 상류 → 20 하류')
    fig.colorbar(im,ax=axes,shrink=.8,label='60초 구간 평균 속도 [km/h]')
    fig.suptitle('마지막 수요를 유지한 9000초 무제어 회복 시험\nseed13 · 4500초 이후 입력률 고정 · 회색: 평균 차량 수5대 미만',fontsize=15)
    fig.supxlabel('각 9000초 런 내부 관측 · 기존 5400초 런과 도시부 일부 궤적 불일치 (보고서 참조)',fontsize=10,color='#5b626b')
    finish(fig,'cooldown_speed_time')
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
    for pct,color in ((80,'#2166ac'),(90,'#d8862c')):
        for direction,style in (('E','-'),('W','--')):
            a=fd[(fd.freeway_percent==pct)&(fd.direction==direction)].copy()
            a['slow']=((a.speed_kph<30)&(a.n_veh>=5)).astype(int)
            b=a.groupby('minute').agg(n=('n_veh','sum'),slow=('slow','sum'))
            axes[0].plot(b.index,b.n,color=color,ls=style,label=f'{pct}–50 / FW_{direction}')
            axes[1].plot(b.index,b.slow,color=color,ls=style)
    for ax in axes:
        for minute in (90,120): ax.axvline(minute,color='#8c98a5',lw=1,ls=':')
        ax.grid(color='#e3e7ea');ax.set_xlim(0,150)
    axes[0].set_ylabel('본선 평균 차량 수 [veh]');axes[0].legend(ncol=2,frameon=False)
    axes[1].set_ylabel('30km/h 미만 구간 수');axes[1].set_xlabel('시뮬레이션 시간 [min]')
    fig.suptitle('5400초 이후에도 수요를 유지했을 때의 본선 축적·저속 구간',fontsize=14)
    fig.supxlabel('각 9000초 런 내부 관측 · 기존 5400초 런과의 전체 궤적 동일성 검증은 실패',fontsize=10,color='#5b626b')
    finish(fig,'cooldown_recovery_series')

if __name__=='__main__':main()
