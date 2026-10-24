"""Record completed REVIEW256 evidence before freezing the launch tree."""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[2]
readme = here / 'README.md'
text = readme.read_text(encoding='utf-8-sig').split('## 진행 및 남은 검증')[0]
text += '''## 완료된 실제 VISSIM 검증

두 조건 모두3600초 정상 완료 후 소유 프로세스가 종료됐다.
3150초 이전2,540,359개 FZP행과3150초 전체 차량 상태는 기존 런과 정확히 같다.
10480만 hold0/0/2초 대 release2/4/6초로 바꾸었으며 다른 명령은 동일하다.
모든 대상SG의 native LDP와 VSL 적용 readback/명령표 검증을 통과했다.
LSA 누락은 기존 승인된 LDP 대체를 적용했다.

| 3600초까지 지표 | hold | release | 차이 |
|---|---:|---:|---:|
|Ω TTT [대·시간]|2998.85186|2996.21486|−2.63700|
|동측 본선 TTT|805.35222|804.80106|−0.55117|
|서측 본선 TTT|621.68462|622.46968|+0.78506|
|관측된 Ω 외부 TTT|1194.78850|1196.00033|+1.21183|
|Ω 정상 유출 사건(5초 표본 추정)|24353|24444|+91|
|Ω 잔여 차량|3875|3782|−93|
|native 차로 변경 실패 삭제|157|155|−2|
|native 총시간(미삽입 대기 포함)|8279.17663|8277.96446|−1.21217|
|종료 미삽입 차량|9409|9411|+2|

실제 마지막3595.1초에서124번 정지차량33→0대,10483 재고47→1대,
10480 재고22→3대로 감소했다. 삭제 증가로 얻은 개선은 아니다.
외부 체류와 미삽입 대기는 조금 악화했으며 이 비용을 숨기지 않는다.
공통 과거 이후450초의 차이이며 전체9000초 개선으로 확대하지 않는다.

두 런의 VISSIG_Controller.dll.err는 모두 COM 미터SC9101–9108에
native signal program이 없다는 동일8개 메시지다. 오류가 전혀 없는 런으로
표현하지 않는다. 해당SG의 실제 전환은 native LDP와 적용 검증으로 확인했다.
기존 routing/travel-time-section 경고 및 차량 삭제도 원자료에 남겨 두었다.

근거: analysis/summary.json, analysis/{hold,release}/execution.json,
queue_trace.csv, area_metrics.json 및 errors.json. native_closure.json.

![공유 차로와 진출로의 실제 재고 반응](analysis/spillback_response.png)

## 모델·선택 결과와 한계

모델의 완화 이득5.10662대·시간은 실측2.63700보다 크다. 실제 release에서는
10483 재고가 일시적으로 약48대까지 늘었다가 회복하지만 모델은 너무 일찍
회복한다. 이번 채택 범위는 누락된 공유 차로 차단과 제어 방향이며,
이득 크기 또는 모든 상태의 보정 완료가 아니다.

3150초 상태에서 정본 SDMPC213축 AD(대체축0)와 writer까지 검증했다.
10480은 직전 실제0초에서 예측 녹색2/4/6초를 선택했다. 최종 명령은
N_P·N_UF 제약과 CSV 바인딩을 통과했다. 이 전체 도시 신호+RM 계획의
예측 Ω TTT는483.99394→476.58813이다. 위 native 두 런은10480만 분리했으므로
전체 선택 계획의 실제 이득으로 해석하지 않는다.

## 후속9000초

next9000_plan.json의 새 출력에 한 번 실행한다. 원래80–90망·seed29·수요·
Ω TTT 목적함수·150초 갱신·450초 예측·fixed90 VSL 규약은 유지한다.
기존 STOP과 결과를 보존한다. 새 모델만 불변 실행본으로 고정한 뒤
green·offset·8개RM을 폐루프 선택한다. 추가 후보 sweep·push는 하지 않는다.
실제 시작/완료 여부는 next9000_plan.json과 새 출력의 native_status.json을 따른다.
'''
readme.write_text(text, encoding='utf-8')
plan_path = here / 'next9000_plan.json'
plan = json.loads(plan_path.read_bytes())
plan.update(status='READY_TO_FREEZE', native_pair_passed=True,
            production_selection_passed=True, native_delta_omega_veh_h=-2.637,
            model_delta_omega_veh_h=-5.10662102,
            overall_gain_qualified=False,
            adoption='Missing shared-lane receiving mechanism and control direction; recovery remains too early.',
            common_native_notice='SC9101..9108 have no native signal program; COM/LDP transitions independently passed.')
plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
headline = ('CURRENT REVIEW256 SHARED-LANE SPILLBACK FIX VALIDATED; READY TO FREEZE/RERUN: '
 'diagnostics/repin_v3c3_review_20261001/spillback256/README.md. '
 'Old233/235fixed90 stopped7959,owned49636/22764closed,STOPpreserved. '
 '10480RED->124lane1queue->10483blocked->Eastspillback proven. Existingpreheadcapacitywasalreadycorrect;addedopt-in124sharedreceiving in2existingmodules,noFD/objective/demandchange. '
 '6tests,masschecksPASS. Two3600native replayscomplete/closed;prior2540359FZProws+3150recordsEXACT;allSG LDP/VSLverified. '
 '10480onlyrelease2/4/6 vs0/0/2:124stopped33->0,10483N47->1,OmegaTTTdelta-2.637vehh;deletions157->155,normalexits+91,externalTTT+1.2118,nativeincluninsert-1.2122. '
 'Modeldelta-5.1066 overstates/recovers tooearly:NOTfullgainqualified. Full213axisSDMPC3150feasible/writerPASS,chose10480[2,4,6],noADfallback. '
 'New9000planned D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000,freezeE20261005_shared124;statusnext9000_plan.json. PreserveallSTOP/no push.')
for name in ('AGENTS.md','CLAUDE.md'):
    path = root / name
    original = path.read_text(encoding='utf-8-sig')
    assert original.startswith('CURRENT REVIEW256 ')
    path.write_text(headline+'\n'+original.split('\n',1)[1], encoding='utf-8')
print('REVIEW256 evidence recorded; ready to freeze')
