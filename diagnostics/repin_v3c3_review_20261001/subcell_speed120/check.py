"""Reuse119's bounded trial with independent canonical METANET half-speeds.

The old experiment and production files are never edited. All changes below
are explicit, guarded source substitutions confined to this diagnostic process.
"""
import difflib
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'subcell_transport119/check.py'
expected='766c0500fdaa2cc095e548d20dd0499cbc97088381e40e0b6c8d3f1b7d2b57cf'
assert hashlib.sha256(OLD.read_bytes()).hexdigest()==expected
OUT=HERE/'attempt3'
assert not OUT.exists(), 'No repeat or extra parameter grid'
source=OLD.read_text(encoding='utf-8')
original=source


def change(old,new):
    global source
    assert source.count(old)==1,(old[:90],source.count(old))
    source=source.replace(old,new)


change("previous_turn='PROGRESS118: lane-reaction conditional candidate rejected;9000 analysis remains stopped.'",
       "previous_turn='PROGRESS119: conservative transport-only candidate gives1percent response improvement, rejected.9000analysis remains stopped.'")
change("change='Cell19 only: preserve current upstream/downstream half route stocks, advance internal flux2*v*U/L and send2*v*D/L, bounded by available stocks/half storage. No extra speed states or capacity benefit.'",
       "change='Cell19 only: same119 conservative half route stocks, now independent METANET speeds initialized from current half speed moments. Same parent coefficients, half lengths. Neighbor18 anticipation sees upstream-half density;20 convection sees downstream-half speed. No fits/capacity bonus.'")
change("limitations='Shared canonical mean speed drives both halves; this is a tested spatial transport closure, not a full refined METANET speed model or microscopic queue solver.'",
       "limitations='Only19 refined. Both halves retain parent calibrated coefficients and common cell VSL-exposure mixture; exposure is not spatially refined. No microscopic lane-change/queue model. Gate is component-only, notOmega/AD qualification.'")
change("H=min(2*v*U/L, U/dt, free_D/dt)*dt; out=min(2*v*D/L,D/dt,canonical downstream supply)",
       "H=min(2*vU*U/L, U/dt, free_D/dt)*dt; out=min(2*vD*D/L,D/dt,canonical downstream supply)")
change("        assignments = {}\n", "        assignments = {}\n        initial_speeds = [[], []]\n")
change("            assignments[p['veh_no']] = int(fw=='FW_E' and i==19 and x>=midpoint)\n",
       "            assignments[p['veh_no']] = int(fw=='FW_E' and i==19 and x>=midpoint)\n            if fw=='FW_E' and i==19:\n                initial_speeds[int(x>=midpoint)].append(float(p['speed_kph']))\n")
change("        state._subcell119 = dict(halves=partitions['FW_E'][19], prepared=None)\n",
       """        assert all(initial_speeds), 'Both initial halves need observed speed support'
        v = [sum(x)/len(x) for x in initial_speeds]
        n = [sum(x.values()) for x in partitions['FW_E'][19]]
        assert abs(sum(a*b for a,b in zip(v,n))/sum(n)-state.freeway_speed['FW_E'][19])<1e-7
        state._subcell119 = dict(halves=partitions['FW_E'][19], prepared=None, speed=v, next_speed=None)
""")
change("        fraction = 2*speeds[19]*dt/lengths[19]\n        assert 0<=fraction<=1, ('subcell CFL',fraction)\n        transfer = min(u*fraction, max(0.,half_capacity-d))\n        out = min(d*fraction,d)/dt\n",
       """        assert abs(lanes[19]-3)<1e-9, 'This trial requires unchanged3 physical/effective lanes at19'
        fu,fd = [2*v*dt/lengths[19] for v in data['speed']]
        assert 0<=fu<=1 and 0<=fd<=1, ('subcell CFL',fu,fd)
        transfer = min(u*fu, max(0.,half_capacity-d))
        out = min(d*fd,d)/dt
""")
change("        data['halves']=[up,down]\n", "        data['halves']=[up,down]\n        assert data['next_speed'] is not None\n        data['speed']=data.pop('next_speed')\n        data['next_speed']=None\n")
change("                           internal=transfer,inflow=sum(incoming.values()),outflow=out))\n",
       "                           internal=transfer,inflow=sum(incoming.values()),outflow=out,speed=list(data['speed']),speed_terms=data['speed_terms']))\n")

