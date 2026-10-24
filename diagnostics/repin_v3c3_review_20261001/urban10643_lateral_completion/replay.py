"""Two bounded conditional checks of one conservative lateral completion law."""
import gzip
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R=HERE.parent
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)


def main():
    target=HERE/'conditional_v2.json';assert not target.exists()
    spec=importlib.util.spec_from_file_location('old_conditional',R/'urban10643_conditional/replay.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    original=old.UrbanTransport
    prior=read(R/'urban10643_conditional/assessment.json')
    manifest=read(HERE/'candidate_manifest.json');network=ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest()==manifest['sources']['network']['sha256']
    protocol=read(HERE/'local_protocol.json')
    cache=read(R/'lane10643_native/rows.json.gz');routes,exits=old.geometry(network)
    rows=[r for r in cache['rows'] if r[0]==old.START and r[2] in old.LOCAL]
    current=old.observe(old.raw_frame(rows,old.START),routes,exits)
    program=old.NativeProgram(read(R/'local10643_receiver/head_audit.json')['cases']['47hold'])
    trace=read(I/'closedloop_recorded2700_select_check_trace10681_entry10643/held_actual_RM_C10681_trace.json.gz')
    room=defaultdict(dict)
    for r in trace['local_receiver_diagnostics']['resources']:
        if r['kind']=='lane_urban_exit_receiving':room[int(r['start_sec'])][int(r['resource'])]=r['available_veh']
    models=[]
    def enabled(*args,**kwargs):
        m=original(*args,**kwargs);m.mandatory_lateral_completion=True;models.append(m);return m
    results={}
    old.UrbanTransport=enabled
    try:
        for timing in ('early','late'):
            result=old.run(current,network,protocol,prior['events'],program,room,timing,'frozen_exit',[])
            baseline=prior['cases'][timing+'_frozen_exit_conserved']
            results[timing]=dict(result=result,before_departures=baseline['departures'],
                native_departures=prior['native']['implied_normal_departures'],
                before_final_n=baseline['final_n'],native_final_n=prior['native']['final_n'],
                blocked=[dict(cell=list(key),reason=reason,steps=n) for (key,reason),n in models[-1].blocked_seconds.items()])
            print(timing,'departures',baseline['departures'],result['departures'],'native',prior['native']['implied_normal_departures'],
                'stock',baseline['final_n'],result['final_n'],'heads',result['head_connector_discharge'],flush=True)
    finally:old.UrbanTransport=original
    target.write_text(json.dumps(dict(status='completed_conditional_candidate',results=results,
        source_pins=PINS,future_native_inputs=True,autonomous=False,new_native=0,new_fzp=0,fit_calls=0,
        caveat='Same actual arrivals and native signals, unserved demand remains explicit; two5s arrival brackets. This does not qualify autonomous gains.'),ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
