# 램프 지향 수요를 키운다 — 도시부 격자를 부풀리지 않고 온램프만 채우는 것이 목적.
#
# 왜 이 방식인가.
#   urban_input 을 전역 스케일하면 램프는 조금 늘고 도시부가 크게 막힌다. 실측(2026-08-04):
#   urban 1.45 -> 2.70 에서 온램프 4,414 -> 6,062 (+37 %) 인데 도시부 대수는 4,594 -> 8,120 (+77 %),
#   정지율 30.2 % -> 41.2 %, 평균속도 32.7 -> 23.4 kph. 추가 수요 대부분이 격자에 앉는다.
#
#   대신 **C-D 링크 위의 전용 기점**을 키운다. 링크 69(input 1101)와 링크 32(input 1102)는
#   C-D 링크에 직접 붙은 vehicleInput 이라, 늘린 수요가 도시부 격자를 안 거치고 곧장 램프로 간다.
#   링크 69 는 4차로에 실측 밀도 6.5 veh/km/ln 로 여유가 가장 크고, 유입 커넥터가 0 인
#   순수 기점이라 오프램프 재순환 논란도 없다.
#
# (a) 입력 프로파일 비례 스케일
#     input 1101 (링크 69) 피크 720 -> 2,000 vph  (x2.7778)
#     input 1102 (링크 32) 피크 720 -> 1,200 vph  (x1.6667)
#     프로파일 형상은 보존한다(전 구간 동일 배율).
#
# (b) VRD 1134 route 1 relFlow 2.0 -> 5.0
#     램프 비중 70.6 % -> 82.8 %. 동시에 route 3(10637 -> 링크 70 -> 10639)에서 route 1(10644 직결)로
#     비중이 옮겨가므로 **정체된 링크 70(실측 k=91.7, v=6.8 kph)을 우회**한다.
#
# 램프 기여가 입력에 선형이 아니다(오프램프 유입이 섞인다). 이 값은 1차안이고
# scripts/compare_ramp_saturation.py 로 재서 보정할 것.
import argparse
import os
import shutil
import sys
import io
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETDIR = os.path.join(REPO, "network", "real_world_gaepo_modi")
TARGETS = ["modi.inpx", "modi_eval_sanitized.inpx", "modi_eval_rw_control.inpx"]

# input no -> (링크, 목표 피크). 현재 피크는 파일에서 읽어 배율을 구하므로 반복 적용이 안전하다.
#
# 1차 실측(2026-08-04 rampdemand_v1, 피크 2000/1200):
#   램프 포화 0.61 -> 0.78, R_F_W q/cap 0.98 까지 올랐고 U턴 차단으로 링크 70 이 0.70 -> 0.41 로 풀렸다.
#   그러나 **링크 69 가 과적됐다** — N 47 -> 850, v 39.5 -> 3.1 kph, k/jam 0.91, 정지율 69 %.
#   출구가 온램프 미터 10644(용량 900) 하나뿐인데 실효 2,900 vph 의 82.8 % 를 밀어넣은 결과다.
#   도시부도 4,594 -> 5,476 (+19 %) 로 끌려 올라갔고 그 대부분이 링크 69 대기열이다.
# 2차: 링크 69 피크를 1,200 으로 낮춘다(실효 1,740, 램프분 1,440 — 미터 900 을 여전히 넘어
#   큐는 생기지만 폭주는 아니다). 링크 32 는 1차 값 유지.
INPUTS = {"1101": ("69", 1200.0), "1102": ("32", 1200.0)}
# VRD no -> {route no: 새 relFlow}
RELFLOW = {"1134": {"1": 5.0}}


def patch(path, apply_it, backup):
    tree = ET.parse(path)
    root = tree.getroot()
    notes, errs = [], []

    for vi in root.iter("vehicleInput"):
        no = vi.get("no")
        if no not in INPUTS:
            continue
        link, new_peak = INPUTS[no]
        if str(vi.get("link")) != link:
            errs.append(f"input {no} 의 link 가 {link} 이 아니라 {vi.get('link')}")
            continue
        rows = list(vi.iter("timeIntervalVehVolume"))
        vols = [float(t.get("volume")) for t in rows]
        # 피크는 t=2700 구간(index 3). 프로파일 형상은 보존하고 배율만 건다.
        cur_peak = vols[3] if len(vols) > 3 else max(vols)
        if cur_peak <= 0:
            errs.append(f"input {no}: 피크가 0 이다 {vols}")
            continue
        if abs(cur_peak - new_peak) < 1e-6:
            notes.append(f"input {no}: 이미 {new_peak:.0f} — 변경 없음")
            continue
        scale = new_peak / cur_peak
        newv = [round(v * scale) for v in vols]
        notes.append(f"input {no} (링크 {link}) x{scale:.4f}  {[int(v) for v in vols]} -> {newv}")
        if apply_it:
            for t, v in zip(rows, newv):
                t.set("volume", str(int(v)))

    for v in root.iter("vehicleRoutingDecisionStatic"):
        no = v.get("no")
        if no not in RELFLOW:
            continue
        for r in v.iter("vehicleRouteStatic"):
            rn = r.get("no")
            if rn not in RELFLOW[no]:
                continue
            target = RELFLOW[no][rn]
            raw = (r.get("relFlow") or "").strip()
            cur = 1.0
            if raw:
                try:
                    cur = float(raw.split(":")[-1])
                except ValueError:
                    errs.append(f"VRD {no} route {rn}: relFlow 파싱 실패 {raw!r}")
                    continue
            if abs(cur - target) < 1e-9:
                notes.append(f"VRD {no} route {rn}: 이미 적용됨")
                continue
            prefix = raw.split(":")[0] if ":" in raw else "2 0"
            newraw = f"{prefix}:{target:g}"
            notes.append(f"VRD {no} route {rn} relFlow {raw or '(빈=1.0)'} -> {newraw}")
            if apply_it:
                r.set("relFlow", newraw)

    if apply_it and not errs:
        if backup:
            bak = path + ".bak_rampdemand"
            if not os.path.exists(bak):
                shutil.copy2(path, bak)
        tree.write(path, encoding="UTF-8", xml_declaration=True)
    return notes, errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다. 없으면 예행")
    ap.add_argument("--files", nargs="*", default=TARGETS)
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    print("(a) input 1101(링크69) 피크 720->2000, input 1102(링크32) 피크 720->1200 (프로파일 비례)")
    print("(b) VRD 1134 route 1 relFlow 2.0 -> 5.0  (램프 70.6%->82.8%, 링크70 우회)")
    print(f"모드: {'적용' if args.apply else '예행(dry-run)'}")
    print()
    fail = 0
    for name in args.files:
        path = os.path.join(NETDIR, name)
        if not os.path.exists(path):
            print(f"  {name}: 없음 — 건너뜀")
            continue
        notes, errs = patch(path, args.apply, not args.no_backup)
        print(f"  ### {name}")
        for n in notes:
            print(f"      {n}")
        for e in errs:
            print(f"      FAIL: {e}")
            fail += 1
    print()
    if fail:
        print(f"RESULT FAIL ({fail}건)")
        return 1
    print("RESULT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
