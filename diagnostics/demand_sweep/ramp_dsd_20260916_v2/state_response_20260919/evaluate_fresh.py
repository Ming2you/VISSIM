"""One frozen, unseen-seed response test; never refits on its outcomes."""
import hashlib
from study import *

def main():
    bank=HERE/'native_s33_v1';freeze=e.load(bank/'model_freeze.json');protocol=e.load(bank/'protocol.json')
    for file,digest in freeze['pins'].items():
        if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=digest:raise AssertionError(('Frozen model changed',file))
    out=bank/'predictions';out.mkdir(exist_ok=False)
    data=e.ObservationData(bank/'observations/none');start=protocol['start_s'];results={}
    for name,path in freeze['models'].items():
        modeldir=ROOT/path;model=e.load_base_model(data.geometry,modeldir/'config.json')
        profile=e.load(modeldir/'port_profile.json');params=e.load(modeldir/'selected_parameters.json')['parameters'];result={}
        for arm,seq in protocol['candidate_bank'].items():
            def command(t):
                i=int((t-start)//150)
                return ({protocol['meter_id']:seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {})
            observed=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
            w=e.window(data,model,start,'history_forecast',profile,command)
            pred=e.simulate(model,w,params)
            scores={r:e.score_rollout(observed,start,pred,r) for r in model.roads}
            if any(s['invalid'] for s in scores.values()):raise AssertionError(('Physical validation failed',name,arm))
            result[arm]={'actual':direction_parts(observed,model,start),'predicted':direction_parts(data,model,start,pred),
                'actual_component':e.component(observed,model,start),'predicted_component':e.component(data,model,start,pred),
                'scores':scores}
            e.save(out/f'{name}_{arm}.json',pred)
        for arm in ARMS:
            result[arm]['delta_east']={kind:{k:result[arm][kind]['FW_E'][k]-result['none'][kind]['FW_E'][k]
                for k in ['mainline','on','off']} for kind in ['actual','predicted']}
        results[name]=result
        print(name,{a:{k:round(sum(v.values()),4) for k,v in r['delta_east'].items()} for a,r in result.items()},flush=True)
    e.save(out/'results.json',{'seed':33,'cutoff_s':start,'horizon_sec':450,'no_future_features':True,
        'freeze_pins_passed':True,'models':results,'scope':'42 mainline cells + 16 ramp connectors; not Omega or full GNE'})

if __name__=='__main__':main()
