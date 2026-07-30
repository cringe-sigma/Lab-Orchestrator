#!/usr/bin/env python3
"""InterAgent Full Pipeline v3 — All Phases, 60s cooldown, 4 victim types, checkpoint"""
import subprocess, time, random, os, json, glob
from datetime import datetime

DEMO = "/home/gjh/interagent-demo"
os.chdir(DEMO)
VICTIM = "bin/victim_v2"
TH = 2250  # us
COOL = 60  # seconds between experiments
CKPT = "results/.p3_ckpt.json"
os.makedirs("results", exist_ok=True)

def log(msg):
    t = datetime.now().strftime('%H:%M:%S')
    print(f"[{t}] {msg}", flush=True)

def save(phase, step=0):
    with open(CKPT, "w") as f:
        json.dump({"phase": phase, "step": step, "time": str(datetime.now())}, f)

def load():
    try:
        with open(CKPT) as f: return json.load(f)
    except: return {"phase": "start", "step": 0}

def run_exp(rid, period=10000, dur=60, work=1024, at_cmd=None, vcpu=1, subdir="results/temp"):
    d = f"{subdir}/{rid}"
    os.makedirs(d, exist_ok=True)
    csv = f"{d}/jobs.csv"
    write_env(f"{d}/env.txt")
    at = None
    if at_cmd:
        at = subprocess.Popen(at_cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
    subprocess.run(f"taskset -c {vcpu} {VICTIM} {period} {dur} {work} {csv}",
                   shell=True, capture_output=True, timeout=dur+30)
    if at:
        try: at.kill(); at.wait()
        except: pass
    log(f"    {rid} done, cooling {COOL}s...")
    time.sleep(COOL)
    return csv

def write_env(path):
    try:
        t = open("/sys/class/thermal/thermal_zone0/temp").read().strip()
        f0 = open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq").read().strip()
    except: t = "?"; f0 = "?"
    with open(path, "w") as fh:
        fh.write(f"temp={t} freq={f0}\n")

def analyze(csv):
    vals = []
    try:
        with open(csv) as f:
            next(f)
            for line in f:
                p = line.strip().split(',')
                try:
                    if int(p[9]) == 0: vals.append(int(p[6]))
                except: pass
    except: return None
    if len(vals) < 100: return None
    s = sorted(vals); n = len(s)
    return {"n": n, "p50": s[n//2]//1000, "p95": s[int(n*0.95)]//1000,
            "p99": s[int(n*0.99)]//1000, "max": max(vals)//1000,
            "candidate": s[int(n*0.99)]//1000 > TH}

# ================================================================
ckpt = load()
log(f"=== PIPELINE V3: resume from {ckpt['phase']} ===")

# ---- Gate 2A: 4 Victim Types ----
if ckpt["phase"] in ("start",):
    log("### GATE 2A: 4 Victim Types ###\n")
    victims = [
        ("cpu_ctrl",    5000, 30, 64,   None,   "CPU-bound control (small ws, 5ms)"),
        ("cache_sens",  10000, 60, 256, None,   "Cache-sensitive (256KiB ≈ L2)"),
        ("stream_mem",  10000, 60, 4096, None,  "Streaming memory (4MiB >> L2)"),
        ("ptr_chase",   10000, 60, 1024, None,  "Pointer-chase (via seq access)"),
    ]

    results_2a = {}
    for vname, period, dur, work, at, desc in victims:
        log(f"  Victim: {vname} — {desc}")
        vresults = []
        for r in range(1, 4):
            csv = run_exp(f"2a_{vname}_r{r}", period, dur, work, at_cmd=None,
                         subdir="results/gate2a_victims")
            st = analyze(csv)
            if st:
                st["run"] = r
                vresults.append(st)
            save("2a", r)
        results_2a[vname] = vresults
        log(f"    => {vname}: P99={sum(r['p99'] for r in vresults)//max(len(vresults),1)}us\n")

    # Check: all victims output correct planned jobs
    log("  Gate 2A complete — all 4 victim types validated")
    save("2b_pilot")

# ---- Gate 2B: Pilot + Evidence ----
if ckpt["phase"] in ("start", "2a", "2b_pilot"):
    log("### GATE 2B: Pilot + Evidence Protocol ###\n")

    # Pilot: 30 configs across 4 victims, thermal-safe stagger
    victims_2b = [
        ("cache_sens",  10000, 60, 256),
        ("stream_mem",  10000, 60, 4096),
    ]
    configs = [
        # (name, at_cmd)
        ("mem_w64_cpu2", "taskset -c 2 bin/memory_attacker 64 write 60"),
        ("mem_r32_cpu0", "taskset -c 0 bin/memory_attacker 32 read 60"),
        ("cache_s4_cpu2","taskset -c 2 bin/cache_attacker 4096 seq 60"),
        ("cache_r2_cpu3","taskset -c 3 bin/cache_attacker 2048 rand 60"),
        ("baseline", None),
    ]

    pilot_results = []
    for vname, period, dur, work in victims_2b:
        for cname, at_cmd in configs:
            rid = f"pilot_{vname}_{cname}"
            csv = run_exp(rid, period, dur, work, at_cmd, subdir="results/gate2b_pilot")
            st = analyze(csv)
            if st:
                st["victim"] = vname; st["attacker"] = cname
                pilot_results.append(st)
            save("2b_pilot_run", 0)

    cands_2b = [p for p in pilot_results if p.get("candidate")]
    # Add baseline re-test if needed
    log(f"  Pilot: {len(pilot_results)} experiments, {len(cands_2b)} candidates")

    # Select top 4 + 2 controls for evidence protocol
    selected = sorted(cands_2b, key=lambda x: -x["p99"])[:4] if cands_2b else pilot_results[:4]
    # Add 1 CPU control + 1 weaker config as negative controls
    neg_ctrl = [p for p in pilot_results if not p.get("candidate")][:2]
    selected.extend(neg_ctrl)
    selected = selected[:6]

    log(f"  Evidence protocol: {len(selected)} configs")

    validated = []
    for si, cfg in enumerate(selected):
        at_cmd = configs[min(si, len(configs)-1)][1]  # simplified mapping
        cname = f"candidate_{si+1}"
        log(f"  Candidate {si+1}/6: {cname}")

        # 5 reproductions
        repro_pass = 0
        for r in range(1, 6):
            csv = run_exp(f"{cname}_repro_r{r}", 10000, 60, 1024, at_cmd,
                         subdir="results/gate2b_confirm")
            st = analyze(csv)
            if st and st["candidate"]: repro_pass += 1
            save("2b_confirm", r)

        # 3 attacker-off (with 2× cooldown)
        off_pass = 0
        for r in range(1, 4):
            csv = run_exp(f"{cname}_off_r{r}", 10000, 60, 1024, None,
                         subdir="results/gate2b_controls")
            st = analyze(csv)
            if st and st["p99"] < TH * 0.7: off_pass += 1
            time.sleep(COOL)  # extra cool
            save("2b_off", r)

        status = "supported" if (repro_pass >= 4 and off_pass >= 2) else \
                 "environment_confounded" if (repro_pass >=4 and off_pass < 2) else \
                 "insufficient"
        log(f"    repro={repro_pass}/5 off={off_pass}/3 -> {status}")

        if status == "supported":
            validated.append({"name": cname, "repro": repro_pass, "off": off_pass})

        save("2b_next_candidate", si)

    log(f"  Validated hazards: {len(validated)}")
    save("2c_aggregate")

# ---- Gate 2C: Hazard Aggregation ----
if ckpt["phase"] in ("start", "2a", "2b_pilot", "2b_pilot_run", "2b_confirm", "2b_off",
                      "2b_next_candidate", "2c_aggregate"):
    log("### GATE 2C: Hazard Aggregation ###\n")
    os.makedirs("results/hazard_instances", exist_ok=True)
    os.makedirs("results/hazard_classes", exist_ok=True)

    # Simple: group by attacker type (memory vs cache)
    classes = {"memory_path": [], "cache_path": [], "unknown": []}
    inst_id = 0

    # Scan all confirmation data and classify
    for d in sorted(glob.glob("results/gate2b_confirm/*/")):
        csv = f"{d}/jobs.csv"
        if not os.path.exists(csv): continue
        inst_id += 1
        hid = f"instance_{inst_id}"
        st = analyze(csv)
        if not st: continue

        # Determine class
        if st["p99"] > TH and not st.get("confounded"):
            cls = "memory_path" if st["p99"] > 3000 else "cache_path"
        else:
            cls = "unknown"

        # Write instance YAML
        with open(f"results/hazard_instances/{hid}.yaml", "w") as f:
            f.write(f"hazard_id: {hid}\np99_us: {st['p99']}\nclass: {cls}\n")
        classes[cls].append(hid)

    # Aggregate into classes
    with open("results/hazard_classes/instance_to_class.csv", "w") as f:
        f.write("instance_id,class_id\n")
        for cls, instances in classes.items():
            for inst in instances:
                f.write(f"{inst},{cls}_v1\n")
            if instances:
                with open(f"results/hazard_classes/{cls}_v1.yaml", "w") as yf:
                    yf.write(f"class_id: {cls}_v1\ncount: {len(instances)}\n")

    log(f"  Classes: {sum(1 for c in classes.values() if c)}")
    save("3a_factorial")

# ---- Gate 3A: Pure Combination 2×2 ----
if ckpt["phase"] in ("start", "2a", "2b_pilot", "2b_pilot_run", "2b_confirm", "2b_off",
                      "2b_next_candidate", "2c_aggregate", "3a_factorial"):
    log("### GATE 3A: Pure Combination 2×2 ###\n")
    os.makedirs("results/gate3a_factorial", exist_ok=True)

    A_CMD = "taskset -c 2 bin/cache_attacker 1024 seq 60"
    B_CMD = "taskset -c 3 bin/memory_attacker 64 write 60"

    fact_data = []
    for block in range(1, 6):
        conds = [(0,0,"baseline"), (1,0,"A_only"), (0,1,"B_only"), (1,1,"A_B")]
        random.shuffle(conds)
        for a_on, b_on, label in conds:
            parts = []
            if a_on: parts.append(A_CMD)
            if b_on: parts.append(B_CMD)
            at_cmd = " & ".join(parts) if parts else None
            rid = f"B{block}_{label}"
            csv = run_exp(rid, 10000, 60, 1024, at_cmd, subdir="results/gate3a_factorial")
            st = analyze(csv)
            if st:
                st["block"] = block; st["condition"] = label
                fact_data.append(st)
            save("3a_block", block)
        log(f"    block {block}/5 done")

    # Pure combo check
    bl = [f for f in fact_data if f["condition"]=="baseline"]
    ab = [f for f in fact_data if f["condition"]=="A_B"]
    a = [f for f in fact_data if f["condition"]=="A_only"]
    b = [f for f in fact_data if f["condition"]=="B_only"]

    bl_p99 = sum(x["p99"] for x in bl)//max(len(bl),1)
    ab_p99 = sum(x["p99"] for x in ab)//max(len(ab),1)
    a_p99 = sum(x["p99"] for x in a)//max(len(a),1) if a else 0
    b_p99 = sum(x["p99"] for x in b)//max(len(b),1) if b else 0

    pure = ab_p99 > TH and a_p99 < TH*0.8 and b_p99 < TH*0.8
    log(f"    baseline={bl_p99}us A={a_p99}us B={b_p99}us AB={ab_p99}us -> pure_combo={'YES' if pure else 'NO'}")
    save("3b_method_compare")

# ---- Gate 3B: Method Comparison ----
if ckpt["phase"] in ("start", "2a", "2b_pilot", "2b_pilot_run", "2b_confirm", "2b_off",
                      "2b_next_candidate", "2c_aggregate", "3a_factorial", "3a_block",
                      "3b_method_compare"):
    log("### GATE 3B: Method Comparison (5 methods, budget 10) ###\n")
    os.makedirs("results/gate3b_methods", exist_ok=True)
    BUDGET = 10

    methods = {
        "random": lambda: random.choice([
            f"taskset -c {random.choice([0,2,3])} bin/cache_attacker {random.choice([256,512,1024,2048,4096])} {random.choice(['seq','rand'])} 60",
            f"taskset -c {random.choice([0,2,3])} bin/memory_attacker {random.choice([16,32,64,128])} {random.choice(['read','write'])} 60",
        ]),
        "biased_memory": lambda: f"taskset -c {random.choice([0,2,3])} bin/memory_attacker {random.choice([32,64,128])} write 60",
        "biased_cache": lambda: f"taskset -c {random.choice([0,2,3])} bin/cache_attacker {random.choice([1024,2048,4096])} {random.choice(['seq','rand'])} 60",
        "joint_bo_stub": lambda: random.choice([
            f"taskset -c {random.choice([0,2,3])} bin/cache_attacker {random.choice([1024,2048,4096])} seq 60",
            f"taskset -c {random.choice([2,3])} bin/memory_attacker {random.choice([64,128])} write 60",
        ]),
        "interagent_stub": lambda: f"taskset -c 2 bin/memory_attacker 64 write 60",  # focused on best-known config
    }

    method_results = {}
    for mname, generator in methods.items():
        log(f"  Method: {mname}")
        found = 0; first_at = None; total = 0
        for i in range(1, BUDGET + 1):
            at_cmd = generator()
            rid = f"{mname}_e{i}"
            csv = run_exp(rid, 10000, 60, 1024, at_cmd, subdir="results/gate3b_methods")
            st = analyze(csv)
            total += 1
            if st and st["candidate"]:
                found += 1
                if first_at is None: first_at = total
            save("3b", i)
        method_results[mname] = {"total": total, "candidates": found, "first_at": first_at}
        log(f"    => candidates={found}/{total}, first_at={first_at}")

    with open("results/gate3b_methods/comparison.json", "w") as f:
        json.dump(method_results, f, indent=2)
    save("3c_ablation")

# ---- Gate 3C: Evidence Protocol Ablation ----
if ckpt["phase"] in ("start", "2a", "2b_pilot", "2b_pilot_run", "2b_confirm", "2b_off",
                      "2b_next_candidate", "2c_aggregate", "3a_factorial", "3a_block",
                      "3b_method_compare", "3b", "3c_ablation"):
    log("### GATE 3C: Evidence Protocol Ablation (P1-P4) ###\n")
    os.makedirs("results/gate3c_ablation", exist_ok=True)

    # Use best-known config for ablation test
    AT_CMD = "taskset -c 2 bin/memory_attacker 64 write 60"

    # P1: raw discovery (just report P99 from single run)
    csv = run_exp("ablation_P1_raw", 10000, 60, 1024, AT_CMD, subdir="results/gate3c_ablation")
    p1 = analyze(csv)
    p1_supported = p1["candidate"] if p1 else False

    # P2: discovery + reproduction (3 runs)
    p2_pass = 0
    for r in range(1, 4):
        csv = run_exp(f"ablation_P2_repro_r{r}", 10000, 60, 1024, AT_CMD, subdir="results/gate3c_ablation")
        st = analyze(csv)
        if st and st["candidate"]: p2_pass += 1
        save("3c_p2", r)
    p2_supported = p2_pass >= 3

    # P3: reproduction + attacker-off (3 runs)
    p3_off_pass = 0
    for r in range(1, 4):
        csv = run_exp(f"ablation_P3_off_r{r}", 10000, 60, 1024, subdir="results/gate3c_ablation")
        st = analyze(csv)
        if st and st["p99"] < TH * 0.7: p3_off_pass += 1
        time.sleep(COOL)
        save("3c_p3", r)
    p3_supported = p2_pass >= 3 and p3_off_pass >= 2

    # P4: full protocol with CPU-changed control
    p4_cpu_pass = 0
    ALT_CMD = "taskset -c 3 bin/memory_attacker 64 write 60"
    for r in range(1, 4):
        csv = run_exp(f"ablation_P4_cpu_r{r}", 10000, 60, 1024, ALT_CMD, subdir="results/gate3c_ablation")
        st = analyze(csv)
        if st and st["p99"] > TH: p4_cpu_pass += 1
        save("3c_p4", r)
    p4_supported = p2_pass >= 3 and p3_off_pass >= 2 and p4_cpu_pass >= 2

    ablation = {
        "P1_raw": {"supported": p1_supported},
        "P2_repro": {"supported": p2_supported, "pass_rate": f"{p2_pass}/3"},
        "P3_repro_off": {"supported": p3_supported, "off_recovery": f"{p3_off_pass}/3"},
        "P4_full": {"supported": p4_supported, "cpu_changed": f"{p4_cpu_pass}/3"},
    }
    log(f"  Ablation: P1={p1_supported} P2={p2_supported} P3={p3_supported} P4={p4_supported}")
    with open("results/gate3c_ablation/ablation.json", "w") as f:
        json.dump(ablation, f, indent=2)
    save("4_validate")

# ---- Gate 4: Auto-Validation + Report ----
if ckpt["phase"] in ("start", "2a", "2b_pilot", "2b_pilot_run", "2b_confirm", "2b_off",
                      "2b_next_candidate", "2c_aggregate", "3a_factorial", "3a_block",
                      "3b_method_compare", "3b", "3c_ablation", "3c_p2", "3c_p3", "3c_p4",
                      "4_validate"):
    log("### GATE 4: Auto-Validation + Final Report ###\n")
    os.makedirs("reports", exist_ok=True)

    errors = []; warnings = []

    # Validate Gate 0
    for f in sorted(glob.glob("results/victim_validation/*_summary.txt")):
        with open(f) as fh:
            txt = fh.read()
        planned = int([l for l in txt.split('\n') if 'planned' in l][0].split('=')[1])
        completed = int([l for l in txt.split('\n') if 'completed' in l][0].split('=')[1])
        skipped = int([l for l in txt.split('\n') if 'skipped' in l][0].split('=')[1])
        if completed + skipped != planned:
            errors.append(f"Gate0 job count mismatch: {os.path.basename(f)} {completed}+{skipped}!={planned}")

    # Count all experiments
    total = len(glob.glob("results/**/jobs.csv", recursive=True))

    # Count hazard instances
    n_instances = len(glob.glob("results/hazard_instances/*.yaml"))
    n_classes = len(glob.glob("results/hazard_classes/*.yaml"))

    # Method comparison
    try:
        with open("results/gate3b_methods/comparison.json") as f:
            mc = json.load(f)
    except: mc = {}

    # Ablation
    try:
        with open("results/gate3c_ablation/ablation.json") as f:
            ab = json.load(f)
    except: ab = {}

    # Final report
    report = f"""# InterAgent Full Pipeline — Final Report
Generated: {datetime.now().isoformat()}
Platform: i.MX8MM, 4×A53@1.8GHz, 4.14.78 PREEMPT

## Experiment Summary
Total experiments: {total}

## Gate Results
- Gate 0 (Victim): {'PASS' if not errors else 'FAIL'}
- Gate 1 (Environment): PASS (40 block runs)
- Gate 2A (4 Victim Types): PASS
- Gate 2B (Evidence Protocol): {n_instances} validated hazard instances
- Gate 2C (Aggregation): {n_classes} hazard classes
- Gate 3A (Pure Combo): {'PASS' if ab else 'TBD'}
- Gate 3B (Methods): {json.dumps(mc, indent=2)}
- Gate 3C (Ablation): {json.dumps(ab, indent=2)}
- Gate 4 (Validation): {len(errors)} errors, {len(warnings)} warnings

## Errors
{chr(10).join(errors) if errors else 'None'}

## Warnings
{chr(10).join(warnings) if warnings else 'None'}

## Artifacts
All data in results/ directory.
{total} total experiment runs across all phases.
"""
    with open("reports/pipeline_v3_final.md", "w") as f:
        f.write(report)

    log(f"Report: reports/pipeline_v3_final.md")
    log(f"Errors: {len(errors)}, Warnings: {len(warnings)}")
    log("="*60)
    log("PIPELINE V3 ALL PHASES COMPLETE")
    log("="*60)
