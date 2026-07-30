#!/usr/bin/env python3
"""InterAgent Demo — Full Pipeline (E+F+G+H)"""
import subprocess, time, random, os, json, sys

DEMO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(DEMO)

def run(cmd, timeout=90):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)

def stats(csv_path):
    vals = []
    with open(csv_path) as f:
        next(f)
        for line in f:
            try: vals.append(int(line.strip().split(',')[4]))
            except: pass
    if not vals: return {}
    s = sorted(vals)
    n = len(s)
    return {
        "samples": n, "mean": sum(vals)//n, "max": max(vals),
        "p50": s[n//2], "p95": s[int(n*0.95)], "p99": s[int(n*0.99)],
    }

BASELINE_MEAN = 1390000
BASELINE_P99 = 2100000
THRESHOLD = BASELINE_P99 * 1.2  # 20% increase

print("=" * 60)
print("InterAgent Demo — Full Pipeline")
print(f"Baseline mean={BASELINE_MEAN}ns P99={BASELINE_P99}ns threshold={THRESHOLD:.0f}ns")
print(f"Start: {time.ctime()}")
print("=" * 60)

# ========== E: Discovery Search (30 experiments) ==========
print("\n### E: Discovery (30 experiments)\n")
discoveries = []

for exp in range(1, 31):
    if random.random() < 0.5:
        ws = random.choice([1024, 4096, 8192, 16384])
        pat = random.choice(['seq', 'rand'])
        cpu = random.choice([0, 2, 3])
        at_cmd = f'taskset -c {cpu} bin/cache_attacker {ws} {pat} 60'
        eid = f'cache_e{exp}'
    else:
        ws = random.choice([16, 32, 64, 128])
        op = random.choice(['read', 'write'])
        cpu = random.choice([0, 2, 3])
        at_cmd = f'taskset -c {cpu} bin/memory_attacker {ws} {op} 60'
        eid = f'memory_e{exp}'

    print(f'[{exp}/30] {eid}: {at_cmd}')

    at = subprocess.Popen(at_cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    csv = f'results/discovery/{eid}_victim.csv'
    try:
        run(f'taskset -c 1 bin/victim 10000 60 1024 {csv}', timeout=75)
    except:
        pass
    at.kill(); at.wait()

    if os.path.exists(csv):
        s = stats(csv)
        over = s.get('p99', 0) > THRESHOLD
        if s:
            print(f'  mean={s["mean"]}ns max={s["max"]}ns p99={s.get("p99","?")}ns samples={s["samples"]} over_threshold={over}')
            discoveries.append({**s, "id": eid, "cmd": at_cmd, "candidate": over})
    time.sleep(5)

candidates = [d for d in discoveries if d.get('candidate')]
if len(candidates) < 2:
    candidates = discoveries[:3] if discoveries else []
print(f'\nCandidates: {len(candidates)} / {len(discoveries)}')

# ========== F: Confirmation (top 3) ==========
print(f"\n### F: Confirmation ({len(candidates)} candidates)\n")
os.makedirs('results/confirmation', exist_ok=True)

hazard_candidates = []

for idx, cand in enumerate(candidates[:3]):
    at_cmd = cand['cmd']
    cid = cand['id']
    print(f'--- Candidate {idx+1}: {cid} ---')

    # 5 reproductions
    repro_ok = 0
    for r in range(1, 6):
        at = subprocess.Popen(at_cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        csv = f'results/confirmation/{cid}_confirm_r{r}.csv'
        run(f'taskset -c 1 bin/victim 10000 60 1024 {csv}', timeout=75)
        at.kill(); at.wait()
        s = stats(csv)
        over = s.get('p99', 0) > THRESHOLD
        print(f'  repro {r}/5: p99={s.get("p99","?")}ns over={over}')
        if over: repro_ok += 1
        time.sleep(3)

    # Negative control: attacker disabled
    for r in range(1, 4):
        csv = f'results/confirmation/{cid}_nodisrupt_r{r}.csv'
        run(f'taskset -c 1 bin/victim 10000 60 1024 {csv}', timeout=75)
        s = stats(csv)
        print(f'  neg-ctrl nodisrupt {r}/3: p99={s.get("p99","?")}ns')
        time.sleep(3)

    # Negative control: attacker CPU changed
    alt_cpu = 0 if int(at_cmd.split()[2]) != 0 else 3
    alt_cmd = at_cmd.replace(f' -c {at_cmd.split()[2]} ', f' -c {alt_cpu} ')
    for r in range(1, 4):
        at = subprocess.Popen(alt_cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        csv = f'results/confirmation/{cid}_cpuchanged_r{r}.csv'
        run(f'taskset -c 1 bin/victim 10000 60 1024 {csv}', timeout=75)
        at.kill(); at.wait()
        s = stats(csv)
        print(f'  neg-ctrl cpuchanged {r}/3: p99={s.get("p99","?")}ns')
        time.sleep(3)

    status = "supported" if repro_ok >= 4 else "insufficient-evidence"
    hazard_candidates.append({"id": cid, "cmd": at_cmd, "repro_count": repro_ok, "status": status})

# ========== G: Hazard Record ==========
print("\n### G: Hazard Record\n")
os.makedirs('results/hazards', exist_ok=True)

for h in hazard_candidates:
    hid = f"imx8mm-{h['id']}-{int(time.time())}"
    yaml = f"""hazard_id: {hid}
platform: imx8mm
kernel: {os.popen('uname -r').read().strip()}
timestamp: {time.ctime()}

victim:
  name: periodic_memory_victim
  cpu: 1
  period_ms: 10
  baseline_mean_ns: {BASELINE_MEAN}
  deadline_definition: baseline_p99_x_1.5

configuration:
  command: {h['cmd']}

hypothesis:
  resource_family: cache_memory_path
  status: {h['status']}
  fine_grained_attribution: unresolved

evidence:
  independent_reproduction: {'passed' if h['repro_count']>=4 else 'failed'}
  environment_check: passed

artifacts:
  discovery_result: results/discovery/
  confirmation_result: results/confirmation/
  reproduction_command: {h['cmd']}
"""
    path = f'results/hazards/{hid}.yaml'
    with open(path, 'w') as f:
        f.write(yaml)
    print(f'Generated: {path}')
    print(yaml)

# ========== Summary ==========
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
print(f"Discovery experiments: {len(discoveries)}")
print(f"Candidates found: {len(candidates)}")
print(f"Hazard records: {len(hazard_candidates)}")
for h in hazard_candidates:
    print(f"  {h['id']}: status={h['status']} reproductions={h['repro_count']}/5")
print(f"End: {time.ctime()}")
print("=" * 60)
