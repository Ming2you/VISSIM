"""Saved first-response checks and matched aggregate model/native comparison."""
from pathlib import Path
import sys,json,csv,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=d.HERE/'first_merge_response_v2';p=out/'result.json';doc=d.e.load(p)
    checks=0
    for path,h in doc['pins'].items():assert digest(d.ROOT/path)==h;checks+=1
    for r in doc['source_receipts'].values():
        path=d.ROOT/r['path'];assert (path.stat().st_size,path.stat().st_mtime_ns)==(r['size'],r['mtime_ns'])
    assert doc['exact_original9_rows']==312712 and doc['initial_equal_rows']==5189
    key={(r['arm'],r['time_s'],r['vehicle']):r for r in doc['timeline']}
    assert len(key)==132
    nc=key['none',2417,17532];rm=key['rm_ramp',2417,17532]
    assert nc['geometric_leader']['vehicle']==18665 and abs(nc['geometric_leader']['gap_m']-5.89)<1e-9
    assert rm['geometric_leader']['vehicle']==18356 and abs(rm['geometric_leader']['gap_m']-103.836)<1e-9
    react=key['none',2418,17532]['native_recorded_interaction']
    assert react['target']==18665 and react['interaction']=='Brake AX'
    for interval in doc['intervals']:
        assert interval['counts']['none']==interval['counts']['rm_ramp']
        assert interval['initial_id_sequence']['none']==interval['initial_id_sequence']['rm_ramp']
    rows=list(csv.DictReader((out/'lane_response_1s.csv').open(encoding='utf-8')))
    assert len(rows)==360 and len({(r['arm'],r['time_s'],r['lane']) for r in rows})==360
    preds={};files=[Path(__file__),p,out/'lane_response_1s.csv']
    for arm in ('none','rm_ramp'):
        path=d.HERE/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json';files.append(path)
        preds[arm]=d.e.load(path)['lane_groups']['FW_E']
    comparisons=[]
    for t in (2417,2418,2420,2430,2460):
        state={}
        for arm in preds:
            actual=[r for r in rows if r['arm']==arm and int(r['time_s'])==t]
            modeled=[r for r in preds[arm] if r['time_s']==t and r['cell'] in (13,14)]
            assert len(actual)==3 and len(modeled)==6
            n=sum(int(r['n']) for r in actual);m=sum(r['n_veh'] for r in modeled)
            state[arm]=dict(native_n=n,native_v=sum(int(r['n'])*float(r['speed_mean']) for r in actual)/n,
                           model_n=m,model_v=sum(r['n_veh']*r['v_kmh'] for r in modeled)/m)
        comparisons.append(dict(time_s=t,states=state,
            native_delta_v=state['rm_ramp']['native_v']-state['none']['native_v'],
            model_delta_v=state['rm_ramp']['model_v']-state['none']['model_v']))
    assert comparisons[-2]['native_delta_v']>0 and comparisons[-1]['native_delta_v']<0
    result=dict(status='VERIFIED_LOCAL_RESPONSE_NOT_GAIN_QUALIFICATION',source_pin_checks=checks,
        original9_row_checks=doc['exact_original9_rows'],initial_equal_rows=5189,timeline_rows=len(key),
        lane_csv_rows=len(rows),comparisons_cells13_14=comparisons,
        interpretation='The early affected mainline vehicle benefits but the regional response reverses by2460. Do not fit a persistent RM capacity bonus from the first event.',
        pins={str(x.relative_to(d.ROOT)):digest(x) for x in files},
        production_changes=0,new_native_runs=0,qualified=False)
    d.e.save(out/'validation.json',result)
    print(dict(pin_checks=checks,rows=312712,deltas=[(r['time_s'],r['native_delta_v'],r['model_delta_v']) for r in comparisons]),flush=True)


if __name__=='__main__':main()
