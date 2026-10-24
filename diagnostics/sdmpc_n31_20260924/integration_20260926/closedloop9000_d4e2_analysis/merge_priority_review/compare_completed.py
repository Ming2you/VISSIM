"""Finite, closed-run comparison; existing indexed FZP reader, no COM or fit."""
from pathlib import Path
from collections import Counter
import bisect
import csv
import gzip
import hashlib
import json
import statistics
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[4].parent / 'control-full-review'
RUNS = Path('D:/VISSIM_runs/20260928_merge10484_priority_s47')
BASE = Path('D:/VISSIM_runs/20260924_release2670_s47')
T0, END = 2670.1, 3120.1
sys.path.insert(0, str(OLD))
from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.capture_native_runtime_errors import parse_bytes
from evaluation.controllers.control_area_objective import physical_membership_from_ledger


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def save(p, x):
    Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def compare():
    assert load(RUNS/'queue_status.json')['stage'] == 'complete'
    assert not (RUNS/'STOP').exists()
    out = HERE/'completed_comparison'
    out.mkdir(exist_ok=False)
    prior = OLD/'diagnostics/metanet_net_gain_goal_20260924/release2670_seed47'
    geometry = load(prior/'observations/hold/geometry.json')
    proof = load(prior/'omega_membership_proof.json')
    ledger = Path(proof['ledger'])
    assert hashlib.sha256(ledger.read_bytes()).hexdigest() == proof['ledger_sha256']
    inside = physical_membership_from_ledger(load(ledger))
    net = ET.parse(HERE/'source/merge10484_priority_s47.inpx')
    assert set(inside) == {z.get('no') for z in net.findall('./links/link')}
    head, = {float(z.get('pos')) for z in net.findall('./signalHeads/signalHead') if z.get('lane').split()[0] == '10484'}
    target = net.find("./links/link[@no='10484']/toLinkEndPt")
    assert target.get('lane') == '24 1'
    direct = [z.get('no') for z in net.findall('./links/link')
        if z.find('fromLinkEndPt') is not None and z.find('toLinkEndPt') is not None
        and z.find('fromLinkEndPt').get('lane').split()[0] == '31'
        and z.find('toLinkEndPt').get('lane').split()[0] == '24']
    assert direct == ['10484'], 'Skipped-ramp transitions require a unique physical connector'
    chain = {int(z['link']): z['offset_m'] for z in geometry['chains']['FW_E']}
    stamps = [round(T0 + 5*i, 1) for i in range(91)]
    results = []
    for variant, root in (('passive', BASE), ('priority', RUNS)):
        common_initial = None
        for arm in ('hold', 'release_10484'):
            run = root/arm/'run'
            receipt = load(run/'run.json')
            validation = load(run/'fixed_validation.json')
            assert receipt['completed'] and not receipt['owned_native_alive'] and receipt['seed'] == 47
            assert validation['passed'] and not validation['unrecorded_signal_groups']
            if variant == 'priority':
                with (run/'native_conflict_readback.csv').open() as f:
                    checked, = list(csv.DictReader(f))
                assert checked['status'] == 'ONEYIELDSTWO' and checked['link1'] == '24' and checked['link2'] == '10484'
            fzp, = (run/'vissim_eval').glob('*.fzp')
            stat = fzp.stat()
            reader = IndexedFzp(fzp, max_bytes=512*1024*1024)
            frames = [(t, reader.snapshot(t)) for t in stamps]
            reader.handle.close()
            assert (stat.st_size, stat.st_mtime_ns) == (fzp.stat().st_size, fzp.stat().st_mtime_ns)
            initial = reader.selected[str(T0)]['selected_raw_rows_sha256']
            if common_initial is None:
                common_initial = initial
            assert initial == common_initial, 'Within-network full native initial frame differs'
            counts, lane_rows = [], []
            for t, frame in frames:
                counts.append(dict(time_s=t, network=len(frame), omega=sum(inside[str(z[0])] for z in frame.values()),
                    pre=sum(z[0] == 10484 and z[2] < head for z in frame.values()),
                    post=sum(z[0] == 10484 and z[2] >= head for z in frame.values()),
                    approach=sum(z[0] == 31 for z in frame.values())))
                cells = {}
                for z in frame.values():
                    if z[0] not in chain:
                        continue
                    c = bisect.bisect_right(geometry['bounds']['FW_E'], chain[z[0]] + z[2])-1
                    if 21 <= c <= 25:
                        cells.setdefault((c, z[1]), []).append(z[3])
                for (c, lane), speeds in cells.items():
                    lane_rows.append(dict(time_s=t, cell=c, lane=lane, n=len(speeds), speed_sum=sum(speeds), stopped=sum(v < 5 for v in speeds)))
            entries, heads, merges, unknown = [], [], [], []
            for (ta, a), (tb, b) in zip(frames, frames[1:]):
                for vid, z in b.items():
                    prev = a.get(vid)
                    if prev is not None and prev[0] == 31 and z[0] == 24:
                        event = dict(vehicle=vid, lo=ta, hi=tb, unique_connector_inferred=True)
                        entries.append(event); heads.append(event); merges.append(event)
                    if z[0] == 10484 and (prev is None or prev[0] != 10484):
                        entries.append(dict(vehicle=vid, lo=ta, hi=tb))
                        if z[2] >= head:
                            heads.append(dict(vehicle=vid, lo=ta, hi=tb))
                for vid, z in a.items():
                    if z[0] != 10484:
                        continue
                    nxt = b.get(vid)
                    merged = nxt is not None and nxt[0] == 24
                    if z[2] < head and (merged or nxt is not None and nxt[0] == 10484 and nxt[2] >= head):
                        heads.append(dict(vehicle=vid, lo=ta, hi=tb))
                    if merged:
                        merges.append(dict(vehicle=vid, lo=ta, hi=tb))
                    elif nxt is None or nxt[0] != 10484:
                        unknown.append(dict(vehicle=vid, lo=ta, hi=tb))
            assert not unknown, 'Unresolved ramp disappearance; do not count as merge'
            assert len(heads)-len(merges) == counts[-1]['post']-counts[0]['post']
            assert len(entries)-len(merges) == sum(counts[-1][k]-counts[0][k] for k in ('pre', 'post'))
            by_id = {z['vehicle']: z for z in merges}
            trips = [(max(0., by_id[z['vehicle']]['lo']-z['hi']), by_id[z['vehicle']]['hi']-z['lo']) for z in heads if z['vehicle'] in by_id]
            integrate = lambda key: sum((a[key]+b[key])*5/7200 for a,b in zip(counts,counts[1:]))
            checkpoints = validation['native_network_performance_checkpoints']
            latent = (checkpoints['3120']['DelayLatent']-checkpoints['2670']['DelayLatent'])/3600
            errors = [z for p in run.glob('*.err') for z in parse_bytes(p.read_bytes())['events']]
            removals = {z['vehicle_id']: z for z in errors if z['kind'] == 'lane_change_removal' and T0 < z['time_sec'] <= END}
            summary = dict(variant=variant, arm=arm, arrivals=len(entries), heads=len(heads), merges=len(merges),
                initial_pre=counts[0]['pre'], final_pre=counts[-1]['pre'], initial_post=counts[0]['post'], final_post=counts[-1]['post'],
                post_wait_veh_h=integrate('post'), pre_wait_veh_h=integrate('pre'), approach31_veh_h=integrate('approach'),
                omega_ttt_veh_h=integrate('omega'), outside_omega_veh_h=integrate('network')-integrate('omega'), external_latent_veh_h=latent,
                completed_head_to_merge=len(trips), censored_head_to_merge=len(heads)-len(trips),
                unique_connector_inferred_merges=sum(z.get('unique_connector_inferred', False) for z in merges),
                completed_trip_mean_bounds_s=[statistics.mean(x[i] for x in trips) for i in (0,1)] if trips else None,
                removals=len(removals), omega_removals=sum(inside[str(z['link'])] for z in removals.values()),
                initial_frame_sha256=initial, source=dict(path=str(fzp), size=stat.st_size, mtime_ns=stat.st_mtime_ns),
                read_bytes=reader.bytes_read, native_validation_passed=True)
            results.append(summary)
            with gzip.open(out/f'{variant}_{arm}_window.json.gz', 'wt', encoding='utf-8') as f:
                json.dump(dict(summary=summary,counts=counts,lane_rows=lane_rows,entries=entries,heads=heads,merges=merges,
                    selected_raw_frames=reader.selected,removals=list(removals.values())), f)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
    differences = {}
    for variant in ('passive','priority'):
        a,b = [z for z in results if z['variant'] == variant]
        differences[variant] = {k: b[k]-a[k] for k in ('merges','heads','omega_ttt_veh_h','outside_omega_veh_h','external_latent_veh_h','post_wait_veh_h')}
    save(out/'summary.json', dict(rows=results,release_minus_hold=differences,window=[T0,END],
        limitations=['Within each network the full initial FZP frame matches. Across priority/passive networks initial states can differ.',
            '5s observations bracket passage times; completed trips exclude censored trips, whose counts are retained.',
            'Omega and in-network costs use 5s trapezoids. External cumulative counters span integer2670..3120.',
            'Direct31->24 observations use the verified unique10484 connector; these inferred skipped samples are counted separately.',
            'No model calibration, autonomous forecast, SDMPC optimization or9000s performance claim.',
            'Native automatic conflict type is enabled, but calculated per-lane type is not exposed by the tested COM attribute.']))
    lines=['# 10484 램프 우선권: 완료된 두 런 비교','', 'seed47 · 3300초 종료 · 평가2670.1–3120.1초. 기존 passive 두 런 재사용.', '',
        '|망|RM|신호 통과|본선 합류|마지막 신호 이후 재고|Ω TTT(대·h)|외부 입력 대기(대·h)|', '|---|---|---:|---:|---:|---:|---:|']
    for z in results:
        lines.append(f"|{z['variant']}|{z['arm']}|{z['heads']}|{z['merges']}|{z['final_post']}|{z['omega_ttt_veh_h']:.3f}|{z['external_latent_veh_h']:.3f}|")
    lines+=['','유지/완화는 각 망 내부에서 같은 초기 상태를 확인했다. 서로 다른 망의 상태는 같지 않으므로 망 간 차이를 동일 초기 상태의 제어 효과로 해석하지 않는다.',
        '차로별 재고·속도 합, 신호/합류 사건과 시간 구간, 삭제 차량은 각 window.json.gz에 보존했다. 종료 재고나 삭제는 합류/완료 차량으로 세지 않았다.',
        '이 결과는 우선권의 실제 실행 반응을 확인하는 짧은 실험이며, plant 이득 보정 완료를 뜻하지 않는다.']
    (out/'README.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    status_path = HERE/'postprocess_status.json'
    try:
        save(status_path, dict(stage='waiting_for_two_native_runs'))
        deadline = time.monotonic()+4*3600
        while True:
            assert not (RUNS/'STOP').exists(), 'Study STOP exists'
            state = load(RUNS/'queue_status.json')
            if state['stage'] == 'complete':
                break
            assert state['stage'] == 'running', state
            assert time.monotonic() < deadline, 'Finite wait expired'
            time.sleep(30)
        save(status_path, dict(stage='analyzing_completed_files'))
        compare()
        save(status_path, dict(stage='complete', report=str(HERE/'completed_comparison/README.md')))
    except Exception as exc:
        save(status_path, dict(stage='failed', error=str(exc)))
        raise
