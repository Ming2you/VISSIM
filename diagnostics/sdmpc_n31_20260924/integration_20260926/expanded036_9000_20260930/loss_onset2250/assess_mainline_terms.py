"""Check noninterference and algebra of the two bounded speed-term traces."""
import csv
import difflib
import gzip
import hashlib
import json
from pathlib import Path

L=Path(__file__).resolve().parent
I=L.parent.parent
O=L/'mainline_balance'
RUN=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins={}


def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)


def close(a,b,label):
    assert abs(a-b)<1e-7,(label,a,b)


def main():
    assert not (O/'terms_verification.json').exists()
    geometry=read(I/'selected/port_gain/geometry.json')
    cells=[c for c in geometry['cells'] if c['road']=='FW_E']
    table=list(csv.DictReader((O/'cells.csv').open(encoding='utf-8')))
    proof=read(O/'summary.json')
    protocol=read(O/'terms_protocol.json')
    for p,digest in protocol['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest
    terms=('relaxation','convection','anticipation','lane_drop_applied','base_clip','merge_applied','boundary_cap_applied')
    output=[];times={}
    for start in (2250,3600):
        base=read(I/f'closedloop_recorded{start}_lever450_RM_C10484_city{start}_ps_all8_clockcandidate/held_actual.json')
        new=read(I/f'closedloop_recorded{start}_lever450_RM_C10484_city{start}_ps_all8_termscandidate/held_actual.json')
        for k in ('ttt_omega_veh_h','cost_by_stock','physical_cell_states','ramps','commands','control_area'):
            assert base[k]==new[k],k
        times[str(start)]=new['wall_sec']
        trace=read(L/f'city_path/{start}_ps_all8_termscandidate/mainline_terms.json.gz')
        assert len(trace)==1350
        frames=[read(RUN/f'lane_observations/frame_{t:06d}.json')['vehicles'] for t in (start,start+150)]
        for cell in range(18,27):
            rr=[r for r in trace if r['cell']==cell]
            assert [r['time'] for r in rr]==list(range(start,start+150))
            for a,b in zip(rr,rr[1:]):close(a['final_speed'],b['speed'],'interstep final speed')
            close(sum(sum(r[k] for k in terms) for r in rr),rr[-1]['final_speed']-rr[0]['speed'],'telescoping speed')
            close(rr[-1]['final_speed'],new['physical_cell_states'][1]['speed_kmh']['FW_E'][cell],'saved endpoint speed')
            row=next(r for r in table if int(r['start'])==start and r['model']=='candidate' and int(r['cell'])==cell)
            if cell in (24,25):
                assert not any(b['road']=='FW_E' and (b.get('from_cell')==cell or b.get('to_cell')==cell) for b in geometry['boundaries'])
                close(sum(r['q_out']/3600 for r in rr),float(row['model_downstream']),'independent step flow')
            speeds=[]
            for frame in frames:
                values=[]
                for v in frame:
                    address=geometry['addresses'].get(str(v[1]))
                    if address and address[0]=='FW_E' and cells[cell]['start_m']<=address[1]+v[3]<cells[cell]['end_m']:
                        values.append(v[4])
                speeds.append(sum(values)/len(values) if values else None)
            close(rr[0]['speed'],speeds[0],'native initial speed')
            output.append(dict(start=start,cell=cell,native_initial_speed=speeds[0],native_end_speed=speeds[1],
                model_end_speed=rr[-1]['final_speed'],model_mean_speed=sum(r['speed'] for r in rr)/150,
                model_mean_desired=sum(r['desired'] for r in rr)/150,
                relaxation_accelerating_steps=sum(r['desired']>=r['speed'] for r in rr),
                means_kmh_per_one_second_step={k:sum(r[k] for r in rr)/150 for k in terms},
                first_step=rr[0],last_step=rr[-1]))
    result=dict(status='complete_observational_diagnosis',adopted=False,forecasts=2,fit=0,optimizer=0,
        forecast_compute_sec=sum(times.values()),forecast_compute_by_state=times,new_native=0,fzp_scans=0,
        state_cost_command_flow_parity=True,step_algebra_and_endpoint_parity=True,rows=output,pins=pins,
        limitations=['Model-internal term accounting, not experimental causal effects of parameters.',
            'Actual endpoint speeds are spatial samples, not a matched vehicle acceleration measurement.',
            'No calibration or new production dynamics. Only first150seconds match executed native commands.'])
    (O/'terms_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    before=(O/'audit_city_arrival.before.py').read_text(encoding='utf-8')
    after=(L/'audit_city_arrival.py').read_text(encoding='utf-8')
    (O/'audit_city_arrival.after.py').write_text(after,encoding='utf-8')
    (O/'instrumentation.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='before.py',tofile='audit_city_arrival.py')),encoding='utf-8')
    print(json.dumps({str(t):[{k:r[k] for k in ('cell','native_end_speed','model_end_speed','model_mean_desired','relaxation_accelerating_steps','means_kmh_per_one_second_step')} for r in output if r['start']==t and r['cell'] in (23,24,25)] for t in (2250,3600)},ensure_ascii=False))


if __name__=='__main__':main()
