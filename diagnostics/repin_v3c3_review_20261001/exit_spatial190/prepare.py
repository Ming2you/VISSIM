"""One two-speed spatial exit-cell probe on frozen148. No production edit."""
import ast
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists()
    p=h.R/'spatial_context148/forecast/executed_function_sources.json'
    source=h.read(p);base=source['RouteLaneRegion'];s=base
    def replace(old,new):
        nonlocal s
        assert s.count(old)==1,(old,s.count(old))
        s=s.replace(old,new)
    replace('        self._split19_init(state,cfg,observations)',
        '''        self._split19_init(state,cfg,observations)
        self.split20_enabled=bool(spec.get('spatial20_enabled',False))
        if self.split20_enabled:self._split20_init(state,cfg,observations)''')
    replace('        self.split19_before = copy.deepcopy(self.split19)',
        '''        if self.split20_enabled:self._split20_plan(cfg)
        self.split19_before = copy.deepcopy(self.split19)''')
    replace('        for i in self.receiving_cells:\n',
        '''        if self.split20_enabled:
            self.free[20]=[max(0.,cfg.network.rho_max*self.lengths[20]/2-n) for n in self.split20_n0[0]]
        for i in self.receiving_cells:
''')
    replace('''        for i,rows in self.before.items():
            through[i] = []''',
        '''        for i,rows in self.before.items():
            if self.split20_enabled and i==20:rows=self.split20_before[1]
            through[i] = []''')
    replace('''                fraction = min(1.,self.oldv[i][g]*dt/self.lengths[i])
                composition = {}''',
        '''                fraction = min(1.,self.oldv[i][g]*dt/self.lengths[i])
                if self.split20_enabled and i==20:
                    fraction=min(1.,self.split20_oldv[1][g]*dt/(self.lengths[20]/2))
                composition = {}''')
    replace("            row = {k:n for k,n in self.before[i][g].items() if k.rsplit('|',1)[-1] == off}",
        """            off_source=self.split20_before[1][g] if self.split20_enabled and i==20 else self.before[i][g]
            row = {k:n for k,n in off_source.items() if k.rsplit('|',1)[-1] == off}""")
    replace('''            _add(self.next[i][g],composition,-1.)
            # Shared-lane FIFO''',
        '''            _add(self.next[i][g],composition,-1.)
            if self.split20_enabled and i==20:_add(self.split20_next[1][g],composition,-1.)
            # Shared-lane FIFO''')
    replace('''                if g is not None:
                    _add(self.next[i][g],moved,-1.);self.outgoing[i][g] += amount''',
        '''                if self.split20_enabled:
                    if i==19:_add(self.split20_next[0][k],moved)
                    elif i==20:_add(self.split20_next[1][g],moved,-1.)
                if g is not None:
                    _add(self.next[i][g],moved,-1.);self.outgoing[i][g] += amount''')
    replace('''        for i,rows in self.next.items():
            if i == 19:''',
        '''        if self.split20_enabled:
            for g,moved in enumerate(self.split20_inner):
                _add(self.split20_next[0][g],moved,-1.)
                _add(self.split20_next[1][g],moved)
        for i,rows in self.next.items():
            if self.split20_enabled and i==20:
                self._split20_exchange(cfg)
                continue
            if i == 19:''')
    replace('''        if i == 19:
            return self._split19_speed(state,cfg,control,mn,exposure)''',
        '''        if i == 19:
            return self._split19_speed(state,cfg,control,mn,exposure)
        if self.split20_enabled and i==20:
            return self._split20_speed(state,cfg,control,mn,exposure)''')
    replace('''            if i == 20:up = self.split19_oldv[1][g]''',
        '''            if i == 20:up = self.split19_oldv[1][g]
            if self.split20_enabled and i==21:up=self.split20_oldv[1][g]''')
    replace('''                down=self.split19_n0[1][g]/half if p==0 else self.n0[20][g]/self.lengths[20]''',
        '''                down=self.split19_n0[1][g]/half if p==0 else self.n0[20][g]/self.lengths[20]
                if self.split20_enabled and p==1:down=self.split20_n0[0][g]/(self.lengths[20]/2)''')
    replace('''        self.stocks = self.next;self.v = self.next_v
        self.split19 =''',
        '''        self.stocks = self.next;self.v = self.next_v
        if self.split20_enabled:self._split20_commit(state,cfg)
        self.split19 =''')
    methods={n.name:ast.get_source_segment(base,n) for n in ast.parse(base).body[0].body if isinstance(n,ast.FunctionDef)}
    # Reuse identical destination/lateral accounting of the existing spatial
    # cell19, now at20. Exit handling above explicitly withdraws downstream.
    for name in ('_split19_check','_split19_exchange'):
        method=methods[name].replace('split19','split20').replace('Spatial19','Spatial20').replace('[19]','[20]')
        s+='\n    '+method+'\n'
    init=methods['_split19_init'].replace('split19','split20').replace('Spatial19','Spatial20').replace('[19]','[20]').replace('==19','==20').replace('!= 19','!= 20').replace('[19:21]','[20:22]')
    old="""        if any(p['freeway']==self.road and p['source_cell']==20 for p in runtime['branches'].values()):
            raise ValueError('Spatial split19 requires no internal off branch')"""
    # The copied message has split20 after the replacement above.
    old=old.replace('split19','split20')
    assert old in init
    init=init.replace(old,"""        offs={o for o,p in runtime['branches'].items() if p['freeway']==self.road and p['source_cell']==20}
        if offs!={'10483'} or self.off_access.get('10483')!=0:
            raise ValueError('Spatial20 requires the existing10483 branch mapping')""")
    init=init.replace('self.split20_rows = [];self.split20_error = 0.',
                      'self.split20_rows = [];self.split20_error = 0.;self.split20_max_courant=0.')
    s+='\n    '+init+'\n'
    s+='''
    def _split20_plan(self,cfg):
        self.split20_before=copy.deepcopy(self.split20)
        self.split20_oldv=copy.deepcopy(self.split20_v)
        self.split20_next=copy.deepcopy(self.split20)
        self.split20_n0=[[sum(row.values()) for row in part] for part in self.split20_before]
        self.split20_inner=[]
        half=self.lengths[20]/2;dt=cfg.simulation.T_f_h
        for g in range(self.groups):
            c=self.split20_oldv[0][g]*dt/half
            self.split20_max_courant=max(self.split20_max_courant,c,self.split20_oldv[1][g]*dt/half)
            if self.split20_max_courant>1.+1e-9:raise ArithmeticError('Spatial20 Courant exceeds1')
            requested={k:n*c for k,n in self.split20_before[0][g].items()}
            total=sum(requested.values());free=max(0.,cfg.network.rho_max*half-self.split20_n0[1][g])
            factor=min(1.,free/total) if total else 0.
            self.split20_inner.append({k:n*factor for k,n in requested.items()})

    def _split20_speed(self,state,cfg,control,mn,exposure):
        from evaluation.controllers.freeway_fd import literature_desired_speed
        net=cfg.network;road=self.road;dt=cfg.simulation.T_f_h;half=self.lengths[20]/2
        self.split20_next_v=[]
        for p in (0,1):
            velocities=[]
            for g,n in enumerate(self.split20_n0[p]):
                command=mn.segment_vsl(control,road,20,cfg,physical_length_km=half,segment_end=p==1)
                active=command<max(cfg.freeway_follower.vsl_set)-.5
                rho=n/half
                down=self.split20_n0[1][g]/half if p==0 else self.n0[21][g]/self.lengths[21]
                up=self.split19_oldv[1][g] if p==0 else self.split20_oldv[0][g]
                target=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,command,net.alpha_vsl,active,
                    net.metanet_a_m,getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
                target=literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get(road),cfg,road,20,rho,target,command,active)
                if exposure is not None:target=exposure.target(cfg,road,20,rho,target,command)
                velocity=mn.metanet_speed_update_kmh(self.split20_exchange_v[p][g],up,rho,down,target,dt,half,
                    net.metanet_tau_h,mn.select_anticipation_nu(rho,net,command),net.metanet_kappa_veh_km_lane,net.v_min)
                requests=sum(row[g] for off,row in self.off_requests.items() if self.off_access[off]==g
                    and net.offramp_route_inventory['branches'][off]['source_cell']==20)
                sent=sum(row[g] for off,row in self.off_sent.items() if self.off_access[off]==g
                    and net.offramp_route_inventory['branches'][off]['source_cell']==20)
                if p==1 and requests>sent+1e-9 and n:
                    velocity=min(velocity,(self.outgoing[20][g]+sent)*half/(dt*n))
                velocities.append(max(net.v_min,velocity))
            self.split20_next_v.append(velocities)
        means=[];counts=[]
        for g in range(self.groups):
            ns=[sum(self.split20_next[p][g].values()) for p in (0,1)];total=sum(ns);counts.append(total)
            means.append(sum(ns[p]*self.split20_next_v[p][g] for p in (0,1))/total if total>1e-9 else sum(self.split20_next_v[p][g] for p in (0,1))/2)
        self.next_v[20]=means
        return sum(n*v for n,v in zip(counts,means))/sum(counts) if sum(counts) else sum(means)/len(means)

    def _split20_commit(self,state,cfg):
        self.split20=self.split20_next;self.split20_v=self.split20_next_v
        self._split20_check(cfg)
        for p in (0,1):
            for g,row in enumerate(self.split20[p]):
                self.split20_rows.append(dict(time_s=state.time_sec+cfg.simulation.T_f_h*3600,
                    part=p,lane=g+1,n_veh=sum(row.values()),v_kmh=self.split20_v[p][g],
                    internal_veh=sum(self.split20_inner[g].values())))
'''
    ast.parse(s);source['RouteLaneRegion']=s
    spec=h.read(h.R/'queue_dynamics178/spec.json');spec.pop('queue178');spec['spatial20_enabled']=True
    proto=copy.deepcopy(h.read(h.R/'merge_priority189/protocol.json'))
    for key in ('formula','literature','assumptions','previous'):proto.pop(key,None)
    proto.update(hypothesis='Does averaging upstream approach and downstream exit queue within cell20 lose the recurrent VSL discharge/recovery response?',
        source='Exact148/132+171, original ramp-first allocation. Only cell20 gains two conserved equal-length subcells with separate METANET speed states. No189 priority or178 phase law.',
        inputs='Initial native positions/speeds/classes only; future current predicted states and accepted movement. Actual future labels only in scoring.',
        assumptions='Each approx100m half remains internally mixed. Physical10483 divergence is1.407m before original cell20 edge; retained existing edge abstraction, no geometry change.',
        source_checks='Reuse split19 accounting with explicit off removal from downstream half; downstream-half speed to21; upstream-half density to19; repeated20 parameter context andhalf length.',
        limitations=['Fixed equal two-half partition; no position/count or parameter search.',
            'Existing parent-cell VSL exposure state shared by halves; not vehicle-level speed exposure.',
            'Per-lane destination mixing and constant calibrated lateral rates remain.',
            'East component scope only, not wholeOmega. Historical inspected states, not blind.'],
        budget=dict(autonomous450_max=13,fit_vectors=0,native=0,FZP=0),
        validation='1 disabled exact parity,12 historical29/43/61/67 controls. Reuse178 baseline.150prefix and450 scores.',
        previous='189 supply sharing rejected.88/89/169 source differences already separated; do not repeat.119/120/144/148 split19;175 split10; no prior split20 two-speed test found.176/180 stop geometry limitations preserved. Claude03 review checked.',
        gates='Existing meaningful pair signs,response>=10%better,absolute<=110%,regret<=.5vehh. Also inspect off136/150 total and middle29/43. If failed no split-size grid.',
        no_future_observations=True)
    pins={str(p):h.sha(p),str(h.R/'queue_dynamics178/spec.json'):h.sha(h.R/'queue_dynamics178/spec.json'),
        str(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py'):h.sha(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py')}
    for q,d in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(q)==d,q
    for name,value in [('protocol',proto),('pins',pins),('spec',spec),('executed_function_sources',source),('coefficients',dict(fit=False,partition=[.5,.5],manifest=str(h.R/'lane_state132/eval_01/manifest.json')))]:h.save(HERE/(name+'.json'),value)
    print('Prepared one cell20 spatial candidate; no rollout yet')


if __name__=='__main__':main()
