"""Record verified306 results without adopting diagnostic composite or changing native jobs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
    assert not (HERE/'completion.json').exists()
    r=read(HERE/'comparison.json');u=read(HERE/'unseen3300.json')
    for doc in (r,u):
        for p,h in doc['source_pins'].items():assert sha(p)==h,p
    q=r['initial_projection'];d=r['omega_delta_veh_h']
    next_step=('Stop local SC12 rate/initial-cohort tuning: a real current-route information loss was corrected, '
      'but the two450s results change joint-city gain by only0.10vehh and remain wrong-sign. '
      'Keep this bounded candidate with untouched ETA and physical provenance. '
      'Use existing closed SC101/SC6 head-time curves and Omega boundary admissions to distinguish '
      'remaining discharge-timing error from realized-admission differences before another model change. '
      'Do not fit future admissions or optimize until the material whole-city response issue is bounded. '
      'Then qualify the justified composite with full AD and saved unused-state RM/city choice within600s; '
      'preserve FW5/U10, horizon450 terminalOFF, same demand/area and immutable native queue. '
      'No automatic new native, coefficient grid or push.')
    text=f'''# SC12 초기 경로 보존 — 제한된 수정·검증

Claude U7와 기존 observation_projection/physical_ramp_branches 구현을 확인했다.
현재 관측에 있는 경로를 잃는 문제를 진단 후보에서 고쳤다. 생산 설정과
실행 중인 VISSIM 동결본·큐는 변경하지 않았다.

## 바꾼 부분

정확한2400초 관측의1220012103 차량4대만 대상으로 했다. 같은 연속 정지선
큐 정의의2대와 잔여2대를 분리했다. static route31:1과 다음 connector10242가
일치하는3대는 북향을 보존한다. 경로 미확인1대는 현재2차로에서 가능한
직진·북향 안에서 기존beta를 정규화한다. 미래 차량 경로를 사용하지 않는다.

초기 큐는 직진1/북향0.5/우회전0.5에서
직진{q['queue_after']['SC12_W_SC11_to_E_SC106']:.6f}/북향{q['queue_after']['SC12_W_SC11_to_N_SC6']:.6f}/우회전0으로 바뀐다.
이동 재고7대 중 관측된2대만 북향 집계 태그를 붙인다. 다른 물리 링크의5대,
도착·저장 해제 예약2420초, 전체 재고와Ω 소속은 그대로다.
현재 관측을 읽을 때만 차량ID를 쓰며 롤아웃은 기존 집계 태그 소비기를 사용한다.
물리 provenance, movement 큐, 관측 요약, 초기 inside/outside 장부를 함께 갱신한다.
동적 이동으로 가짜 유입·유출을 추가하지 않는다.

## 검증 결과

5개 시험을 통과했다. 같은 초기 상태의 도시신호 유지/변경450초2회를 완료했다.
두 조건의RM·VSL·상한·수요는 같으며, 조건별3블록 writer와NP/NUF,
물리 수용·차량 보존, 초기 상태 불변, 예약된 태그의 실제 소비를 확인했다.

|지표|이전305|현재306|실측|
|---|---:|---:|---:|
|도시 변경−유지 Ω TTT[대·시간]|{d['old']:.4f}|{d['new']:.4f}|+5.2867|
|유지 첫150초 SC12W 북향 방출[대]|2.9101|5.0982|직접 동일 경계값 없음|
|변경 첫150초 SC12W 북향 방출[대]|0.9742|1.8509|직접 동일 경계값 없음|
|유지 SC6 직진+우회전 MAE[대/150초]|24.5067|23.8857|—|
|변경 SC6 직진+우회전 MAE[대/150초]|19.4208|19.6696|—|

초기 방향 배분 문제는 바로잡았지만 전체 손익 방향은 여전히 반대다.
SC6 일부 방출은 개선됐고 다른 조건의 오차는 소폭 커졌다. 초기4대 수정의
효과를 전체 도시부 문제 해결로 해석하지 않는다. SC12 상한·초기 재고를
추가로 미세 조정하는 탐색은 이어가지 않는다.

같은 초기화 함수를 이 후보에 사용하지 않은3300초 상태에도 적용했다.
현재 링크5대 중 알려진 북향4대를 보존했고, 대기3대·잔여2대·상류6대 및
3320초 예약을 유지했다. 이 검사는 초기화의 다른 상태 적용 확인이다.
3300초 새 제어 손익·다른seed·전체AD·새SDMPC 선택을 검증한 것은 아니다.

## 실행 기록과 한계

첫 시도는 예측 전에 deepcopy의pickle 내부 공유 구조 차이를 물리 값 차이로
오인하여 중단됐다. 실제 두runtime의 배열·재고 값 차이는0이었다.
정확한 값 비교로 고치고 object 배열도 처리한5시험을 통과한 뒤 별도v2에 실행했다.
초기 실패 로그와 tests_v2 실패 기록을 보존한다. 새native 실행이나 무조건 재시도는 없다.
v2 소유 실행session4925는exit0이며450초예측2회가 완료됐다.
각 endpoint5.65/5.85초는 전체SDMPC 계산시간이 아니다.

본선/램프5초·도시10초·150초 제어·450초 지평·말단OFF·Ω701 유지.
새계수fitting/전체AD/최적화/native/FZP스캔/push는0회다. 전체 목표는 미완료다.
다음은 기존SC101/SC6 방출 시각과실제영역 유입의차이를 사용해 남은 큰오차를
구분하는 것이다. 미래 유입값을 넣어 자율 예측 성능이라고 하지 않는다.

정본: comparison.json, unseen3300.json, tests_v3.log.
결과: E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2.
'''
    (HERE/'README.md').write_text(text,encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    entry=dict(status='complete_initial_route_pair_whole_gain_unqualified',goal_complete=False,
        updated_utc=now,previous_goal_turn='no_progress_status_reply_revalidated',
        this_goal_turn='progress_initial_composition_fix_five_tests_two450_and_unseen_initialization',
        model_delta_veh_h=d['new'],previous_model_delta_veh_h=d['old'],native_delta_veh_h=5.28666666666649,
        budget=r['budget'],tests=5,unseen_initial_state_sec=3300,unseen_forecasts=0,
        owned_forecast_process_exited=True,tool_session=4925,exit_code=0,
        output='E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2',next_step=next_step,
        source_pins={str(p):sha(p) for p in (HERE/'comparison.json',HERE/'unseen3300.json',HERE/'README.md',Path(__file__))})
    save(HERE/'completion.json',entry)
    for p in (A/'plan.json',H/'plan.json'):
        doc=read(p);doc.update(status='fw5_urban10_runtime_verified_city_gain_direction_unqualified',
            current_stage='sc12_initial306_complete',latest_stage=str(HERE/'README.md'),current_workers=[],
            goal_complete=False,updated_utc=now,last_goal_turn=entry['this_goal_turn'],next_step=next_step)
        doc['sc12_initial306']={k:v for k,v in entry.items() if k!='source_pins'}
        save(p,doc)
    print('RECORDED306: actual initial-route loss repaired; whole-city gain still unqualified; no active owned forecast')
if __name__=='__main__':main()
