import json,sys
d=json.load(open(f'scan/{sys.argv[1]}.json',encoding='utf-8'))
w0,w1=int(sys.argv[2])//60,int(sys.argv[3])//60
x0=d['lane_x0']
print('tag',d['tag'],'window',sys.argv[2],sys.argv[3],' bin: lane1..4 speed (veh/km/lane)')
for lb in range(len(d['lN'][0])):
    x=x0+lb*100
    if x<4200 or x>7800: continue
    row=[]
    for ln in range(4):
        n=sum(d['lN'][w][lb][ln] for w in range(w0,w1)); s=sum(d['lV'][w][lb][ln] for w in range(w0,w1))
        fr=sum(d['frames'][w0:w1])
        row.append(f"{(s/n if n else float('nan')):5.1f}({n/fr/0.1:5.1f})")
    print(int(x),' '.join(row))
