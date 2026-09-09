# 본선 전체 off-ramp 비율 0.2의 출처와 첫 150초 유량 차이

현재 네 그룹의 `off_ramp_split_ratio=0.2`는 Ver2의 정적 경로 가중치에서 나온 값이 아니다. vendor의 합성 NumSim 기본 설정을 상속한다. 계산식에서 off/through 분모를 잘못 바꿔 쓴 오류는 확인되지 않았다. **Ver2 경로 prior와의 차이는 실재하지만, 현재 한 그룹·한 셀 모델에 native 비율을 대입하는 것만으로 올바른 물리 모델이 되지는 않는다.** 생산 파일과 활성 런 입력은 변경하지 않았다.

`vendor/NumSim-mine/src/config/default.yaml:163–167`이 네 값을 0.2로 정의한다. 같은 파일 303–305행은 2026-06-30의 **off-ramp split 0.2 합성 plant에서 MFD setpoint를 재보정**했다고 설명한다. 따라서 그 주석은 비율 자체를 Ver2 관측으로 추정했다는 근거가 아니다. 190–191행의 과거 0.06→0.4 설명은 현재 0.2와도 다르므로 현재값의 실험 이력을 확정하는 근거로 쓰지 않았다. Git에서 이 다섯 줄은 vendor를 처음 동봉한 `c8cf9d4c54340a7ed79e95dd9084115e9055976b`(2026-08-05)부터 존재한다. `state.py:361`의 dataclass 기본 0.06은 실제 YAML 로딩에 가려진다.

정본 adapter의 `build_config`는 7530행에서 vendor YAML을 선택하고 7669–7688행에서 flagship·calibration·canonical parameters·tuning을 순서대로 적용한다. 현재 β0 full config, parameters, calibration/override에 이 비율 키가 없으며 **실제 `build_config` 호출 결과 네 값 모두 0.2**를 다시 확인했다. 별도의 NumSim 시나리오 override 함수(`models/demand.py:143–154`)는 현재 adapter/runtime 경로에서 호출하지 않는다.

원본은 `network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx`, SHA256 `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`이다. 아래 가중치는 동일 decision의 signal+direct+through 전체를 분모로 삼는다. `direct/(signal+direct)`라는 다른 비율과 구분했다.

| 모델 그룹 | decision | signal 가중치 | direct 가중치 | through 가중치 | eligible decision cohort의 total off prior | 현재 모델 |
|---|---:|---:|---:|---:|---:|---:|
| OR_F_E | 1130 | 1.6 | 4 | 8 | 5.6/13.6 = 0.411765 | 0.2 |
| OR_D_E | 1131 | 4 | 3 | 8 | 7/15 = 0.466667 | 0.2 |
| OR_D_W | 1132 | 3 | 3 | 10 | 6/16 = 0.375000 | 0.2 |
| OR_F_W | 1133 | 1 (빈 값 기본) | 3 | 8 | 4/12 = 0.333333 | 0.2 |

1133-2의 XML `relFlow=""`는 0으로 해석하지 않았다. 설치된 **VISSIM 2020 공식** `C:\Program Files\PTV Vision\PTV Vissim 2020\Doc\Eng\attribute.xlsx`, `Attributes` 시트 1777행은 `VehicleRouteStatic / RelFlow / TimeInterval / DefaultVal=1`을 명시한다. 문서 SHA256은 `139705be4bac9ac41e88c9c201a8704fb37f0631834dd49d546f57aa37e8c57e`이다. 기존 `offramp_routing.py:59`와 `resolve_lane_routes.py:92`의 빈 값 기본 1 규칙이 이 공식 자료와 일치한다. 이것은 로드된 런에서 COM `RelFlow(1)`을 직접 읽은 증거와는 구분한다.