insert=r'''
    def update_half_speeds(state,cfg,control,fw,i,speeds,rhos,lengths,exposure,qin,qout,dt):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        from evaluation.controllers.freeway_fd import literature_desired_speed, state_response_coefficients
        net=cfg.network;mn=area._mn;data=state._subcell119;p=data['prepared']
        assert active and fw=='FW_E' and i==19
        assert not (getattr(net,'freeway_hadiuzzaman',{}) or {}).get(fw), 'Not a Hadi trial'
        length=lengths[i]/2;ns=[p['u'],p['d']];vs=data['speed']
        density=[n/(length*3) for n in ns]
        ups=[speeds[i-1],vs[0]];downs=[density[1],rhos[i+1]]
        updated=[];terms=[]
        # The canonical component observer stores one event per physical cell.
        # Keep both actual half evaluations, then use its existing lane-group
        # convention (maximum cap effect) for the one cell19 summary slot.
        recorder=mn.effective_desired_speed_kmh
        assert recorder.__name__=='record_desired', 'Expected existing component VSL observer'
        observed=inspect.getclosurevars(recorder).nonlocals['observed_desired']
        start_events=len(observed)
        assert start_events==20, ('cell19 parent audit position',start_events)
        for j in (0,1):
            vsl=mn.segment_vsl(control,fw,i,cfg,physical_length_km=length,segment_end=j==1)
            rho=density[j];is_active=vsl<max(cfg.freeway_follower.vsl_set)-.5
            desired=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,vsl,net.alpha_vsl,is_active,
                        net.metanet_a_m,getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
            desired=literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get(fw),cfg,fw,i,rho,desired,vsl,is_active)
            if exposure is not None:
                desired=exposure.target(cfg,fw,i,rho,desired,vsl)
            nu0=mn.select_anticipation_nu(rho,net,vsl)
            ctx=copy.deepcopy(adapter._FW_SEG_CTX)
            assert ctx['armed'] and abs(ctx['p']['segment_length_km']-length)<1e-12
            par=ctx['p'];tau=par.get('metanet_tau_h',net.metanet_tau_h)
            kappa=par.get('metanet_kappa_veh_km_lane',net.metanet_kappa_veh_km_lane)
            tau,nu=state_response_coefficients(ctx.get('state_response',{}),vs[j],desired,rho,downs[j],
                        ctx.get('response_rho_crit',par['rho_crit']),tau,nu0)
            pieces=dict(relaxation=dt/tau*(desired-vs[j]),convection=dt/length*vs[j]*(ups[j]-vs[j]),
                        anticipation=-nu*dt/(tau*length)*(downs[j]-rho)/(rho+kappa))
            expected=max(net.v_min,vs[j]+sum(pieces.values()))
            phi=ctx.get('phi',0.);dl=ctx.get('dlam',0.)
            drop=phi*dt*dl*max(rho,0.)*vs[j]**2/(length*max(ctx.get('lanes',0.),1e-9)*max(par['rho_crit'],1e-9)) if phi>0 and dl>0 else 0.
            expected=max(net.v_min,expected-drop)
            nxt=mn.metanet_speed_update_kmh(vs[j],ups[j],rho,downs[j],desired,dt,length,
                                           net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
            assert abs(nxt-expected)<1e-8, ('physical half equation',nxt,expected)
            assert math.isfinite(nxt) and nxt>=net.v_min
            updated.append(nxt)
            terms.append(dict(**pieces,lane_drop=-drop,length_km=length,density=rho,downstream_density=downs[j],
                              speed=vs[j],desired=desired,next_speed=nxt,equation_error=abs(nxt-expected)))
        assert len(observed)==start_events+2, 'Every half FD call must be audited'
        half_audit=list(observed[start_events:])
        parent_audit=observed[start_events-1]
        observed[start_events-1:]=[max(half_audit,key=lambda x:x[2]-x[1])]
        assert len(observed)==start_events
        data['half_vsl_audit']=dict(halves=half_audit,unused_parent=parent_audit)
        new_n=[ns[0]+qin*dt-p['transfer'],ns[1]+p['transfer']-qout*dt]
        assert min(new_n)>=-1e-8
        data['next_speed']=updated;data['speed_terms']=terms
        return sum(n*v for n,v in zip(new_n,updated))/sum(new_n) if sum(new_n)>1e-10 else sum(updated)/2

'''
change("    source=inspect.getsource(old_step)\n",insert+"    source=inspect.getsource(old_step)\n")

