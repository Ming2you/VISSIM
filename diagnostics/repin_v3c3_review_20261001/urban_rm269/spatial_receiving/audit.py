"""Closed paired MER and saved model response; no prediction or live files.

Detector crossings at1m are distinct from boundary admissions at0m. Tail events
and vehicle disappearances are never counted as a normal crossing.
"""
from pathlib import Path
from collections import defaultdict
import ctypes,gzip,hashlib,json,sys

HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck

RUNS=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
PINS={}
def pin(p):
    p=Path(p);PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    pin(p);return json.loads(Path(p).read_bytes())

def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not (HERE/'timing.json').exists()
    out={}
    for arm in ('hold','selected'):
        folder=RUNS/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        events=[];frames={};tail=defaultdict(int)
        for end in (2400,2550,2700,2850):
            raw=read(folder/f'state_{end:06}.json');bundle=oc.load_bundle(raw);o=bundle.obs
            ds,_=oc.read_detector_csv(o['detector_config']['path'],o['detector_config']['sha256'])
            oc.validate_raw(o,ds,expected_simres=10);check_rule_crosscheck(o,ds)
            assigned=oc.assign_window(o,bundle.mer_rows)
            for p in [o['detector_config']['path'],folder/o['mer']['chunk'],folder/o['err']['chunk'],
                      folder/o['frames']['previous']['path'],folder/o['frames']['current']['path']]:pin(p)
            for t,f in ((end-150,bundle.frame_start),(end,bundle.frame_end)):
                assert f['complete'];frames[t]=[v for v in f['vehicles'] if v[1]==10681]
            for d in ds:
                if d.link!=10681 or d.role not in ('ramp_arrival','meter_head'):continue
                role='entry_1m' if d.role=='ramp_arrival' else 'head'
                tail[role]+=assigned.tails[d.dcp_no]
                events.extend(dict(t=e.t_entry,vehicle=e.veh,lane=d.lane,role=role)
                              for e in assigned.entries[d.dcp_no])
        path=H/f'lateral_turnover_bound/forecast2400/{arm}.response.json.gz';pin(path)
        with gzip.open(path,'rt',encoding='utf8') as f:model=json.load(f)
        services=[x for x in model['resource_allocations'] if x['kind']=='physical_ramp_head_service'
                  and x['resource'].startswith('RM_C10681:')]
        entry=[x for x in model['transfers'] if x['target']=='ramp:RM_C10681']
        # Native past2250..2400 is kept separate; never an in-horizon input.
        bins=[]
        for start in range(2250,2850,30):
            end=start+30
            row=dict(start=start,end=end,native={r:sum(start<e['t']<=end and e['role']==r for e in events)
                 for r in ('head','entry_1m')})
            if start>=2400:
                row['model']={'head':sum(x['accepted_total_veh'] for x in services if start<x['end_sec']<=end),
                              'entry_0m':sum(x['vehicles'] for x in entry if start<x['end_sec']<=end)}
            bins.append(row)
        # Accepted entry and physical prehead head crossings use exact link geometry.
        headpos=290.72003141146473
        snapshots=[]
        for t,rows in sorted(frames.items()):
            snapshots.append(dict(t=t,lanes=[dict(lane=l,prehead=sum(v[2]==l and v[3]<headpos for v in rows),
                prehead_positions_m=sorted(v[3] for v in rows if v[2]==l and v[3]<headpos),
                posthead=sum(v[2]==l and v[3]>=headpos for v in rows)) for l in (1,2)]))
        out[arm]=dict(bins=bins,events=events,snapshots=snapshots,unassigned_tails=dict(tail))
        print(arm,json.dumps(bins[5:10]),flush=True)
        del model
    pin(__file__)
    report=dict(status='complete',arms=out,source_pins=PINS,new_predictions=0,new_native=0,fzp_scans=0,
        limitations=['Closed detector timing diagnostic; no new fit or autonomous validation.',
         'Native entry at1m and model admission at0m have a small different boundary; do not force equality.',
         'Head service and entrance flow are different boundaries and need spatial initialization.',
         'No inference of backward wave speed from the control labels or future flows.'])
    (HERE/'timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

if __name__=='__main__':main()
