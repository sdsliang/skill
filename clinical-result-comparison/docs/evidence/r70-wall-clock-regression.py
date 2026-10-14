import json, pathlib, re, subprocess, sys, statistics as st
base = pathlib.Path.home()/".local/state/toolsmith-runs"
rows=[]
for d in sorted(base.iterdir()):
    if not d.is_dir(): continue
    m = re.match(r"^(\d{8}-\d{6})-(r[\w]*(?:-\w+)?)$", d.name)
    if not m: continue
    rj = d/"run.json"
    if not rj.exists(): continue
    r = json.loads(rj.read_text())
    gen = r.get("tag","?")
    gm = re.match(r"^(r\d+n?)-(4|18|14)$", gen)
    if not gm: continue
    server = r.get("server_latency_ms",0)/1000
    steps = max([p.get("steps",0) for p in r.get("polls",[])] or [0])
    md = d/"messages.json"
    out=rea=0
    if md.exists():
        msgs = json.loads(md.read_text())
        for mm in msgs:
            for p in mm.get("parts",[]):
                t=p.get("type")
                if t=="reasoning": rea += len(p.get("text") or "")
    try:
        s = subprocess.run([sys.executable,"-B","tools/semantic-timing.py",str(d)],capture_output=True,text=True).stdout
        mo = re.search(r"out (\d+) / reasoning (\d+)", s)
        if mo: out=int(mo.group(1)); rea=int(mo.group(2))
    except Exception: pass
    rows.append(dict(gen=gm.group(1), grp=gm.group(2), dir=d.name, wall=server, steps=steps, out=out, rea=rea))
prot = ("r62","r63","r65","r65n","r67","r68","r69")
print(f"{'gen':6}{'grp':>4} {'wall_s':>7} {'steps':>5} {'out_tok':>8} {'ms/out_tok':>10} {'tok/s':>6}")
for r in rows:
    if r["gen"] not in prot: continue
    ratio = r["wall"]*1000/r["out"] if r["out"] else 0
    tps = r["out"]/r["wall"] if r["wall"] else 0
    print(f"{r['gen']:6}{r['grp']:>4} {r['wall']:7.1f} {r['steps']:5d} {r['out']:8,d} {ratio:10.2f} {tps:6.1f}")
print()
groups={}
for r in rows:
    if r["gen"] in prot: groups.setdefault(r["gen"],{})[r["grp"]]=r
for gen in prot:
    g=groups.get(gen)
    if not g: continue
    w=[v["wall"] for v in g.values()]; o=[v["out"] for v in g.values()]; s=[v["steps"] for v in g.values()]
    rt=[v["wall"]*1000/v["out"] for v in g.values() if v["out"]]
    print(f"{gen:6} wall均值{st.mean(w):6.1f} 极差{min(w):6.1f}-{max(w):6.1f}({(max(w)-min(w))/st.mean(w)*100:4.0f}%)"
          f" | steps {s} | out {[f'{x:,}' for x in o]} | ms/out_tok {min(rt):.2f}-{max(rt):.2f} ({min(rt)/max(rt)*100:.0f}%eff)")
print()
seq=[(gen, st.mean([v['wall'] for v in groups[gen].values()])) for gen in prot if gen in groups]
print("代际均值序列:", " -> ".join(f"{g} {w:.0f}" for g,w in seq))
for i in range(1,len(seq)):
    d=seq[i][1]-seq[i-1][1]
    print(f"  {seq[i-1][0]}->{seq[i][0]}: {d:+.0f} s ({d/seq[i-1][1]*100:+.0f}%)")
allw=[v["wall"] for g in groups.values() for v in g.values()]
allr=[v["wall"]*1000/v["out"] for g in groups.values() for v in g.values() if v["out"]]
print(f"\n全部 {len(allw)} 跑: wall 均值{st.mean(allw):.0f} 标准差{st.pstdev(allw):.0f} 极差 {min(allw):.0f}-{max(allw):.0f}")
print(f"           ms/out_tok 均值{st.mean(allr):.2f} 标准差{st.pstdev(allr):.2f} 极差 {min(allr):.2f}-{max(allr):.2f} (±{(max(allr)-min(allr))/2/st.mean(allr)*100:.0f}%)")