| decision-route | 종류 | 시작 링크부터 목적 링크까지의 전체 경로 |
|---|---|---|
| 1130-1 | signal | 74 → 10699 → 2 → 10643 |
| 1130-2 | through | 74 → 10699 → 2 |
| 1130-3 | direct | 74 → 10699 → 2 → 10682 → 121 → 10773 → 123 |
| 1131-1 | through | 2 → 10613 → 119 → 10702 → 24 |
| 1131-2 | signal | 2 → 10481 → 127 |
| 1131-3 | direct | 2 → 10613 → 119 → 10483 → 124 → 10775 → 125 |
| 1132-1 | direct | 26 → 10479 → 125 |
| 1132-2 | signal | 26 → 10491 → 129 → 10777 → 127 |
| 1132-3 | through | 26 → 10771 → 120 |
| 1133-1 | direct | 120 → 10645 → 123 |
| 1133-2 | signal | 120 → 10638 → 70 → 10776 → 126 |
| 1133-3 | through | 120 |

1130-1의 10643은 `destLink`이며 `linkSeq`만 검색하면 누락된다. 모든 raw `relFlow`, route ID, destination position, 정확한 출처 파일/길이/hash는 `total_offramp_ratio_audit.json`에 보존했다. 네 decision은 모두 `allVehTypes=true`, `combineStaRoutDec=true`, `routeChoiceMeth=STATIC`이다. Native는 relative weight 합을 전체로 정규화한다. 또한 같은 링크에서 앞선 route가 끝나고 다음 decision이 이어지면 조건에 따라 다음 route까지 조합해 일찍 선택한다. [PTV 정적 경로 설명](https://cgi.ptvgroup.com/vision-help/VISSIM_11_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_statische_Routen_Attr.htm), [PTV 2020 decision/combination 설명](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_statische_RoutenEntsch_Attr.htm).

따라서 **동일 시간창의 모든 본선 차량**이 위 표의 동일 모집단인 것은 아니다. E의 1130은 chain 35.478m, 1131은 5055.097m에 있다. 1130-through는 link2의 2268.326m에서 끝나고 1131은 2320.570m에 있어 간격은 52.244m다. W의 1132는 75.749m, 1133은 chain 4246.588m이며, 1132-through 끝과 1133 사이 간격은 35.263m다. 해당 체인 위의 static decision은 이 네 개뿐이다. 조합 경로의 사전 선택과 중간 합류 때문에 현재 출구에 도달한 cohort는 더 앞선 시간의 선택·대기·합류 이력을 갖는다.

| 그룹 | 실제 진행 방향의 순서 (chain m, 반올림) | 현재 그룹 모델 셀 |
|---|---|---:|
| F_E | signal10643 4386.333 → merge10639 4610.819 → direct10682 4746.884 → merge10681 4899.956 | off 8, 두 merge 모두 9 |
| D_E | signal10481 6826.843 → merge10490 7153.367 → direct10483 7240.272 → merge10484 7448.366 | off 13 |
| D_W | direct10479 3425.401 → merge10480 3525.124 → signal10491 3650.905 → merge10482 3832.586 | off 6 |
| F_W | direct10645 5909.740 → merge10646 6075.357 → signal10638 6224.840 → merge10644 6777.115 | off 11 |

첫 출구 이후에 합류한 차량은 앞선 decision을 통과한 cohort가 아니며 앞선 출구로 되돌아갈 수 없다. 현재 모델은 두 출구를 한 셀로 합산하고 direct/signal share로 재분배한다. F_E의 136m weaving에서는 첫 merge와 direct diverge 순서도 축약되어 있다. Native prior를 한 개의 평균 셀 전체 유량에 곱하면 이러한 구조적 차이가 남는다. 위 chain 수치는 정본 ramp-split geometry의 것이며, decision chain 환산에는 정본 control mapping의 mm 단위 반올림 offset을 썼다.

현재 global 계산은 `area_freeway_accounting.py:115–126,171–181`에서 기존 제한을 적용한 gross sending `q`를 만들고 `normal_off=p*q`, `mainline_sending=(1-p)*q`로 나눈다. 이후 두 receiving 제약은 따로 적용된다. Local plant도 같은 ratio를 복사하고 같은 식을 쓴다(`local_freeway_plant.py:84,260`). **p는 gross sending 중 원하는 출구 비율**이다. 본선 receiving만 막히면 실현된 off/(off+through)는 p보다 커질 수 있으므로, 실현 departure fraction을 코드의 p와 혼동하면 안 된다.

Flow의 실제 900 action·750 관측이력·초기 상태를 사용한 900–1050 replay에서 15×10초 전부 off receiving rejection=0이고 schedule에서도 rejection=0이다. 아래 295대는 1초 FZP에서 실제 `from_link → offconnector`가 관찰된 8개 branch entry의 합이다. connector 초기재고 배출이나 생성·소멸 차량을 더하지 않았다.

| 그룹 | 예측 accepted 대수 | 물리 branch entry 대수 | baseline gross q 적분 | 같은 q에만 native prior를 곱한 대수 |
|---|---:|---:|---:|---:|
| F_E | 38.513 | 68 | 192.564 | 79.291 |
| D_E | 26.888 | 67 | 134.441 | 62.739 |
| D_W | 42.812 | 77 | 214.062 | 80.273 |
| F_W | 33.143 | 83 | 165.713 | 55.238 |
| 합 | 141.356 | 295 | — | 277.541 |

마지막 열은 **고정된 baseline q를 다시 곱한 대수 진단이며 예측 재실행 결과가 아니다.** 비율을 바꾸면 후속 밀도·속도·도시 유입·receiving도 변한다. 이 열이 관측 합에 가까운 것은 보정의 검증이나 인과 기여율이 아니다. 특히 F_W는 여전히 55.2 vs83으로 남으며 FE는 방향이 반대다.

물리 분모에도 주의가 필요하다. link2의 departure198은 F_E 두 출구68뿐 아니라 D_E signal35와 downstream 연결95를 포함한다. link119 departure110은 direct32+through78이며 그 이전에 D_E signal35가 이미 빠지고 merge10490에서10대가 합류했다. link120의 관찰된 link-change departure83은 두 offbranch 전부이고, 별도로128대가 끝점에서 사라졌다. `83/83`은 off 비율이 아니다. link26의77/203도 출구 사이 merge와 시간창의 재고 변화가 섞여 있다. 이 집계만으로 의사결정 cohort의 native 확률을 재추정하지 않았다.

가장 작은 다음 검증은 **동일한 실제 초기 상태·명령·예측 수요·direct shares·capacity를 두고, 별도 cfg 복제본의 네 total ratio만 변경한 한 interval 재실행**이다. 이는 prior 민감도 실험으로만 표기하고 모델 q, 각 branch 전달량, FW/urban 잔차와 보존을 함께 비교한다. Flow가 이 제한된 paired replay를 수행한다. 그 다음 실제 calibration을 논하려면 각 decision 통과 unique-ID를 추적해 해당 route/through 종료까지 연결하고, 창 이전 선택 차량·창 끝 미도착 차량·중간 합류 cohort를 별도로 세어야 한다. 시점별 source-link departure를 분모로 바꾸는 것만으로는 부족하다. 임의 capacity나 phi, 비율 fitting은 이번 감사 범위에 없다.

재현: `python -X utf8 diagnostics/audit_total_offramp_ratio.py`. 실제 cfg=0.2, 공식 빈값 기본1, 12개 전체 경로, 15step accepted 적분 일치, receiving/schedule rejection0, 295 observed entry 합, 모든 입력 hash 불변을 검사했다. FZP 전체/추가 scan, optimizer, VISSIM 실행은 하지 않았다. 산출물은 이 문서와 `total_offramp_ratio_audit.json/.csv`, 읽기 전용 재현 스크립트다.
