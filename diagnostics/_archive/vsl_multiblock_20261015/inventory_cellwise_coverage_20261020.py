"""Inventory preserved OFF observations for future per-cell identification.

Observed targets only: no forecasts, parameter fits, FZP scans or native runs.
"""
import hashlib,json,math,os,sys
from pathlib import Path
V=Path(__file__).resolve().parent
O=V/'cellwise_coverage_20261020'
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
OBS=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
PINS={}
def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
def save(p,x):
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(tmp,p)
def main():
    assert not O.exists(),'Reuse completed inventory'
    assert not (V/'STOP').exists()
    queue=read(Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json'))['conditions']['off']
    assert queue['owners_closed'] and queue['native_exit_code']==0 and queue['normal_sim_done']==8100
    contract=read(ROOT/'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
    mapping=read(ROOT/contract['mapping']['path'])
    assert PINS[str(ROOT/contract['mapping']['path'])]==contract['mapping']['sha256']
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    runtime=route.compile_inventory(contract,mapping)
    rows=[]
    for sec in range(900,8101,150):
        raw=read(OBS/f'state_{sec:06d}.json')
        assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
        groups={road:[[] for _ in range(31)] for road in ('FW_E','FW_W')}
        for car in raw['vehicle_records']['records']:
            if str(car['link_no']) not in runtime['physical']:continue
            road,pos,index=route._position(runtime,car['link_no'],car['position_m'])
            groups[road][index].append(car['speed_kph'])
        row=dict(time_sec=sec,roads={})
        for road,bins in groups.items():
            m=mapping['freeway_model_links'][road]
            assert len(m['segment_lanes'])==31 and len(m['segment_length_profile_km'])==31
            row['roads'][road]=dict(n=[len(b) for b in bins],speed=[sum(b)/len(b) if b else None for b in bins],
                density=[len(b)/(m['segment_lanes'][c]*m['segment_length_profile_km'][c]) for c,b in enumerate(bins)])
        rows.append(row)
    cells=[]
    for road in ('FW_E','FW_W'):
        for c in range(31):
            points=[(r['time_sec'],r['roads'][road]['speed'][c],r['roads'][road]['density'][c],r['roads'][road]['n'][c]) for r in rows if r['roads'][road]['speed'][c] is not None]
            assert points
            low=[t for t,v,d,n in points if v<40]
            mid=[t for t,v,d,n in points if 40<=v<80]
            high=[t for t,v,d,n in points if v>=80]
            down=[b[0] for a,b in zip(points,points[1:]) if b[0]-a[0]==150 and b[1]-a[1]<=-15]
            up=[b[0] for a,b in zip(points,points[1:]) if b[0]-a[0]==150 and b[1]-a[1]>=15]
            cells.append(dict(road=road,cell=c,observations=len(points),speed_min=min(p[1] for p in points),speed_max=max(p[1] for p in points),
                density_min=min(p[2] for p in points),density_max=max(p[2] for p in points),n_min=min(p[3] for p in points),n_max=max(p[3] for p in points),
                illustrative_speed_band_counts=dict(below40=len(low),from40to80=len(mid),atleast80=len(high)),
                slowing15kph_per150s_times=down,recovery15kph_per150s_times=up,
                interpretation='Descriptive speed bands and changes, not traffic-regime labels or identification sufficiency thresholds.'))
    summary={road:dict(cells=31,observations_per_cell_min=min(r['observations'] for r in cells if r['road']==road),
        cells_with_both_below40_and_atleast80=[r['cell'] for r in cells if r['road']==road and r['illustrative_speed_band_counts']['below40'] and r['illustrative_speed_band_counts']['atleast80']],
        cells_with_no_below40=[r['cell'] for r in cells if r['road']==road and not r['illustrative_speed_band_counts']['below40']]) for road in ('FW_E','FW_W')}
    O.mkdir()
    save(O/'observations.json',dict(rows=rows,source_pins=PINS,records_copied=False))
    save(O/'coverage.json',dict(summary=summary,cells=cells,snapshot_times=49,source='VSL OFF with recorded SDMPC city/RM; not network-wide no control',
        geometry='Both directions31physical cells; lane counts and lengths from pinned mapping, not uniform4lanes.',
        next='Keep per-cell freedom only for parameters supported by observed density/speed/flow and transitions. Shared priors for weak cells; inspect multiple contiguous episodes, fit coupled states and fluxes jointly, reserve episodes/seeds. This inventory does not identify parameters or prove an FD.',
        forecasts=0,fits=0,native=0,source_pins=PINS))
    for name in ('plan.json','summary.json'):
        p=V/name;x=json.loads(p.read_text(encoding='utf8'))
        x['cellwise_coverage_20261020']=dict(status='completed_preserved_snapshot_inventory',artifact=str(O/'coverage.json'),directions=2,cells_per_direction=31,snapshot_times=49,forecasts=0,fits=0,native=0)
        x['next']='Use completed62-cell observation coverage to prepare parameter identifiability and episode-level coupled calibration; weakly observed cells retain priors. Preserve fixed seed67/71 checks as validation; no retuning to their errors. Current focused16–18 correction is unadopted; completed predictions and baseline caches are reusable.'
        save(p,x)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
