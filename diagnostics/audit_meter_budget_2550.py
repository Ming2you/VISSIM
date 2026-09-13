"""Read fixed2550 action/raw only; no controller import or simulation."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run='codex_area_sources_beta0_s13_20260910';dec=ROOT/'evaluation/runs'/run/('decisions_'+run)
    paths=[dec/'action_002550.json',dec/'action_002550.csv',dec/'state_002550.json',ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',Path(__file__)]
    before={str(p.relative_to(ROOT)):sha(p) for p in paths};a=load(paths[0]);raw=load(paths[2]);d=a['diagnostics'];m=d['_control_area_meter_finalized']
    rows=[]
    for r,realized in a['ramp_metering'].items():
        rows.append({'ramp':r,'requested_before_guard_vph':m['requested_rates'][r],
                     'requested_after_guard_vph':d['rw_meter_requested_'+r],
                     'realized_vph':realized,'realized_minus_guard_request_vph':realized-d['rw_meter_requested_'+r],
                     'physical_queue_veh':raw['ramp_counts'][r],
                     'observed_approach_stopped_veh':a['metadata']['rw_spill_'+r+'_veh'],
                     'guard_forced':a['metadata']['rw_spill_guard_'+r]})
    budget=sum(a['ramp_metering'].values());assert abs(budget-a['N_UF_star'])<1e-9
    report={'schema':'actual-meter-budget-audit/v1','run':run,'sim_sec':2550,'source_sha256':before,
            'group_rows':rows,'intent_N_UF_star_vph':d['leader_candidate_intent_N_UF_star'],
            'guard_request_total_vph':sum(r['requested_after_guard_vph'] for r in rows),
            'realized_N_UF_star_vph':budget,'leader_upper_bound_vph':d['leader_nuf_bound_upper'],
            'exceeds_upper_bound_vph':budget-d['leader_nuf_bound_upper'],
            'physical_green_sec':{k:v for k,v in d.items() if k.startswith('rw_meter_green_')},
            'finalizer_guard_metadata':m['guard_metadata'],
            'source_changes':[p for p,h in before.items() if sha(ROOT/p)!=h],
            'scope':'Real selected action; physical greens, abstract table-realized rates and model budget are separate from measured vehicle flow. Not included in the objective-scope patch.'}
    assert not report['source_changes']
    out=ROOT/'diagnostics/meter_budget_2550.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'realized_budget':budget,'excess':report['exceeds_upper_bound_vph'],'source_changes':[]}))
if __name__=='__main__':main()
