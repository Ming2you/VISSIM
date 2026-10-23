"""Process-local conservative cell15 refinement; no production installation.

Three longitudinal compartments retain current route and VSL-exposure tags.
No merge, exit, signal or VSL sign lies inside cell15. Physical interfaces stay
canonical; only the cell's internal representation is refined. No fitted gains.
"""
import copy
import inspect
import math
import unittest

CELL=15
COUNT=3


def transport(rows, internal, incoming, outgoing):
    """Simultaneous upwind tag transport, with independently accepted boundaries."""
    totals=[math.fsum(r.values()) for r in rows]
    assert len(rows)==3 and len(internal)==2
    amounts=[*internal,outgoing]
    assert all(-1e-9<=q<=n+1e-8 for q,n in zip(amounts,totals))
    sent=[{k:n*q/total for k,n in row.items() if n*q>0} if total else {} for row,q,total in zip(rows,amounts,totals)]
    result=[]
    for j,row in enumerate(rows):
        inflow=incoming if j==0 else sent[j-1]
        result.append({k:max(0.,row.get(k,0.)-sent[j].get(k,0.)+inflow.get(k,0.)) for k in set(row)|set(inflow)})
    for k in set().union(*(set(r) for r in rows),incoming):
        residual=sum(r.get(k,0.) for r in result)-sum(r.get(k,0.) for r in rows)-incoming.get(k,0.)+sent[-1].get(k,0.)
        assert abs(residual)<1e-8
    return result


class TransportTests(unittest.TestCase):
    def test_no_flow(self):
        rows=[{'a':3.},{'b':2.},{'c':1.}]
        self.assertEqual(transport(rows,[0,0],{},0),rows)
    def test_no_teleport(self):
        result=transport([{'a':3.},{},{ }],[3,0],{},0)
        self.assertEqual(result[1]['a'],3)
        self.assertEqual(result[2],{})
    def test_exit_tag_from_last(self):
        result=transport([{'a':6.},{'b':4.},{'c':2.}],[2,1],{'d':3.},1)
        self.assertEqual(result,[{'a':4.,'d':3.},{'a':2.,'b':3.},{'b':1.,'c':1.}])
    def test_reject_overdraw(self):
        with self.assertRaises(AssertionError):transport([{'a':1.},{},{}],[2,0],{},0)
    def test_empty_cell_receives(self):
        self.assertEqual(transport([{},{},{}],[0,0],{90.:2.},0),[{90.:2.},{},{}])


