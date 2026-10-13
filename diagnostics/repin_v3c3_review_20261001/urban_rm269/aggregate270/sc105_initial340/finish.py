"""Record340's bounded result without modifying pinned experiment plans."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE/'completion.json').exists()
    review=read(HERE/'assessment.json'); run=read(HERE/'forecast3300_v2/summary.json')
    assert review['status']=='review_complete' and run['status']=='complete'
    assert all(sha(p)==h for p,h in run['source_pins'].items())
    assert all(sha(p)==h for p,h in review['source_pins'].items())
    stamp=datetime.now(timezone.utc).isoformat()
    next_step=('Use existing latest329 hold/city and330 joint responses to refresh327 input/normal-outflow inventory-time decomposition. '
        'Separate remaining city-command error from RM effect and common exogenous boundary uncertainty; do not add317/326 conditional deltas to the latest model. '
        'Do not repeat SC105 ETA/rate/split tuning:340 improves local timing but leaves wholeOmega/RM delta unchanged. '
        'Preserve337 feasible10681 selection,338 other-seed limits, FW5/U10,450s,terminalOFF,Omega701. '
        'Production integration and full decision timing remain to be qualified; no new full native/grid/push at this stage.')
    completion=dict(status='complete_bounded_sc105_current_projection_review',goal_complete=False,
        production_adopted=False,completed_utc=stamp,assessment=str(HERE/'assessment.json'),
        assessment_sha256=sha(HERE/'assessment.json'),
        input_states_checked=3,forecasts450_completed=3,review_added_forecasts=0,
        ad=0,optimizer=0,native=0,new_fits=0,fzp_scans=0,push=False,
        rm_delta=review['release_minus_hold']['current340']['omega'],rm_delta_change=review['rm_delta_change'],
        verdict=review['verdict'],next_step=next_step,
        source_pins={str(p):sha(p) for p in (HERE/'review.py',HERE/'README.md',HERE/'assessment.json',HERE/'forecast3300_v2/summary.json',Path(__file__))})
    (HERE/'completion.json').write_text(json.dumps(completion,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        assert str(path) not in run['source_pins']
        plan=read(path)
        plan.update(current_stage='sc105_initial340_review_complete_local_timing_improved_whole_gain_unqualified',
            current_workers=[],latest_stage=str(HERE/'README.md'),next_step=next_step,goal_complete=False,updated_utc=stamp,
            latest_goal_turn=dict(classification='progress',previous_goal_turn='progress340_projection_and_three_forecasts',
                evidence='Completed340 stored-response audit: command parity, source pins, group mass balance and unchanged RM gain; no reruns.'))
        plan['sc105_initial340_completed']={k:completion[k] for k in ('status','assessment','assessment_sha256','input_states_checked','forecasts450_completed','rm_delta','rm_delta_change','verdict','goal_complete')}
        path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path,prefix in ((A/'README.md','sc105_initial340/README.md'),(A.parent/'README.md','aggregate270/sc105_initial340/README.md')):
        text=path.read_text(encoding='utf8')
        title='# 最新340: SC105 현재 대기열·이동 재고 분리 검증'
        if not text.startswith(title):
            intro=(title+'\n\nSC105 두 번째150초 직진 방출14.78→24.89대(실측 전용차로 하한27),10565 공급74.89→78.01대. '
                'RM 완화−유지 ΩTTT는−0.271377대·시간으로 그대로다. 초기3상태·예측3회·보존/제약 확인, 전체 도시+RM 손익·생산 채택은 미완료. '
                f'근거: [{prefix}]({prefix}). 기존 완료 예측/동결 실행을 반복하지 않았다. 아래는 이전 기록이다.\n\n')
            path.write_text(intro+text,encoding='utf8')
    print('SC105_REVIEW_RECORDED goal_complete=false')

if __name__=='__main__':main()
