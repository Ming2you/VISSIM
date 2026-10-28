import json,sys
def find(d,key,p=''):
    if isinstance(d,dict):
        for k,v in d.items():
            if k==key: yield p+'/'+k, v
            yield from find(v,key,p+'/'+k)
    elif isinstance(d,list):
        for i,v in enumerate(d): yield from find(v,key,p+f'[{i}]')
for fn in sys.argv[2:]:
    d=json.load(open(fn,encoding='utf-8'))
    for path,v in find(d,sys.argv[1]):
        s=json.dumps(v,ensure_ascii=False)
        print(fn, path, s[:400])
