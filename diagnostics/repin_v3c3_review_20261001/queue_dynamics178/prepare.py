"""One frozen slow/moving population candidate in the existing lane region."""
import copy
import gzip
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def pressure(n,s,dn,ds,L,Ld,critical,downcritical,jam):
    return min(1.,max(0.,(n/L-critical)/(jam-critical),
        (dn/Ld-downcritical)/(jam-downcritical),ds/dn if dn else 0.))


METHODS='''
    def _phase_init(self,observations):
        # [slow count, slow speed moment, moving speed moment]. These are
        # subsets/moments of self.stocks, never additional traffic inventory.
        self.phase={i:[[0.,0.,0.] for _ in range(self.groups)] for i in self.cells if i!=19}
        self.phase_rows=[];self.phase_events=[]
        for physical,fw,i,classes in observations:
            if fw!=self.road or i not in self.phase:continue
            g=physical['lane_index']-1;v=physical['speed_kph'];n=sum(classes.values())
            if v<5:self.phase[i][g][0]+=n;self.phase[i][g][1]+=n*v
            else:self.phase[i][g][2]+=n*v
        for i,rows in self.phase.items():
            for g,p in enumerate(rows):
                n=sum(self.stocks[i][g].values())
                assert abs(p[1]+p[2]-n*self.v[i][g])<1e-7
                assert 0<=p[0]<=n+1e-9
        self.phase_initial=copy.deepcopy(self.phase)

    def _phase_begin(self):
        self.phase0=copy.deepcopy(self.phase);self.phase_next=copy.deepcopy(self.phase)
        self.phase_start_n={i:[sum(r.values()) for r in rows] for i,rows in self.stocks.items()}
        self.phase_balance={i:[[0.,0.,0.,0.,0.,0.] for _ in rows] for i,rows in self.phase.items()}

    def _phase_flux(self,i,g,k,amount,kind):
        # Longitudinal accepted flux samples speed-weighted phase stocks.
        # Its Courant-limited total is the SAME flux used by the route ledger.
        if i in self.phase0:
            p=self.phase0[i][g];n=self.phase_start_n[i][g]
            total_moment=p[1]+p[2]
            slow=amount*p[1]/total_moment if total_moment>1e-12 else 0.
            sw=p[1]/p[0] if p[0]>1e-12 else 0.
            moving=n-p[0];mv=p[2]/moving if moving>1e-12 else 0.
            vals=[slow,slow*sw,(amount-slow)*mv]
            for z in range(3):self.phase_next[i][g][z]-=vals[z]
            self.phase_balance[i][g][1]+=slow
        else:
            v=self.split19_oldv[1][g] if i==19 else self.oldv[i][g]
            vals=[amount,amount*v,0.] if v<5 else [0.,0.,amount*v]
        if kind=='through' and i+1 in self.phase_next:
            for z in range(3):self.phase_next[i+1][k][z]+=vals[z]
            self.phase_balance[i+1][k][0]+=vals[0]

    def _phase_lateral(self,i,matrix,ns):
        if i not in self.phase_next:return
        old=copy.deepcopy(self.phase_next[i])
        for g,row in enumerate(matrix):
            for k,amount in enumerate(row):
                if not amount:continue
                frac=amount/ns[g]
                vals=[v*frac for v in old[g]]
                for z in range(3):
                    self.phase_next[i][g][z]-=vals[z]
                    self.phase_next[i][k][z]+=vals[z]
                self.phase_balance[i][g][3]+=vals[0]
                self.phase_balance[i][k][2]+=vals[0]

    def _phase_change(self,i,g,state,cfg):
        p=self.phase_next[i][g];n=sum(self.next[i][g].values())
        # Small roundoff only; no clipping inventory to conceal a mass error.
        if min(p)<-1e-7 or p[0]>n+1e-7:raise ArithmeticError('178 phase transport budget')
        p[:]=[max(0.,x) for x in p]
        old=self.phase0[i][g];n0=self.phase_start_n[i][g]
        if i+1 in self.phase0:
            dn=self.phase_start_n[i+1][g];ds=self.phase0[i+1][g][0]
        else:
            dn=state.freeway_density[self.road][i+1]*self.lengths[i+1];ds=0.
        fd=cfg.network.freeway_segment_params[self.road]
        jam=cfg.network.rho_max
        pressure=min(1.,max(0.,(n0/self.lengths[i]-fd[i]['rho_crit'])/(jam-fd[i]['rho_crit']),
            (dn/self.lengths[i+1]-fd[i+1]['rho_crit'])/(jam-fd[i+1]['rho_crit']),ds/dn if dn else 0.))
        sec=cfg.simulation.T_f_h*3600
        a,b=self.spec178['formation_per_sec'],self.spec178['release_per_sec']
        onset=(n-p[0])*(-math.expm1(-a*pressure*sec))
        release=p[0]*(-math.expm1(-b*(1-pressure)*sec))
        # Convert disjoint OLD populations simultaneously. New slow vehicles
        # brake to zero; released slow vehicles keep their speed moment before
        # METANET accelerates the moving population. No instantaneous v_free.
        moving=n-p[0];u=p[2]/moving if moving>1e-10 else 0.
        w=p[1]/p[0] if p[0]>1e-10 else 0.
        p[2]+=-onset*u+release*w;p[1]-=release*w;p[0]+=onset-release
        self.phase_balance[i][g][4]=onset;self.phase_balance[i][g][5]=release
        self.phase_events.append(dict(time_s=state.time_sec,cell=i,lane=g+1,pressure=pressure,
            n0=n0,s0=old[0],transport_s=p[0]-onset+release,n_next=n,onset=onset,release=release,
            balance=list(self.phase_balance[i][g]),s_next=p[0],slow_moment=p[1]))
        return p,n

    def _phase_finish(self,state,cfg):
        for i,rows in self.phase_next.items():
            for g,p in enumerate(rows):
                n=sum(self.next[i][g].values());b=self.phase_balance[i][g]
                expected=self.phase0[i][g][0]+b[0]-b[1]+b[2]-b[3]+b[4]-b[5]
                if abs(expected-p[0])>1e-7 or p[0]<-1e-7 or p[0]>n+1e-7:
                    raise ArithmeticError('178 slow subset conservation')
                if abs(p[1]+p[2]-n*self.next_v[i][g])>1e-7:
                    raise ArithmeticError('178 velocity moment')
                self.phase_rows.append(dict(time_s=state.time_sec+cfg.simulation.T_f_h*3600,
                    cell=i,lane=g+1,n=n,s=p[0],slow_moment=p[1],moving_moment=p[2],v=self.next_v[i][g]))
        self.phase=self.phase_next
'''


