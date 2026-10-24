"""Persist the new causal-mechanism lead, keeping the full goal incomplete."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE/'completion.json').exists()
    data=read(HERE/'assessment.json');side=read(HERE/'side_limits.json');bypass=read(HERE/'bypass.json')
    for report in (data,side,bypass):
        assert all(sha(p)==h for p,h in report['source_pins'].items())
    assert bypass['native']['hold']['red_interval']==19 and bypass['native']['city']['red_interval']==11
    assert bypass['geometry']['shared_connectors']
    step=('Investigate one aggregate shared-lane prehead bypass correction for SC6_E_SC104_to_N_SC103/10142. '
          'Current geometry leaves11.846m before SG6:6, native has19/11 red-interval departures, and Claude bd39205 excluded it because it shares lane1 with10200. '
          'Separate direct signal authority from through-queue blocking; do not simply mark unrestricted unsignalized, refit saturation, or invent a gain bonus. '
          'Check reusable68 lane/route access mechanics first, then one bounded candidate with same current states/actions/accepted receiving and mass. '
          'Latest341 shows city normal-outflow cost sign still wrong while RM-vector sign survives input accounting. '
          'Retain340 physical initialization as diagnostic, do not repeatSC105 ETA/rate tuning. '
          'Preserve FW5/U10,450s,terminalOFF,Omega701; no new full native or push. Full integration/feasible selection/runtime validation still required.')
    stamp=datetime.now(timezone.utc).isoformat()
    result=dict(status='completed_accounts_and_physical_mismatch_diagnosis',goal_complete=False,
        completed_utc=stamp,production_changed=False,new_forecasts=0,ad=0,optimizer=0,native=0,fits=0,fzp=0,push=False,
        latest_model_comparisons={k:{f:r[f] for f in ('native','model','parts')} for k,r in data['contrasts'].items()},
        candidate_implemented=False,next_step=step,
        source_pins={str(p):sha(p) for p in (HERE/'audit.py',HERE/'side_limits.py',HERE/'bypass.py',HERE/'assessment.json',HERE/'side_limits.json',HERE/'bypass.json',HERE/'README.md',Path(__file__))})
    (HERE/'completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p in (A/'plan.json',A.parent/'plan.json'):
        plan=read(p);plan.update(current_stage='gain_account341_SC6_shared_lane_prehead_mismatch_identified',current_workers=[],
            latest_stage=str(HERE/'README.md'),next_step=step,goal_complete=False,updated_utc=stamp,
            latest_goal_turn=dict(classification='progress',previous_goal_turn='progress340_projection_forecasts',
                evidence='340 finalized;341 latest three-arm conservation/time budget and native red-passage demonstrate direct-signal mismatch with shared-lane caveat. No new forecasts/native.'))
        plan['gain_account341']={k:result[k] for k in ('status','completed_utc','latest_model_comparisons','candidate_implemented','goal_complete')}
        p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p,rel in ((A/'README.md','gain_account341/README.md'),(A.parent/'README.md','aggregate270/gain_account341/README.md')):
        old=p.read_text(encoding='utf8')
        intro=('# 최신341: 도시 신호 손익과 공유차로 우회전 제한 분리\n\n'
            '최신329/330의 RM 벡터 이득은 정상유출 시간항에서도 방향이 맞고, 도시 신호의 방출 지연 방향은 반대다. '
            'SC6 동측10142는 신호11.846m 전에 분기하며 적색 중19/11대 통과를 확인했다. Claude도 공유 직진차로 때문에 무신호 목록에서 제외한 곳이다. '
            f'직접 신호 제한과 공유차로 막힘 분리 후보가 다음 작업이며 아직 구현되지 않았다. [근거]({rel}). '
            '목표 미완료; 새 예측·native·fit·push0. 아래는 이전 기록이다.\n\n')
        p.write_text(intro+old,encoding='utf8')
    print('GAIN341_PROGRESS_RECORDED goal_complete=false candidate_implemented=false')

if __name__=='__main__':main()
