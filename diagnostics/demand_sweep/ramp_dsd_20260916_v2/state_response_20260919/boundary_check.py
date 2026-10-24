"""Separate causal boundary error from conditional physical response error."""
from study import *

def main():
    out=HERE/'boundary_v1';out.mkdir(exist_ok=False)
    cases=build_cases();params=e.load(BASE/'selected_parameters.json')['parameters'];results={}
    for seed,case in cases.items():
        start=case['start'];results[str(seed)]={}
        for mode in ['history_forecast','conditioned_diagnostic']:
            rows={}
            for arm in ARMS:
                data=case['items']['pair_'+arm]['data'];seq=case['protocol']['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in case['protocol'].get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                w=e.window(data,case['model'],start,mode,case['profile'],command)
                pred=e.simulate(case['model'],w,params)
                rows[arm]={'parts':direction_parts(data,case['model'],start,pred),'actual':direction_parts(data,case['model'],start)}
                if arm=='none':
                    comparison=[]
                    for pr in pred['cells']:
                        if pr['road']!='FW_E':continue
                        obs=next(r for r in data.cells[pr['time_s']] if r['road']==pr['road'] and r['cell']==pr['cell'])
                        comparison.append({'time_s':pr['time_s'],'cell':pr['cell'],'model':pr,'actual':obs})
                    e.save(out/f'cells_{seed}_{mode}.json',comparison)
            results[str(seed)][mode]=rows
    e.save(out/'results.json',results)
    for seed,modes in results.items():
        for mode,arms in modes.items():
            for arm in ARMS[1:]:
                print(seed,mode,arm,{k:round(arms[arm]['parts']['FW_E'][k]-arms['none']['parts']['FW_E'][k],4) for k in ['mainline','on','off']},flush=True)

if __name__=='__main__':main()
