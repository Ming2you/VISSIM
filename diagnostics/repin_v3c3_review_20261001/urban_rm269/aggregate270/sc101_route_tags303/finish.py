"""Record completed303 and the evidence-based integration decision."""
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
A=HERE.parent;ROOT=HERE.parents[4]
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main():
    assert not (HERE/"completion.json").exists()
    r=read(HERE/"comparison.json");support=read(HERE/"support.json")
    for p,h in r["source_pins"].items():assert sha(p)==h,p
    totals={mode:{arm:sum(b["accepted"] for b in row[mode]["blocks"])
                  for arm,row in r["conditional_service_replay"].items()}
            for mode in ("base","past_supported_capacity")}
    native={arm:sum(b["native_count"] for b in row["base"]["blocks"]) for arm,row in r["conditional_service_replay"].items()}
    delta=lambda v:v["city"]-v["hold"]
    assert delta(totals["base"])>0 and delta(totals["past_supported_capacity"])<0 and delta(native)<0
    rows=[]
    for arm,row in r["arms"].items():
        fmt=lambda v:" / ".join(f"{x:.2f}" for x in v)
        for kind,entry in row["route_departure"].items():
            rows.append(f"| {arm} {kind} | {fmt(entry['old'])} | {fmt(entry['new'])} |")
    doc=f"""# SC15 합류 후 원천별 집계 회전 태그(303)

과거에 확인된 유입원별 회전 정보를 같은 부모 도착량 안에 유지했다. 차량 수·수용공간·초기 재고는 늘리지 않았다. **두 자율450초 예측을 통과했지만 전체 도시 손익 방향은 아직 틀렸다.**

## 기존 자료와 표현

Claude U7은 초기 anchor 잔차에 경로/차로 태그를 붙이는 방식을 설명한다. 이번에는 그 단일 부모 재고 원칙과 기존 split_tagged_arrival 호출을 사용하며, 새로 수용된 SC15 북행 유입만 대상으로 한다. 원천1086/1087은 RD1014 뒤로 다른 차로에 합류하므로 RD1014의 공통 회전비율을 무조건 적용하지 않는다.

900–2100초에 출발하고2395.1초까지 추적한 과거 자료의 범주는 다음과 같다.

| 원천 | 직진 확인 | 우회전 확인 | 좌회전 확인 | 미확인 |
|---|---:|---:|---:|---:|
|1086|56|0|9|4|
|1087|14|31|1|22|

비율은 전체 관측 원천 대수69/68로 나눈다. 미확인 몫을 제거하고 관측된 차량만으로 다시 정규화하지 않는다. **미확인 몫은 기존β로 배분한다는 모델링 가정**을 별도로 유지했다. 관측 누락이 무작위라는 증거는 없고, 이 가정을 확정된 회전확률이나 실제 차량 목적지라고 부르지 않는다.

미확인분에 기존β를 사용한 유효 비율은1086의 직진/우회전/좌회전이 약85.35/0.25/14.40%,1087은43.97/47.01/9.02%다. 모두 기존 과거자료의 식별 범위 안이지만 유일하게 식별된 값은 아니다. seed·시각·명령에 붙는 보너스가 없고 검증 미래의 차량ID도 사용하지 않는다.

태그는 원천별·도착10초 구간별4개 범주로만 저장한다. 새 차량 재고가 아니며 기존 arrival/storage 버퍼가 실제 여행시간·수용량을 소유한다. 초기 경로 태그가 같은 시각에 있어도 그 몫을 다시 나누지 않는다.

## 보존 및 자율 예측

두 조건 모두 새 북행 수용량 **{r['arms']['hold']['tagged_amount_veh']:.5f}대**가 태그와 일치하고, 매10초 원천 수용량은 이전302와 동일했다. 미확인11.53775대도 별도로 남겼다. 지평 말단까지 모두 도착했으며 예정량=도착량+미도착 태그 보존을 세 제어 블록에서 확인했다. 부모 재고만 차량 장부에 들어간다.

| 방출 [대/150초, 세 구간] | 기존302 | 태그303 |
|---|---|---|
{chr(10).join(rows)}

도시신호−유지 전체 Ω TTT는 **{r['old_city_minus_hold_veh_h']:+.5f}→{r['new_city_minus_hold_veh_h']:+.5f}대·시간**, 실측 **{r['native_city_minus_hold_veh_h']:+.5f}**다. 차이는 약0.091대·시간으로 작다. 경로 구분 오류를 줄였다고 해서 전체 도시 이득을 검증했다고 하지 않는다.

초기 상태 차이0, 동일 수요/Ω701/450초 지평/말단비용OFF, 같은 RM·VSL·NP/NUF 명령,3블록 writer와 변경폭, 상태4개의 차량 장부, 수용량/NP·NUF 제약을 모두 확인했다.4시험은 부모량 보존, 기존 초기 태그 공존, 과잉태그/미래자료 거부, active derivative 보존을 다룬다. 마지막은 작은 수치형 시험이며 **전체AD·최적화 동등성 검증은 아니다**. 실제 endpoint는약5초, 새 SDMPC·native 런은0회다.

## 다음 조합을 선택한 근거

현재 수정된 도착량을 사용해 기존 SC101 상한과 이미 과거1650–1950초에 얻은 상한5236.48대/시간을 국소적으로 재생했다. 새 방출률은 맞추지 않았다. 기존 상한으로 실제 예측의 매10초 재고·방출을1e−7 이내로 재현한 뒤 상한 하나만 바꿨다.

| 조건부 누적 SC101 직진 방출 [대/450초] | 현재 상한 | 기존 과거 지원 상한 | 관측 head |
|---|---:|---:|---:|
|유지|{totals['base']['hold']:.3f}|{totals['past_supported_capacity']['hold']:.3f}|{native['hold']}|
|도시신호|{totals['base']['city']:.3f}|{totals['past_supported_capacity']['city']:.3f}|{native['city']}|
|도시−유지|{delta(totals['base']):+.3f}|{delta(totals['past_supported_capacity']):+.3f}|{delta(native):+.3f}|

누적방출 방향은 과거 지원 상한에서 실측과 같아진다. 다만 일부150초 방출 오차는 커진다. 사용자 기준에 따라 모든 구간 궤적을 맞추는 대신 **누적 방출과 제어 손익 방향**을 우선해, 현재 경로/공급 수정과 이 기존 상한을 통합한 전체망 후보를 다음 한 쌍의 예측으로 확인할 근거가 있다고 판단했다.

이 표는 예측 도착량·다른 수용 수요를 고정한 조건부 계산이다. 회랑 피드백을 다시 풀지 않았고 head 통과량은 최종 회전량과 완전히 같지 않다. 따라서 이 표만으로 전체 Ω TTT 또는 native 개선을 선언하지 않는다. 지평 확대·말단비용·새 상한 격자·전체 VISSIM 재실행은 이번에 수행하지 않았다.

## 출력과 실행 범위

결과는 E:/VISSIM_analysis/20261010_sc101_route_tags303/forecast2400이다. C가 다시 가득 차 완료된 citysplit287 예측 출력59개/약496MB를 E로 옮겼다. 복사·이동 후 SHA256을 모두 검증하고 기존 경로는 junction으로 유지했다. 코드·실행 중인 큐·동결본은 그대로다. 영수증은 같은 E 결과 상위의 citysplit287_migration.json이다.

이번 단계의 실행은 자율450초2회와 조건부 국소재생4회, 신규 서비스 적합/전체AD/최적화/native/FZP스캔/생산 적용/push0회다. 목표는 미완료다.
"""
    (HERE/"README.md").write_text(doc,encoding="utf8")
    next_step=("Evaluate one integrated450s hold/city pair with the already past-supported SC101 service ceiling "
               "and303 supply/route corrections; prioritize cumulative discharge and Omega gain direction, "
               "not per-bin MAE. No new rate fitting or parameter grid. Then qualify AD/feasible selection if justified.")
    result=dict(status=r["status"],goal_complete=False,
        previous_goal_turn="progress_sc101_peeloff302_complete",
        current_goal_turn_classification="progress_source_route_tags_and_directional_integration_evidence",
        budget=r["budget"],conditional_totals=totals,native_head_totals=native,
        source_pins={str(p):sha(p) for p in (HERE/"comparison.json",HERE/"README.md",Path(__file__))},
        next_step=next_step,updated_utc=datetime.now(timezone.utc).isoformat())
    save(HERE/"completion.json",result)
    rel=(HERE/"README.md").relative_to(ROOT).as_posix()
    for parent in (A,A.parent):
        p=parent/"plan.json";plan=read(p)
        plan.update(status="fw5_urban10_runtime_verified_source_route_tags_city_gain_unqualified",
            current_stage="sc101_route_tags303_complete_integration_warranted",latest_stage=rel,current_workers=[],
            goal_complete=False,next_step=next_step,last_goal_turn=result["current_goal_turn_classification"],
            updated_utc=result["updated_utc"],large_diagnostic_output_root="E:/VISSIM_analysis",
            sc101_route_tags303=dict(completion=(HERE/"completion.json").relative_to(ROOT).as_posix(),
                completion_sha256=sha(HERE/"completion.json"),output="E:/VISSIM_analysis/20261010_sc101_route_tags303/forecast2400",
                budget=r["budget"]))
        save(p,plan)
        p=parent/"README.md";previous=p.read_text(encoding="utf8")
        p.write_text("# 최신: 원천별 집계 경로 태그(303)\n\n"
            "두 원천의 새 북행57.115대를 같은 부모 도착 재고 안에 경로별로 유지했고 미확인 몫은 별도로 기록했다. "
            "초기재고·수요·수용·차량장부와 수치형 미분 시험을 통과했다. 전체 Ω 도시−유지는−2.53158, "
            "native+5.28667대·시간으로 아직 반대다. 기존 과거 SC101 상한과의 조건부 조합은 누적방출 손익 방향을 "
            "맞춰 다음 제한적 전체망 조합 검증 근거가 생겼다. 새 계수 격자 탐색은 하지 않는다. 상세: "+rel+"\n\n---\n\n"+previous,encoding="utf8")
    print("COMPLETE303",totals,"native",native,"goal remains active")

if __name__=="__main__":main()

