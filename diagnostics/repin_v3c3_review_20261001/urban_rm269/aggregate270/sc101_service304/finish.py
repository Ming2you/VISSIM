"""Record304 without changing production or declaring the goal complete."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
OUT=Path("E:/VISSIM_analysis/20261010_sc101_service304/forecast2400")
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def main():
    assert not (HERE/"completion.json").exists()
    r=read(HERE/"comparison.json");s=read(OUT/"summary.json")
    for report in (r,s):
        for p,h in report["source_pins"].items():assert sha(p)==h,p
    improvement=100*(1-r["absolute_gain_error_new"]/r["absolute_gain_error_old"])
    next_step=("Retain SC101 candidate and FW5/urban10 as diagnostics. Do not repeat rate fitting, this pair or unchanged optimization. "
        "Use existing closed city-pair boundary/SC6 timing and stock-cost records to localize remaining whole-Omega gain error. "
        "Qualify unused-state large tradeoffs and full AD/feasible choice after a justified material correction. No automatic native or production adoption.")
    text=f"""# SC101 공급·경로·방출 상한의 결합 검증

본선·램프5초 / 도시부10초,450초 지평,말단비용OFF,Ω701 TTT를 유지했다.
짧은 셀의 내부 계산은 유지한다. 생산 코드와 실행 중 native 동결본은 변경하지 않았다.

303의 공급량·이동시간·신호등 앞 우회전·출발원별 집계 경로에,
과거1650–1950초 대기열 방출로 산정한 SC101 직진 상한2969.549→5236.479대/시를 결합했다.
새 계수 추정과 격자 탐색은 없다. 공통2400초 초기 상태에서 RM/VSL이 같은
유지/도시신호 명령으로450초씩2회 예측했다. 미래 관측을 예측 입력으로 사용하지 않았다.

|도시신호 변경−유지|303기준|304|실측|
|---|---:|---:|---:|
|SC101450초 누적 방출 차이[대]|+5.181|−6.465|−9|
|전체Ω TTT 차이[대·시간]|−2.532|−1.386|+5.287|

전체 손익 오차는7.818→6.673대·시간으로{improvement:.2f}% 줄었다.
국소 누적 방출 방향은 맞지만 전체 손익 방향은 아직 반대다.
바뀐 Ω 비용은 SC101 직진 대기 항목이며 다른 Ω 비용 변화는 사실상 없다.
전체 도시 문제 해결이나 SDMPC native 선택 개선으로 판정하지 않는다.

직진 방출[2400–2550,2550–2700,2700–2850]:
- 유지78.091/51.102/54.462대; 실측72/73/48대.
- 도시신호71.938/62.983/42.269대; 실측67/66/51대.
-2850초 직진 잔여대기:유지6.550대,도시신호13.622대.
-2850초 Ω 내부재고:유지4840.121대,도시신호4844.048대.

초기 재고·예약·수요는 동일하다.303에서 추가로 바뀐 network 필드는 직진 상한 하나다.
우회전 상한과 무신호 속성,경로와 차로,유한 수용공간을 유지했다.
물리 장부·경로 태그·실제 승인 유량·3블록writer·NP/NUF 검사를 통과했다.
수용 제약 초과는 수치오차 수준이며 초기상태 변경은0이다.
기존 경로4시험과 서비스7시험을 재사용했다. 새 AD/전체선택/native/FZP재읽기는0회다.

고정 명령 endpoint 약5초는 설정·자료읽기·최적화 시간을 제외한 값이다.
기존 본선5/도시10 전체SDMPC 선택은약244–321초,반복예산PFO2/SDMPC2이며
수렴한 최적해가 아닌 최선 관측 실행가능 명령이다. 장시간native시간 보장은 아니다.

과거 달성유량은 모든 미래 포화유량의 보장이 아니며,
native head통과수는 이후 차로변경까지 반영한 최종 경로 전수조사가 아니다.
미확인 출발원 경로에는 기존β를 명시적 사전값으로 쓴다.
이번 상태는 개발 자료이고 독립seed 검증이 아니다.

다음에는 상한을 다시 탐색하지 않는다. 기존 도시신호 쌍의 경계유입·SC6 도착시각과
항목별 비용으로 남은 큰 오차를 분리한다. 작은 속도오차나 미세한 손익 부호 때문에
전셀 재보정·계수격자를 추가하지 않는다. 전체AD/선택과 생산 반영은 별도 검증이 필요하다.

정본:comparison.json
예측:E:/VISSIM_analysis/20261010_sc101_service304/forecast2400
전체 목표는 미완료다.
"""
    (HERE/"README.md").write_text(text,encoding="utf8")
    now=datetime.now(timezone.utc).isoformat()
    entry=dict(status="complete_local_discharge_direction_improved_whole_city_gain_unqualified",
        goal_complete=False,updated_utc=now,budget=r["budget"],
        model_delta_veh_h=r["city_minus_hold_omega_veh_h"]["new"],
        previous_model_delta_veh_h=r["city_minus_hold_omega_veh_h"]["old"],
        native_delta_veh_h=r["native_city_minus_hold_omega_veh_h"],
        absolute_gain_error_improvement_percent=improvement,
        source_pins={str(p):sha(p) for p in (HERE/"comparison.json",HERE/"README.md",OUT/"summary.json",Path(__file__))},
        next_step=next_step)
    save(HERE/"completion.json",entry)
    for file in (A/"plan.json",H/"plan.json"):
        p=read(file)
        p.update(status="fw5_urban10_runtime_verified_integrated_sc101_gain_unqualified",
            current_stage="sc101_service304_complete",current_workers=[],goal_complete=False,
            last_goal_turn="progress_integrated_service_pair_without_refit",
            latest_stage=str((HERE/"README.md").relative_to(HERE.parents[4])),
            next_step=next_step,updated_utc=now)
        p["sc101_service304"]={k:v for k,v in entry.items() if k!="source_pins"}
        if "current_prediction_clock" in p:
            p["historical_prediction_clock_before277"]=p["current_prediction_clock"]
            p["current_prediction_clock"]=dict(freeway_sec=5,urban_sec=10,internal_substeps_retained=True,
                applied_scope="opt-in offline prediction and saved-state selection",native_frozen_tree_changed=False)
        save(file,p)
    print("RECORDED304; whole gain unresolved; no active worker; FW5/urban10 unchanged")

if __name__=="__main__":main()

