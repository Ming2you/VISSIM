# Off-ramp direction split audit

현재 D=.468/F=.484는 방향을 구분하지 않는 adapter fallback이다. `urban.ramp.offramp_direct_share`가 n7에 없으므로 `vissim_stackelberg_adapter.py:3114`의 두 상수가 네 legacy group에 적용된다. CLAUDE.md:1042는 30결정 실측이라고 설명하지만, 이번 검색에서 그 30결정 원자료·추정식·사용 네트워크 hash를 찾지 못했다.

## 서로 다른 세 가지 수치

| 그룹 | 현재 설정 | Ver2 정적 route 조건부 prior | n7 전체 저장창 관측 비율 | 관측 direct/signal |
|---|---:|---:|---:|---:|
| OR_D_E | .468 | 3/(3+4)=.428571 | .600451 | 532/354 |
| OR_D_W | .468 | 3/(3+3)=.500000 | .297544 | 424/1001 |
| OR_F_E | .484 | 4/(4+1.6)=.714286 | .814433 | 790/180 |
| OR_F_W | .484 | 3/(3+1)=.750000 | .368012 | 474/814 |

관측 비율은 **routing truth가 아니다**. 36개 저장창(명목 관측 종료5370초)의 `link_departures_window`를 분모 가중 합산했다. VBS `AccumulateDepartures`는30초 스캔에서 이전에 보였던 링크를 벗어난 차량만 센다. 커넥터를 두 스캔 사이에 완전히 통과한 차량은 누락되고, 길이·속도·정체에 따라 분기별 검출률이 다르다. 또한 마지막 관측 링크에서 소멸한 차량도 departure로 센다. 이 비율을 다음 창의 정확한 분율로 직접 적용하면 측정 편향을 모형에 넣는다.

NC900의 F_E166/217=.764977은 **직전150초가 아닌 초기~900초 누적31샘플**이다. n7의900초는5샘플,48/(48+8)=.857143이다. controlled 모드는 decision JSON을 쓰고 창을 reset한 다음 해당 초의 CSV 스캔을 하므로 명목 창은 보통 t−180~t−30초다. n7의1050/1650/1950/2250/2850/3750/4650초는 기록 샘플이4개여서 명목5개와 다르다. 별도 audit snapshot의 reset 여부를 확인해야 하며, CSV에는 `samples_missing_from_nominal_schedule`로 드러냈다.

## 정적 prior의 적용 범위

네트워크는 SHA256 `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`로 고정했다. 정적 routing time interval은 시작0초 단 하나다. decision1130/1131/1132/1133은 모두 `allVehTypes=true`, `routeChoiceMeth=STATIC`, `combineStaRoutDec=true`이고 해당 분기들을 직접 사용하는 다른 static decision은 없다. 네트워크에 dynamic/partial routing decision도 없다. F_E의 signal10643은 route의 `destLink`이므로 linkSeq만 검색하면 잘못 빠진다. F_W signal10638의 빈 relFlow는 정본 규칙에 따라1이며0이 아니다.

다만 이 값은 **해당 decision을 지난 차량의 조건부 route prior**다. 각 legacy off-ramp 그룹의 두 물리 분기 사이에 on-ramp merge가 있다.

- E_F: signal4386m → R_F_E1 merge4611m → direct4747m.
- E_D: signal6827m → R_D_E1 merge7153m → direct7240m.
- W_D: direct3425m → R_D_W1 merge3525m → signal3651m.
- W_F: direct5909m → R_F_W1 merge(상세 JSON 참조) → signal6225m.

따라서 중간 합류 차량은 앞 분기를 선택할 수 없으며, 기존 하나의 legacy group에 조건부 prior를 적용하는 것은 근사다. 향후 원인 검증은 두 물리 diverge와 중간 merge를 구별해야 한다. 이번 overlay는 미래 관측값을 사용하지 않는 **별도 ablation용 prior**이며 최종 정본 분율로 확정하지 않았다.

## 준비한 구현과 검증

`evaluation/controllers/offramp_routing.py`는 `urban.ramp.offramp_direct_route_prior`가 없으면 아무 설정도 바꾸지 않는다. 있으면 overlay·실제 네트워크·run provenance hash를 대조하고 XML의 route weight, 시간구간, vehicle type, decision 위치와 다른 decision 중복을 다시 검증한 뒤 direct landing 초기화 직후 방향별 dict를 바꾼다. source hash, decision, relFlow 원문, 빈값 기본1 적용 여부, 이전 설정값을 metadata에 남긴다. worker는 설정된 dict를 전달받으므로 다시 추정하지 않는다.

사용 overlay: `diagnostics/offramp_route_prior_overlay.json`.
원천 prior: `diagnostics/offramp_route_prior_ver2.json`.
4개 전용 테스트와3개 기존 runtime parity/worker 테스트 통과. 기본 n7 수치와 config flag 없는 경로의 동작이 유지된다.

재현: `python diagnostics/probe_offramp_shares.py`.
전체 창 CSV: `diagnostics/offramp_share_windows.csv`.
입력별 hash·XML route·물리 merge 범위·분기길이·관측 통계: `diagnostics/offramp_share_audit.json`.
