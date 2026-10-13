"""Bounded SC104 fixed-head clock/service diagnostic, no future input."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,math
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc104_arrival344 import candidate as route
from evaluation.controllers.fixed_signal_schedule import FixedControllerSchedule,compile_fixed_signal_schedules
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
NET=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
M=route.KEEP
def support():
    d=json.loads((HERE/'past_head.json').read_bytes())
    assert d['read_until_sec']==2400
    for p,h in d['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError('Past source changed: '+p)
    ws=d['windows']
    if [(w['start'],w['end']) for w in ws]!=[(1800,2100),(2100,2400)]:raise ValueError('Unreviewed support window')
    rates=[w['all_green_crossings']*3600/w['green_sec'] for w in ws]
    if not all(w['all_green_crossings']>=20 for w in ws):raise ValueError('Insufficient past crossings')
    if not math.isclose(min(rates),d['lower_observed_rate']):raise ValueError('Support rate mismatch')
    return min(rates)
def install(cfg,network,frame,*,service=False):
    receipt=route.install(cfg,network,frame)
    spec=cfg.network.urban_movements[M]
    if spec['intersection']!='SC104' or spec['phase'] or spec.get('unsignalized'):raise ValueError('SC104 fixed authority changed')
    spec['sc104_qualified_fixed_clock']=True
    old=cfg.network.movement_capacity_by_movement_veh_h[M]
    if not math.isclose(old,826.1224489795918):raise ValueError('Service prior changed')
    if service:cfg.network.movement_capacity_by_movement_veh_h[M]=support()
    return dict(route=receipt,old_rate=old,new_rate=cfg.network.movement_capacity_by_movement_veh_h[M],
        groups=['6'],clock_convention='native after-step t+1; verified on past600s',production_adopted=False)
@contextmanager
def fixed_clock():
    original=FixedControllerSchedule.movement_green_fraction
    def qualified(self,spec,start_sec=None,duration_sec=None,group_ids=None):
        if not spec.get('sc104_qualified_fixed_clock'):
            return original(self,spec,start_sec,duration_sec,group_ids)
        if self.node_id!='SC104' or spec.get('origin')!='in_SC104_E' or spec.get('phase'):
            raise ValueError('Qualified fixed head used by wrong movement')
        if group_ids is not None and group_ids!=('6',):raise ValueError('Conflicting group authority')
        return original(self,spec,None if start_sec is None else start_sec+1,duration_sec,('6',))
    FixedControllerSchedule.movement_green_fraction=qualified
    try:yield
    finally:FixedControllerSchedule.movement_green_fraction=original
