"""One conservative interior10639 candidate from frozen173; no coefficient fit."""
import ast
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def build():
    source=copy.deepcopy(h.read(h.R/'merge_target173/executed_function_sources.json'))
    code=source['RouteLaneRegion']
    def replace(old,new):
        nonlocal code
        assert code.count(old)==1,old
        code=code.replace(old,new)
    replace('        self.assert_partition(state)\n\n    def assert_partition',
            '        self.assert_partition(state)\n        self._split10_init(state,cfg,observations,spec)\n\n    def assert_partition')
    replace('        n = sum(self.stocks[i][self.ramp_access[ramp]].values())', '''        if i == 10:
            n = sum(self.split10[1][self.ramp_access[ramp]].values())
            return self._split10_budget(cfg,n,self.split10_lengths[1])/cfg.simulation.T_f_h
        n = sum(self.stocks[i][self.ramp_access[ramp]].values())''')
    replace('        self.n0 = {i:', '''        self.split10_before = copy.deepcopy(self.split10)
        self.split10_oldv = copy.deepcopy(self.split10_v)
        self.split10_next = copy.deepcopy(self.split10)
        self.split10_n0 = [[sum(row.values()) for row in part] for part in self.split10_before]
        self.split10_backbudget = [self._split10_budget(cfg,n,self.split10_lengths[1]) for n in self.split10_n0[1]]
        self.split10_backfree = list(self.split10_backbudget)
        self.n0 = {i:''')
    replace('''                physical = self.free[i][g]
                limit = dt*hadi_receiving_vph(n/self.lengths[i],jam,critical,capacity,wave,0.)''', '''                length = self.lengths[i]
                if i == 10:
                    n = self.split10_n0[0][g];length = self.split10_lengths[0]
                physical = max(0.,jam*length-n)
                limit = dt*hadi_receiving_vph(n/length,jam,critical,capacity,wave,0.)''')
    replace('''            if amount > self.free[i][g]+1e-7:
                raise ArithmeticError('Accepted merge exceeds its physical lane space')
            self.free[i][g] -= amount;self.merge[i][g] += amount
            _add(self.next[i][g],_classes('expected_merge:'+ramp,p['route_weights']),amount)''', '''            classes = _classes('expected_merge:'+ramp,p['route_weights'])
            if i == 10:
                if amount > self.split10_backfree[g]+1e-7:
                    raise ArithmeticError('10639 merge exceeds downstream-part receiving')
                self.split10_backfree[g] -= amount
                _add(self.split10_next[1][g],classes,amount)
            else:
                if amount > self.free[i][g]+1e-7:
                    raise ArithmeticError('Accepted merge exceeds its physical lane space')
                self.free[i][g] -= amount
            self.merge[i][g] += amount
            _add(self.next[i][g],classes,amount)''')
    replace('        through = {}', '''        # Same existing ramp-first priority, now sharing the rear part's
        # old receiving envelope with the conservative internal transfer.
        self.split10_inner=[]
        for g,row in enumerate(self.split10_before[0]):
            fraction=min(1.,self.split10_oldv[0][g]*dt/self.split10_lengths[0])
            requested={k:n*fraction for k,n in row.items()};total=sum(requested.values())
            factor=min(1.,self.split10_backfree[g]/total) if total else 0.
            self.split10_inner.append({k:n*factor for k,n in requested.items()})
        through = {}''')
    replace('        for off,requests in self.off_requests.items():', '''        through[10]=[{k:n*min(1.,self.split10_oldv[1][g]*dt/self.split10_lengths[1]) for k,n in row.items()}
                     for g,row in enumerate(self.split10_before[1])]
        for off,requests in self.off_requests.items():''')
    replace('''                if g is not None:
                    _add(self.next[i][g],moved,-1.);self.outgoing[i][g] += amount''', '''                if i == 9:
                    _add(self.split10_next[0][k],moved)
                elif i == 10:
                    _add(self.split10_next[1][g],moved,-1.)
                if g is not None:
                    _add(self.next[i][g],moved,-1.);self.outgoing[i][g] += amount''')
    replace('''        for i,rows in self.next.items():
            old = copy.deepcopy(rows)''', '''        for g,moved in enumerate(self.split10_inner):
            _add(self.split10_next[0][g],moved,-1.)
            _add(self.split10_next[1][g],moved)
        for i,rows in self.next.items():
            if i == 10:
                self._split10_exchange(cfg)
                continue
            old = copy.deepcopy(rows)''')
    replace('''    def speed(self, i, state, cfg, control, mn, exposure, delta, kappa):
        from''', '''    def speed(self, i, state, cfg, control, mn, exposure, delta, kappa):
        if i == 10:
            return self._split10_speed(state,cfg,control,mn,exposure,delta,kappa)
        from''')
    replace('''            command = mn.segment_vsl(control,road,i,cfg)''', '''            if i == 11:up = self.split10_oldv[1][g]
            command = mn.segment_vsl(control,road,i,cfg)''')
    replace('''        self.stocks = self.next;self.v = self.next_v
        self.assert_partition(state)''', '''        self.stocks = self.next;self.v = self.next_v
        self.split10 = self.split10_next;self.split10_v = self.split10_next_v
        self._split10_check(cfg)
        for p in (0,1):
            for g,row in enumerate(self.split10[p]):
                internal=sum(self.split10_inner[g].values())
                merge=self.merge[10][g] if p else 0.
                incoming=self.incoming[10][g] if p==0 else internal
                outgoing=internal if p==0 else self.outgoing[10][g]
                budget=self.free[10][g] if p==0 else self.split10_backbudget[g]
                if incoming+merge>budget+1e-7:raise ArithmeticError('Split10 shared receiving exceeded')
                cfl=self.split10_oldv[p][g]*cfg.simulation.T_f_h/self.split10_lengths[p]
                self.split10_rows.append(dict(time_s=state.time_sec+cfg.simulation.T_f_h*3600,
                    part=p,lane=g+1,n_before=self.split10_n0[p][g],n_veh=sum(row.values()),
                    v_kmh=self.split10_v[p][g],length_km=self.split10_lengths[p],
                    incoming_veh=incoming,outgoing_veh=outgoing,merge_veh=merge,
                    internal_veh=internal,receiving_budget_veh=budget,courant=cfl,
                    lateral_veh=sum(row.values())-self.split10_n0[p][g]-incoming-merge+outgoing))
        self.assert_partition(state)''')
    code+='''
    def _split10_init(self,state,cfg,observations,spec):
        from evaluation.controllers.offramp_routing import _add,_position
        runtime=cfg.network.offramp_route_inventory
        if any(p['freeway']==self.road and p['source_cell']==10 for p in runtime['branches'].values()):
            raise ValueError('Spatial10 requires no interior exit')
        merges={r for r,p in runtime['merges'].items() if p['freeway']==self.road and p['cell']==10}
        if merges!={'RM_C10639'}:raise ValueError('Spatial10 requires10639')
        start,end=runtime['bounds'][self.road][10:12];split=float(spec['merge_split_position_m'])
        if not start<split<end:raise ValueError('Split10 outside physical cell')
        self.split10_lengths=[(split-start)/1000.,(end-split)/1000.]
        if abs(sum(self.split10_lengths)-self.lengths[10])>1e-9:raise ValueError('Split10 length mismatch')
        self.split10=[[{} for _ in range(self.groups)] for _ in (0,1)]
        moments=[[0.]*self.groups for _ in (0,1)]
        for physical,fw,i,classes in observations:
            if fw!=self.road or i!=10:continue
            _,x,_=_position(runtime,physical['link_no'],physical['position_m'])
            p=int(x>=split);g=physical['lane_index']-1
            _add(self.split10[p][g],classes);moments[p][g]+=physical['speed_kph']
        self.split10_v=[[moments[p][g]/sum(row.values()) if sum(row.values()) else self.v[10][g]
                        for g,row in enumerate(part)] for p,part in enumerate(self.split10)]
        self.split10_rows=[];self.split10_error=0.
        self.split10_excess=[[max(0.,sum(row.values())-cfg.network.rho_max*self.split10_lengths[p])
                             for row in part] for p,part in enumerate(self.split10)]
        self._split10_check(cfg)
        self.split10_initial=dict(stocks=copy.deepcopy(self.split10),speeds=copy.deepcopy(self.split10_v),
                                  lengths_km=list(self.split10_lengths),initial_excess=copy.deepcopy(self.split10_excess))

    def _split10_budget(self,cfg,n,length):
        fd=cfg.network.freeway_segment_params[self.road][10];jam=cfg.network.rho_max;critical=fd['rho_crit']
        capacity=critical*fd['v_free']*math.exp(-1/fd['metanet_a_m'])
        return min(max(0.,jam*length-n),cfg.simulation.T_f_h*hadi_receiving_vph(n/length,jam,critical,capacity,capacity/(jam-critical),0.))

    def _split10_check(self,cfg):
        from evaluation.controllers.offramp_routing import _add
        for g in range(self.groups):
            combined={}
            for p in (0,1):
                row=self.split10[p][g]
                if any(not math.isfinite(n) or n < -1e-8 for n in row.values()):
                    raise ArithmeticError('Negative/nonfinite split10 stock')
                excess=max(0.,sum(row.values())-cfg.network.rho_max*self.split10_lengths[p])
                if excess>self.split10_excess[p][g]+1e-7:raise ArithmeticError('New split10 storage excess')
                self.split10_excess[p][g]=excess
                _add(combined,row)
            expected=self.stocks[10][g]
            error=max([abs(combined.get(k,0.)-expected.get(k,0.)) for k in combined.keys()|expected.keys()]+[0.])
            self.split10_error=max(self.split10_error,error)
            if error>1e-7:raise ArithmeticError('Split10 destination partition differs')

    def _split10_exchange(self,cfg):
        from evaluation.controllers.offramp_routing import _add
        self.split10_exchange_v=[]
        dt=cfg.simulation.T_f_h
        for p,rows in enumerate(self.split10_next):
            old=copy.deepcopy(rows);ns=[sum(r.values()) for r in old];matrix=[]
            for g,rates in enumerate(self.rates):
                hazard=sum(rates)
                matrix.append([ns[g]*(1.-math.exp(-hazard*dt*3600))*r/hazard if hazard else 0. for r in rates])
            for k in range(self.groups):
                total=sum(row[k] for row in matrix)
                factor=min(1.,max(0.,cfg.network.rho_max*self.split10_lengths[p]-ns[k])/total) if total else 0.
                for g in range(self.groups):matrix[g][k]*=factor
            moment=[n*v for n,v in zip(ns,self.split10_oldv[p])]
            for g,row in enumerate(matrix):
                for k,amount in enumerate(row):
                    if not amount:continue
                    classes={key:n*amount/ns[g] for key,n in old[g].items()
                             if key.rsplit('|',1)[-1]!='10682' or (g>0 and k==g-1)}
                    amount=sum(classes.values())
                    _add(rows[g],classes,-1.);_add(rows[k],classes)
                    moment[g]-=amount*self.split10_oldv[p][g];moment[k]+=amount*self.split10_oldv[p][g]
            self.split10_exchange_v.append([moment[g]/sum(row.values()) if sum(row.values())>1e-9 else self.split10_oldv[p][g]
                                           for g,row in enumerate(rows)])
        self.next[10]=[{} for _ in range(self.groups)]
        for part in self.split10_next:
            for g,row in enumerate(part):_add(self.next[10][g],row)
'''
    old149=h.merge_position149_source(h.read(h.R/'spatial_context148/forecast/executed_function_sources.json'))['RouteLaneRegion']
    tree=ast.parse(old149).body[0];lines=old149.splitlines(keepends=True)
    n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_split23_speed')
    speed=''.join(lines[n.lineno-1:n.end_lineno])
    speed=speed.replace('split23','split10').replace('[23]','[10]').replace('[24]','[11]').replace('road,23,','road,10,')
    speed=speed.replace('self.oldv[22][g]','state.freeway_speed[road][9]')
    code+='\n'+speed+'\n';ast.parse(code);source['RouteLaneRegion']=code
    old="if hasattr(joint_lanes,'split19') and i == 19:"
    assert source['rollout'].count(old)==1
    source['rollout']=source['rollout'].replace(old,"if (hasattr(joint_lanes,'split19') and i == 19) or (hasattr(joint_lanes,'split10') and i == 10):")
    return source


