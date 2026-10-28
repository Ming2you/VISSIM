# VERIFY: local NC FZP rows up to 895.1 s (HANDOFF:48 says 431,233 rows) and data-line sha256 (method of codex hash unknown)
import hashlib
F = "D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp"
n = 0; h = hashlib.sha256(); h2 = hashlib.sha256()
with open(F, "rb") as fh:
    for raw in fh:
        if not raw[:1].isdigit():
            continue
        if float(raw.split(b";", 1)[0]) > 895.1:
            break
        n += 1; h.update(raw); h2.update(raw.rstrip(b"\r\n") + b"\n")
print("rows<=895.1", n, "sha(data lines raw)", h.hexdigest()[:16], "sha(LF)", h2.hexdigest(), "codex f1a0b040b711e597")
