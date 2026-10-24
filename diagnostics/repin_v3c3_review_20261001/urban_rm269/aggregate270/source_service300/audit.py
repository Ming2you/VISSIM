"""Bounded conditional SC101 queue replay; no network rollout or coefficient fit.

Reuse predicted arrivals and actual control clocks from299. The baseline replay
must reproduce every recorded accepted amount/queue. One already measured past
service ceiling then separates masked readiness from the low service ceiling.
Changed upstream/downstream feedback is deliberately not claimed here.
"""
from collections import defaultdict
from pathlib import Path
import gzip
import hashlib
import json

HERE=Path(__file__).resolve().parent
A=HERE.parent
H=A.parent
M='SC101_S_SC1_to_N_SC2005'
SRC='movement:'+M
PINS={}


def pin(p):
    p=Path(p);data=p.read_bytes();PINS[str(p.resolve())]=hashlib.sha256(data).hexdigest();return data


def read(p):return json.loads(pin(p))


def replay(rows,initial,rate):
    q=initial;result=[]
    for x in rows:
        q+=x['arrivals']
        cap=rate*x['green_sec']/3600.
        offer=min(q,cap)
        sent=min(offer,x['receiving_for_this_movement'])
        result.append(dict(sec=x['sec'],ready=q,cap=cap,accepted=sent,
            starved_opportunity=max(0.,cap-q),receiving_loss=offer-sent,
            arrivals=x['arrivals'],remaining=q-sent))
        q-=sent
        assert q>=-1e-8
    assert abs(initial+sum(x['arrivals'] for x in rows)-sum(x['accepted'] for x in result)-q)<1e-7
    return result


def summary(rows,native):
    blocks=[]
    for i,start in enumerate((2400,2550,2700)):
        r=[x for x in rows if start<=x['sec']<start+150]
        blocks.append(dict(start=start,accepted=sum(x['accepted'] for x in r),
            arrivals=sum(x['arrivals'] for x in r),end_ready=r[-1]['remaining'],
            starved_opportunity=sum(x['starved_opportunity'] for x in r),
            receiving_loss=sum(x['receiving_loss'] for x in r),native_count=native[i],
            error=sum(x['accepted'] for x in r)-native[i]))
    return dict(blocks=blocks,head_mae=sum(abs(x['error']) for x in blocks)/3,
        head_time_cost=-sum(x['accepted']*(2850-x['sec'])/3600 for x in rows),
        ready_cost=sum(x['remaining']*10/3600 for x in rows))


def main():
    assert not (HERE/'assessment.json').exists()
    done=read(A/'sc101_clock299/completion.json')
    assert done['status']=='complete_physical_side_entry_diagnostic_gain_unqualified'
    for p,h in done['source_pins'].items():assert hashlib.sha256(pin(p)).hexdigest()==h,p
    audit=read(A/'sc101_clock299/assessment.json')
    prior=read(H/'sc101_recombined/forecast2400/candidate_application.json')
    assert prior['cutoff_sec']==2400 and max(prior['support']['end_sec'])<2400
    assert abs(prior['after_veh_h']-sum(prior['support']['per_head_rate_veh_h'].values()))<1e-7
    for p in [H/'sc101_recombined/README.md',H/'service_ceiling/README.md',
            H.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md']:
        pin(p)
    results={}
    for version in ('combined298','sc101_clock299'):
        results[version]={}
        for arm in ('hold','city'):
            response=json.loads(gzip.decompress(pin(A/version/'forecast2400'/f'{arm}.response.json.gz')))
            initial=response['initial_freeway_operands']['urban_movement_queue'][M]
            resources={(r['start_sec'],r['resource'],r['kind']):r for r in response['resource_allocations']
                if r['resource'] in (M,'storage:SC101_to_SC2005')}
            incoming=defaultdict(float)
            for r in response['transfers']:
                if r['target']==SRC and r['source']!=SRC:incoming[r['start_sec']]+=r['vehicles']
            greens={r['sec']:r['green_sec'] for block in audit['model'][arm]['blocks'] for r in block['ticks']}
            rows=[]
            for t in range(2400,2850,10):
                rece=resources[t,'storage:SC101_to_SC2005','regular_receiving']
                other=rece['accepted_total_veh']-rece['accepted_by_source_veh'].get(SRC,0.)
                rows.append(dict(sec=t,arrivals=incoming[t],green_sec=greens[t],
                    receiving_for_this_movement=max(0.,rece['available_veh']-other)))
            base=replay(rows,initial,prior['before_veh_h'])
            qerror=serror=0.
            for r in base:
                q=resources[r['sec'],M,'urban_movement_stock']['available_veh']
                s=resources[r['sec'],M,'urban_movement_intended_limit']['accepted_total_veh']
                qerror=max(qerror,abs(r['ready']-q));serror=max(serror,abs(r['accepted']-s))
            assert max(qerror,serror)<1e-7,(version,arm,qerror,serror)
            alternate=replay(rows,initial,prior['after_veh_h'])
            native=[b['count'] for b in audit['native'][arm]['blocks']]
            results[version][arm]=dict(baseline=summary(base,native),past_service=summary(alternate,native),
                max_queue_reproduction_error=qerror,max_flow_reproduction_error=serror,
                rows=rows,past_service_rows=alternate)
    differences={version:{mode:arms['city'][mode]['head_time_cost']-arms['hold'][mode]['head_time_cost']
        for mode in ('baseline','past_service')} for version,arms in results.items()}
    native_delta=sum(b['head_time_cost'] for b in audit['native']['city']['blocks'])-sum(b['head_time_cost'] for b in audit['native']['hold']['blocks'])
    pin(Path(__file__))
    report=dict(status='complete_conditional_service_transport_decomposition',previous_goal_turn_classification='progress',
        results=results,head_time_cost_delta=differences,native_head_time_cost_delta=native_delta,
        past_rate_veh_h=prior['after_veh_h'],source_pins=PINS,goal_complete=False,
        budget=dict(new_full_forecasts=0,conditional_single_movement_replays=8,optimizer=0,ad=0,native=0,fzp=0,new_fits=0),
        limitations=['Replay fixes prior predicted arrivals and other receiver demand. It is not autonomous network validation.',
            'The alternative uses an already measured1650–1950 rate, not a fitted future rate.',
            'Same-movement mass conservation is checked, but altered whole-network feedback is not recomputed.',
            'Head-time delta is not automatically a whole-Omega or causal control gain.',
            'No current/future native observations replace predicted arrivals.'])
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('TIMING',differences,'native',native_delta)
    for v,arms in results.items():
        for a,data in arms.items():
            print(v,a,'PAST_SERVICE',[(x['accepted'],x['starved_opportunity']) for x in data['past_service']['blocks']],
                'MAE',data['baseline']['head_mae'],data['past_service']['head_mae'])


if __name__=='__main__':main()
