# Urban Follower ID ↔ VISSIM SC 매핑 오류 정정 (2026-08-01)

## 요약

분산 urban follower 구성(`19sc`, `15core`)이 **Urban Follower ID를 VISSIM SC 번호로 착각**한 채
생성돼 있었다. 두 체계는 완전히 다르다. 그 결과 19sc는 19개 중 14개, 15core는 15개 중 8개가
엉뚱한 신호기를 제어하고 있었다.

## 근본 원인

`scripts/generate_real_world_distributed_players.py`의 구 정의에 자백이 남아 있다.

```python
# Manual interpretation of the user's 2026-07-28 marked-up 15-player core.
CORE15_SC_NUMBERS = [1, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 107, 108]
```

`primary19`도 같은 착각으로 `1 <= no <= 19`(SC 번호 1~19)를 그대로 썼다.

사용자가 표시한 번호는 **Urban Follower ID**였고, 실제 VISSIM SC 번호는 별개다.
추적되지 않는 자료(마크업 이미지)를 사람이 눈으로 해석해 코드에 상수로 박은 것이 원인이다.

## 정확한 매핑 (Urban-Follower.xlsx 기계 추출)

| UF | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **SC** | 1004 | 1005 | 107 | 108 | 109 | 1003 | 105 | 1 | 11 | 12 | 106 | 1001 | 1002 | 101 | 5 | 6 | 104 | 102 | 103 |

### 독립 검증

xlsx의 SC별 신호헤드 수와 네트워크 인벤토리(`modi.inpx` 파싱)의 `signal_head_count`를 대조 —
**19개 중 16개 정확히 일치**. 불일치 3건은 xlsx가 부분집합인 경우다.

| UF | SC | xlsx 헤드 | 인벤토리 헤드 | 해석 |
|---|---|---|---|---|
| 4 | 108 | 14 | 16 | 2개 제외 |
| 15 | 5 | 16 | 31 | 도곡역, SG 24개 대형 교차로 — 절반 이하만 선택 |
| 18 | 102 | 16 | 23 | 한티역, SG 16개 — 7개 제외 |

부분집합은 오류가 아니라 "해당 팔로워가 제어할 헤드만 고른" 것으로 보인다. UF→SC는 전부
1:1이며(추출기가 1:N을 오류로 차단), 이 3건은 pending dual-ring 투영 작업과 직결된다.

## 대조표

**15core** (= UF 1~16 중 11 제외)

| | SC 집합 |
|---|---|
| 정정 후 | `1, 5, 6, 11, 12, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005` |
| 구 구현 | `1, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 107, 108` |

- 우연히 맞은 것 **7개**: `1, 5, 6, 11, 12, 107, 108`
- 틀리게 제어 중 **8개**: `4, 7, 9, 10, 13, 14, 15, 16` (urban follower가 아닌 신호기)
- 누락 **8개**: `101, 105, 109, 1001, 1002, 1003, 1004, 1005`

**19sc** (= UF 1~19 전체)

| | SC 집합 |
|---|---|
| 정정 후 | `1, 5, 6, 11, 12, 101, 102, 103, 104, 105, 106, 107, 108, 109, 1001~1005` |
| 구 구현 | `SC1 ~ SC19` |

- 우연히 맞은 것 **5개**: `1, 5, 6, 11, 12`

## 변경 내용

| 파일 | 내용 |
|---|---|
| `scripts/extract_urban_follower_map.py` | 신규. Urban-Follower.xlsx → 추적 CSV 기계 추출 |
| `evaluation/real_world_modi_inventory/urban_follower_sc_map.csv` | 신규. UF→SC 요약(19행) |
| `evaluation/real_world_modi_inventory/urban_follower_signal_map.csv` | 신규. UF→SC/SG/헤드 상세(275행) |
| `scripts/generate_real_world_distributed_players.py` | `CORE15_SC_NUMBERS` 제거 → `CORE15_URBAN_FOLLOWER_IDS`(UF ID) + CSV 조회. `primary19`도 매핑 기반으로 정정 |

상세 CSV는 `outputs/real_world_distributed_signal_todo_20260731.md`가 다음 단계로 요구한
"사용자 검증 player↔SC/SG 매핑 표(player_id, sc_no, sg_no, signal_head_no)"에 해당한다.

### 재발 방지 가드 2종

같은 부류의 **침묵 실패**를 막기 위해 생성기가 이제 다음 경우에 중단한다.

1. 선택된 SC가 인벤토리에 없거나 비활성 → 인벤토리 재생성 명령 안내
2. 선택된 SC가 eval 네트워크에 없음 → movement가 빈 채로 생성되던 경로. 네트워크 재빌드 순서 안내

## 파이프라인 재빌드 — 완료