class Refinement:
    def __init__(self,out):
        from evaluation.controllers import offramp_routing as routing, area_freeway_accounting as area, freeway_fd as fd
        self.route,self.area,self.fd=routing,area,fd
        self.old_init,self.old_route,self.old_step=routing.initialize_inventory,routing.advance_inventory,area._freeway_substep_events
        self.old_exposure=fd.VSLExposure.advance
        self.context={};self.trace=[];self.max_balance=0.;self.max_cohort=0.
        source=inspect.getsource(self.old_step)
        changed=source
        def replace(old,new):
            nonlocal changed
            assert changed.count(old)==1,(old[:100],changed.count(old))
            changed=changed.replace(old,new)
        anchor='        receiving_for_mainline = [max(0.0, receiving[i] - ramp_in_by_link[link][i]) for i in range(len(rho_for_flow))]\n'
        replace(anchor,'        _refine15_prepare(state,cfg,link,vehicles,speeds,lengths,lanes_now,q_values,receiving,dt_h,exposure)\n'+anchor)
        anchor='            vsl_i = _mn.segment_vsl(control, link, i, cfg)\n'
        replace(anchor,"            if link=='FW_E' and i==14:\n                downstream_rho=_refine15_head_density(state)\n            if link=='FW_E' and i==16:\n                upstream_speed=state._refine15['speed'][-1]\n"+anchor)
        anchor='            if v_new <= net.v_min + 1e-09:\n'
        replace(anchor,"            if link=='FW_E' and i==15:\n                v_new=_refine15_speed(state,cfg,control,speeds,rho_for_flow,lengths,exposure,q_in,q_out,dt_h)\n"+anchor)
        namespace=dict(self.old_step.__globals__,_refine15_prepare=self.prepare,_refine15_head_density=self.head_density,_refine15_speed=self.speed)
        exec(compile(changed,'<refine15 isolated diagnostic>','exec'),namespace)
        self.new_step=namespace['_freeway_substep_events']
        (out/'executed_step.py.txt').write_text(changed,encoding='utf8')
        self.route.initialize_inventory=self.initialize
        self.route.advance_inventory=self.advance_routes
        self.area._freeway_substep_events=self.new_step
        owner=self
        def advance(exposure,*a,**kw):return owner.advance_exposure(exposure,*a,**kw)
        self.fd.VSLExposure.advance=advance

    def restore(self):
        self.route.initialize_inventory=self.old_init;self.route.advance_inventory=self.old_route
        self.area._freeway_substep_events=self.old_step;self.fd.VSLExposure.advance=self.old_exposure

    def initialize(self,state,cfg,raw,*,lane_partition=None):
        assert lane_partition is None
        rt=cfg.network.offramp_route_inventory
        assert not any(x['freeway']=='FW_E' and x['source_cell']==CELL for x in rt['branches'].values())
        assert not any(x['freeway']=='FW_E' and x['cell']==CELL for x in rt['merges'].values())
        bounds=rt['bounds']['FW_E'];length=bounds[CELL+1]-bounds[CELL]
        dims={road:[COUNT if road=='FW_E' and i==CELL else 1 for i in range(len(bs)-1)] for road,bs in rt['bounds'].items()}
        assignments={};speeds=[[] for _ in range(COUNT)]
        for v in raw['vehicle_records']['records']:
            if str(v['link_no']) not in rt['physical']:continue
            road,pos,i=self.route._position(rt,v['link_no'],v['position_m'])
            part=min(COUNT-1,int((pos-bounds[CELL])/length*COUNT)) if road=='FW_E' and i==CELL else 0
            assignments[v['veh_no']]=part
            if road=='FW_E' and i==CELL:speeds[part].append(v['speed_kph'])
        result=self.old_init(state,cfg,raw,lane_partition=dict(groups_per_cell=dims,vehicle_group=assignments))
        partitions=state.offramp_route_inventory_state.pop('lane_cells')
        assert all(speeds)
        moments=[math.fsum(s)/len(s) for s in speeds]
        stocks=[math.fsum(r.values()) for r in partitions['FW_E'][CELL]]
        assert stocks==list(map(len,speeds))
        assert abs(sum(n*v for n,v in zip(stocks,moments))/sum(stocks)-state.freeway_speed['FW_E'][CELL])<1e-7
        state._refine15=dict(routes=partitions['FW_E'][CELL],speed=moments,cohorts=None,prepared=None,next_speed=None)
        return result

    def prepare(self,state,cfg,road,vehicles,speeds,lengths,lanes,flows,receiving,dt,exposure):
        if road!='FW_E':return
        data=state._refine15
        assert exposure is not None and CELL not in exposure.signs
        assert abs(lanes[CELL]-4)<1e-9
        assert data['prepared'] is None and data['next_speed'] is None
        n=[math.fsum(r.values()) for r in data['routes']]
        assert abs(sum(n)-vehicles[CELL])<1e-7
        length=lengths[CELL]/COUNT;cap=cfg.network.rho_max*4*length
        fractions=[v*dt/length for v in data['speed']]
        assert all(0<=f<=1+1e-10 for f in fractions),('CFL',fractions)
        assert all(-1e-8<=x<=cap+1e-7 for x in n)
        transfer=[min(n[j]*fractions[j],max(0.,cap-n[j+1])) for j in range(COUNT-1)]
        sending=n[-1]*fractions[-1]/dt
        raw=vehicles[CELL]*speeds[CELL]/lengths[CELL]
        if flows[CELL]<raw-1e-8:sending=min(sending,flows[CELL])
        flows[CELL]=sending;receiving[CELL]=min(receiving[CELL],max(0.,cap-n[0])/dt)
        if data['cohorts'] is None:
            current={k:v for k,v in exposure.cohorts[CELL].items() if v>1e-8}
            assert set(current)=={110.},'No unobserved within-cell initial VSL assignment permitted'
            data['cohorts']=[{110.:x} for x in n]
        assert all(abs(sum(r.values())-x)<1e-7 for r,x in zip(data['cohorts'],n))
        assert all(not any(t!=0 for t in row.values()) for row in exposure.tangents),'Scalar diagnostic only'
        data['prepared']=dict(n=n,internal=transfer,length=length,capacity=cap,dt=dt)
        self.context[id(exposure)]=data

    @staticmethod
    def head_density(state):
        p=state._refine15['prepared'];return p['n'][0]/(4*p['length'])

    def speed(self,state,cfg,control,speeds,rhos,lengths,exposure,qin,qout,dt):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        net=cfg.network;mn=self.area._mn;data=state._refine15;p=data['prepared']
        ns=p['n'];vs=data['speed'];length=p['length'];density=[n/(4*length) for n in ns]
        up=[speeds[CELL-1],*vs[:-1]];down=[*density[1:],rhos[CELL+1]]
        updated=[]
        for j in range(COUNT):
            vsl=mn.segment_vsl(control,'FW_E',CELL,cfg,physical_length_km=length,segment_end=j==COUNT-1)
            active=vsl<max(cfg.freeway_follower.vsl_set)-.5
            desired=mn.effective_desired_speed_kmh(density[j],net.v_free,net.rho_crit,vsl,net.alpha_vsl,active,net.metanet_a_m,getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
            desired=self.fd.literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get('FW_E'),cfg,'FW_E',CELL,density[j],desired,vsl,active)
            oldrow,oldt=exposure.cohorts[CELL],exposure.tangents[CELL]
            try:
                exposure.cohorts[CELL]=data['cohorts'][j];exposure.tangents[CELL]={k:0. for k in data['cohorts'][j]}
                desired=exposure.target(cfg,'FW_E',CELL,density[j],desired,vsl)
            finally:exposure.cohorts[CELL],exposure.tangents[CELL]=oldrow,oldt
            assert adapter._FW_SEG_CTX['armed'] and adapter._FW_SEG_CTX['dlam']==0
            nxt=mn.metanet_speed_update_kmh(vs[j],up[j],density[j],down[j],desired,dt,length,net.metanet_tau_h,mn.select_anticipation_nu(density[j],net,vsl),net.metanet_kappa_veh_km_lane,net.v_min)
            assert math.isfinite(nxt) and nxt>=net.v_min
            updated.append(nxt)
        incoming=[qin*dt,*p['internal']];outgoing=[*p['internal'],qout*dt]
        nextn=[n+a-b for n,a,b in zip(ns,incoming,outgoing)]
        assert all(-1e-8<=n<=p['capacity']+1e-7 for n in nextn)
        data['next_speed']=updated
        return math.fsum(n*v for n,v in zip(nextn,updated))/sum(nextn) if sum(nextn)>1e-10 else sum(updated)/COUNT

    def advance_exposure(self,exposure,old_n,new_n,internal,total_out,entry,ramps,commands):
        data=self.context.pop(id(exposure),None)
        if data is None:return self.old_exposure(exposure,old_n,new_n,internal,total_out,entry,ramps,commands)
        p=data['prepared'];rows=data['cohorts'];upstream=exposure.cohorts[CELL-1]
        assert ramps[CELL]==0 and CELL not in exposure.signs
        incoming={k:n*internal[CELL-1]/old_n[CELL-1] for k,n in upstream.items()} if old_n[CELL-1] else {}
        newrows=transport(rows,p['internal'],incoming,total_out[CELL])
        # The canonical neighbor gets the actual downstream compartment's mix.
        # Only this temporary aggregate composition is artificial; it is replaced
        # by the conservative three-compartment total immediately afterwards.
        lower=sum(rows[-1].values())
        projected={k:n*old_n[CELL]/lower for k,n in rows[-1].items()} if lower else dict(exposure.cohorts[CELL])
        exposure.cohorts[CELL]=projected;exposure.tangents[CELL]={k:0. for k in projected}
        self.old_exposure(exposure,old_n,new_n,internal,total_out,entry,ramps,commands)
        combined={k:sum(r.get(k,0.) for r in newrows) for k in set().union(*(set(r) for r in newrows))}
        error=abs(sum(combined.values())-new_n[CELL]);self.max_cohort=max(self.max_cohort,error);assert error<1e-7
        exposure.cohorts[CELL]=combined;exposure.tangents[CELL]={k:0. for k in combined}
        data['cohorts']=newrows

    def advance_routes(self,state,cfg,road,**kwargs):
        if road!='FW_E':return self.old_route(state,cfg,road,**kwargs)
        data=state._refine15;p=data['prepared'];rows=data['routes'];dt=kwargs['duration_h']
        outgoing=kwargs['mainline'][CELL]*dt;lower=rows[-1];lowern=sum(lower.values())
        remaining={k:n*(1-outgoing/lowern) for k,n in lower.items()} if lowern else {}
        state.offramp_route_inventory_state['cells'][road][CELL]=dict(lower)
        result=self.old_route(state,cfg,road,**kwargs)
        interim=state.offramp_route_inventory_state['cells'][road][CELL]
        incoming={k:interim.get(k,0.)-remaining.get(k,0.) for k in set(interim)|set(remaining)}
        assert min(incoming.values(),default=0)>-1e-8
        incoming={k:max(0.,v) for k,v in incoming.items()}
        assert abs(sum(incoming.values())-kwargs['mainline'][CELL-1]*dt)<1e-7
        updated=transport(rows,p['internal'],incoming,outgoing)
        combined={k:sum(r.get(k,0.) for r in updated) for k in set().union(*(set(r) for r in updated))}
        residual=sum(combined.values())-sum(p['n'])-sum(incoming.values())+outgoing
        self.max_balance=max(self.max_balance,abs(residual));assert abs(residual)<1e-7
        assert all(abs(sum(r.values())-sum(c.values()))<1e-7 for r,c in zip(updated,data['cohorts']))
        state.offramp_route_inventory_state['cells'][road][CELL]=combined
        data['routes']=updated;data['speed']=data['next_speed'];data['next_speed']=None;data['prepared']=None
        self.route._update_missed_target_diagnostics(state)
        self.trace.append(dict(time=state.time_sec+dt*3600,n=[sum(r.values()) for r in updated],speed=list(data['speed']),
                               fraction90=[r.get(90.,0)/sum(r.values()) if sum(r.values()) else 0 for r in data['cohorts']],
                               incoming=sum(incoming.values()),outgoing=outgoing,internal=p['internal']))
        return result