extra=r'''
    def edit_once(text,old,new):
        assert text.count(old)==1,(old[:100],text.count(old))
        return text.replace(old,new)
    changed=edit_once(changed,
        "            if ramp_velocity_moment is not None and ramp_in_by_link[link][i] > 0:\n",
        "            if _subcell120_active() and link=='FW_E' and i==20:\n                upstream_speed=state._subcell119['speed'][1]\n            if ramp_velocity_moment is not None and ramp_in_by_link[link][i] > 0:\n")
    changed=edit_once(changed,
        "            vsl_i = _mn.segment_vsl(control, link, i, cfg)\n",
        "            if _subcell120_active() and link=='FW_E' and i==18:\n                downstream_rho=state._subcell119['prepared']['u']/(3*lengths[19]/2)\n            vsl_i = _mn.segment_vsl(control, link, i, cfg)\n")
    changed=edit_once(changed,
        "            if v_new <= net.v_min + 1e-09:\n",
        "            if _subcell120_active() and link=='FW_E' and i==19:\n                v_new=_subcell120_speed(state,cfg,control,link,i,speeds,rho_for_flow,lengths,exposure,q_in,q_out,dt_h)\n            if v_new <= net.v_min + 1e-09:\n")
'''
change("    (HERE/'executed_step.py.txt').write_text(changed,encoding='utf-8')\n",extra+"    (HERE/'executed_step.py.txt').write_text(changed,encoding='utf-8')\n")
change("    namespace=dict(old_step.__globals__,_subcell119_prepare=prepare)\n",
       "    namespace=dict(old_step.__globals__,_subcell119_prepare=prepare,_subcell120_speed=update_half_speeds,_subcell120_active=lambda:active)\n")
change("decision='EXPAND_SHORT_VALIDATION' if all(gates.values()) else 'REJECT_TRANSPORT_CANDIDATE'",
       "decision='EXPAND_SHORT_VALIDATION' if all(gates.values()) else 'REJECT_TWO_SPEED_CANDIDATE'")
change("speed_terms=data['speed_terms']))", "speed_terms=data['speed_terms'],half_vsl_audit=data['half_vsl_audit']))")
change("        budget=dict(fits=0, first_forecasts=3, additional_only_if_pass=10, candidates=1),",
       "        budget=dict(fits=0, first_forecasts=2, reused_disabled=1, failed_first_step=1, additional_only_if_pass=10, candidates=1),")
change("            pred,measure=helper.predict(context['component'],replay,Obs(r['truth']),r,450)\n",
       """            if not enabled:
                with gzip.open(HERE/'disabled.json.gz','rt',encoding='utf-8') as f: pred=json.load(f)
                measure=read(HERE/'partial.json')[0]
                measure.pop('version'); measure.pop('max_subcell_balance_residual')
            else:
                pred,measure=helper.predict(context['component'],replay,Obs(r['truth']),r,450)
""")
# Keep the first failed attempt intact. Only output paths change; relative
# helper/model references retain HERE at the original diagnostic directory.
source=source.replace('HERE/','OUT/')
source=source.replace("OUT/'disabled.json.gz'","HERE/'disabled.json.gz'").replace("OUT/'partial.json')[0]","HERE/'partial.json')[0]")
source=source.replace("ROOT = HERE.parents[2]\n", "ROOT = HERE.parents[2]\nOUT = HERE/'attempt3'\n")

OUT.mkdir()
(OUT/'candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),fromfile='119/check.py',tofile='120/in-memory-diagnostic')),encoding='utf-8')
(OUT/'executed_driver.py.txt').write_text(source,encoding='utf-8')
namespace={'__name__':'subcell120_diagnostic','__file__':str(HERE/'in_memory.py')}
exec(compile(source,'<subcell120 bounded diagnostic>','exec'),namespace)
namespace['main']()
assert hashlib.sha256(OLD.read_bytes()).hexdigest()==expected