def main():
    assert not (HERE/'protocol.json').exists(),'Preserve previous attempt'
    source=build();prior=h.read(h.R/'merge_target173/protocol.json')
    spec=h.read(h.R/'merge_target173/spec.json')
    geometry=h.read(h.R/'merge_target172/protocol.json')['geometry']['10639']
    spec['merge_split_position_m']=geometry['x_m']
    h.save(HERE/'executed_function_sources.json',source);h.save(HERE/'spec.json',spec)
    driver=h.R/'state_lateral168/run.py';(HERE/'driver_before.py.txt').write_bytes(driver.read_bytes())
    paths=[Path(__file__),h.R/'merge_target173/executed_function_sources.json',h.R/'merge_target173/spec.json',
           h.R/'merge_target172/protocol.json',h.R/'merge_transition174/completion.json',Path(h.__file__),
           h.ROOT/'evaluation/controllers/physical_ramp_boundary.py']
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS174 actual speed/population diagnosis and conditional spatial screen.',
        hypothesis='Retain observed internal10 spatial state with conservative transport and actual rear injection; assess whether it improves first-region merge/recovery response.',
        comparison='Matched frozen173 route-lane10--11 versus same coefficients with interior10 split. Neither arm includes19--25; not whole171 improvement.',
        geometry=geometry,budget=dict(forecasts=21,fit=0,native=0,FZP=0),
        constants='Same153 coefficients,173 lateral rates/inlet shares,171 admission,all demands/routes/commands/VSL history/off storage and1s integration.',
        shared_receiving='Old rear FD-derived receiving shared by10639 merge first then internal transfer; front receiving admits upstream flow. No borrowing newly freed space.',
        initial_excess='Retain observed local excess without deleting vehicles; free space zero while above jam, excess may not increase.',
        gate='Exact baseline173 parity,route/mass/sharedspace;log1s Courant and peak speeds. Stop candidate series on nonfinite,negative,new storage/receiving violation or Courant>1.05; no timestep or speed clipping workaround. Need merge/gain/recovery improvement,not only speed.',
        limitations='Same inspected29/67/61 states,not blind. Fixed173 microscopic priority and inlet/lateral approximations remain. Conditions of fullOmega/8ramps/independent/SDMPC/native remain.',
        pins={str(p):h.sha(p) for p in paths},protected_sha256=prior['protected_sha256'],STOP=prior['STOP']))
    print('prepared175 geometry',geometry,'forecast cap21')


if __name__=='__main__':main()
