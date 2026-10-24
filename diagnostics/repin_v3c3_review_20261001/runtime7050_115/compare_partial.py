"""User-requested matched0..7050 comparison of the closed failed run; no replay."""
import ctypes
import ctypes.wintypes
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from scripts.measure_control_area import read_fzp_frames,measure_frames,state_frame,terminal_lengths,sha256
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from diagnostics.capture_native_runtime_errors import parse_bytes

def read(p):return json.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    output=HERE/'partial7050';output.mkdir(exist_ok=False)
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    k.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    area_path=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/control_area_membership_213a5d.json'
    document=read(area_path);membership=physical_membership_from_ledger(document);terminals=terminal_lengths(document)
    runs={'nc':Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
          'sdmpc':Path('D:/VISSIM_runs/20261003_service66_queuezero_s29_9000/sdmpc')}
    summary=dict(scope='closed failed-run comparison0..7050; user authorized partial analysis; not9000 qualification',
        end_sec=7050,seed=29,Omega='freeway+protected urban',membership_path=str(area_path),membership_sha256=sha256(area_path),
        native_uninserted_at7050_comparison=None,uninserted_limitation='NC end-of-run9000 ERR is not comparable to failed7050; not substituted',arms={})
    common=None
    geometry=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    start=time.perf_counter()
    for arm,run in runs.items():
        name='sdmpc31_'+('nc' if arm=='nc' else 'sdmpc')+'9000_s29'
        network=run/'network'/f'{name}.inpx'
        assert sha256(network)=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
        decisions=run/('decisions_'+name)
        initial=read(decisions/'state_000900.json')['vehicle_records'];assert initial['complete']
        if common is None:common=initial['records']
        else:assert common==initial['records'],'Common precontrol900 stock differs'
        state_path=decisions/'state_007050.json';raw=read(state_path)
        final=state_frame(state_path,7050,expected_run_id=raw['run_provenance']['run_id'])
        error_path=run/'network'/f'{name}_001.err'
        parsed=parse_bytes(error_path.read_bytes());assert not parsed['unparsed_removal_lines']
        removals={str(e['vehicle_id']):e for e in parsed['events'] if e['kind']=='lane_change_removal' and e['time_sec']<=7050}
        fzp,=(run/'vissim_eval').glob('*.fzp');before=fzp.stat();prefix=hashlib.sha256();prefix_count=0
        previous=None
        def frames():
            nonlocal previous,prefix_count
            for frame in read_fzp_frames(fzp):
                if frame.time_sec>7050:break
                if frame.time_sec<900:
                    # Fixed native state fields, not a claim about all FZP columns.
                    for no,v in sorted(frame.vehicles.items()):
                        prefix.update(f'{frame.time_sec}|{no}|{v.link}|{v.position_m}|{v.speed_kph}\n'.encode('ascii'));prefix_count+=1
                if previous:
                    dt=frame.time_sec-previous.time_sec
                    for no in previous.vehicles.keys()-frame.vehicles.keys():
                        v=previous.vehicles[no]
                        if no in removals and v.link in terminals:
                            reach=v.speed_kph/3.6*dt+1.5*dt*dt+10
                            overshoot=v.speed_kph/3.6*.1+.015+10
                            assert not -overshoot<=terminals[v.link]-v.position_m<=reach,('Removal would be normal exit',no)
                previous=frame
                yield frame
        metrics,rows=measure_frames(frames(),membership,terminals,end_sec=7050,final_frame=final,
                                  max_tail_extrap_sec=0,simulation_step_sec=.1)
        after=fzp.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        assert metrics['sampling']['nominal_step_sec']==5 and not metrics['sampling']['missing_snapshot_gaps']
        assert metrics['boundaries']['unobserved_tail_sec']==0
        residence=metrics['physical_link_residence'];parts={}
        for road in ['FW_E','FW_W']:
            links={str(l) for l,a in geometry['addresses'].items() if a[0]==road}
            parts[road+'_mainline']=sum(v['ttt_veh_h'] for l,v in residence.items() if l in links)
        parts['Omega_other']=metrics['ttt_veh_h']-sum(parts.values())
        armout=output/arm;armout.mkdir()
        save(armout/'metrics.json',metrics)
        with (armout/'timeseries.csv').open('w',newline='',encoding='utf8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        row=dict(TTT_Omega_veh_h=metrics['ttt_veh_h'],TTT_parts=parts,
            outside_Omega_residence_veh_h=sum(v['ttt_veh_h'] for v in residence.values() if not v['inside']),
            sampled_normal_exit_events=metrics['ttd_observed_plus_terminal_events'],
            normal_exit_limitation='Observed Omega crossings + inferred reachable terminal departures;5s sampling can miss short excursions',
            native_removals_0_7050=len(removals),native_removals_inside=sum(membership[str(e['link'])] for e in removals.values()),
            unresolved_inside_disappearances=metrics['unresolved_inside_disappearances'],
            Omega_end_vehicles=metrics['censored_last_observed_inside_vehicles'],network_end_vehicles=raw['total_vehicles'],
            last_fzp_sec=metrics['boundaries']['last_fzp_sec'],final_frame_sec=7050,
            prefix_fields_sha256=prefix.hexdigest(),prefix_records=prefix_count,
            fzp_path=str(fzp),fzp_bytes=before.st_size,fzp_mtime_ns=before.st_mtime_ns,
            state_sha256=sha256(state_path),err_sha256=sha256(error_path))
        summary['arms'][arm]=row;save(output/'partial.json',summary)
        print(json.dumps({arm:row},ensure_ascii=False),flush=True)
    a,b=(summary['arms'][arm] for arm in ['nc','sdmpc'])
    summary['common900_state_exact']=True
    summary['common_pre900_fzp_fields_exact']=(a['prefix_fields_sha256'],a['prefix_records'])==(b['prefix_fields_sha256'],b['prefix_records'])
    assert summary['common_pre900_fzp_fields_exact']
    summary['delta_TTT_Omega_veh_h']=b['TTT_Omega_veh_h']-a['TTT_Omega_veh_h']
    summary['TTT_change_percent']=100*summary['delta_TTT_Omega_veh_h']/a['TTT_Omega_veh_h']
    summary['delta_TTT_parts']={key:b['TTT_parts'][key]-a['TTT_parts'][key] for key in a['TTT_parts']}
    summary['elapsed_sec']=time.perf_counter()-start
    save(output/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='arms'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
