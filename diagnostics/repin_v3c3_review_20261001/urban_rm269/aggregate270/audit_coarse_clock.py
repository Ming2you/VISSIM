"""Current-geometry time-step screen and exact cycle-service integration audit.

This is not a full METANET stability proof, traffic forecast or runtime test.
"""
import hashlib
import json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.interval_service import meter_service_vehicles


def main():
    here=Path(__file__).resolve().parent
    source=here.parent/'runtime600/bounded_full/network.json'
    net=json.loads(source.read_text(encoding='utf-8'))
    cells=[dict(road=road,cell=i,length_m=length*1000.)
           for road,lengths in net['freeway_segment_length_profile_km'].items()
           for i,length in enumerate(lengths)]
    speed=110.
    screens=[]
    for dt in (1,5,10):
        ratios=[speed/3.6*dt/c['length_m'] for c in cells]
        screens.append(dict(step_sec=dt,max_advective_courant=max(ratios),
                            cells_above_one=sum(r>1. for r in ratios)))
    minimum=min(cells,key=lambda c:c['length_m'])
    integration_errors=[]; cases=0
    for name,row in net['physical_ramp_branches']['ramps'].items():
        cycle=row['cycle_sec']
        for green,rate in row['service_by_green_veh_h'].items():
            g=float(green)
            for offset in (0.,2.5):
                fine=sum(meter_service_vehicles(rate,2400+t,1,cycle,g,offset) for t in range(450))
                coarse=sum(meter_service_vehicles(rate,2400+t,10,cycle,g,offset) for t in range(0,450,10))
                integration_errors.append(abs(fine-coarse));cases+=1
    if max(integration_errors)>1e-8:
        raise ArithmeticError('Coarse integration changed the calibrated RM service')
    result=dict(status='component_clock_checks_passed_full_coupled_prediction_pending',
        source=dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
        screen_speed_kph=speed,cells=len(cells),shortest_cell=minimum,
        shortest_cell_travel_sec=minimum['length_m']/(speed/3.6),
        travel_in_10sec_m=speed/3.6*10,advection_screens=screens,
        advection_scope='Necessary explicit local advection screen at110kph, not complete nonlinear METANET stability certification. Supply clipping alone does not restore correct travel time.',
        ramp_service_cases=cases,max_cycle_service_vehicle_error=max(integration_errors),
        ramp_service_scope='Potential calibrated service only, with infinite ready queue and receiving. Actual merge and urban cost must be checked in the coupled plant.',
        coarse_horizon_sec=450,coarse_updates=45,control_interval_sec=150,
        proposed_clock='Aggregate urban/ramp updates10s; retain short mainline integration initially and integrate accepted inter-network flows conservatively.',
        full_native_changes=0,full_sdmpc_timing_measured=False)
    (here/'coarse_clock_audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
