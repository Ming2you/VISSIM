"""Measure fixed receiving geometry only; no traffic rollout."""
import ctypes
import json
from pathlib import Path
import random
import time
from evaluation.controllers.physical_urban_transport import ReceivingEnvelope
from envelope_candidate import initial_bound

def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    out=Path(__file__).with_name('envelope_microbenchmark.json')
    assert not out.exists()
    rows=[]
    for n in (10,50,80):
        rng=random.Random(n)
        positions=[rng.uniform(0,500) for _ in range(n)]
        records={}
        values={}
        for label,fn in [('original',ReceivingEnvelope.initial_bound),('candidate',initial_bound)]:
            env=ReceivingEnvelope(500.,5.,13.89,3.2557309454394003,positions)
            start=time.perf_counter()
            values[label]=[fn(env,elapsed) for elapsed in range(1,151) for _ in range(2)]
            records[label]=time.perf_counter()-start
        assert values['original']==values['candidate']
        rows.append(dict(vehicles=n,calls=300,wall_sec=records,
                         speedup=records['original']/records['candidate'],same_values=True))
    result=dict(scope='Fixed initial geometry only; includes cache build/invalidation checks; no full decision speed claim',
                rows=rows,native_runs=0,predictions=0)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(out.read_text(encoding='utf8'))
if __name__=='__main__':main()
