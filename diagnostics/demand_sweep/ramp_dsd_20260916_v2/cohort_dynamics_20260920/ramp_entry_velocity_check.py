"""Bounded causal ramp-entry mean-speed mixing check in the existing plant.

Only preceding150s native departure speeds are used. Frozen speed is a hypothesis,
not a qualified prediction of actuator-dependent acceleration or insertion gaps.
No source copy, future traffic input, mass/actuator/cost modification, or adoption.
"""
from pathlib import Path
import copy
import hashlib
import inspect
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import urban_route_transport as u
import canonical_harness as ch
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups

HERE = Path(__file__).resolve().parent
ARMS = ('none', 'rm_ramp', 'vsl', 'both')


def mixture(stock, base_speed, ramp_amount, entry_speed):
    if not all(math.isfinite(x) for x in (stock, base_speed, ramp_amount, entry_speed)):
        raise ValueError('Nonfinite mixing state')
    if min(stock, base_speed, ramp_amount, entry_speed) < 0 or ramp_amount > stock+1e-7:
        raise ValueError('Ramp amount must remain within the conserved recipient stock')
    if not ramp_amount:
        return base_speed
    value = (max(0., stock-ramp_amount)*base_speed+ramp_amount*entry_speed)/stock
    assert min(base_speed, entry_speed)-1e-8 <= value <= max(base_speed, entry_speed)+1e-8
    return value


