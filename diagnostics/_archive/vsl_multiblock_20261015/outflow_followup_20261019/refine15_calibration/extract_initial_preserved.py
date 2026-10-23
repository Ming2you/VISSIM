"""One new spatial measurement from completed hold FZP; not a TTT reanalysis."""
import datetime,hashlib,json,math,sys
from pathlib import Path
A=Path(__file__).resolve().parent;O=A/'refine15_calibration'
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
RUN=Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold')
SOURCE=RUN/'vissim_eval/sdmpc31_g_2250_hold_s29_001.fzp'
CLOSURE=Path('E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis/runtime_closure.json')
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def main():
    assert not O.exists(),'Reuse completed or partial extraction; do not duplicate'
    closure=read(CLOSURE)
    assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0 and closure['normal_native_end_sec']==2700
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    contract=read(ROOT/'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
    runtime=route.compile_inventory(contract,read(ROOT/contract['mapping']['path']))
    bounds=runtime['bounds']['FW_E'];sub=(bounds[16]-bounds[15])/3
    lengths=[bounds[15]-bounds[14],sub,sub,sub,bounds[17]-bounds[16]]
    assert abs(sub-175.4293076923077)<1e-6
    O.mkdir()
    protocol=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),purpose='Resolution-specific baseline dynamic calibration, not VSL-benefit fitting.',
        measurement='New5s cell14/three cell15 compartments/cell16 stock and spatial-mean speed. Existing Omega TTT caches untouched.',
        data_source=str(SOURCE),baseline='Completed qualified hold110, city/RM as recorded; no VSL90 samples in calibration.',
        training=dict(start_sec=900.1,end_sec=2100.1),purge=dict(start_sec=2100.1,end_sec=2250.1),validation=dict(start_sec=2250.1,end_sec=2695.1),
        models=['Parent-resolution control fit','Three-compartment fit with shared dynamic coefficients'],
        coefficients=['1/tau_sec','nu_downstream_ge/tau_sec','nu_downstream_lt/tau_sec'],
        fixed=['FD free speed/critical density/shape','kappa','geometry/lanes','convection coefficient','demand/controls','macroFW5/U10'],
        method='One nonnegative linear least-squares fit per spatial resolution; no coefficient grid. Weight by min of current/next observed stock. Input data from observed current states only; next observation is a training/validation target, never a rollout boundary.',
        budgets=dict(fits=2,native=0,optimizer=0,coefficient_grid=0),
        qualification='Full-column rank, finite positive relaxation; report fit and baseline held-out one-step speed errors. At least10percent held-out weighted-RMSE reduction versus transferred parent coefficients is required before at most two autonomous450s fine-grid forecast checks. No adoption based on one-step regression.',
        limitations=['FZP time grid is0.1mod5, different from integer-time snapshots; never silently align them.',
            'Cell mean change includes population turnover; regression is an empirical Eulerian equation fit, not identification of vehicle acceleration.',
            'One seed and contiguous time validation are preliminary; independent seed67/71 and response/physics/AD gates remain mandatory.'])
    save(O/'protocol.json',protocol)
    original_stat=(SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns)
    frames={};header=None;digest=hashlib.sha256();records=0;accepted=0;non_grid=0
    with SOURCE.open('rb') as f:
        for line in f:
            digest.update(line)
            if line.startswith(b'$VEHICLE:'):
                names=line.strip().split(b':',1)[1].split(b';')
                header={v:i for i,v in enumerate(names)}
                required=[b'SIMSEC',b'NO',b'LANE\\LINK\\NO',b'POS',b'SPEED']
                assert all(k in header for k in required),header
                continue
            if header is None or not line.strip() or line.startswith((b'*',b'$')):continue
            fields=line.strip().split(b';');records+=1
            t=float(fields[header[b'SIMSEC']]);tick=round((t-.1)/5)
            if abs(t-(tick*5+.1))>1e-6:non_grid+=1;continue
            if t<900 or t>2700:continue
            frame=frames.setdefault(t,dict(n=[0]*5,vsum=[0.]*5))
            link=fields[header[b'LANE\\LINK\\NO']].decode('ascii')
            if link not in runtime['physical']:continue
            road,pos,cell=route._position(runtime,link,float(fields[header[b'POS']]))
            if road!='FW_E' or cell not in (14,15,16):continue
            index=0 if cell==14 else (4 if cell==16 else 1+min(2,int((pos-bounds[15])/sub)))
            speed=float(fields[header[b'SPEED']]);assert math.isfinite(speed) and speed>=0
            frame['n'][index]+=1;frame['vsum'][index]+=speed;accepted+=1
    assert (SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns)==original_stat
    PINS[str(SOURCE)]=digest.hexdigest()
    rows=[]
    for t,f in sorted(frames.items()):
        rows.append(dict(time=t,n=f['n'],speed=[s/n if n else None for s,n in zip(f['vsum'],f['n'])]))
    assert len(rows)==360 and all(abs(b['time']-a['time']-5)<1e-7 for a,b in zip(rows,rows[1:]))
    assert all(all(n>0 for n in r['n']) for r in rows),'Missing cell observations must be handled explicitly'
    save(O/'native_hold_cells.json',dict(status='complete_new_spatial_measurement',rows=rows,length_m=lengths,lanes=[4]*5,
        total_fzp_records=records,accepted_spatial_records=accepted,offgrid_exit_rows_excluded=non_grid,source_pins=PINS,
        new_fzp_scans=1,ttt_reanalysis=0,new_native=0,new_forecasts=0,new_fits=0))
    print(json.dumps(dict(frames=len(rows),accepted_records=accepted,first_time=rows[0]['time'],last_time=rows[-1]['time'],source_sha256=digest.hexdigest())))
if __name__=='__main__':main()
