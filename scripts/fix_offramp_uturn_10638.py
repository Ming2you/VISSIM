# OR_F_W 오프램프(커넥터 10638)의 U턴 경로를 막는다.
#
# 무엇이 문제인가.
#   VRD 1133 route 2 는 본선 26 -> 커넥터 10638 -> 링크 70 으로 내리는 경로인데
#   destPos 가 65.34 m 에서 끝난다. 링크 70 의 온램프 커넥터 10639(R_F_E)는 180.1 m 이고
#   링크 70 위에는 VRD 가 없다. 그래서 route 가 끝난 차량이 아무 통제 없이 10639 로 올라갈 수 있다
#   = 서행 본선에서 내려 곧바로 동행 본선으로 재진입하는 U턴이다.
#   10638 은 실측 k=95.4 veh/km/ln, v=6.3 kph 로 네트워크에서 가장 막힌 커넥터이기도 하다.
#
#   다른 오프램프 6개는 이 문제가 없다. combineStaRoutDec=true 아래에서 route 가 온램프 지점
#   **너머까지** 이어지거나(10483/10491/10682), 착지 자체가 이미 모든 온램프 하류다
#   (10481/10479/10645). 즉 설계가 이미 U턴을 막고 있고 10638 만 예외다.
#
# 무엇을 바꾸나.
#   destPos 65.344 -> 333.0. 링크 70 은 338 m 이고 출구 커넥터가 10641 @334.0, 10700 @337.7 이다.
#   333.0 이면 온램프 10639(180.1)를 route 통제 하에 지나치고, 두 출구 중 하나로 링크 71 에 빠진다
#   (둘 다 링크 71 로 간다). 링크 71 은 SC 1004 가 서비스한다.
#
# 원본(modi.inpx)·sanitized·플랜트 세 파일을 동일하게 고친다. 구조 변경이 아니라 속성 하나라
# 파이프라인 재생성 없이 동기가 유지된다.
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
VRD_NO = "1133"
CONNECTOR = "10638"
OLD_POS = 65.344307144023091
NEW_POS = 333.0


def patch(path, apply_it, backup):
    tree = ET.parse(path)
    root = tree.getroot()
    hits = []
    for v in root.iter("vehicleRoutingDecisionStatic"):
        if v.get("no") != VRD_NO:
            continue
        for r in v.iter("vehicleRouteStatic"):
            keys = [i.get("key") for i in r.iter("intObjectRef") if i.get("key")]
            if CONNECTOR not in keys:
                continue
            hits.append((r, r.get("destLink"), float(r.get("destPos") or 0.0)))
    if len(hits) != 1:
        return None, f"route 를 {len(hits)}개 찾았다 (1개여야 한다)"
    r, dest_link, cur = hits[0]
    if str(dest_link) != "70":
        return None, f"destLink 가 70 이 아니라 {dest_link}"
    if abs(cur - NEW_POS) < 1e-6:
        return "이미 적용됨", None
    if abs(cur - OLD_POS) > 1.0:
        return None, f"destPos 가 예상값 {OLD_POS:.3f} 이 아니라 {cur:.3f} — 수동 확인 필요"
    if not apply_it:
        return f"적용 예정 {cur:.3f} -> {NEW_POS:.1f}", None
    if backup:
        bak = path + ".bak_uturn"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
    r.set("destPos", f"{NEW_POS:.14f}")
    tree.write(path, encoding="UTF-8", xml_declaration=True)
    return f"적용 {cur:.3f} -> {NEW_POS:.1f}", None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다. 없으면 예행")
    ap.add_argument("--files", nargs="*", default=TARGETS,
                    help="대상 파일명. 기본은 원본/sanitized/플랜트 셋")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    print(f"VRD {VRD_NO} / 커넥터 {CONNECTOR} route 의 destPos: {OLD_POS:.3f} -> {NEW_POS:.1f}")
    print(f"모드: {'적용' if args.apply else '예행(dry-run)'}")
    print()
    fail = 0
    for name in args.files:
        path = os.path.join(NETDIR, name)
        if not os.path.exists(path):
            print(f"  {name:<30} 없음 — 건너뜀")
            continue
        msg, err = patch(path, args.apply, not args.no_backup)
        if err:
            print(f"  {name:<30} FAIL: {err}")
            fail += 1
        else:
            print(f"  {name:<30} {msg}")
    print()
    if fail:
        print(f"RESULT FAIL ({fail}건)")
        return 1
    print("RESULT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
