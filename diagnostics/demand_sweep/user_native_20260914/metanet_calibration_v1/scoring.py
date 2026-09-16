"""Predeclared training and held-out metrics; no metric fitted on test data."""
import math


def stats(errors):
    if not errors: return {'mae':None,'rmse':None,'bias':None,'count':0}
    return {'mae':sum(abs(x) for x in errors)/len(errors),
            'rmse':math.sqrt(sum(x*x for x in errors)/len(errors)),
            'bias':sum(errors)/len(errors),'count':len(errors)}


def onset(rows):
    seq=[]
    for r in sorted(rows,key=lambda x:x['time_s']):
        if r['n_veh']>=5 and r['v_kmh'] is not None and r['v_kmh']<30:
            seq.append(r['time_s'])
            if seq[-1]-seq[0]>=120: return seq[0]
        else:
            seq=[]
    return None


def score_rollout(data,cutoff,rollout,road):
    observed={(t,r['cell']):r for t,rows in data.cells.items() if cutoff<=t<=cutoff+450
              for r in rows if r['road']==road}
    predicted={(int(r['time_s']),int(r['cell'])):r for r in rollout['cells'] if r['road']==road}
    expected={(t,c) for t in range(cutoff+30,cutoff+451,30) for c in range(21)}
    if set(predicted)!=expected or not expected.issubset(observed):
        raise ValueError('Missing or extra prediction/observation states')
    flow={(int(r['window_end_s']),int(r['cell'])):r for r in rollout['flows'] if r['road']==road}
    if set(flow)!=expected: raise ValueError('Missing or extra physical flow capture')
    if not all((t,road,c) in data.flows for t,c in expected):
        raise ValueError('Missing observed physical flows')
    rho=[];speed=[];count=[];qerrors=[];offerrors=[];horizons={}
    e14_discharge=[0.,0.]
    obs_ttt=pred_ttt=0.
    old_obs=old_pred=sum(observed[cutoff,c]['n_veh'] for c in range(21))
    confusion={'true_positive':0,'false_positive':0,'true_negative':0,'false_negative':0}
    for t in range(cutoff+30,cutoff+451,30):
        er=[];ev=[];en=[]
        for c in range(21):
            o,p=observed[t,c],predicted[t,c]
            er.append(p['rho_veh_per_km_lane']-o['rho_veh_per_km_lane'])
            en.append(p['n_veh']-o['n_veh'])
            if o['n_veh']>=5 and o['v_kmh'] is not None:
                ev.append(p['v_kmh']-o['v_kmh'])
                oc=o['v_kmh']<30
                pc=p['n_veh']>=5 and p['v_kmh']<30
                confusion[('true_' if pc==oc else 'false_')+('positive' if pc else 'negative')]+=1
            f=flow[t,c];a=data.flows[t,road,c]
            po=f['downstream_crossings']+f['off_departures']+f['terminal_exits']
            oo=float(a['downstream_crossings'])+float(a['off_departures'])+float(a['terminal_exits_inferred'])
            qerrors.append((po-oo)*120.)
            if any(b['kind']=='offramp' and b['road']==road and int(b['from_cell'])==c for b in data.definitions.values()):
                offerrors.append((f['off_departures']-float(a['off_departures']))*120.)
            if road=='FW_E' and c==13:
                e14_discharge[0]+=oo; e14_discharge[1]+=po
        rho.extend(er); speed.extend(ev); count.extend(en)
        new_obs=sum(observed[t,c]['n_veh'] for c in range(21))
        new_pred=sum(predicted[t,c]['n_veh'] for c in range(21))
        obs_ttt+=(old_obs+new_obs)*30/7200
        pred_ttt+=(old_pred+new_pred)*30/7200
        old_obs,old_pred=new_obs,new_pred
        if t-cutoff in (150,300,450):
            horizons[str(t-cutoff)]={'density':stats(er),'speed':stats(ev),'cell_n':stats(en),
                'total_n_observed':new_obs,'total_n_predicted':new_pred}
    detail=next(r for r in rollout['diagnostics']['roads'] if r['road']==road)
    projections=int(detail.get('density_projection_count',0))
    exceed=int(detail.get('jam_density_exceedance_count',0))
    negative=int(detail.get('negative_density_count',0))
    residual=float(detail['continuity_residual_max_veh'])
    if 'jam_density_exceedance_count' not in detail:
        raise ValueError('Missing jam-density exceedance audit')
    finite=all(math.isfinite(x) for x in rho+speed+count+qerrors)
    invalid=(not finite or projections>0 or exceed>0 or negative>0 or residual>1e-6)
    density,speeds,flows=stats(rho),stats(speed),stats(qerrors)
    objective=(density['rmse']/10)**2+(speeds['rmse']/20)**2+(flows['rmse']/1000)**2 if finite and speeds['count'] else 1e6
    if invalid: objective+=1e6+100*(projections+exceed+negative)+min(1e6,residual*1e4)
    events=[]
    for c in range(21):
        obs=[observed[t,c] for t in range(cutoff,cutoff+451,30)]
        pred=[observed[cutoff,c]]+[predicted[t,c] for t in range(cutoff+30,cutoff+451,30)]
        a,b=onset(obs),onset(pred)
        events.append({'cell':c,'observed_first_sustained_in_window_s':a,
            'predicted_first_sustained_in_window_s':b,
            'status':'both' if a is not None and b is not None else 'miss' if a is not None else 'false_alarm' if b is not None else 'neither',
            'timing_error_s':None if a is None or b is None else b-a})
    result={'cutoff_s':cutoff,'road':road,'invalid':invalid,'objective':objective,
        'density':density,'speed':speeds,'cell_n':stats(count),'flow_vph':flows,
        'off_flow_vph':stats(offerrors),'horizons':horizons,
        'freeway_ttt_observed_veh_h':obs_ttt,'freeway_ttt_predicted_veh_h':pred_ttt,
        'e14_discharge_observed_veh':e14_discharge[0] if road=='FW_E' else None,
        'e14_discharge_predicted_veh':e14_discharge[1] if road=='FW_E' else None,
        'congestion_confusion':confusion,'onset_events':events,'diagnostics':detail,
        'definitions':{'flow':'30-second total cell outflow=downstream spatial crossings+off departures+terminal departures, converted toveh/h',
            'speed_mask':'Observed cellN>=5; poor predictions with N<5 are not silently removed',
            'ttt':'Freeway component only,30-second state trapezoid; not total Omega objective including urban/ramp waits',
            'onset':'First sustained low-speed span inside this prediction window, not necessarily original network breakdown time'}}
    return result


def persistence_score(data,cutoff,road):
    initial={r['cell']:r for r in data.cells[cutoff] if r['road']==road}
    rho=[];speed=[]
    for t in range(cutoff+30,cutoff+451,30):
        for o in data.cells[t]:
            if o['road']!=road: continue
            p=initial[o['cell']]
            rho.append(p['rho_veh_per_km_lane']-o['rho_veh_per_km_lane'])
            if o['n_veh']>=5 and o['v_kmh'] is not None and p['v_kmh'] is not None:
                speed.append(p['v_kmh']-o['v_kmh'])
    return {'cutoff_s':cutoff,'road':road,'density':stats(rho),'speed':stats(speed),
        'scope':'Initial observed N/rho/v held; no physical flow forecast or control response'}