SC 1001~1005는 사용자가 수정한 `modi.inpx`에 새로 추가된 신호기다. 전 단계 완료.

| 단계 | 산출물 | 결과 |
|---|---|---|
| 1. 인벤토리 재생성 | `evaluation/real_world_modi_inventory/*` | ✅ SC 1001~1005 반영 |
| 2. sanitize | `modi_eval_sanitized.inpx` | ✅ 전파 확인 |
| 3. freeway 제어층 설치 | `modi_eval_rw_control.inpx` | ✅ DSD 37→101, SC 37→45, SH 475→485 |
| 4. base control mapping | `evaluation/real_world_modi_control/*` | ✅ SEGMENTS=16 RAMP_METERS=8 |
| 5. 분산 플레이어 재생성 | `*_distributed_{19sc,15core}_*` | ✅ 19/15개 |

### 검증

| 항목 | 19sc | 15core |
|---|---|---|
| signals 집합이 UF 매핑과 일치 | ✅ | ✅ |
| urban_movements 총계 | 84 | 60 |
| movement 0개인 signal | 없음 | 없음 |
| 신규 SC 1001~1005 movement 수 | 각 4 | 각 4 |

이전 구현에서 신규 SC는 eval 네트워크에 없어 **빈 movement로 조용히 생성**됐을 경로였다.
지금은 각 4개씩 정상 배정됐고, 새 가드가 이 상황을 애초에 차단한다.

## 부수 발견 — VISSIM COM ProgID 파손 (31개 스크립트 전체 영향)

재빌드 중 `CreateObject("Vissim.Vissim")`이 `ActiveX component can't create object`로 실패했다.
원인은 저장소가 아니라 머신 등록 상태다.

| ProgID | 대상 실행파일 | 존재 |
|---|---|---|
| `Vissim.Vissim` (전 스크립트가 사용) | `PTV Vissim 2026\exe\Vissim260.exe` | ❌ |
| `Vissim.Vissim.2020` | `PTV Vissim 2020\exe\Vissim200.exe` | ✅ |

VISSIM 2026을 설치했다 제거하면서 일반 ProgID가 사라진 실행파일을 계속 가리키게 됐다.
저장소의 VBS **31개 전부**가 이 ProgID를 쓰므로 COM 툴체인 전체가 죽어 있었다
(메인 러너 `run_real_world_stackelberg_controller.vbs` 포함).

**조치**: `install_real_world_freeway_controls.vbs`에 ProgID 폴백 체인
(`Vissim.Vissim` → `Vissim.Vissim.2020` → `Vissim.Vissim-64.20` → `Vissim.Vissim.200`)과
`VISSIM_PROGID` 환경변수 우선 지정을 추가했다. 이 경로로 재빌드가 통과했다
(`STAGE=COM_PROGID Vissim.Vissim.2020`).

**남은 선택**: 근본 해결은 관리자 권한 재등록이다 — 31개 전부가 한 번에 복구된다.

```bash
& "C:\Program Files\PTV Vision\PTV Vissim 2020\exe\Vissim200.exe" /regserver
```

재등록을 하지 않을 경우, 나머지 30개 VBS(특히 실제 런에 쓰는
`run_real_world_stackelberg_controller.vbs`)에도 같은 폴백을 넣어야 한다.

> ⚠️ VBS 파일은 **순수 ASCII를 유지할 것**. cscript가 .vbs를 시스템 ANSI 코드페이지(CP949)로
> 읽어서 비ASCII 바이트가 문자열 상수를 깨뜨린다. 실제로 한글 주석을 넣었다가
> "종료되지 않은 문자열 상수"로 실패했다. 저장소의 VBS 31개가 전부 ASCII인 것은 우연이 아니다.

## 주의 사항

- **기존 15core/19sc 실행 결과는 전부 폐기 대상**이다. `evaluation/runs/rw_15core_sc108_4500_20260728` 등
  잘못된 SC 집합에서 나온 것이므로 증거로 쓸 수 없다.
  (`outputs/real_world_distributed_signal_todo_20260731.md`의 경고가 이 원인으로 확정됐다.)
- `Urban-Follower.xlsx`와 `Urban Follower ID.png`는 현재 **git 미추적**이다. 이제 파이프라인이 이
  매핑에 의존하므로 커밋을 권장한다 — 추적되지 않는 원본이 이 버그의 근본 원인이었다.
- `core15`의 `include_sc1_coupling = False`(SC1 approach-only) 설정은 그대로 두었다. SC1(=UF8)은
  정정 후에도 15core에 포함되지만, 이 결합 해제가 여전히 의도한 바인지는 확인이 필요하다.
- 이번 정정은 `pstack-flagship` 컨트롤러 이식(브랜치 `pstack-flagship-controller`)과 무관하다.
  해당 작업은 분산 경로를 명시적으로 제외했다.
