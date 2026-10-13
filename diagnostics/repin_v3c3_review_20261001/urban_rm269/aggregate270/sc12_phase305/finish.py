"""Record bounded305 work and the observed initial-route issue."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
def main():
    assert not (HERE/"completion.json").exists()
    r=read(HERE/"comparison.json");projection=read(HERE/"current_projection.json")
    for doc in (r,projection):
        for p,h in doc["source_pins"].items():assert sha(p)==h,p
    next_step=("Use the existing Claude U7/current-route projection mechanisms to preserve the known current SC12W route/lane composition in initial queues and pending arrivals. "
        "Verify raw2400 records, per-link provenance and existing ETA before changing only the supported subset; unknown routes retain an explicit prior. "
        "Do not retag all7 origin residual vehicles from the4 observed terminal-link vehicles. "
        "Keep shared1707.1725 service as a bounded diagnostic, no further rate search. "
        "Compare one bounded composite hold/city pair then unused-state/AD/controller choice as justified; keep horizon450 terminalOFF FW5/U10 and frozen native queue.")
    text="""# SC12 서측 신호·방출 상한과 초기 경로 배분

이전304턴은 실제450초 예측2회를 완료한 진행이었다.
이번에는 기존 Claude U7/C3 기록,닫힌 MER/LDP,저장된5초 위치 캐시 및
예측 응답을 재사용했다. 새 VISSIM·FZP 스캔·전체 최적화는 하지 않았다.

## 확인한 것

북측 도로에서 확인된 서측 출발 차량을 실제 head 기록과 결합했다.
유지37대는 모두2차로 head50201이며33대GREEN/4대AMBER였다.
도시22대 중20대GREEN,1대는GREEN→RED 전환 직후,1대는ID/시각 결합 미확인이다.
단순히 잘못된 현시로 북향 movement를 연결한 것이 부족 유량의 주원인이라는 근거는 없다.
5초 위치 증거와 정지선 계수의 경계·미확인 한계는 그대로 유지한다.

기존960대/시는 과거에 경로가 확인된 일부 통과수/전체GREEN시간이다.
이는 불완전한 평균 달성유량이며 포화 방출 상한과 동일한 추정량이 아니다.
과거1892초 녹색 시작 전에 정지한 연속9대의 head 통과를 확인했다.
직진1대가 먼저 지나고 북향8대가 뒤따랐다. 시작 손실과 직진 서비스 시간을
모두 분모에 넣은 북향 유효율은1707.1725대/시다.
전체 head 예산을 북향에 몰아주거나 미래 검증 통과수로 계수를 맞추지 않았다.

순수 북향 연속 대기열만 요구한 첫 검사는 적격자료가 없었다.
직진 선두도 같은 물리 head를 쓰므로 이를 제외할 수 없다는 증거를 보고,
그 시간까지 포함한 공유 head 대기 차량군 검사를 따로 보존했다.
적격 차량군은1회뿐이다. 보편적인 포화유량이나 일반적인 공유차로 모형의
식별 완료로 해석하지 않는다. 추가 계수 탐색은 하지 않는다.

## 한 후보의 실제 전체 예측

304조합에 북향 두 별칭의 공유 서비스 한도만 바꿨다.
공통 초기2400초,동일 RM/VSL,도시신호 유지/변경450초씩2회다.
물리 저장공간·실제 수용·현재 경로·3블록writer·NP/NUF·초기 상태 불변을 확인했다.
별칭 두 개가 각각 별도 예산을 얻지 않고 한 서비스 예산을 공유한다.
3개 시험과 각 예측45구간의 실제 공유 서비스 증거를 확인했다.

|지표|304|305|실측|
|---|---:|---:|---:|
|유지 SC6 직진+우회전[대/150초]|59.47/69.69/57.60|59.47/71.99/60.03|89/92/84|
|도시 SC6 직진+우회전[대/150초]|54.58/44.06/79.80|54.58/44.06/84.22|92/39/100|
|도시−유지 Ω TTT[대·시간]|−1.3860|−1.2851|+5.2867|
|SC6 정지선 시점 가중 차이[대·시간]|+1.2156|+1.3165|+2.3460~+2.3877|

