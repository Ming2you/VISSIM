import sqlite3, sys
P = "D:/VISSIM_handoff/20261024/raw/nc/network/sdmpc31_nc9000_s29.results/1.db"
con = sqlite3.connect(f"file:{P}?mode=ro&immutable=1", uri=True)
cur = con.cursor()
for (name,) in cur.execute("select name from sqlite_master where type='table'").fetchall():
    cols = [r[1] for r in cur.execute(f"pragma table_info('{name}')").fetchall()]
    n = cur.execute(f"select count(*) from '{name}'").fetchone()[0]
    print(name, n, cols[:40])
print(cur.execute("select * from SIMULATIONRUN").fetchall())
rows = cur.execute("select * from VEHICLENETWORKPERFORMANCEMEASUREMENT_EvaluationTimeInterval").fetchall()
cols = [r[1] for r in cur.execute("pragma table_info('VEHICLENETWORKPERFORMANCEMEASUREMENT_EvaluationTimeInterval')").fetchall()]
print(cols)
for r in rows[:30]:
    print(r)
