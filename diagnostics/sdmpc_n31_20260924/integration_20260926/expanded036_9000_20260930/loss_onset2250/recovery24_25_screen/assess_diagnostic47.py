"""Independent RM response of a physically rejected candidate, without refitting."""
import hashlib
import json
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent;I=L.parent.parent
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def main():
    assert not (O/'response47_verification.json').exists()
    protocol=read(O/'response_diagnostic_protocol.json')
    for p,digest in protocol['pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest
    proof=read(L/'posthead_clock10490/independent47_verification.json')
    base=I/'closedloop_recorded2700_lever450_trace10484_clock_ind47_20261001'
    new=I/'closedloop_recorded2700_lever450_trace10484_fd125_ind47diag_20261001'
    receipts=[read(folder/'fixed_replay_receipt.json') for folder in (base,new)]
    for receipt,folder,config in zip(receipts,(base,new),(L/'posthead_clock10490/candidate_config.json',O/'fd125/candidate_config.json')):
        directory=Path(receipt.pop('derived_directory'))
        assert directory.is_relative_to(folder) and directory.is_dir()
        name=str(config.relative_to(Path.cwd()))
        assert receipt['files'].pop(name)==hashlib.sha256(config.read_bytes()).hexdigest()
    assert receipts[0]==receipts[1]
    results={};costs={};times={}
    for arm in ('held_actual','release_actual'):
        r=read(new/(arm+'.json'));b=read(base/(arm+'.json'))
        assert r['commands']==b['commands'] and r['physical_cell_states'][0]==b['physical_cell_states'][0]
        assert r['validation']['all_actuator_and_step_constraints_checked']
        assert max(abs(x['residual']) for x in r['ramps'].values())<1e-7
        parts={road:r['cost_by_stock']['freeway:'+road] for road in ('FW_E','FW_W')}
        parts['ramps']=sum(v for k,v in r['cost_by_stock'].items() if k.startswith('ramp:'))
        parts['other_Omega']=r['ttt_omega_veh_h']-sum(parts.values())
        costs[arm]=parts;times[arm]=r['wall_sec'];results[arm]=r
    h,r=results['held_actual'],results['release_actual']
    assert h['physical_cell_states'][0]==r['physical_cell_states'][0]
    delta=r['ttt_omega_veh_h']-h['ttt_omega_veh_h']
    old=proof['models']['candidate']
    report=dict(status='independent_response_diagnostic_complete',adopted=False,physical_screen_passed=False,
        screen_verdict_unchanged=read(O/'frozen_selection.json')['selected'] is None,
        native_delta_omega=proof['native_delta_omega'],previous_delta_omega=old['delta_omega'],candidate_delta_omega=delta,
        rank_preserved=delta*proof['native_delta_omega']>0,
        error_before=abs(old['delta_omega']-proof['native_delta_omega']),error_after=abs(delta-proof['native_delta_omega']),
        delta_components={k:costs['release_actual'][k]-costs['held_actual'][k] for k in costs['held_actual']},
        previous_delta_components=old['delta_by_group'],native_delta_components=proof['native_delta_by_group'],
        outside_delta=r['tracked_outside_residence_veh_h']-h['tracked_outside_residence_veh_h'],
        ramp_merges={a:{k:v['merge'] for k,v in row['ramps'].items()} for a,row in results.items()},
        ramp_final_stocks={a:{k:v['final_stock'] for k,v in row['ramps'].items()} for a,row in results.items()},
        forecast_compute_sec=sum(times.values()),times=times,forecasts=2,optimizer=0,refit=0,new_native=0,
        common_initial_commands_writer_mass_passed=True,pins=pins,
        limitations=['Additional diagnostic explicitly declared after physical-screen rejection; not a retroactive pass.',
            'Native actual commands are conditioning inputs; future native traffic was not used.',
            'Tests strong10484 RM hold/release only; no VSL response or fullSDMPC derivative/selection proof.'])
    (O/'response47_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('pins','ramp_merges','ramp_final_stocks')},ensure_ascii=False))

if __name__=='__main__':main()
