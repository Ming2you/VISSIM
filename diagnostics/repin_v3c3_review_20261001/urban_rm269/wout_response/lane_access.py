"""Reconstruct original RM cohorts from saved receipt fractions, not a new rollout."""
import ctypes
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'sc1_supply/forecast2400'
RUNS = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
PINS = {}


def read(path, compressed=False):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if compressed else raw)


def main():
    out = HERE / 'lane_access.json'
    assert not out.exists()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    state = read(BASE / 'state.json')
    original = [c for c in state['known_legsplit_route_state']['cohorts'] if c['target']=='RM_C10681']
    assert sum(c['vehicles'] for c in original)==40
    net = read(BASE / 'network.json')
    assert set(net['known_legsplit_routes']['entry_lane_receiving']['ramp_lanes']) == {'1','2'}
    arms = {}
    for arm in ('hold','selected'):
        folder = RUNS / arm / f'decisions_sdmpc31_g_2400_{arm}_s29'
        frames = {}
        for end in (2550,2700,2850):
            raw = read(folder / f'state_{end:06}.json')
            for when in ('previous','current'):
                spec = raw['obs150']['frames'][when]
                path = folder / spec['path']
                assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['sha256']
                f = read(path)
                assert f['complete']
                frames[f['time_s']] = {v[0]:v for v in f['vehicles']}
        initial = [v for v in frames[2400].values() if v[1]==68 and v[8]=='STATIC' and (v[6],v[7])==(1135,4)]
        counts = Counter(str(v[2]) for v in initial)
        model_counts = Counter()
        for c in original:
            for lane,share in c['lane68']['shares'].items():model_counts[lane]+=c['vehicles']*share
        assert counts==model_counts
        response = read(BASE / (arm+'.response.json.gz'), True)
        rows = {r['start_sec']:r for r in response['resource_allocations']
            if r['kind']=='legsplit_source_reach_share' and r['resource']=='SC1004_W_out:RM_C10681'}
        transfers = Counter()
        for r in response['transfers']:
            if r['source']=='storage:SC1004_W_out' and r['target']=='ramp:RM_C10681':
                transfers[r['start_sec']]+=r['vehicles']
        assert set(rows)==set(transfers)
        cohorts = json.loads(json.dumps(original))
        blocks = []
        for t in range(2400,2850):
            # This is the existing known_legsplit_commit proportional debit.
            # Future receipts are read only to attribute an already finished
            # prediction; they are never proposed as autonomous model inputs.
            rr = rows.get(t)
            if rr:
                requested,accepted = rr['available_veh'],rr['accepted_total_veh']
                assert 0<=accepted<=requested+1e-8 and abs(accepted-transfers[t])<1e-8
                eligible = [c for c in cohorts if c['due']<=t]
                assert sum(c['vehicles'] for c in eligible)<=requested+1e-7
                for c in eligible:c['vehicles']*=1-accepted/requested
            if t+1 in (2550,2700,2850):
                now=frames[t+1];by_lane={}
                for lane in ('1','2','3','4'):
                    originals=[v for v in initial if str(v[2])==lane]
                    native_still=sum(v[0] in now and now[v[0]][1]==68 for v in originals)
                    model_still=sum(c['vehicles']*c['lane68']['shares'].get(lane,0) for c in cohorts)
                    by_lane[lane]=dict(initial=len(originals),native_still68=native_still,
                        model_still_W_out=model_still,
                        native_on10681=sum(v[0] in now and now[v[0]][1]==10681 for v in originals),
                        native_current_links=dict(Counter(str(now[v[0]][1]) if v[0] in now else 'absent_not_assumed_exit' for v in originals)))
                blocks.append(dict(end_sec=t+1,by_initial_lane=by_lane))
        arms[arm]=blocks
        del response
    code = HERE.parents[3] / 'evaluation/controllers/route_choice_corridor.py'
    PINS[str(code)] = hashlib.sha256(code.read_bytes()).hexdigest()
    PINS[str(Path(__file__))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(status='complete_saved_cohort_attribution',initial_RM_veh=40,
        physical_connecting_lanes=[1,2],initial_nonconnecting_lane_veh=16,
        latest_initial_RM_request_due=max(c['due'] for c in original),arms=arms,
        source_pins=PINS,new_rollouts=0,new_native=0,coefficients_fitted=0,
        limitations=['The model cohorts keep initial lane labels but do not explicitly solve lateral transfers to the ramp lanes.',
            'This attributes saved predictions using saved request/receipt fractions, not an independent autonomous forecast.',
            'A missing vehicle is not counted as a normal exit; native removals remain in the existing canonical analysis.',
            'The two arms also differ in city and other RM controls, so this is not isolated10681 causality.'])
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='source_pins'},indent=2))


if __name__=='__main__':main()
