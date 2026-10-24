"""Commit the completed local scope/service audit to the active plans."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
A = HERE.parent
H = A.parent
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def main():
    assert not (HERE/'completion.json').exists()
    review = read(HERE/'assessment.json')
    service = read(HERE/'service_review.json')
    assert len(review['native']) == 4 and len(service['rows']) == 15
    assert sum(r.get('entries_balance_derived',0) for r in review['native']) == 151
    assert sum(r.get('exits',0) for r in review['native']) == 146
    assert all(len(r['upstream_heads']) == 8 for r in review['native'][1:])
    assert 'Ran 3 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    for arm in review['models'].values():
        assert all(abs(g['balance_error']) < 1e-7 for w in arm['windows'] for g in w['groups'].values())
    pins = {**review['source_pins'], **service['source_pins']}
    for p,h in pins.items():
        assert sha(Path(p)) == h, p
    for p in (HERE/'README.md',HERE/'assessment.json',HERE/'service_review.json',*HERE.glob('*.py'),
              A/'flow279/README.md',H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md',
              H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U8.md'):
        pins[str(p)] = sha(p)
    next_step = ('Retain fixed FW5/U10 coefficients and all physical invariants. Qualify latest331/329 diagnostic model in scalar versus full-axis AD worker before another wholeSDMPC choice. Restore the exact same scoped hooks and follower bindings; no silent fallback to279 model. Reuse332 physical command responses. The known279/333 upstream supply residual is not a new fit target; no parameter grid or tiny -.271 sign fitting. Whole city/joint ranking and independent-state/seed material direction remain unqualified. No new native or push in this handoff.')
    stage = dict(status='complete_scope_and_service_audit',readme=str(HERE/'README.md'),
                 assessment=str(HERE/'assessment.json'),service=str(HERE/'service_review.json'),
                 forecasts=0,ad=0,optimizer=0,native=0,fits=0,fzp=0,push=0,goal_complete=False,
                 corrected52_model_delta=review['corrected_release_minus_hold_cost']['approach52_all_origins'],
                 parent_actual_entries=151,parent_actual_exits=146,
                 reused_known279_residual=True,production_changes=0)
    now = datetime.now(timezone.utc).isoformat()
    for parent in (A,H):
        p = parent/'plan.json'
        backup = parent/'plan.before333.json'
        assert not backup.exists()
        backup.write_bytes(p.read_bytes())
        doc = read(p)
        doc.update(flow_scope333=stage,current_stage='flow_scope333_scope_fixed_supply_timing_separated',
                   latest_stage=str(HERE/'README.md'),next_step=next_step,current_workers=[],goal_complete=False,
                   updated_utc=now,last_goal_turn='progress333_scope_accounting_fixed_and_service_limits_separated',
                   latest_goal_turn_audit=dict(previous='progress332_saved_response_and_queue_closure',
                       current='progress333_new_all_origin_scope_and_native_green_vs_ready_stock_evidence; prior279_supply_residual_reused_not_new'))
        save(p,doc)
    save(HERE/'completion.json',dict(stage,completed_at=now,source_pins=pins,next_step=next_step))
    print('COMPLETE333: diagnostic scope repaired; service split saved; no new forecasts or model fit; goal active.')


if __name__=='__main__':
    main()
