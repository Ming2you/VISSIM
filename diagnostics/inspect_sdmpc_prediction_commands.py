from pathlib import Path
import json
import pickle
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def differences(a,b,path):
    if type(a) is not type(b):
        yield dict(path=path,before=repr(a),after=repr(b));return
    if isinstance(a,dict):
        for key in a.keys()|b.keys():
            if key not in a or key not in b:yield dict(path=path+'.'+str(key),before=repr(a.get(key)),after=repr(b.get(key)))
            else:yield from differences(a[key],b[key],path+'.'+str(key))
    elif isinstance(a,(list,tuple)):
        if len(a)!=len(b):yield dict(path=path+'.length',before=len(a),after=len(b))
        for i,(x,y) in enumerate(zip(a,b)):yield from differences(x,y,path+'.'+str(i))
    elif a!=b:
        row=dict(path=path,before=a,after=b)
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):row['abs_error']=abs(a-b)
        yield row


def main():
    folder=ROOT/'diagnostics/sdmpc_prediction_20260922'
    a,b=[pickle.loads(p.read_bytes()) for p in
         (ROOT/'diagnostics/sdmpc_speed_20260922/full_decision_v1/result.pickle',folder/'full_decision_v1/result.pickle')]
    rows=list(differences(vars(a['response']['control']),vars(b['response']['control']),'control'))
    rows+=list(differences(a['response']['command_evidence'],b['response']['command_evidence'],'command'))
    (folder/'command_differences.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