SC6 방출 반응은 개선됐지만 전체 손익 방향은 아직 반대다.
정지선 시점 가중치는 Ω 경계 비용과 같지 않으므로 합산해 설명하지 않는다.
첫150초 서측 유입의 부족은 상한 증가로 거의 변하지 않았다.
그 구간은 준비 재고와 초기 경로 배분을 먼저 확인해야 한다.

## 다음 수정의 구체적 근거

정확한2400초 초기 관측의1220012103에는4대가 있었고,
그중3대는 현재 static route31:1/NextLink10242로 북향임을 독립적으로 확인했다.
모델은 해당 링크의 대기2대/이동2대 총량은 유지하지만 대기2대를
직진1.0/북향0.5/우회전0.5로 나누며,SC11_to_SC12의 초기 도착에는 경로 태그가 없다.
head_phase 옵션이 켜져 있어도 명시적 차로 적용 범위에서 이 링크가 빠져
검지기 가중치 배분으로 돌아가는 코드 경로를 확인했다.

이는 미래 관측으로 만든 단서가 아니라 현재 관측에 이미 있는 정보를
초기 집계 상태에서 잃는 문제다. Claude U7의 구성 오배정과 같은 종류다.
단,4대 관측으로 origin의 전체 이동7대를 모두 북향으로 바꾸면 안 된다.
현재 물리 소속·차로·기존 도착 예약시각을 지키면서 확인된 몫만 보존하고,
경로 미확인 차량은 명시적 사전값으로 남겨야 한다.
이후 제한된 비교와 미사용 상태에서 큰 손익을 검증한다.

본선/램프5초·도시10초·제어150초·지평450초·말단OFF·Ω701·수요는 그대로다.
순수 예측 endpoint4.62/4.77초는 전체 SDMPC 시간으로 부르지 않는다.
생산 변경·native·push·전체AD·새 최적화는0회다. 전체 목표는 미완료다.

정본: assessment.json, past_shared_prefix_support.json, comparison.json,
current_projection.json. 실행: E:/VISSIM_analysis/20261010_sc12_phase305/forecast2400.
"""
    (HERE/"README.md").write_text(text,encoding="utf8")
    now=datetime.now(timezone.utc).isoformat()
    entry=dict(status="complete_service_pair_initial_route_projection_issue_confirmed",goal_complete=False,
        updated_utc=now,previous_goal_turn="progress_integrated_SC101_pair304",this_goal_turn="progress_phase_audit_service_pair_and_current_route_root_cause",
        budget=r["budget"],tests=3,past_service_support_windows=1,
        model_delta_veh_h=r["omega_delta_veh_h"]["new"],previous_model_delta_veh_h=r["omega_delta_veh_h"]["old"],
        native_delta_veh_h=r["native_omega_delta_veh_h"],owned_forecast_process_exited=True,
        source_pins={str(p):sha(p) for p in (HERE/"assessment.json",HERE/"comparison.json",HERE/"current_projection.json",HERE/"README.md",Path(__file__))},
        next_step=next_step)
    save(HERE/"completion.json",entry)
    for p in (A/"plan.json",H/"plan.json"):
        doc=read(p)
        doc.update(status="fw5_urban10_runtime_verified_initial_route_projection_unqualified",
            current_stage="sc12_phase305_complete",latest_stage=str(HERE/"README.md"),
            current_workers=[],goal_complete=False,updated_utc=now,
            last_goal_turn=entry["this_goal_turn"],next_step=next_step)
        doc["sc12_phase305"]={k:v for k,v in entry.items() if k!="source_pins"}
        save(p,doc)
    print("RECORDED305; completed two forecasts, next current-route initialization; no active owned worker")
if __name__=="__main__":main()

