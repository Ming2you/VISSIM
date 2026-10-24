"""Locate the saved175 VSL cost-response error; accounting, not causality."""
import csv
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'gain_ledger.json').exists()
    out=HERE/'forecast';rows=h.read(out/'rows.json')
    pins={str(Path(__file__)):h.sha(__file__),str(out/'rows.json'):h.sha(out/'rows.json')}
    arms=('release','release_vsl90');modes=('unsplit173','split175')
    times=[round(2670.1+30*i,6) for i in range(16)]
    stocks={};speeds={};lookup={(r['version'],r['arm']):r for r in rows if r['case']=='s67_late'}
    for arm in arms:
        path=h.I/'heldout67_freeway_20260930/observations'/arm/'cells_30s.csv'
        pins[str(path)]=h.sha(path)
        with path.open(encoding='utf-8-sig',newline='') as f:
            native=[r for r in csv.DictReader(f) if r['road']=='FW_E' and round(float(r['time_s']),6) in times]
        stocks['actual',arm]={(round(float(r['time_s']),6),int(r['cell'])):float(r['n_veh']) for r in native}
        speeds['actual',arm]={(round(float(r['time_s']),6),int(r['cell'])):float(r['v_kmh']) if r['v_kmh'] else None for r in native}
        assert len(stocks['actual',arm])==16*31
        for mode in modes:
            path=out/mode/('s67_late_'+arm+'.json.gz');pins[str(path)]=h.sha(path);pred=h.read(path)
            stocks[mode,arm]={(round(r['time_s'],6),r['cell']):r['n_veh'] for r in pred['cells']}
            speeds[mode,arm]={(round(r['time_s'],6),r['cell']):r['v_kmh'] for r in pred['cells']}
            for i in range(31):
                stocks[mode,arm][times[0],i]=stocks['actual',arm][times[0],i]
                speeds[mode,arm][times[0],i]=speeds['actual',arm][times[0],i]
    def integral(mode,arm,cells,tt):
        d=stocks[mode,arm]
        return sum(sum(d[a,i]+d[b,i] for i in cells)*(b-a)/7200 for a,b in zip(tt,tt[1:]))
    for mode in ('actual',)+modes:
        for arm in arms:
            ref=lookup['unsplit173' if mode=='actual' else mode,arm]['actual' if mode=='actual' else 'predicted']['mainline_ttt']
            assert abs(integral(mode,arm,range(31),times)-ref)<1e-8
    regions={'upstream0_8':range(0,9),'first_ramps9_13':range(9,14),'between14_17':range(14,18),
             'second_ramps18_25':range(18,26),'downstream26_30':range(26,31)}
    ledger=[]
    for block,tt in [('whole450',times)]+[(f'block{b+1}',times[5*b:5*b+6]) for b in range(3)]:
        for name,cells in regions.items():
            delta={mode:integral(mode,arms[1],cells,tt)-integral(mode,arms[0],cells,tt) for mode in ('actual',)+modes}
            ledger.append(dict(block=block,region=name,lo=tt[0],hi=tt[-1],delta_ttt_veh_h=delta,
                               split_error=delta['split175']-delta['actual']))
    cell_rows=[]
    for cell in range(31):
        delta={mode:integral(mode,arms[1],[cell],times)-integral(mode,arms[0],[cell],times) for mode in ('actual',)+modes}
        states={}
        for mode in ('actual',)+modes:
            for arm in arms:
                valid=[t for t in times[1:] if speeds[mode,arm][t,cell] is not None]
                nsum=sum(stocks[mode,arm][t,cell] for t in valid)
                v=sum(stocks[mode,arm][t,cell]*speeds[mode,arm][t,cell] for t in valid)/nsum if nsum else None
                states[mode+'_'+arm]=dict(mean_n=sum(stocks[mode,arm][t,cell] for t in times[1:])/15,n_weighted_sample_speed=v)
        cell_rows.append(dict(cell=cell,delta_ttt_veh_h=delta,split_error=delta['split175']-delta['actual'],states=states))
    components={}
    for mode in ('actual',)+modes:
        a,b=[lookup['unsplit173' if mode=='actual' else mode,arm]['actual' if mode=='actual' else 'predicted'] for arm in arms]
        components[mode]={k:b[k]-a[k] for k in ('ttt','mainline_ttt','ramp_ttt','off_ttt','end_n','exits')}
        assert abs(sum(z['delta_ttt_veh_h'][mode] for z in ledger if z['block']=='whole450')-components[mode]['mainline_ttt'])<1e-8
    for path,digest in pins.items():assert h.sha(path)==digest,path
    h.save(HERE/'gain_ledger.json',dict(scope='East31+4on+4off,30s trapezoids,2670.1..3120.1;not wholeOmega;source/merge differences are not controlled causal contributions.',
        comparison='seed67 RM release fixed, VSL90 minus110;same initial state, prediction inputs unchanged.',components=components,
        regions=ledger,cells=cell_rows,input_sha256=pins,new_predictions=0,new_native=0))
    print('components',components)
    for z in ledger:
        if z['block']=='whole450':print(z)
    print('largest signed cell response errors',[(z['cell'],z['delta_ttt_veh_h']) for z in sorted(cell_rows,key=lambda z:abs(z['split_error']),reverse=True)[:6]])


if __name__=='__main__':main()
