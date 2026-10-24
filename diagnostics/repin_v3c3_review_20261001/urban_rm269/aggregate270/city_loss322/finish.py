from pathlib import Path
from datetime import datetime, timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    reports=[json.loads((HERE/n).read_bytes()) for n in ('assessment.json','signal_review.json')]
    for r in reports:
        for p,h in r['source_pins'].items():assert sha(p)==h,p
    assert reports[0]['status']=='complete_city_loss_operands_separated'
    assert all(sum(b['receiving_loss'] for b in value['blocks'])<1e-8
               for arm in reports[0]['model'].values() for value in arm.values())
    now=datetime.now(timezone.utc).isoformat()
    next_step=('Do not repeat SC6/SC101 service or ETA tuning. Current321 shows no receiver rejection at these heads; '
        'SC1015236.48 ceiling already applied and errors concern readiness/timing. SC16 north-left is a separate material failure: '
        '206.53veh/h permits only1.033/0.975 per150s while native8/10/10 and1/10/9; actual18/17s greens match. '
        'Current exclusive lane4 stopped1veh is projected left0.2/through0.4/right0.4; fix only supported current physical ownership, '
        'not every NULL route. Supply/turning also deficient: total predictedSC16left2.13/2.01; actual28/20. '
        'Review Claude SC16 routing changes and the pinned old network, then derive one past-only aggregate SC12north->SC16 '
        'accepted-supply/route-composition/service correction, preserving finite receiving, queue/arrival separation and single ownership. '
        'No future native route/admission inputs. Do not transplant beta from different v3c1 network or raise ceiling alone and declare success. '
        'Limit candidate count; qualify meaningful whole-response on unused state and AD/full feasibleSDMPC<600s after material gain evidence. '
        'Keep FW5/U10,horizon450,terminalOFF,Omega701,same demand/area and immutable queue; no automatic fullnative/grid/push. '
        'Source admission318 remains separate conditional evidence; no whole gain completion claim.')
    done=dict(status='complete_city_loss_root_operands_diagnosed',goal_complete=False,production_adopted=False,
        previous_goal_turn='no_progress_clock_status_only_revalidated',
        this_goal_turn='progress_current321_three_head_operand_audit_native_green_check_SC16_supply_service_and_initial_lane_loss_identified',
        current_workers=[],closed_tool_session=38343,execution_exit_code=0,budget=reports[0]['budget'],
        updated_utc=now,next_step=next_step,source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before322.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        value=json.loads(path.read_bytes());value.update(current_stage='city322_remaining_losses_split_SC16_supply_turn_and_service',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=next_step,
            latest_goal_turn_audit={k:done[k] for k in ('previous_goal_turn','this_goal_turn')})
        value['city_loss322']=dict(completion=str(out),sha256=sha(out),adopted=False,status=done['status'])
        tmp=path.with_suffix('.tmp322.json');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED322: three-head losses separated; SC16 supply/turn/service correction next; goal active incomplete.')

if __name__=='__main__':main()
