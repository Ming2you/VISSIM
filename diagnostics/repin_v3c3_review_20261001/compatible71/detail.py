"""Reuse the established conditional replay and compare actual lane receipts."""
import ast
import gzip
import hashlib
import json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.frozen10643_receiver import assess as component

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)


def main():
    assert not (HERE/'detail.json').exists()
    native=read(HERE.parent/'frozen10643_receiver/local_state_audit.json')
    prior=read(HERE.parent/'frozen10643_receiver/assessment.json')
    cohorts=read(HERE.parent/'entry10643/native_cohorts.json')
    manifest=read(HERE/'candidate_manifest.json')
    profile=read(ROOT/manifest['sources']['port_profile']['path'])
    cases={};modes=('baseline','native_residual_space','native_all_frozen_space')
    for name,key,folder in [('47hold','held_actual','closedloop_recorded2700_select_check_trace10681_compatible71_47'),
                            ('47selected','selected','closedloop_recorded2700_select_check_trace10681_compatible71_47'),
                            ('43nc','held_actual','closedloop_recorded2250_lever450_trace10681_compatible71_43')]:
        tr=read(I/folder/(key+'_RM_C10681_trace.json.gz'))
        local=tr['local_receiver_diagnostics'];heads=[]
        for native_head in native['cases'][name]['head_comparison']:
            lane=native_head['lane'];connector=native_head['modeled_connector'];total=0.
            for r in local['resources']:
                if r['kind']=='lane_urban_sending' and ast.literal_eval(r['resource'])==(71,lane,3):
                    total+=r['accepted_by_source_veh'].get(str(('exit',connector)),0.)
            heads.append(dict(lane=lane,native_green_head=native_head['green_crossings'],
                baseline_connector=native_head['model_corresponding_connector_outflow'],candidate_connector=total))
        cases[name]={'heads':heads}
        if name.startswith('47'):
            arm='hold' if key=='held_actual' else 'selected'
            frame_path=next(Path(p) for p in prior['source_pins'] if p.endswith('frame_002700.json') and arm in Path(p).parts)
            initial=read(frame_path)['vehicles'];assert PINS[str(frame_path)]==prior['source_pins'][str(frame_path)]
            cases[name]['conditional_cases']={mode:component.replay(tr,initial,profile['travel_speed_kmh']['10643'],cohorts['cases'][arm]['witnesses'],mode) for mode in modes}
    out=dict(status='completed_frozen_future_entry_diagnosis_not_autonomous',cases=cases,component_replays=6,
        new_full_forecasts=0,new_native=0,new_fzp_scan=0,source_pins=PINS,
        limitations=['Native head and model connector planes differ by about2m; GREEN crossings are comparable diagnostics, not exact event identity.',
         'All-space conditional replay withholds other traffic and freezes receiving history; it is not feasible full-network control.',
         'Aggregate5->4 movements also include mandatory other-turn traffic. Do not interpret them as discretionary10635 reverse exchanges.'])
    (HERE/'detail.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for name,row in cases.items():
        print(name,'HEAD',row['heads'])
        for mode,c in row.get('conditional_cases',{}).items():print(name,mode,c['drain_total'],c['final_stock'],c['final_external_backlog'])


if __name__=='__main__':main()
