"""Completed-run physical replay qualification using existing bounded readers."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'reports/20260911_decision_runtime')]
import audit_fw8_rg_meter_response as meters
import audit_nuf_band_native as local


def main():
    name=sys.argv[1]
    label=sys.argv[2]
    target=D/(label+'.json')
    if target.exists():raise FileExistsError(target)
    started=time.perf_counter()
    meters.END=1350
    base=meters.load_run('codex_physical8_fw080_u050_open1350_v1')
    run=meters.load_run(name)
    receipt=json.loads((run['directory']/'completion_receipt.json').read_text(encoding='utf-8-sig'))
    report={'completed':False,'native_execution_passed':receipt['native_execution_passed'],
        'native_lsa_com_coverage_passed':receipt['native_lsa_com_coverage_passed'],
        'execution_checks':{k:v['passed'] for k,v in receipt['native_execution_verification']['checks'].items()},
        'source_pins':{**base['pins'],**run['pins']},
        'logical_targets_replayed':False,'full_action_replay_pass':False,
        'finite_neighborhood_certified':False,
        'scope':'Completed selected physical-command replay only; fixed-profile NP/NUF metadata mismatch retained separately; not closed loop or GNE certification.'}
    assert report['native_execution_passed']
    meters.START,meters.END=1,900
    report['warmup_prefix']=meters.first_raw_difference(base,run)
    assert report['warmup_prefix']['all_raw_data_rows_equal']
    meters.START,meters.END=900,1350
    report['first_post900_difference']=meters.first_raw_difference(base,run)
    exclusions=('local_observation.signal_observation_window.config_sha256','network_path',
                'run_provenance.manifest_path','run_provenance.run_id','sim_period_sec')
    states=[]
    for item in (base,run):
        p=item['directory']/('decisions_'+item['name'])/'state_000900.json'
        raw=json.loads(p.read_text(encoding='utf-8-sig'))
        for key in exclusions:
            parent=raw;parts=key.split('.')
            for part in parts[:-1]:parent=parent[part]
            parent.pop(parts[-1],None)
        states.append(raw)
    report['state_identity_exclusions']=exclusions
    report['initial900_observations_and_head_history_exact']=states[0]==states[1]
    assert report['initial900_observations_and_head_history_exact']
    expected=list(csv.DictReader((D/'fast_np_replay_preflight_v2/action_000900.csv').open(encoding='utf-8-sig',newline='')))
    report['all_four_decision_csv_rows_exact']={}
    for sec in (900,1050,1200,1350):
        p=run['directory']/('decisions_'+name)/f'action_{sec:06d}.csv'
        rows=list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
        report['all_four_decision_csv_rows_exact'][str(sec)]=rows==expected
    assert all(report['all_four_decision_csv_rows_exact'].values())
    report['ramps450']=meters.collect(run)
    report['sc1004']={k:local.signal_window(item,sc=1004,start=900,end=1350)
                     for k,item in (('baseline',base),('selected',run))}
    report['approach_corridors']={k:local.corridor_window(item,roads=[68,69,70,71,420,121],start=900,end=1350)
                                 for k,item in (('baseline',base),('selected',run))}
    report['source_changes']=[p for p,h in report['source_pins'].items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    report['completed']=not report['source_changes']
    report['wall_sec']=time.perf_counter()-started
    target.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('completed','native_execution_passed','native_lsa_com_coverage_passed','initial900_observations_and_head_history_exact','wall_sec','source_changes')}))


if __name__=='__main__':
    try:
        main()
    except Exception:
        (D/(sys.argv[2]+'.failed.json')).write_text(json.dumps({'completed':False,'error':traceback.format_exc()},indent=2)+'\n',encoding='utf-8')
        raise
