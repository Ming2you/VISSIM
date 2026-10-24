"""Read-only native1s observation replay through the canonical adapter/writer."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,csv,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
N=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native348'
SOURCE=Path('E:/VISSIM_runs/20261011_native348_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
ap=argparse.ArgumentParser();ap.add_argument('--condition',choices=('window','optimized','off'),required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
args.out.mkdir(exist_ok=False);(args.out/'vsl_history').mkdir()
os.chdir(ROOT);sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0',RW_DECISION_FAIL_FAST='1')
from evaluation.controllers import vissim_stackelberg_adapter as a,obs150_contract as oc,vsl_exposure_history as vh,multirate_freeway as fw
def audit(event,values):
    if event=='open' and isinstance(values[0],str) and isinstance(values[1],str) and any(x in values[1] for x in ('w','a','+')):
        if Path(values[0]).resolve().is_relative_to(SOURCE):raise RuntimeError('Diagnostic attempted to alter failed native evidence')
sys.addaudithook(audit)
def derived(raw,document):
    path=args.out/f"derived_{document['sim_sec']:06d}.json";path.write_bytes(oc.derived_bytes(document));return path
oc.write_derived=derived
initialize=vh.initialize
vh.initialize=lambda *v,**kw:initialize(*v,**dict(kw,history_directory=args.out/'vsl_history'))
def forbidden(*v,**kw):raise AssertionError('Startup command must not run a forecast')
a.build_one_step_prediction=forbidden
path=SOURCE/'state_000001.json';before=path.read_bytes();tuning=N/f'{args.condition}_config.json'
sys.argv=[a.__file__,'--state-json',str(path),'--out-action-json',str(args.out/'action.json'),'--out-action-csv',str(args.out/'action.csv'),
    '--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
    '--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),
    '--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
    '--tuning-json',str(tuning),'--controller','no-control']
started=time.perf_counter();a.main()
result=json.loads((args.out/'action.json').read_bytes())
assert path.read_bytes()==before and result['metadata']['sim_sec']==1
assert result['prediction']['status']=='not_requested'
assert result['prediction']['mode']=='native_startup_command_only'
assert result['diagnostics']['no_control_active']==1
with (args.out/'action.csv').open(encoding='utf8',newline='') as f:rows=list(csv.DictReader(f))
assert rows and all(float(r['speed_kph'])==110 for r in rows if r['kind']=='vsl')
assert not any(r['kind']=='signal' for r in rows)
receipt=dict(status='canonical_startup_replay_passed_not_native_run',condition=args.condition,seconds=time.perf_counter()-started,
    original_time_preserved=1,new_predictions=0,new_native=0,source_sha256=hashlib.sha256(before).hexdigest(),rows_by_kind={k:sum(r['kind']==k for r in rows) for k in set(r['kind'] for r in rows)},
    runtime_setup_sha256=hashlib.sha256((ROOT/'evaluation/controllers/runtime_setup.py').read_bytes()).hexdigest(),
    adapter_sha256=hashlib.sha256((ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py').read_bytes()).hexdigest())
(args.out/'verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))
