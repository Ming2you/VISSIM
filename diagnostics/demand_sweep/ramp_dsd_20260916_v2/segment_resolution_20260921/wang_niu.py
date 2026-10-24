"""Bounded Wang--Niu Eq4 check through the existing Hadi/physical runner.

NC-only capacity bracket; freeze before action replay. Positive capacity drop
is an unidentified sensitivity, not a fitted benefit or adoption candidate.
"""
import json,sys
from pathlib import Path
import calibrate as c
import hadiuzzaman as h
from prepare import save
B=c.B;O=B/'wang_niu_v1';K=h.K;ROOT=c.ROOT


def run(name,**kw):
    return h.run('wn_'+name,output_group=O.name,**kw)


def replay(name,row,**changes):
    p=row['spec'];s=p['hadiuzzaman'];cell=s['cells'][0]
    kw=dict(law=s['relaxation'],ctm=s['ctm'],tau=p['tau_sec'],nu=p['nu_km2_h'],kappa=p.get('kappa',17),
        q=cell['capacity_vphpl'],w=cell['wave_kmh'],critical=cell['rho_critical'],
        branch=s['congested_branch'],scope=s.get('relaxation_cells'),nc=False)
    kw.update(changes)
    return run(name,**kw)


def main():
    source=ROOT/'evaluation/controllers/physical_lane_groups.py'
    paper=Path('C:/Users/alsrj/Downloads/wang-niu-2019-integrated-variable-speed-limit-and-ramp-metering-control-study-on-flow-interaction-between-mainline-and.pdf')
    cfgpath=K/'segment_resolution_20260921_cal_hd_disabled/config.json'
    vf=c.load(cfgpath)['config_overrides']['network']['v_free'];assert vf==120.
    jam=180.;q0=c.load(B/'hadiuzzaman_v1/receiving_seed.json')['capacity_vphpl']
    save(O/'protocol.json',dict(seed=23,initial_s=2400,horizon_s=450,train=[2400,2700],late=[2700,2850],
        prediction_step_s=1,production_step_s=5,new_native_runs=0,independent_validation=False,
        selected_on='NC loss only, frozen before late/action checks',
        scope='FW_E mainline + four on-ramp connectors + four off-ramp connectors; not full Omega',
        physical_jam=jam,free_speed_kmh=vf,critical_rule='Q/v_free, receiving only; METANET equilibrium unchanged',
        q_status='observed NC inflow envelope bracket, not proven capacity',theta_status='unidentified; .15 only sensitivity',
        congestion_trigger='rho>Q/v_free; explicit diagnostic interpretation, no hysteresis or VSL reward',
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'hadiuzzaman.py',B/'run.py',source,c.O/'observed_none.npz',cfgpath]},
        paper_path=str(paper),paper_sha256=c.sha(paper)))
    base=run('disabled',nc=False)
    for arm in ('none','rm_ramp','vsl','both'):
        assert c.load(O/base['name']/f'refined_guard1_{arm}.json')==c.load(B/f'refined_guard1_{arm}.json')
    rows=[]
    for ratio in (.9,1.,1.1):
        q=q0*ratio;crit=q/vf;w=q/(jam-crit)
        rows.append(run('receive_q'+str(int(ratio*100)),law='fd_cap',q=q,w=w,critical=crit,branch='capacity_critical'))
    # One change from preceding Hadi receiving test: branch consistency only.
    run('closure_only',law='fd_cap',q=q0,w=15.,critical=27.,branch='capacity_critical')
    selected=h.choose(rows);save(O/'selected_receiving.json',selected);save(O/'nc_candidates.json',rows)
    scope=c.load(B/'hadiuzzaman_v1/scope_protocol.json')['cells']
    scoped=run('direct_u',law='command',tau=108,nu=35,kappa=47,q=q0,w=q0/(jam-q0/vf),
        critical=q0/vf,branch='capacity_critical',scope=scope)
    save(O/'frozen.json',dict(receiving=selected,direct_u=scoped,selection_complete=True))
    replay('receiving_actions',selected)
    replay('direct_actions',scoped)
    replay('theta15_actions',selected,theta=.15)
    replay('fixed_theta15_actions',selected,theta=.15,branch='fixed_wave')
    print('DONE bounded model/action comparison',flush=True)


def joint_main():
    frozen=c.load(O/'frozen.json');scope=c.load(B/'hadiuzzaman_v1/scope_protocol.json')['cells']
    grid=[('fd_cap',2200,18,35,17),('fd_cap',2200,12,17.5,17),
          ('fd_cap',2200,30,17.5,35),('fd_cap',1980,30,17.5,35),('fd_cap',2420,30,17.5,35),
          ('command',2200,60,17.5,35),('command',2200,108,17.5,47),
          ('command',2200,150,35,47),('command',2420,108,35,47)]
    save(O/'joint_protocol.json',dict(grid=grid,selection='NC2400-2700 only; freeze before late2700-2850/actions',
        positive_drop=0,free_speed_kmh=120.,jam_density=180.,same_state_and_commands=True,
        scope='receiving Q and speed tau/nu/kappa; not all model parameters',
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'hadiuzzaman.py',B/'run.py',
            ROOT/'evaluation/controllers/physical_lane_groups.py',c.O/'observed_none.npz']}))
    rows=[frozen['receiving'],frozen['direct_u']]
    for j,(law,q,tau,nu,kappa) in enumerate(grid):
        rows.append(run('joint_'+str(j),law=law,q=q,w=q/(180-q/120),critical=q/120,
            tau=tau,nu=nu,kappa=kappa,branch='capacity_critical',scope=scope if law=='command' else None))
    save(O/'joint_candidates.json',rows)
    fd=h.choose([r for r in rows if r['spec']['hadiuzzaman']['relaxation']=='fd_cap'])
    direct=h.choose([r for r in rows if r['spec']['hadiuzzaman']['relaxation']=='command'])
    save(O/'joint_frozen.json',dict(receiving=fd,direct_u=direct,best=h.choose(rows)))
    replay('joint_receiving_actions',fd)
    replay('joint_direct_actions',direct)
    print('DONE joint calibration and frozen action replays',flush=True)


if __name__=='__main__':joint_main() if '--joint' in sys.argv else main()
