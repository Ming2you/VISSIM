"""Matched450s one-meter causal replay; canonical runner/writer, no MPC calls."""
import csv
import hashlib
import io
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUT=I/'native_rm10480_spill256'
RUN=Path('D:/VISSIM_runs/20261005_rm233_235_fixed90_s29_9000/sdmpc')
DEC=RUN/'decisions_sdmpc31_sdmpc9000_s29'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    assert not OUT.exists(), 'Preserve prior preparation'
    OUT.mkdir()
    pins={};changes=[]
    mapping=read(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
    meter=next(x for x in mapping['ramp_meters'] if x['id']=='RM_C10480')
    assert meter['sc_no']==9101 and meter['connector']==10480
    capacity=None
    for arm in ['hold','release']:
        folder=OUT/arm/'commands';folder.mkdir(parents=True)
        for t in [1,*range(150,3601,150)]:
            source=DEC/f'action_{t:06d}.csv';pins[str(source)]=sha(source)
            raw=source.read_bytes();reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')));rows=list(reader)
            target=next(r for r in rows if r['id']=='RM_C10480')
            g=float(target['green_sec']); rate=float(target['rate_vph'])
            if g:capacity=rate/g*10 if capacity is None else capacity; assert abs(rate/g*10-capacity)<1e-8
            old=dict(target)
            if arm=='release' and t>=3150:
                new=2+2*((t-3150)//150)
                target['green_sec']=str(float(new));target['rate_vph']=str(new*capacity/10)
                target['metadata']=target['metadata'].replace('group_rate_vph='+old['rate_vph'],'group_rate_vph='+target['rate_vph'])
                with (folder/source.name).open('w',newline='',encoding='utf-8') as f:
                    writer=csv.DictWriter(f,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(rows)
                assert {k for k in target if target[k]!=old[k]}<= {'green_sec','rate_vph','metadata'}
                changes.append(dict(time=t,old_green=g,new_green=new,only_changed_id='RM_C10480'))
            else:(folder/source.name).write_bytes(raw)
            # Replay runner consumes CSV. Do not copy100MB optimizer diagnostics
            # or pretend this diagnostic replay made a new optimizer decision.
            save(folder/source.with_suffix('.json').name,dict(metadata=dict(sim_sec=t,
                controller_status='diagnostic_fixed_sequence',scope='Saved actual CSV replay; no optimizer or plant prediction',
                original_csv_path=str(source),original_csv_sha256=pins[str(source)],
                replay_csv_sha256=sha(folder/source.name)),diagnostics={}))
            for suffix in ['csv','json']:
                p=folder/f'action_{t:06d}.{suffix}';pins[str(p)]=sha(p)
    for t in [1,*range(150,3150,150)]:
        assert sha(OUT/'hold/commands'/f'action_{t:06d}.csv')==sha(OUT/'release/commands'/f'action_{t:06d}.csv')
    for t in range(3150,3601,150):
        rows=[list(csv.DictReader((OUT/a/'commands'/f'action_{t:06d}.csv').open(encoding='utf-8-sig'))) for a in ['hold','release']]
        assert len(rows[0])==len(rows[1])==213
        assert [a['id'] for a,b in zip(*rows) if a!=b]==['RM_C10480']
    network=RUN/'network/sdmpc31_sdmpc9000_s29.inpx'
    save(OUT/'protocol.json',dict(start_sec=3150,end_sec=3600,seed=29,arms=['hold','release'],
        network=str(network),network_sha256=sha(network),command_pins=pins,control_start_sec=900,
        controller='wu-link',native_authorization_pending=False,native_authorization='User requested stop, fix spillback and rerun; prior authorization for necessary VISSIM tests',
        sim_resolution=10,vehicle_record_interval_sec=5,observation_interval_sec=150,
        max_native_runs=2,automatic_retries=0,controller_optimization=False,
        intervention='Only10480 at3150/3300/3450: g2/4/6 instead of recorded0/0/2. Final3600 g8 is endpoint-only.',
        rationale='10480queue backs into124 and10483; test only this meter before modifying plant/optimizer.',
        full_physical_prefix_parity_required=True,new_output='D:/VISSIM_runs/20261005_rm10480_spill256'))
    save(HERE/'preparation.json',dict(protocol=str(OUT/'protocol.json'),changes=changes,
        production_changed=False,stopped_prior_run=str(RUN),old_STOP_preserved=True))
    print('prepared two3600s replays;450s one-meter contrast, otherwise identical recorded CSV')

if __name__=='__main__':main()
