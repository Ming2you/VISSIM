"""Read-only matched native snapshot estimate; never claims FZP completion."""
import argparse
import bisect
from collections import Counter
import csv
import ctypes
import ctypes.wintypes
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.control_area_objective import physical_membership_from_ledger

END = 6600
MEMBERSHIP = None
VSL_WINDOW = None
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
RUNS = {
    'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
    'sdmpc': Path('D:/VISSIM_runs/20261005_rm233_235_fixed90_s29_9000/sdmpc'),
}
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    assert not (HERE / 'summary.json').exists(), 'Preserve completed analysis'
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
    k.SetPriorityClass.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    area_path = MEMBERSHIP or I / 'selected/scenario/control_area_membership_213a5d.json'
    area = read(area_path)
    membership = physical_membership_from_ledger(area)
    geo = read(I / 'selected/port_gain/geometry.json')
    chains = {int(x['link']): (road, x['offset_m']) for road, chain in geo['chains'].items() for x in chain}
    assert all(membership[str(link)] for link in chains)
    times = np.array([0, 1] + list(range(150, END + 1, 150)), dtype=float)
    sample_times = times[1:]
    parts = ['FW_E', 'FW_W', 'Omega_other', 'outside_Omega']
    data, provenance, warmup = {}, {}, {}
    for arm, run in RUNS.items():
        provenance_paths = list(run.glob('run_provenance_*.json'))
        assert len(provenance_paths) == 1, 'Require one unambiguous native run'
        name = provenance_paths[0].stem.removeprefix('run_provenance_')
        prov = read(provenance_paths[0])
        provenance[arm] = prov
        assert prov['seed'] == 29 and prov['sim_period_sec'] >= END
        network = Path(prov['files']['network']['path'])
        network_sha = hashlib.sha256(network.read_bytes()).hexdigest()
        assert network_sha == prov['files']['network']['sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
        assert network_sha == area['network']['sha256']
        PINS[str(network)] = network_sha
        counts = {road: np.zeros((31, len(sample_times)), dtype=int) for road in ['FW_E', 'FW_W']}
        sums = {road: np.zeros_like(x, dtype=float) for road, x in counts.items()}
        stocks = np.zeros((len(times), len(parts)), dtype=int)
        rows = 0
        for si, t in enumerate(sample_times):
            state = read(run / f'decisions_{name}' / f'state_{int(t):06d}.json')
            v = state['vehicle_records']; records = v['records']
            assert state['sim_sec'] == t == v['paused_at_sim_sec'] == v['capture_sim_sec_before'] == v['capture_sim_sec_after']
            assert state['run_provenance']['run_id'] == prov['run_id']
            assert v['complete'] and v['unobservable_count'] == 0
            assert len(records) == v['record_count'] == state['total_vehicles']
            assert len({x['veh_no'] for x in records}) == len(records)
            direct_counts = Counter(str(x['link_no']) for x in records)
            assert dict(direct_counts) == {str(link): n for link, n in v['full_network_link_counts'].items() if n}
            assert set(direct_counts) <= membership.keys()
            if t <= 900:
                digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
                if arm == 'nc': warmup[int(t)] = digest
                else: assert digest == warmup[int(t)], ('Unmatched warmup', t)
            rows += len(records)
            for x in records:
                link = int(x['link_no']); address = chains.get(link)
                if address is not None:
                    road, offset = address
                    pos = offset + x['position_m']; bounds = geo['bounds'][road]
                    assert bounds[0] <= pos <= bounds[-1]
                    cell = min(30, bisect.bisect_right(bounds, pos) - 1)
                    speed = x['speed_kph']; assert np.isfinite(speed) and speed >= 0
                    counts[road][cell, si] += 1; sums[road][cell, si] += speed
                    stocks[si + 1, parts.index(road)] += 1
                elif membership[str(link)]: stocks[si + 1, 2] += 1
                else: stocks[si + 1, 3] += 1
            assert stocks[si + 1].sum() == len(records)
            assert stocks[si + 1, :3].sum() == sum(n for link, n in direct_counts.items() if membership[link])
            for road in counts:
                selected = [x['speed_kph'] for x in records if chains.get(int(x['link_no']), (None,))[0] == road]
                assert counts[road][:, si].sum() == len(selected)
                assert abs(sums[road][:, si].sum() - sum(selected)) < 1e-7
        increments = (stocks[1:] + stocks[:-1]) * .5 * np.diff(times)[:, None] / 3600
        cumulative = np.vstack([np.zeros(4), np.cumsum(increments, axis=0)])
        # Independent direct trapezoid, including the actual t=1 warmup observation.
        for pi in range(4):
            direct = sum((stocks[j, pi] + stocks[j-1, pi]) * (times[j]-times[j-1]) / 7200 for j in range(1,len(times)))
            assert abs(direct - cumulative[-1, pi]) < 1e-9
        speeds = {road: np.divide(sums[road], counts[road], out=np.full_like(sums[road], np.nan), where=counts[road] > 0) for road in counts}
        data[arm] = dict(stocks=stocks, cumulative=cumulative, speed=speeds, counts=counts, rows=rows)
        np.savez_compressed(HERE / f'{arm}_snapshots.npz', times=times, stocks=stocks, cumulative_ttt=cumulative,
                            **{road+'_speed': x for road,x in speeds.items()}, **{road+'_counts': x for road,x in counts.items()},
                            **{road+'_bounds_m': geo['bounds'][road] for road in counts})
        with (HERE / f'{arm}_timeseries.csv').open('w', newline='', encoding='utf8') as f:
            fields = ['sim_sec'] + [part+'_N' for part in parts] + [part+'_TTT_veh_h' for part in parts]
            writer = csv.writer(f); writer.writerow(fields)
            writer.writerows([t, *stocks[i].tolist(), *cumulative[i].tolist()] for i,t in enumerate(times))
    # Native terminal times may differ; both records cover the same END cutoff.
    for key in ['seed', 'control_interval_sec', 'demand_scale']:
        assert provenance['nc'][key] == provenance['sdmpc'][key]
    for key in ['network','control_mapping','vehicle_input_roles','demand_profile','urban_input_gate_map','generated_vbs_config','signal_group_plan']:
        assert provenance['nc']['files'][key]['sha256'] == provenance['sdmpc']['files'][key]['sha256'], key
    for key in ['RW_MAINLINE_SG_ONLY','RW_OBS150_EXPECTED_SIMRES','RW_OBS150_VEHREC_SEC','RW_OFFSET_WRITER','RW_RAMP_AMBER_SEC']:
        assert provenance['nc']['env'][key] == provenance['sdmpc']['env'][key], key
    comparisons = {}
    for part in ['Omega'] + parts:
        vals = {arm: float(d['cumulative'][-1,:3].sum() if part == 'Omega' else d['cumulative'][-1, parts.index(part)]) for arm,d in data.items()}
        comparisons[part] = dict(**vals, delta_control_minus_nc=vals['sdmpc']-vals['nc'], improvement_percent=100*(1-vals['sdmpc']/vals['nc']))
    # Existing completed NC 5s-FZP summary: validation of coarse integration only,
    # never use its discrepancy as a correction or bound for the control run.
    fine_reference = None
    if MEMBERSHIP is None:
        cache = I / 'expanded036_9000_20260930/analysis/nc/area_timeseries.csv'
        raw = cache.read_bytes(); PINS[str(cache)] = hashlib.sha256(raw).hexdigest()
        cache_rows = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
        fine_nc = float(np.interp(END, [float(x['sim_sec']) for x in cache_rows], [float(x['ttt_veh_h_cumulative']) for x in cache_rows]))
        coarse_nc = comparisons['Omega']['nc']
        fine_reference = dict(TTT_veh_h=fine_nc, coarse_minus_fine_veh_h=coarse_nc-fine_nc,
            relative_error_percent=100*(coarse_nc/fine_nc-1), source=str(cache), interpolated_end_sec=END,
            control_error_not_inferred=True)
    sensitivity = {}
    for interval in [150,300]:
        idx = [j for j,t in enumerate(times) if t in (0,1,END) or t % interval == 0]
        totals = {}
        for arm,d in data.items():
            ns = d['stocks'][idx,:3].sum(axis=1)
            totals[arm] = float(((ns[1:]+ns[:-1])*.5*np.diff(times[idx])/3600).sum())
        sensitivity[str(interval)] = dict(**totals, improvement_percent=100*(1-totals['sdmpc']/totals['nc']))
    summary = dict(status='INTERIM_SNAPSHOT_ESTIMATE_NOT_FINAL', end_sec=END,
        native_period_sec={arm: prov['sim_period_sec'] for arm, prov in provenance.items()},
        source='Completed saved native full-vehicle snapshots; no new COM reads and no plant prediction',
        observation_times=sample_times.tolist(), seed=29, initial_empty_at0=True,
        method=f'Trapezoid of physical Omega stock at t=0,1,150,...,{END}; identical sparse estimator for both arms',
        Omega='controlled freeway plus protected urban; all observed ramp/urban stocks on inside links included',
        membership_path=str(area_path), inside_link_count=sum(membership.values()),
        comparison_veh_h=comparisons, coarse_time_sensitivity=sensitivity,
        snapshot_rows={a:d['rows'] for a,d in data.items()},
        end_stock={a:dict(zip(parts,d['stocks'][-1].tolist())) for a,d in data.items()},
        matched_metadata=True, warmup_records_exact_at=list(warmup),
        nc_fine_reference=fine_reference,
        current_fzp_bytes=next((RUNS['sdmpc']/'vissim_eval').glob('*.fzp')).stat().st_size,
        limitations=['150s snapshots can miss between-sample queue changes and wave propagation.',
            f'No final gain claim: matched observation cutoff is {END}; this is not a completed-run analysis.',
            'Native deletion, uninserted vehicles and exact exit events have not been compared at this cutoff.',
            'Outside-Omega residence is a diagnostic; uninserted waiting is not present in saved vehicle records.',
            'Heatmap is instantaneous samples expanded to nearest midpoints, not150s average or5s FZP.',
            'This compares the combined policy, not the isolated causal gain of RM or VSL.'],
        source_sha256=PINS, live_processes_or_configuration_changed=False, FZP_read=False,
        vsl_window_sec=VSL_WINDOW)
    draw(data, sample_times, geo)
    draw_ttt(data, times, sum(membership.values()))
    save(HERE/'summary.json', summary)
    print(json.dumps({k:summary[k] for k in ['status','comparison_veh_h','end_stock','nc_fine_reference','coarse_time_sensitivity']},ensure_ascii=False),flush=True)


def draw(data, sample_times, geo):
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':12,'figure.facecolor':'white'})
    edges = np.r_[sample_times[0], (sample_times[:-1]+sample_times[1:])/2, sample_times[-1]]
    cmap = plt.get_cmap('RdYlBu').copy(); cmap.set_bad('#e4e4e4')
    for road,label in [('FW_E','동측'),('FW_W','서측')]:
        fig, axes = plt.subplots(2,1,figsize=(13.5,10),sharex=True,sharey=True)
        fig.subplots_adjust(left=.085,right=.765,bottom=.15,top=.865,hspace=.22)
        control_title = ('SDMPC + 동측 고정 VSL90' if VSL_WINDOW is None else
                         f'SDMPC · 동측 병목 VSL90: {VSL_WINDOW[0]}–{VSL_WINDOW[1]}초')
        for ax,arm,title in zip(axes,['nc','sdmpc'],['무제어 · VSL110',control_title if road=='FW_E' else 'SDMPC · 서측 VSL110 유지']):
            mesh = ax.pcolormesh(edges,np.array(geo['bounds'][road])/1000,data[arm]['speed'][road],cmap=cmap,vmin=0,vmax=120,shading='flat')
            ax.set(xlim=(1,END),ylim=(0,geo['bounds'][road][-1]/1000),ylabel='진입점부터 거리 [km] → 하류')
            ax.set_title(title,fontsize=15,loc='left')
            if arm == 'sdmpc':
                ax.axvline(900,ls=':',color='#333333',lw=.9)
                if VSL_WINDOW is not None and road == 'FW_E':
                    for boundary in VSL_WINDOW:
                        if boundary <= END:
                            ax.axvline(boundary,ls='--',color='#333333',lw=1.1)
            marks=sorted([b for b in geo['boundaries'] if b['road']==road and b['kind'] in ('ramp','offramp')],key=lambda b:b['chain_pos_m'])
            last=-1
            for b in marks:
                y=b['chain_pos_m']/1000; at=max(y,last+.45); last=at
                ax.axhline(y,color='#293443',lw=.45,alpha=.45,ls='--')
                ax.annotate(f"{b['connector']} {'진입' if b['kind']=='ramp' else '진출'}",xy=(END,y),xytext=(END+145,at),fontsize=9.5,va='center',clip_on=False,arrowprops=dict(arrowstyle='-',lw=.6,color='#465566'))
        axes[-1].set_xlabel('시뮬레이션 시간 [초]')
        axes[-1].set_xticks(sorted(set([1, END] + list(range(900, END-299, 900)))))
        axes[-1].tick_params(axis='x',labelsize=10)
        cax=fig.add_axes([.91,.25,.018,.50]); fig.colorbar(mesh,cax=cax,label='관측 차량 평균속도 [km/h]',extend='max')
        fig.suptitle(f'{label} 본선 | 무제어 vs 현재 SDMPC 런',fontsize=19,y=.97)
        fig.text(.085,.914,f'동일 망·수요·seed29 · 1–{END:,}초 중간 결과 · 31개 물리 셀',fontsize=12)
        caption = '150초 간격 순간 관측 · 점선: 900초 SDMPC 시작'
        if VSL_WINDOW is not None and road == 'FW_E':
            caption += f' · 파선: VSL90 {VSL_WINDOW[0]}–{VSL_WINDOW[1]}초 (밖은110)'
        fig.text(.085,.080,caption,fontsize=10.5)
        fig.text(.085,.047,'회색: 관측 차량 없음 · 램프 표시는 본선 접속 위치 · 색상 범위는 두 조건 동일',fontsize=11,color='#555555')
        fig.savefig(HERE/f'{road}_NC_vs_SDMPC_to{END}.png',dpi=150)
        plt.close(fig)


def draw_ttt(data, times, inside_count):
    fig, axes = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True)
    fig.subplots_adjust(left=.10, right=.97, top=.84, bottom=.15, hspace=.32)
    for arm, label, color, style in [('nc', '무제어', '#56616c', '--'),
                                      ('sdmpc', '현재 SDMPC', '#166a9f', '-')]:
        axes[0].plot(times, data[arm]['cumulative'][:, :3].sum(axis=1),
                     label=label, color=color, ls=style, lw=2)
    delta = data['sdmpc']['cumulative'] - data['nc']['cumulative']
    for y, label, color in [(delta[:, 0], '동측 본선', '#277da8'),
                             (delta[:, 1], '서측 본선', '#9b6f23'),
                             (delta[:, 2], '도시부·램프', '#b35477'),
                             (delta[:, :3].sum(axis=1), '전체 Ω', '#20262c')]:
        axes[1].plot(times, y, label=label, color=color, lw=2)
    axes[1].axhline(0, color='#808080', lw=.8)
    for ax in axes:
        ax.grid(alpha=.18)
        ax.axvline(900, color='#555555', ls=':', lw=1)
        ax.legend(frameon=False, ncol=2, loc='upper left')
        ax.set_xlim(0, END)
    axes[0].set_ylabel('누적 Ω TTT [차량·시간]')
    axes[0].set_ylim(bottom=0)
    axes[1].legend(frameon=False, ncol=4, loc='lower left', bbox_to_anchor=(0, 1.02), fontsize=11)
    axes[1].set_ylabel('SDMPC - 무제어 [차량·시간]')
    axes[1].set_xlabel('시뮬레이션 시간 [초]')
    axes[1].set_xticks(sorted(set([0, END] + list(range(900, END-299, 900)))))
    fig.suptitle('전체 망 TTT 비교 | 현재 런 중간 결과', fontsize=19, y=.97)
    fig.text(.10, .90, f'동일 망·수요·seed29 · 0–{END:,}초 · 접근도로 포함 Ω {inside_count}개 링크', fontsize=12)
    fig.text(.10, .065, '150초 재고 관측의 사다리꼴 적분 추정 · 아래 패널: 음수는 TTT 감소, 양수는 증가', fontsize=11)
    fig.text(.10, .03, '최종 5초 FZP 성능 검증 아님 · 외부 대기·정상 유출·삭제·미삽입은 별도 검증 대상', fontsize=10.5, color='#555555')
    fig.savefig(HERE / f'TTT_NC_vs_SDMPC_to{END}.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--end', type=int, default=END)
    parser.add_argument('--sdmpc-run', type=Path, default=RUNS['sdmpc'])
    parser.add_argument('--nc-run', type=Path, default=RUNS['nc'])
    parser.add_argument('--out', type=Path, default=HERE)
    parser.add_argument('--membership-json', type=Path)
    parser.add_argument('--vsl-window', type=int, nargs=2, metavar=('START', 'END'),
                        help='Display the recorded bottleneck VSL90 interval; outside it VSL110')
    args = parser.parse_args()
    assert 900 <= args.end <= 9000 and args.end % 150 == 0
    END, HERE = args.end, args.out.resolve()
    VSL_WINDOW = args.vsl_window
    if VSL_WINDOW is not None:
        assert 0 <= VSL_WINDOW[0] < VSL_WINDOW[1]
    MEMBERSHIP = args.membership_json.resolve() if args.membership_json else None
    RUNS = {'nc': args.nc_run.resolve(), 'sdmpc': args.sdmpc_run.resolve()}
    main()
