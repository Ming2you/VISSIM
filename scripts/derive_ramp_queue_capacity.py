# 온램프 대기행렬 저류 용량을 **램프 커넥터 실제 기하**에서 유도해 용량 JSON 에 합친다.
#
# 왜 필요한가.
#   생성기가 on_ramp receiving 저류를 상수 180 대로 깔고 있었다
#   (generate_real_world_distributed_players.py:394). 실제 커넥터는 149~730 m 라
#   물리 저류가 21~107 대다. 램프 미터링이 조일 수 있는 큐 상한을 좌우하는 값인데
#   최대 8배 어긋난다.
#
#   2026-08-05 에 사용자가 램프미터 신호두를 램프 **시작점 -> 끝점**(길이의 98~99%)으로
#   옮기면서 이 값이 더 중요해졌다. 이제 대기행렬이 커넥터 전체에 쌓인다.
#
# 모델 저류 이름.
#   실제로 쓰이는 것은 on_ramp movement 의 receiving_link 인 `SC{sc}_R_{dir}` 4개다.
#   `SC1001_R_D_W_queue` / `OR_D_W_storage` 는 참조 0개인 유령이라 건드리지 않는다.
#
# 커넥터 -> 모델 램프.
#   RW_RAMP_METER_CONNECTORS 와 RW_RAMP_METER_MODEL_KEYS 가 1:1 로 대응한다.
#   모델 램프 하나에 커넥터 2개가 붙는데 실측 결과 **병렬**이다(각각 다른 도시부 링크에서
#   진입: R_D_W 는 10480<-31, 10482<-32). 두 큐가 같은 모델 램프로 합쳐지므로 용량은 합산.
#
# 큐가 커넥터를 넘치면 상류 도시부 링크로 역류하는데, 그 링크들은 이미 도시부 분할에
# 들어가 있다. 그래서 램프 큐 용량은 커넥터 몫까지만 잡는 것이 경계로 맞다.
import argparse
import io
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NET = os.path.join(REPO, "network", "real_world_gaepo_modi", "modi_eval_rw_control.inpx")
DEFAULT_CONNECTORS = "10480,10482,10646,10644,10639,10681,10490,10484"
DEFAULT_MODEL_KEYS = "R_D_W,R_D_W,R_F_W,R_F_W,R_F_E,R_F_E,R_D_E,R_D_E"
DEFAULT_INTERFACE = "R_D_W:1001,R_D_E:1001,R_F_W:1004,R_F_E:1004"


def link_geometry(network_path):
    root = ET.parse(network_path).getroot()
    geo = {}
    for link in root.iter("link"):
        no = link.get("no")
        if no is None:
            continue
        pts = [(float(p.get("x")), float(p.get("y"))) for p in link.iter("linkPolyPoint")]
        length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 0.0
        geo[str(no)] = {"len_m": length, "lanes": max(1, len(link.findall("./lanes/lane")))}
    return geo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default=DEFAULT_NET)
    ap.add_argument("--capacity-json", required=True,
                    help="derive_urban_storage_capacity.py 산출 JSON. jam density 를 읽고 여기에 합친다")
    ap.add_argument("--connectors", default=DEFAULT_CONNECTORS)
    ap.add_argument("--model-keys", default=DEFAULT_MODEL_KEYS)
    ap.add_argument("--ramp-interface-sc", default=DEFAULT_INTERFACE)
    ap.add_argument("--jam", type=float, default=0.0, help="0 이면 용량 JSON 의 값을 쓴다")
    ap.add_argument("--write", action="store_true", help="주면 용량 JSON 을 실제로 갱신한다")
    args = ap.parse_args()

    payload = json.load(open(args.capacity_json, encoding="utf-8"))
    jam = args.jam or float(payload.get("jam_density_veh_km_lane") or 130.0)

    conns = [c.strip() for c in args.connectors.split(",") if c.strip()]
    keys = [k.strip() for k in args.model_keys.split(",") if k.strip()]
    if len(conns) != len(keys):
        print(f"오류 — 커넥터 {len(conns)}개와 모델키 {len(keys)}개의 수가 다르다.")
        return 2

    iface = {}
    for part in str(args.ramp_interface_sc).split(","):
        if ":" in part:
            ramp, sc = part.split(":", 1)
            iface[ramp.strip()] = sc.strip()

    geo = link_geometry(args.network)
    per_key, detail = {}, {}
    missing = []
    for conn, key in zip(conns, keys):
        g = geo.get(conn)
        if g is None:
            missing.append(conn)
            continue
        cap = g["len_m"] / 1000.0 * g["lanes"] * jam
        per_key[key] = per_key.get(key, 0.0) + cap
        detail.setdefault(key, []).append((conn, g["len_m"], g["lanes"], cap))

    if missing:
        print(f"경고 — 네트워크에 없는 커넥터 {missing}. 그만큼 용량이 과소평가된다.")

    print(f"jam density = {jam:.1f} veh/km/lane")
    print()
    print(f"{'모델 램프':<10}{'커넥터':>10}{'길이m':>9}{'차로':>5}{'저류veh':>10}")
    names = {}
    for key in sorted(detail):
        for conn, length, lanes, cap in detail[key]:
            print(f"{key:<10}{conn:>10}{length:>9.1f}{lanes:>5}{cap:>10.1f}")
        sc = iface.get(key)
        if sc is None:
            print(f"{'':<10}{'-> 인터페이스 SC 미지정, 건너뜀':<34}")
            continue
        direction = key.rsplit("_", 1)[-1]          # R_D_W -> W
        name = f"SC{sc}_R_{direction}"
        names[name] = round(per_key[key], 1)
        old = (payload.get("urban_link_storage_veh") or {}).get(name)
        print(f"{'':<10}{'-> ' + name:<24}{per_key[key]:>10.1f}"
              f"   (현행 {old if old is not None else '상수 180'})")
        print()

    payload.setdefault("urban_link_storage_veh", {}).update(names)
    # 모델 램프키(R_D_W 등) 기준 상한도 같이 낸다. NetworkConfig.ramp_queue_max_veh_by_ramp 로
    # 실려서 리더 압력 정규화와 팔로워 큐 상한이 **같은 물리**를 보게 한다(비면 스칼라 폴백).
    payload["ramp_queue_max_veh_by_ramp"] = {k: round(v, 1) for k, v in sorted(per_key.items())}
    payload["ramp_queue_source"] = "scripts/derive_ramp_queue_capacity.py"
    payload["ramp_queue_note"] = ("램프미터 신호두가 커넥터 끝(98~99%)에 있어 큐가 커넥터 전체에 쌓인다. "
                                  "커넥터를 넘치는 분은 상류 도시부 링크로 역류하며 그 링크는 도시부 분할에 있다.")

    if args.write:
        json.dump(payload, open(args.capacity_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"갱신 완료 -> {args.capacity_json}  (램프 저류 {len(names)}개)")
    else:
        print(f"미리보기만 함. 반영하려면 --write 를 준다. (램프 저류 {len(names)}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
