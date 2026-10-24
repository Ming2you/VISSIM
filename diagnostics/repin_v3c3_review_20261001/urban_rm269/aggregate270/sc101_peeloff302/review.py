"""Compare302 with completed301, using saved native caches."""
from collections import defaultdict
from datetime import datetime, timezone
import gzip, hashlib, json, pickle
from pathlib import Path
HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
OUT=Path("E:/VISSIM_analysis/20261010_sc101_peeloff302/forecast2400")
MOV="SC101_S_SC1_to_E_SC5"
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")

def witnesses(cache,position):
    tracks=defaultdict(list)
    for f in cache["frames"]:
        for r in f["rows"]:tracks[r[0]].append((f["sec"],r))
    result=[]
    for veh,track in tracks.items():
        for (t0,r0),(t1,r1) in zip(track,track[1:]):
            if r0[1]==1220011503 and r0[3]<=position and r1[1] in (10528,336) and t1-t0<=5.01:
                result.append(dict(veh=veh,lower_sec=t0,upper_sec=t1))
                break
    return result

def main():
    assert not (HERE/"comparison.json").exists() and not (HERE/"completion.json").exists()
    new=read(OUT/"summary.json")
    old=read(A/"sc15_source301/forecast2400/summary.json")
    proof=read(HERE/"evidence.json")
    prior=read(A/"sc15_source301/comparison.json")
    truth=read("E:/VISSIM_analysis/20261010_sc15_source300/completion.json")
    assert new["status"]=="complete" and new["forecasts"]==2 and new["initial_state_error"]==0
    assert new["fits"]==new["optimizer_calls"]==new["native_runs"]==new["production_changes"]==0
    pins={}
    for report in (new,proof):
        for p,h in report["source_pins"].items():assert sha(p)==h,p
        pins.update(report["source_pins"])
    from evaluation.controllers import signal_actuation_contract as signals
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    cfg,_,_=pickle.loads((A/"citysplit287/forecast2400/initial.pickle").read_bytes())
    arms={}
    for arm in ("hold","city"):
        nr,orr=new["results"][arm],old["results"][arm]
        assert nr["shared_constraints"]["feasible"] and nr["resource_max_exceedance"]<1e-7
        assert nr["writer_three_blocks"] and nr["conservation_states"]==4
        cp=Path(truth["arms"][arm]["cache"]);assert sha(cp)==truth["arms"][arm]["cache_sha256"]
        cache=json.loads(gzip.decompress(cp.read_bytes()));pins[str(cp)]=sha(cp)
        events=witnesses(cache,proof["connector"]["source_pos"])
        native=[sum(e["lower_sec"]>=s and e["upper_sec"]<=s+150 for e in events) for s in (2400,2550,2700)]
        action_folder=A.parent/"selection2400_discrete/hold" if arm=="hold" else A/"citysplit287/forecast2400/city_only"
        actions={}
        for s in (2400,2550,2700):
            p=action_folder/f"action_{s:06}.json";pins[str(p)]=sha(p)
            actions[s]=adapter.control_from_json(p,cfg,ControlAction)
        model={}
        for label,folder in (("old",A/"sc15_source301/forecast2400"),("new",OUT)):
            p=folder/(arm+".response.json.gz");pins[str(p)]=sha(p)
            response=json.loads(gzip.decompress(p.read_bytes()))
            assert response["model_constraint_coverage"]["complete"]
            rows=[t for t in response["transfers"] if t["source"]=="movement:"+MOV and t["target"]!=t["source"]]
            counts=[sum(t["vehicles"] for t in rows if s<=t["start_sec"]<s+150) for s in (2400,2550,2700)]
            red=0
            for t in rows:
                sec=t["start_sec"];block=2400+int((sec-2400)//150)*150
                frac=signals.phase_fraction(actions[block],cfg,cfg.network.urban_movements[MOV],round(sec/10))
                if frac==0:red+=t["vehicles"]
            model[label]=dict(counts=counts,accepted_during_former_full_red=red,
                mae_to_witnessed_lower_bound=sum(abs(x-y) for x,y in zip(counts,native))/3)
        assert model["old"]["accepted_during_former_full_red"]==0
        assert model["new"]["accepted_during_former_full_red"]>0
        arms[arm]=dict(old_omega=orr["omega_ttt_veh_h"],new_omega=nr["omega_ttt_veh_h"],
            right_departure=model,native_right_crossing_lower_bounds=native,native_right_witnesses=events,
            resource_max_exceedance=nr["resource_max_exceedance"],shared_feasible=True,
            writer_three_blocks=True,conservation_states=4,endpoint_wall_sec=nr["wall_sec"])
    delta=arms["city"]["new_omega"]-arms["hold"]["new_omega"]
    old_delta=prior["new_city_minus_hold_veh_h"]
    for p in (OUT/"summary.json",A/"sc15_source301/comparison.json",HERE/"evidence.json",HERE/"tests.log",
              HERE/"preflight_e.json",HERE/"run.log",OUT.parent/"source301_migration.json",Path(__file__)):
        pins[str(p)]=sha(p)
    budget=dict(fixed450=2,ad=0,optimizer=0,native=0,fzp_scans=0,new_fits=0,production_changes=0)
    report=dict(status="complete_signal_authority_corrected_city_gain_unqualified",goal_complete=False,
        arms=arms,old_city_minus_hold_veh_h=old_delta,new_city_minus_hold_veh_h=delta,
        native_city_minus_hold_veh_h=prior["native_city_minus_hold_veh_h"],
        gain_direction_correct=delta*prior["native_city_minus_hold_veh_h"]>0,
        initial_state_error=0,existing_rate_veh_h=proof["existing_capacity_veh_h"],source_pins=pins,budget=budget,
        limitations=["Geometry and past RED crossings establish absent source signal authority, not absence of downstream yielding.",
            "Existing180.45veh/h service remains an approximation; no gap or lane-level FIFO was added.",
            "No source/lane-specific turning fractions were changed in this step.",
            "Native5s crossing counts are lower bounds, not a complete census.",
            "Whole-city gain remains opposite; do not call this a gain calibration success.",
            "No new held-out-state full-optimizer or native qualification has been done."])
    save(HERE/"comparison.json",report)
    rows=[]
    for arm,row in arms.items():
        fmt=lambda xs:" / ".join(f"{x:.2f}" for x in xs)
        rows.append(f"| {arm} | {fmt(row['right_departure']['old']['counts'])} | "
                    f"{fmt(row['right_departure']['new']['counts'])} | {fmt(row['native_right_crossing_lower_bounds'])} |")
    doc=f"""# SC101 신호 전 우회전의 잘못된 신호 대기 제거(302)

**물리적인 신호 연결 오류를 확인하고 오프라인 후보에서 수정했다. 전체 도시 손익 예측은 아직 반대다.** 계수를 새로 적합하지 않았다.

## 근거와 변경

원래 망의 RD1014:3은1220011503의1차로193.005m에서10528→336으로 분기한다. SC101의 모든 신호는206.275–209.188m에 있어 분기 뒤다.10528·336에는 신호가 없다. 기존 모델은 이 우회전에 SC101_p1(SG4·8)을 붙여 적색 동안 서비스를0으로 만들었다.

과거900–2395.1초의 저장 위치 캐시에서 분기 전·후를5초 이하 간격으로 확인했다. 통과 구간 전체가SG8 적색인 차량17대, 녹색33대, 전환을 포함한2대가 있다. 미래 검증 자료로 신호를 추론한 것이 아니다. Claude STAGE3/U7는 기존 SC1/SC105 위상 수정과 공급 타이밍 문제를 다루지만 이번10528 수정은 포함하지 않았다.

기존 phase-authority 설정 직후, 서비스 자원 생성 전에 **해당 movement의 unsignalized만True**로 설정했다. 원래 위상 이름·경로·회전비·저장공간·초기 상태는 보존했다. 방출률 **{proof['existing_capacity_veh_h']:.5f}대/시간**도 동일하다. 하류10529는 TWOYIELDSONE 양보 관계이며 이를 무제약 흐름으로 취급하지 않는다. 모델은 현재 기존 유한 서비스와 수용공간으로 근사하고, 횡방향 gap을 새로 계산하지는 않는다.

## 동일 상태의450초 비교

| 우회전 방출 [대/150초, 세 구간] | 기존301 | 수정302 | native 관측 하한 |
|---|---|---|---|
{chr(10).join(rows)}

기존 신호 적색10초 블록에서도 새 모델은 유한한 우회전 방출을 낸다. 초기 대기 해소 후에는 예상 도착량에 제한되어 방출 상한만큼 계속 나가지 않는다. 초기 대기 해소 뒤 방출이 감소하는 현상은 잘못된 적색 신호만으로 설명되지 않는다. native 통과량은 불완전한 관측 하한이므로 이를 완전한 방출량 정합으로 해석하지 않는다. 기존의 공통 회전비가 원천별 경로를 구분하지 않는 문제는 남아 있다.

도시신호−유지 Ω TTT: 기존 **{old_delta:+.5f}**, 수정 **{delta:+.5f}**, native **{prior['native_city_minus_hold_veh_h']:+.5f}대·시간**. 전체 손익 오차를 개선했다고 주장할 크기가 아니며, SC101 직진 방출량은 두 조건 모두 이전과 같다.

초기 상태 차이0, 동일 수요와 RM/VSL/NP·NUF 명령,3블록 writer/변경폭, 두 조건 각각4개 상태 보존 장부, 수용량과 NP/NUF 제약을 통과했다. 구조/실제 신호 시계 관련4시험도 통과했다. endpoint 계산은{arms['hold']['endpoint_wall_sec']:.2f}/{arms['city']['endpoint_wall_sec']:.2f}초이며 전체SDMPC 시간이 아니다. 새 최적화·AD·native·FZP 스캔·계수 적합·생산 적용·push는0회다.

## 파일 위치와 남은 작업

첫 준비는 C드라이브 공간 부족으로 예측 시작 전에 실패했다(run.log). 실패 파일은 보존했다. 완료된301 출력51개/약11MB를 E로 복사하고 파일별SHA256을 확인한 뒤 C를 비웠으며, 기존 경로는 junction으로 유지했다. 영수증은 E:/VISSIM_analysis/20261010_sc101_peeloff302/source301_migration.json이다. 새 예측은 E:/VISSIM_analysis/20261010_sc101_peeloff302/forecast2400이며, 완료 예측을 재실행하지 않았다. 향후 큰 진단 출력도 E를 쓴다.

첫 감사 audit.log는 실제 문자열 SG번호를 정수로 기대한 검사 실패다. 원본 형식에 맞춘 audit_v2.log가 정본이며 두 로그를 보존했다.

다음에는 이미 확보한 과거 원천1086/1087 경로 증거를 사용해, 같은 부모 도착 재고 안에서 원천별 회전 태그를 보존할 수 있는지 검토한다. 미해결22대를 임의로 확정하지 않고, 수요나 초기 재고를 늘리거나 검증 미래의 차량ID를 넣지 않는다. 손익을 바꾸기 위한 추가 방출률 격자는 수행하지 않는다. 현재 native 큐와 동결본은 수정하지 않았다.
"""
    (HERE/"README.md").write_text(doc,encoding="utf8")
    complete=dict(status=report["status"],goal_complete=False,
        previous_goal_turn="progress_sc15_source301_completed",
        current_goal_turn_classification="progress_verified_physical_signal_fix_and_two_autonomous_forecasts",
        source_pins={str(p):sha(p) for p in (HERE/"comparison.json",HERE/"README.md",Path(__file__))},
        output=str(OUT),budget=budget,
        next_step="Retain source/lane-specific downstream aggregate route tags using past support with unresolved outcomes explicit; no further service-rate fitting.",
        updated_utc=datetime.now(timezone.utc).isoformat())
    save(HERE/"completion.json",complete)
    rel=(HERE/"README.md").relative_to(ROOT).as_posix()
    for parent in (A,A.parent):
        p=parent/"plan.json";plan=read(p)
        plan.update(status="fw5_urban10_runtime_verified_sc101_signal_authority_corrected_city_gain_unqualified",
            current_stage="sc101_peeloff302_complete_not_gain_qualified",latest_stage=rel,current_workers=[],
            goal_complete=False,next_step=complete["next_step"],last_goal_turn=complete["current_goal_turn_classification"],
            updated_utc=complete["updated_utc"],large_diagnostic_output_root="E:/VISSIM_analysis",
            sc101_peeloff302=dict(completion=(HERE/"completion.json").relative_to(ROOT).as_posix(),
                completion_sha256=sha(HERE/"completion.json"),output=str(OUT),budget=budget))
        save(p,plan)
        readme=parent/"README.md";previous=readme.read_text(encoding="utf8")
        readme.write_text("# 최신: SC101 신호 전 우회전 정합(302)\n\n"
            "분기193m 뒤에206–209m 신호가 있는데 모델은 우회전에도 신호를 걸고 있었다. "
            "과거 적색 통과17대로 확인하고, 동일 방출률/재고/수용을 유지한 후보에서 신호 제한만 제거했다. "
            f"두450초 예측의 도시−유지 Ω TTT는{delta:+.5f}, native+5.28667대·시간으로 아직 반대다. "
            "전체 이득 검증 완료가 아니며 다음은 원천별 집계 경로 태그다. 큰 출력은 E로 전환했다. "
            "상세: "+rel+"\n\n---\n\n"+previous,encoding="utf8")
    print("COMPLETE302",old_delta,delta,"native",prior["native_city_minus_hold_veh_h"])
    for arm,row in arms.items():print(arm,row["right_departure"],"native lower",row["native_right_crossing_lower_bounds"])
    print("verified forecast pins",len(new["source_pins"]),"goal remains active")

if __name__=="__main__":main()