def main():
    spatial = '--short-merge-cell' in sys.argv
    modes = ('short_merge_keep',) if spatial else ('reference','mix_keep_merge','mix_replace_merge')
    out = HERE/('ramp_entry_velocity_work_v3' if spatial else 'ramp_entry_velocity_work_v2')
    out.mkdir(exist_ok=False)
    # All coefficients here are mass weights. No response-gain coefficient fit.
    assert mixture(10., 100., 2., 50.) == 90.
    assert mixture(2., 100., 2., 50.) == 50.
    assert mixture(0., 100., 0., 50.) == 100.
    assert mixture(10., 30., 2., 60.) == 36.
    history_path = u.H/'controller_response_s23_v1/none/port_events.csv'
    history = [r for r in u.e.rows(history_path) if r['kind']=='departure' and 2250<float(r['time_s'])<=2400]
    speeds = {}
    for port in (10639,10681,10490,10484):
        rows = [r for r in history if int(r['connector'])==port]
        assert rows, port
        speeds['RM_C'+str(port)] = dict(count=len(rows),
            speed_kmh=math.fsum(float(r['speed_kmh']) for r in rows)/len(rows),
            first_event=min(float(r['time_s']) for r in rows),last_event=max(float(r['time_s']) for r in rows))
    core = [u.e.ROOT/'evaluation/controllers'/name for name in
            ('vissim_stackelberg_adapter.py','physical_lane_groups.py','physical_ramp_boundary.py')]
    core += [u.e.CAL/'canonical_harness.py',Path(__file__),Path(u.__file__),history_path,
             HERE/'port_travel_fit_v1/selected_parameters.json']
    pins = {p.relative_to(u.e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in core}
    u.e.save(out/'protocol.json',dict(source_pins=pins,cutoff_s=2400,history_start_exclusive_s=2250,
        entry_speed_definition='Last connector speed at native departure time minus1s; fixed preceding150s mean.',
        estimated_entry_speeds=speeds,arms=list(ARMS),modes=list(modes),partition_ports=['10643','10483'] if spatial else ['10643'],
        assumption='All accepted ramp vehicles carry frozen precontrol mean speed; candidate-independent. Does not predict gap/order or future acceleration.',
        scope='FW_E only, same450s states/flows/actuators/costs; mean mixing before lateral exchange and speed ODE.',
        double_counting='Keep delta1 and replace with delta0 are separate diagnostic hypotheses, neither presumed correct.',
        qualified=False,new_native_runs=0,production_changes=0, optional_core_method_change=True))
    original_label = PhysicalLaneGroups._label
    original_config = ch.CanonicalFreewayModel._config
    original_advance = PhysicalLaneGroups.advance
    summaries = {}
    for mode in modes:
        trace = []
        calls = 0
        config_checks = []
        pre_exchange_moments = {}
        consumed_checks = 0

        def configured(self, road, parameters):
            cfg = original_config(self,road,parameters)
            if road=='FW_E':
                assert cfg.network.metanet_delta_merge==1.
                if mode=='mix_replace_merge':
                    cfg.network.metanet_delta_merge=0.
                config_checks.append(cfg.network.metanet_delta_merge)
            return cfg

        def labelled(self, arrivals, ratios, eligible_by_off=None):
            nonlocal calls
            result = original_label(self,arrivals,ratios,eligible_by_off)
            frame=inspect.currentframe().f_back
            if (frame.f_code.co_name!='advance' or Path(frame.f_code.co_filename).resolve()!=core[1]
                    or self.road!='FW_E'):
                del frame
                return result
            local=frame.f_locals
            assert self.sec==1 and not self.momentum_advection
            assert len(self.spec['ramp_access'])==4
            assert set(self.spec['ramp_access'])==set(speeds)
            assert all(sum(p['cell']==q['cell'] for q in self.spec['ramp_access'].values())==1
                       for p in self.spec['ramp_access'].values())
            for ramp,p in self.spec['ramp_access'].items():
                cell=p['cell'];amounts=local['ramp_in'][cell]
                part=self.partitions.get(cell)
                stocks=part['post_n'] if part else self.n[cell]
                velocities=part['post_v'] if part else self.v[cell]
                for group,amount in enumerate(amounts):
                    if not amount:continue
                    n=stocks[group];entry=speeds[ramp]['speed_kmh']
                    if part:
                        old=local['part_before'][cell]
                        assumed=old['post_v'][group]
                        before=((old['post_n'][group]-local['outgoing'][cell][group])*assumed+
                            local['cross'][cell][group]*old['pre_v'][group]+amount*assumed)/n
                    else:
                        assumed=before=local['oldv'][cell][group]
                    new=before+amount*(entry-assumed)/n
                    expected=before if mode=='reference' else new
                    assert abs(velocities[group]-expected)<1e-7
                    trace.append(dict(arm=ARMS[calls//450],time_s=local['state'].time_sec,
                        ramp=ramp,cell=cell,group=group,partition=part is not None,
                        stock=n,ramp_amount=amount,entry_speed=entry,assumed_ramp_speed=assumed,
                        v_before=before,v_after=velocities[group],computed_v_after=new,
                        moment_change_applied=n*(velocities[group]-before),
                        expected_moment_change=0. if mode=='reference' else amount*(entry-assumed)))
            for cell in (9,13,14):
                if cell in self.partitions:continue
                pre_exchange_moments[local['state'].time_sec,cell] = math.fsum(
                    n*v for n,v in zip(self.n[cell],self.v[cell]))
            calls+=1
            del frame
            return result

        def advance(self,state,control,demand,cfg,**kwargs):
            nonlocal consumed_checks
            if self.road!='FW_E':return original_advance(self,state,control,demand,cfg,**kwargs)
            if mode!='reference':kwargs['ramp_entry_speed_kmh']={r:v['speed_kmh'] for r,v in speeds.items()}
            mn=ch.accounting._mn;original_speed=mn.metanet_speed_update_kmh
            def observed(*args,**kw):
                nonlocal consumed_checks
                f=inspect.currentframe().f_back
                if (f.f_code.co_name=='advance' and Path(f.f_code.co_filename).resolve()==core[1]
                        and f.f_locals['i'] in (9,13,14) and f.f_locals['i'] not in self.partitions and f.f_locals['g']==0):
                    cell=f.f_locals['i'];plant=f.f_locals['self']
                    actual=math.fsum(n*v for n,v in zip(plant.n[cell],plant.v[cell]))
                    assert abs(actual-pre_exchange_moments[state.time_sec,cell])<1e-6
                    assert args[0]==plant.v[cell][0]
                    consumed_checks+=1
                del f
                return original_speed(*args,**kw)
            mn.metanet_speed_update_kmh=observed
            try:return original_advance(self,state,control,demand,cfg,**kwargs)
            finally:mn.metanet_speed_update_kmh=original_speed

        PhysicalLaneGroups._label=labelled
        ch.CanonicalFreewayModel._config=configured
        PhysicalLaneGroups.advance=advance
        folder='ramp_entry_velocity_'+mode+'_v2'
        try:
            u.run_probe(lateral_access=True,prefer_receiving=True,trace_limits=False,
                network_exit_intent=True,current_exit_intent=True,branch_partition='on',
                branch_exchange='off',partition_context='on',transport_step=1,output_name=folder,
                partition_ports=['10643','10483'] if spatial else None)
        finally:
            PhysicalLaneGroups._label=original_label
            ch.CanonicalFreewayModel._config=original_config
            PhysicalLaneGroups.advance=original_advance
        assert calls==1800
        assert consumed_checks==(3600 if spatial else 5400)
        assert len(config_checks)==4
        for arm in ARMS:
            pred=u.e.load(HERE/folder/f'prediction_{arm}.json')
            base=u.e.load(HERE/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json')
            if mode=='reference':assert pred==base,arm
            for field in ('cells','flows','ports','ramps'):
                assert [r for r in pred[field] if r.get('road')=='FW_W']==[r for r in base[field] if r.get('road')=='FW_W']
            assert pred['local_ramp_audit']['passed']
            for r in pred['diagnostics']['roads']:
                assert r['continuity_residual_max_veh']<1e-7
                assert r['negative_density_count']==r['jam_density_exceedance_count']==0
        assert max(abs(r['moment_change_applied']-r['expected_moment_change']) for r in trace)<1e-7
        result=u.e.load(HERE/folder/'result.json')
        summaries[mode]=dict(deltas=result['deltas'],nc_objective=result['summaries']['none']['score']['objective'],
            steps_checked=calls,consumed_ode_moment_checks=consumed_checks,entry_mix_rows=len(trace),delta_merge_values=config_checks,qualified=False)
        u.e.save(out/f'{mode}_trace.json',trace)
        u.e.save(out/f'{mode}_summary.json',summaries[mode])
        print(json.dumps(dict(mode=mode,**summaries[mode])),flush=True)
    for name,digest in pins.items():assert hashlib.sha256((u.e.ROOT/name).read_bytes()).hexdigest()==digest,name
    u.e.save(out/'result.json',dict(status='CAUSAL_FROZEN_ENTRY_SPEED_DIAGNOSTIC',cases=summaries,
        source_pins_verified=True,qualified=False,production_changes=0, optional_core_method_change=True,new_native_runs=0,
        note='No independent holdout or multi-state guards. Absolute accuracy and gain must both be checked before adoption.'))


if __name__=='__main__':
    main()
