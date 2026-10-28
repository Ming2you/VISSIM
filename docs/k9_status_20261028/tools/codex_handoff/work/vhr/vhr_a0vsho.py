# compare every handoff code/ file (no .git) with the A0 tree and my tree, long-path safe
import hashlib, os, json
PFX = chr(92)*2 + '?' + chr(92)
HO='D:/VISSIM_handoff/20261024/code'
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f: h.update(f.read())
    return h.hexdigest()
rels=[]
for root,dirs,files in os.walk(PFX+os.path.abspath(HO)):
    if '.git' in dirs: dirs.remove('.git')
    for fn in files: rels.append(os.path.relpath(os.path.join(root,fn), PFX+os.path.abspath(HO)))
out={'handoff_files':len(rels)}
for name,root in [('a0','D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code'),('vhr','D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/code')]:
    miss=diff=0
    for r in rels:
        a=PFX+os.path.abspath(root)+chr(92)+r
        if not os.path.isfile(a): miss+=1; continue
        if sha(a)!=sha(PFX+os.path.abspath(HO)+chr(92)+r): diff+=1
    out[name]=dict(missing=miss,differs=diff)
print(json.dumps(out)); json.dump(out,open('a0_vs_handoff.json','w'))
