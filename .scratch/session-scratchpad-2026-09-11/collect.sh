ssh sat 'cd /home/sat/mcrl-v025-cf3-pilot-ws/runs && python3 - <<"PY"
import json, glob, os
rows=[]
for d in sorted(glob.glob("A*-s*/")):
    d=d.rstrip("/")
    st=json.load(open(d+"/status.json")) if os.path.exists(d+"/status.json") else {}
    rd={}
    if os.path.exists(d+"/readings.jsonl"):
        for line in open(d+"/readings.jsonl"):
            r=json.loads(line)
            if "gate" in r: continue
            rd.setdefault(r["episode"], r)
    print(d, st.get("status"), st.get("episodes_completed"), "rss=%.2f"%(st.get("rss_gb") or 0), " ".join("ep%d:%.4gM/hi%.3f/ha%.3f/sv%.4f"%(e, r["measured_ee"]/1e6, r["measured_h_inter"], r.get("measured_h_intra") or -1, r["measured_served"]) for e,r in sorted(rd.items())))
if os.path.exists("learning-check/DECISION.json"): print("DECISION", open("learning-check/DECISION.json").read().replace("\n"," "))
PY
uptime; free -g | sed -n 2p'
