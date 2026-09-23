r"""Is the model smearing the queue front at the coarse cells 14-15?

Compares the per-cell occupancy TIME SERIES (not just the window mean) for the congested
stretch, model vs native, in the no-control (hold / none) case first - if the model cannot
hold a sharp front even without control, that is a discretization/wave problem, not a
metering-response problem.
"""
import sys, json, os, importlib.util
from collections import defaultdict
from pathlib import Path
ROOT=Path(r'D:\VISSIM-merge\sim3')
CAL=ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
RD=ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
MODEL=RD/'controller_response_4500_v1/model_v3'
sys.path[:0]=[str(CAL),str(RD),str(ROOT/'.review-deps'),str(ROOT)]
from canonical_harness import load_base_model
import evaluate_response as er
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
CUT=float(os.environ.get('QF_CUTOFF','3450.1')); WIN=450.
CELLS=list(range(11,21))
NONE=Path(r'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\run\vissim_eval\baseline_001.fzp')

def native_series(geom):
    link={}
    for road,rs in geom['chains'].items():
        for r in rs: link[str(r['link'])]=(road,float(r['offset_m']))
    bounds=sorted((c['start_m'],c['end_m'],c['cell']) for c in geom['cells'] if c['road']=='FW_E')
    per=defaultdict(lambda: defaultdict(int))
    with NONE.open('rb') as f:
        for raw in f:
            if not raw[:1].isdigit(): continue
            p=raw.split(b';',6); t=float(p[0])
            if t<CUT-1e-6: continue
            if t>CUT+WIN+1e-6: break
            lk=p[2].decode('ascii')
            if lk not in link: continue
            road,off=link[lk]
            if road!='FW_E': continue
            x=off+float(p[4])
            for a,b,i in bounds:
                if a-1e-6<=x<b: per[t][i]+=1; break
    return per

if __name__=='__main__':
    spec=importlib.util.spec_from_file_location('h',ROOT/'diagnostics/offramp_dynamic_20260922/study.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    data,_=m.corrected_data()
    cfg=json.loads((MODEL/'config.json').read_text(encoding='utf-8-sig'))
    cfg['freeway']['physical_integration_step_sec']=1
    tmp=MODEL/'_probe_qf.json'; tmp.write_text(json.dumps(cfg),encoding='utf-8')
    model=load_base_model(data.geometry,tmp)
    params=load(MODEL/'selected_parameters.json')['parameters']
    _nu=os.environ.get('QF_NU'); _ka=os.environ.get('QF_KAPPA')
    if _nu or _ka:
        import copy as _c; params=_c.deepcopy(params)
        for _r in params['by_direction'].values():
            if _nu: _r['nu_km2_h']=float(_nu)
            if _ka: _r['kappa_veh_km_lane']=float(_ka)
        print(f"  [probe] nu={_nu or 'base'} kappa={_ka or 'base'}")
    profile=load(RD/'controller_response_4500_v1/model_v3/port_profile.json')
    policy=load(Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls/rules/prepared_rm/rule_policy.json'))
    ids={d:120. for z,v in policy['zone_dsds'].items() for d in v}
    w=er.window(data,model,CUT,'history_forecast',profile,lambda t:({},ids))
    pred=er.simulate(model,w,params)
    ms=defaultdict(dict)
    for x in pred['cells']:
        if x['road']=='FW_E' and x['cell'] in CELLS: ms[x['time_s']][x['cell']]=x['n_veh']
    nat=native_series(data.geometry)
    lens={c['cell']:c['end_m']-c['start_m'] for c in data.geometry['cells'] if c['road']=='FW_E'}
    print("=== 무제어 밀도 프로파일 (veh/km), 셀 11~20 ===")
    print("  셀:      " + " ".join(f"{c:>7}" for c in CELLS))
    print("  길이m:   " + " ".join(f"{lens[c]:>7.0f}" for c in CELLS))
    for label,series in (('native',nat),('모형',ms)):
        ts=sorted(series)
        for frac in (0.0,0.25,0.5,0.75,1.0):
            t=ts[min(len(ts)-1,int(frac*(len(ts)-1)))]
            row=series[t]
            print(f"  {label:<6} t={t:>7.1f}: " + " ".join(f"{(row.get(c,0)/lens[c]*1000):>7.1f}" for c in CELLS))
        print()
    # 전선 날카로움: 인접 셀 밀도 차의 최대 절대값
    print("=== 전선 날카로움 (인접 셀 밀도차 최대, veh/km) ===")
    for label,series in (('native',nat),('모형',ms)):
        best=0.; bt=None
        for t,row in series.items():
            d=[abs(row.get(CELLS[i+1],0)/lens[CELLS[i+1]]*1000 - row.get(CELLS[i],0)/lens[CELLS[i]]*1000) for i in range(len(CELLS)-1)]
            if d and max(d)>best: best=max(d); bt=t
        print(f"  {label}: 최대 {best:.1f} veh/km (t={bt})")
