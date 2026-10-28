import json, hashlib, os
B = "D:/VISSIM_handoff/20261024"
fz = json.load(open(f"{B}/evidence/original_nc_FREEZE.json", encoding="utf-8-sig"))["files"]
fz = {k.replace("\\", "/"): v for k, v in fz.items()}
root = f"{B}/original_code_dependencies/nc"
ok = bad = missing = 0; badl = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        if f == "SHA256SUMS.txt": continue
        p = os.path.join(dp, f).replace("\\", "/"); rel = p[len(root) + 1:]
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if rel not in fz: missing += 1; badl.append(("notinfreeze", rel))
        elif fz[rel] == h: ok += 1
        else: bad += 1; badl.append(("diff", rel))
print("original_code_dependencies/nc vs original_nc_FREEZE.json: match", ok, "differ", bad, "not in freeze", missing, badl[:5])
# provenance-pinned files of NC run vs these copies
prov = json.load(open(f"{B}/raw/nc/run_provenance_sdmpc31_nc9000_s29.json", encoding="utf-8-sig"))
pre = prov["workspace_root"].replace("\\", "/") + "/"
chk = []
for k, v in prov["files"].items():
    p = v["path"].replace("\\", "/")
    if p.startswith(pre):
        rel = p[len(pre):]
        local = f"{root}/{rel}"
        h = hashlib.sha256(open(local, "rb").read()).hexdigest() if os.path.exists(local) else None
        chk.append((k, rel, h == v["sha256"] if h else "absent"))
print("NC provenance-pinned files present in original_code_dependencies/nc with same sha:", chk)
cs = prov.get("controller_sources", [])
n_ok = 0; n_abs = 0
for x in cs:
    p = x["path"].replace("\\", "/"); rel = p[len(pre):] if p.startswith(pre) else None
    if rel and os.path.exists(f"{root}/{rel}"):
        n_ok += hashlib.sha256(open(f"{root}/{rel}", "rb").read()).hexdigest() == x["sha256"]
    else: n_abs += 1
print("controller_sources", len(cs), "sha match", n_ok, "absent", n_abs)
