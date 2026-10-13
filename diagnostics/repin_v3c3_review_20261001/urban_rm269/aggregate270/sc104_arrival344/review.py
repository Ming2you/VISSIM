"""Close the completed route-only experiment using existing response caches."""
from pathlib import Path
import gzip,hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent
M='SC104_E_to_W_SC6'
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def main():
    assert not (HERE/'result.json').exists()
    s=read(HERE/'forecast2400/summary.json');assert s['forecasts']==4
    for p,h in s['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    rows={}
    for arm in ('disabled_hold','hold','city','joint'):
        r=read(HERE/f'forecast2400/{arm}.response.json.gz')
        resources=r['resource_allocations']
        flows=[q for q in resources if q['resource']==M and q['kind']=='urban_movement_intended_limit']
        queues=[q for q in resources if q['resource']==M and q['kind']=='urban_movement_stock']
        rows[arm]=dict(omega=s['results'][arm]['omega_ttt_veh_h'],
            departure=sum(q['accepted_total_veh'] for q in flows),
            ready_last_before_service=queues[-1]['available_veh'],
            outside_ttt=sum(s['results'][arm]['outside_costs_by_stock'].values()),
            wall_sec=s['results'][arm]['wall_sec'],
            feasible=s['results'][arm]['shared_constraints']['feasible'])
    native={}
    for arm in ('hold','city'):
        c=read(Path('E:/VISSIM_analysis/20261010_exit_timing309')/(arm+'.json.gz'))
        ev=[e for e in c['events'] if e['kind']=='observed_entry' and 2400<=e['mid_sec']<2850
            and str(e['from_link']) in ('10125','1220061200') and str(e['to_link'])=='1220021204']
        native[arm]=dict(total=len(ev),bins=[sum(t<=e['mid_sec']<t+150 for e in ev) for t in (2400,2550,2700)],
            source=str(c['source']),validation_only=True)
    assert rows['hold']['ready_last_before_service']>rows['disabled_hold']['ready_last_before_service']+60
    assert abs(rows['hold']['departure']-rows['disabled_hold']['departure'])<1e-9
    result=dict(status='route_repaired_service_bound_masks_incoming',rows=rows,native_incoming=native,
        deltas=dict(city_minus_hold=rows['city']['omega']-rows['hold']['omega'],
            joint_minus_city=rows['joint']['omega']-rows['city']['omega']),
        forecasts=4,tests=6,native_runs=0,optimizer=0,production_adopted=False,goal_complete=False,
        source_pins=s['source_pins'],
        next_step='Qualify SC104 straight service from past native crossings and signal exposure; do not fit to future140. Right SC6 service still unqualified.')
    (HERE/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','rows','native_incoming','deltas')},indent=2))
if __name__=='__main__':main()
