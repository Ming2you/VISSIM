"""One-shot lightweight pre-control comparison; never reads FZP or starts runs."""
import csv
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUNS={'nc':Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
      'sdmpc':Path('D:/VISSIM_runs/20261002_service66_s29_9000/sdmpc')}
PINS={}

def data(path):
    raw=path.read_bytes();PINS[str(path)]=hashlib.sha256(raw).hexdigest();return raw

def load(path):return json.loads(data(path).decode('utf-8-sig'))

def main():
    output=HERE/'matched_nc_preflight.json'
    assert not output.exists(),'Preserve existing preflight'
    report={'created_at':datetime.datetime.now().astimezone().isoformat(),
        'status':'started','nc_directory':str(RUNS['nc']),'sdmpc_directory':str(RUNS['sdmpc']),
        'fzp_reads':0,'full_native_execution_verified':False,'gain_qualified':False}
    try:
        names={a:f'sdmpc31_{a}9000_s29' for a in RUNS}
        provenance={a:load(p/f'run_provenance_{names[a]}.json') for a,p in RUNS.items()}
        conditions=('seed','sim_period_sec','control_interval_sec','state_log_interval_sec','demand_scale')
        report['conditions']={k:provenance['nc'][k] for k in conditions}
        assert all(provenance['nc'][k]==provenance['sdmpc'][k] for k in conditions)
        assert report['conditions']==dict(seed=29,sim_period_sec=9000,control_interval_sec=150,
                                         state_log_interval_sec=150,demand_scale=1.)
        report['equal_files']={}
        for key in ('network','control_mapping','generated_vbs_config','vehicle_input_roles',
                    'demand_profile','urban_input_gate_map','signal_group_plan'):
            records={a:p['files'][key] for a,p in provenance.items()}
            for record in records.values():
                actual=hashlib.sha256(data(Path(record['path']))).hexdigest()
                assert actual==record['sha256'],(key,'actual file changed')
            assert records['nc']['sha256']==records['sdmpc']['sha256'],key
            report['equal_files'][key]=records
        report['runner_sha_equal']={k:provenance['nc']['files'][k]['sha256']==provenance['sdmpc']['files'][k]['sha256']
                                    for k in ('main_vbs_runner','watchdog_wrapper')}
        for key in ('RW_OBS150_EXPECTED_SIMRES','RW_OBS150_VEHREC_SEC','RW_OBSERVATION_CADENCE',
                    'RW_OBS150_DETECTORS_SHA256','RW_MAINLINE_SG_ONLY','RW_RAMP_AMBER_SEC','RW_OFFSET_WRITER'):
            assert provenance['nc']['env'][key]==provenance['sdmpc']['env'][key],key
        signal_tables={}
        for arm,p in provenance.items():
            table={}
            for record in p['signal_programs']:
                path=Path(record['path']);assert hashlib.sha256(data(path)).hexdigest()==record['sha256']
                assert path.name not in table;table[path.name]=record['sha256']
            signal_tables[arm]=table
        assert signal_tables['nc']==signal_tables['sdmpc']
        report['native_signal_files']=signal_tables['nc']
        decisions={a:p/f'decisions_{names[a]}' for a,p in RUNS.items()}
        report['frames']=[];report['warmup_commands']=[]
        for sec in (0,1,150,300,450,600,750,900):
            frames={a:load(p/f'lane_observations/frame_{sec:06d}.json') for a,p in decisions.items()}
            for arm,frame in frames.items():
                assert frame.pop('run_id')==provenance[arm]['run_id']
            assert frames['nc']==frames['sdmpc'],('frame',sec)
            report['frames'].append(dict(sim_sec=sec,all_fields_except_run_id_exact=True,
                                         vehicles=len(frames['nc']['vehicles'])))
        for sec in (1,150,300,450,600,750):
            tables={a:list(csv.DictReader(data(p/f'action_{sec:06d}.csv').decode('utf-8-sig').splitlines()))
                    for a,p in decisions.items()}
            assert tables['nc']==tables['sdmpc'],('warmup commands',sec)
            report['warmup_commands'].append(dict(sim_sec=sec,all_columns_equal=True,rows=len(tables['nc'])))
        log=data(RUNS['nc']/f'runlog_{names["nc"]}.txt').decode('utf-8-sig').splitlines()
        assert 'STAGE=SIM_DONE' in log and 'SIM_SEC=9000' in log
        assert f'OK {names["nc"]} attempt=1 ' in data(RUNS['nc']/'launch.log').decode('utf-8-sig')
        report['matched_nc_completed']=True
        report['status']='PRECONTROL_SNAPSHOT_AND_COMMAND_PASS'
        report['limitations']=['Eight captured frames and warmup commands match; full 5s FZP prefix is still required after native closure.',
            'This does not certify post900 LDP/VSL execution, solver convergence, or gain.',
            'Different controller/model files are expected; runtime differences are recorded and native equality is checked directly.']
    except Exception as exc:
        report['status']='FAILED';report['error']=repr(exc)
        raise
    finally:
        report['pins']=PINS
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(report['status'],'signals',len(signal_tables['nc']),'frames',len(report['frames']))

if __name__=='__main__':main()
