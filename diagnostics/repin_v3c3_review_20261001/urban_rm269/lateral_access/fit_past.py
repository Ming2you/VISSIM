"""One past-only effective lateral-access estimate from current-ID witnesses."""
import hashlib,json,math
from pathlib import Path
from scipy.optimize import minimize_scalar

HERE=Path(__file__).resolve().parent;H=HERE.parent
NATIVE=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def main():
    assert not (HERE/'past_fit.json').exists()
    net=read(H/'sc1_supply/forecast2400/network.json')
    caps=net['known_legsplit_routes']['entry_lane_receiving']['road_capacity_veh']
    rows=[]
    for start in (1800,1950,2100,2250):
        raw=read(NATIVE/f'state_{start+150:06}.json')['obs150'];frames={}
        for side in ('previous','current'):
            desc=raw['frames'][side];p=NATIVE/desc['path'];f=read(p)
            assert PINS[str(p)]==desc['sha256'] and f['complete']
            frames[f['time_s']]={v[0]:v for v in f['vehicles']}
        assert set(frames)=={start,start+150}
        p=NATIVE/raw['mer']['chunk'];b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
        assert PINS[str(p)]==raw['mer']['chunk_sha256']
        arrivals={r[4] for r in map(json.loads,b.splitlines()) if r[1] in (960276,960277) and r[2] is not None and start<=r[2]<start+150}
        for lane in (3,4):
            initial=[v for v in frames[start].values() if v[1]==68 and v[2]==lane and v[8]=='STATIC' and (v[6],v[7])==(1135,4)]
            moved=[];retained=[];censored=[]
            for v in initial:
                end=frames[start+150].get(v[0])
                if v[0] in arrivals or (end is not None and end[1]==68 and end[2]<lane):moved.append(v[0])
                elif end is not None and end[1]==68:retained.append(v[0])
                else:censored.append(v[0])
            occupancy=[sum(v[1]==68 and v[2]==lane-1 for v in f.values()) for f in frames.values()]
            gap=sum(max(0.,1.-n/caps[str(lane-1)]) for n in occupancy)/2
            rows.append(dict(start_sec=start,lane=lane,initial=len(initial),moved_ids=moved,retained_ids=retained,
                             censored_ids=censored,adjacent_occupancy=occupancy,gap_fraction=gap))
    def loss(rate):
        score=0.
        for r in rows:
            x=rate*150*r['gap_fraction']
            score+=-len(r['moved_ids'])*math.log(-math.expm1(-x))+len(r['retained_ids'])*x
        return score
    fit=minimize_scalar(loss,bounds=(1e-6,1.),method='bounded',options={'xatol':1e-10})
    assert fit.success and math.isfinite(fit.fun) and 1e-6<fit.x<1
    cfg=read(H/'sc1_supply/config.json')
    cfg['urban']['known_wout_lateral_access']={'rate_per_sec':float(fit.x)}
    (HERE/'config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(status='one_past_only_effective_rate',rate_per_sec=float(fit.x),negative_log_likelihood=float(fit.fun),fit_evaluations=fit.nfev,
        calibration_end_sec=2400,rows=rows,source_pins=PINS,
        limits=['150s endpoints provide lower-bound lateral-progress witnesses, not all instantaneous lane changes.',
                'Absent IDs without a ramp-entry witness are excluded, never assumed discharged.',
                'Endpoint-averaged adjacent vacancy is a calibration approximation; the autonomous candidate uses predicted current vacancy only.',
                'A single congested-state effective rate is a test candidate, not a qualified free-flow law.'])
    (HERE/'past_fit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print('rate_per_sec',fit.x,'loss',fit.fun,'nfev',fit.nfev,'moved',sum(len(r['moved_ids']) for r in rows),'retained',sum(len(r['retained_ids']) for r in rows))
if __name__=='__main__':main()