def main():
    assert not (HERE/'coefficients.json').exists(),'Preserve the completed finite candidate'
    protected=h.read(h.R/'state_lateral168/protocol.json')
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    spec=read(h.F/'joint_lane_25/protocol.json')['candidate']
    spec.update(congested_receiving_cells=[21],reciprocal_off='10483')
    # The instantiated parameters, not a separately remembered FD, define
    # the exact density pressure used by training and runtime.
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    common.setup()
    context=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')
    model=context['component']
    cfg=model._config('FW_E',context['parameters']['by_direction']['FW_E'])
    from evaluation.controllers.freeway_geometry import cell_lengths_km
    lengths=cell_lengths_km(cfg.network,'FW_E',31)
    fd=cfg.network.freeway_segment_params['FW_E'];jam=cfg.network.rho_max
    # FD configuration is obtained via the existing replay configuration.
    h.save(HERE/'protocol.json',dict(hypothesis='Dynamic slow subset and finite release separate phase occupancy from moving recovery; replacing the algebraic exit-speed cap only within20--25.',
        cells=list(range(20,26)),source='Exact148 lane region;132 coefficients;171 physical ramp storage; unchanged19 split and lateral rates.',
        train='29none/VSL cached2220.1..2970.1 only. No67/43/61 fitting.',
        fit='Two pooled count/exposure hazards, bounds0..1/s, no feature or coefficient grid.',
        inputs='Current own/downstream density and downstream slow fraction, current actual accepted physical transport. No time/seed/command bonus or future measurements.',
        limitations=['Same-lane endpoints censor transitions during cell/lane crossings.','Incoming from scalar cell19 is classified using boundary mean speed; merge entrants are moving at existing local mean for moment accounting.','Phase stocks are lane totals, not phase-specific destination classes.','Observed slow moment transported; newly stopped vehicles assumed zero speed.'],
        budget=dict(autonomous450_max=25,fit_vectors=1,native=0,FZP=0),
        gates='Conservation and exact initial means; meaningful pair TTT signs; response>=10%better, absolute<=110%, regret<=.5. Same-component diagnostics, not wholeOmega.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP']))
    sources=read(h.R/'state_information92/protocol.json')['inputs']
    samples=[]
    for name in ('29_none','29_vsl'):
        p=h.ROOT/sources[name]['path'];assert h.sha(p)==sources[name]['sha256']
        doc=read(p);assert doc['fields']==['cell','speed_kmh','x_m','lane']
        frames={float(t):v for t,v in doc['frames'].items()}
        for t,tn in zip(sorted(frames),sorted(frames)[1:]):
            assert abs(tn-t-5)<1e-6
            a,b=frames[t],frames[tn]
            for i in range(20,26):
                for g in range(1,4):
                    own={k:v for k,v in a.items() if v[0]==i and v[3]==g}
                    down=[v for v in a.values() if v[0]==i+1 and v[3]==g]
                    n=len(own);s=sum(v[1]<5 for v in own.values());dn=len(down);ds=sum(v[1]<5 for v in down)
                    z=pressure(n,s,dn,ds,lengths[i],lengths[i+1],fd[i]['rho_crit'],fd[i+1]['rho_crit'],jam)
                    onset=released=0
                    for key,v in own.items():
                        w=b.get(key)
                        if w is None or w[0]!=i or w[3]!=g:continue
                        onset+=int(v[1]>=5 and w[1]<5);released+=int(v[1]<5 and w[1]>=5)
                    samples.append(dict(case=name,time=t,cell=i,lane=g,n=n,s=s,pressure=z,
                        onset=onset,release=released,formation_exposure=5*(n-s)*z,release_exposure=5*s*(1-z)))
    coeff={}
    for label,key in [('formation','onset'),('release','release')]:
        count=sum(x[key] for x in samples);exposure=sum(x[label+'_exposure'] for x in samples)
        assert count>0 and exposure>0
        coeff[label+'_per_sec']=min(1.,count/exposure)
        coeff[label+'_fit']=dict(count=count,exposure=exposure,raw_rate=count/exposure,
            zero_exposure_events=sum(x[key] for x in samples if x[label+'_exposure']==0))
    coeff.update(frozen=True,training_seed=29,features='own/downstream FD excess + downstream slow fraction',sample_count=len(samples))
    spec['queue178']=coeff
    source=read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    code=source['RouteLaneRegion']
    def change(old,new):
        nonlocal code
        assert code.count(old)==1,(old,code.count(old))
        code=code.replace(old,new)
    change('        self._split19_init(state,cfg,observations)\n',
           '        self._split19_init(state,cfg,observations)\n        self.spec178=spec["queue178"]\n        self._phase_init(observations)\n')
    change('        self.before = copy.deepcopy(self.stocks)\n',
           '        self._phase_begin()\n        self.before = copy.deepcopy(self.stocks)\n')
    change("            _add(self.next[i][g],_classes('expected_merge:'+ramp,p['route_weights']),amount)\n",
           "            _add(self.next[i][g],_classes('expected_merge:'+ramp,p['route_weights']),amount)\n            if i in self.phase_next:self.phase_next[i][g][2]+=amount*self.oldv[i][g]\n")
    change('            self.off_classes[off] = composition\n',
           "            self.off_classes[off] = composition\n            self._phase_flux(i,g,None,amount,'off')\n")
    change('                amount = sum(moved.values())\n',
           "                amount = sum(moved.values())\n                if i>=19:self._phase_flux(i,g,k,amount,'through')\n")
    change('            moment = [n*v for n,v in zip(ns,self.oldv[i])]\n',
           '            self._phase_lateral(i,matrix,ns)\n            moment = [n*v for n,v in zip(ns,self.oldv[i])]\n')
    change('\n        for g,n in enumerate(self.n0[i]):\n',
           '\n        for g,n in enumerate(self.n0[i]):\n            phase,count=self._phase_change(i,g,state,cfg)\n            moving=count-phase[0]\n            phase_u=phase[2]/moving if moving>1e-10 else 0.\n')
    change('            if i == 20:up = self.split19_oldv[1][g]\n',
           '            if i == 20:up = self.split19_oldv[1][g]\n            elif i-1 in self.phase0:\n                pp=self.phase0[i-1][g];mm=self.phase_start_n[i-1][g]-pp[0]\n                up=pp[2]/mm if mm>1e-10 else self.oldv[i-1][g]\n')
    change('mn.metanet_speed_update_kmh(self.exchange_v[i][g],up,rho,down,target,dt,self.lengths[i],',
           'mn.metanet_speed_update_kmh(phase_u,up,rho,down,target,dt,self.lengths[i],')
    old='''            if requests > sent+1e-9 and n:
                velocity = min(velocity,(self.outgoing[i][g]+sent)*self.lengths[i]/(dt*n))
            values.append(max(net.v_min,velocity))
'''
    new='''            velocity=max(net.v_min,velocity)
            if not math.isfinite(velocity) or velocity*dt/self.lengths[i]>1.05:
                raise ArithmeticError('178 moving speed/Courant invalid')
            phase[2]=moving*velocity
            values.append((phase[1]+phase[2])/count if count>1e-10 else velocity)
'''
    change(old,new)
    change('    def commit(self, state, cfg):\n',
           '    def commit(self, state, cfg):\n        self._phase_finish(state,cfg)\n')
    code+=METHODS
    compile(code,'178_candidate','exec')
    changed=dict(source,RouteLaneRegion=code)
    assert all(changed[k]==v for k,v in source.items() if k!='RouteLaneRegion')
    h.save(HERE/'coefficients.json',coeff);h.save(HERE/'spec.json',spec)
    h.save(HERE/'executed_function_sources.json',changed)
    with gzip.open(HERE/'fit_rows.json.gz','wt',encoding='utf8') as f:json.dump(samples,f,allow_nan=False)
    h.save(HERE/'pins.json',pins)
    (HERE/'completed175_runner.py.txt').write_bytes((h.R/'state_lateral168/run.py').read_bytes())
    h.save(HERE/'preflight.json',dict(status='prepared',coefficients_frozen=True,other_four_functions_unchanged=True,
        manifest_sha256=h.sha(h.R/'lane_state132/eval_01/manifest.json'),source_sha256=h.sha(HERE/'executed_function_sources.json')))
    print(coeff,flush=True)


if __name__=='__main__':main()
