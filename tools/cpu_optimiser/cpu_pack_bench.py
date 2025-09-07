#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cpu_pack_bench.py  (v1.1)
CPU-only concurrency benchmark for llamafile/llama.cpp.

What’s new in v1.1
- Packs run CONCURRENTLY: for each (instances=m, threads/instance=tpi),
  start m processes together, pin to disjoint CPU sets, and wait for all.
- Group timeout & kill-on-timeout to avoid stranded procs.
- Optional start staggering (--stagger-ms) to reduce loader thrash.

What it measures
- Per-instance tokens/s (parsed from stdout+stderr)
- Aggregate tokens/s (sum), median/min/max, wall_s_max (longest instance)
- Peak per-process RSS (MiB), RAM fit checks from warm-up probe

Notes
- Forces CPU-only: -ngl 0, CUDA_VISIBLE_DEVICES="", LLAMA_NO_GPU=1.
- Parses timings from stderr too (many builds print there).
"""

import argparse
import csv
import datetime as dt
import errno
import json
import math
import os
import platform
import re
import shlex
import statistics as stats
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------- utilities ---------------------------

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s or "")

def cmd_exists(name: str) -> bool:
    from shutil import which
    return which(name) is not None

def round_to_even(x: int) -> int:
    return x if x % 2 == 0 else (x - 1 if x > 1 else x)

def now_iso_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

# --------------------------- CPU / RAM detection ---------------------------

def detect_physical_cores() -> int:
    # 1) lscpu -p=CPU,CORE,SOCKET
    try:
        out = subprocess.run(["lscpu", "-p=CPU,CORE,SOCKET"],
                             capture_output=True, text=True, timeout=2.0)
        if out.returncode == 0 and out.stdout:
            combos = set()
            for ln in out.stdout.splitlines():
                if not ln or ln.startswith("#"): continue
                parts = ln.split(",")
                if len(parts) >= 3:
                    combos.add((int(parts[1]), int(parts[2])))
            if combos:
                return len(combos)
    except Exception:
        pass
    # 2) /sys topology
    try:
        combos = set()
        base = Path("/sys/devices/system/cpu")
        for topo in base.glob("cpu[0-9]*/topology"):
            try:
                core_id = int((topo / "core_id").read_text().strip())
            except Exception:
                continue
            try:
                pkg_id = int((topo / "physical_package_id").read_text().strip())
            except Exception:
                pkg_id = 0
            combos.add((pkg_id, core_id))
        if combos:
            return len(combos)
    except Exception:
        pass
    # 3) heuristic
    logical = os.cpu_count() or 1
    return max(1, logical // 2)

def detect_logical_cpus() -> int:
    return os.cpu_count() or detect_physical_cores()

def mem_available_mib() -> int:
    # /proc/meminfo (Linux)
    try:
        txt = Path("/proc/meminfo").read_text()
        m = re.search(r"^MemAvailable:\s+(\d+)\s*kB", txt, re.MULTILINE)
        if m:
            return int(m.group(1)) // 1024
    except Exception:
        pass
    return 0

# --------------------------- parsing from logs ---------------------------

GENERIC_TOKPS = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(?:tok/s|tokens/s|tokens per second)\b", re.IGNORECASE)
DECODE_TOKPS = re.compile(r"\beval\s*time\s*=\s*.*?\(\s*[0-9.]+\s*ms per token,\s*([0-9.]+)\s*tokens per second\)", re.IGNORECASE)
PROMPT_TOKPS = re.compile(r"prompt\s*eval\s*time\s*=\s*.*?\(\s*[0-9.]+\s*ms per token,\s*([0-9.]+)\s*tokens per second\)", re.IGNORECASE)

CPU_BUF = re.compile(r"CPU buffer size\s*=\s*([0-9.]+)\s*MiB", re.IGNORECASE)
KV_ANY  = re.compile(r"\bKV buffer size\s*=\s*([0-9.]+)\s*MiB", re.IGNORECASE)
COMP_ANY= re.compile(r"\bcompute buffer size\s*=\s*([0-9.]+)\s*MiB", re.IGNORECASE)
MODEL_SZ= re.compile(r"model size\s*=\s*([0-9.]+)\s*GiB", re.IGNORECASE)

def parse_tokps(text: str) -> Dict[str, Optional[float]]:
    text = strip_ansi(text)
    out = {"decode_tokps": None, "prompt_tokps": None, "fallback_tokps": None}
    m = DECODE_TOKPS.search(text)
    if m:
        try: out["decode_tokps"] = float(m.group(1))
        except Exception: pass
    m = PROMPT_TOKPS.search(text)
    if m:
        try: out["prompt_tokps"] = float(m.group(1))
        except Exception: pass
    last = None
    for m in GENERIC_TOKPS.finditer(text):
        try: last = float(m.group(1))
        except Exception: pass
    out["fallback_tokps"] = last
    return out

def parse_memory_clues(text: str) -> Dict[str, Optional[float]]:
    text = strip_ansi(text)
    d = {"cpu_buf_mib": None, "kv_buf_mib": None, "compute_mib": None, "model_size_gib": None}
    m = CPU_BUF.search(text)
    if m:
        try: d["cpu_buf_mib"] = float(m.group(1))
        except Exception: pass
    m = KV_ANY.search(text)
    if m:
        try: d["kv_buf_mib"] = float(m.group(1))
        except Exception: pass
    m = COMP_ANY.search(text)
    if m:
        try: d["compute_mib"] = float(m.group(1))
        except Exception: pass
    m = MODEL_SZ.search(text)
    if m:
        try: d["model_size_gib"] = float(m.group(1))
        except Exception: pass
    return d

# --------------------------- monitors ---------------------------

def _parse_kib_from_status_val(s: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*kB", s or "")
    return int(m.group(1)) if m else None

class CPUProcessMonitor(threading.Thread):
    """Polls /proc/<pid>/status for VmRSS/VmHWM and keeps the peak (KiB)."""
    def __init__(self, pid: int, interval: float = 0.25):
        super().__init__(daemon=True)
        self.pid = pid
        self.interval = interval
        self._stop_event = threading.Event()
        self.peak_kib = 0
    def stop(self): self._stop_event.set()
    def run(self):
        status_path = Path(f"/proc/{self.pid}/status")
        while not self._stop_event.is_set():
            try:
                txt = status_path.read_text()
                m_hwm = re.search(r"^VmHWM:\s*(.+)$", txt, re.MULTILINE)
                m_rss = re.search(r"^VmRSS:\s*(.+)$", txt, re.MULTILINE)
                kib = None
                if m_hwm: kib = _parse_kib_from_status_val(m_hwm.group(1))
                if kib is None and m_rss: kib = _parse_kib_from_status_val(m_rss.group(1))
                if kib is not None and kib > self.peak_kib: self.peak_kib = kib
            except Exception:
                pass
            self._stop_event.wait(self.interval)

# --------------------------- process helpers ---------------------------

def compose_command(exec_via: str, binary: str, argv: List[str]) -> List[str]:
    if exec_via == "direct": return [binary] + argv
    elif exec_via == "sh":   return ["sh", binary] + argv
    elif exec_via == "bash": return ["bash", binary] + argv
    else:                    return [binary] + argv

def preflight(binary: str, exec_via: str):
    bin_path = Path(binary)
    if not bin_path.exists():
        raise SystemExit(f"[preflight] binary not found: {binary}")
    if not os.access(bin_path, os.X_OK):
        try:
            os.chmod(bin_path, os.stat(bin_path).st_mode | 0o111)
        except Exception:
            print(f"[preflight] couldn't chmod +x; run: chmod +x {binary}", file=sys.stderr)
    if cmd_exists("file"):
        try:
            out = subprocess.run(["file", "-b", str(bin_path)], capture_output=True, text=True, timeout=2.0)
            print(f"[preflight] file: {out.stdout.strip()}")
        except Exception:
            pass
    help_cmd = compose_command(exec_via, str(bin_path), ["-h"])
    try:
        sm = subprocess.run(help_cmd, capture_output=True, text=True, timeout=6.0)
        if sm.returncode not in (0, 1):
            print(f"[preflight] '-h' rc={sm.returncode}; continuing.", file=sys.stderr)
        else:
            print("[preflight] binary ran and printed help (good).")
    except subprocess.TimeoutExpired:
        print("[preflight] help timed out; continuing.", file=sys.stderr)
    except OSError as e:
        if e.errno == errno.ENOEXEC and exec_via in ("auto","direct"):
            print("[preflight] got ENOEXEC; consider --exec-via sh", file=sys.stderr)
        else:
            raise

def build_base_argv(args, threads: int, n_predict: Optional[int] = None, prompt: Optional[str] = None) -> List[str]:
    """Always forces -ngl 0 for CPU-only."""
    argv = []
    if args.model:
        argv += ["-m", str(args.model)]
    argv += ["-ngl", "0", "-t", str(threads),
             "-n", str(n_predict if n_predict is not None else args.n_predict),
             "-s", str(args.seed),
             "-p", (prompt if prompt is not None else args.prompt)]
    if args.ctx_size: argv += ["-c", str(args.ctx_size)]
    if args.temp is not None: argv += ["--temp", str(args.temp)]
    if args.top_p is not None: argv += ["--top-p", str(args.top_p)]
    if args.top_k is not None: argv += ["--top-k", str(args.top_k)]
    if args.extra_args: argv += shlex.split(args.extra_args)
    return argv

def read_merged(out_path: Path, err_path: Path) -> str:
    try: a = Path(out_path).read_text(errors="ignore")
    except Exception: a = ""
    try: b = Path(err_path).read_text(errors="ignore")
    except Exception: b = ""
    return strip_ansi(a + "\n" + b)

# --------------------------- warm-up probe (RAM) ---------------------------

def warmup_probe(args, outdir: Path, threads_probe: int) -> Dict[str, float]:
    tag = f"warmup_t{threads_probe}"
    stdout_path = outdir / f"{tag}.stdout.txt"
    stderr_path = outdir / f"{tag}.stderr.txt"
    argv = build_base_argv(args, threads=threads_probe, n_predict=1, prompt="probe")
    cmd = compose_command(args.exec_via, str(args.binary), argv)

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["LLAMA_NO_GPU"] = "1"

    t0 = time.time()
    with open(stdout_path, "w") as fo, open(stderr_path, "w") as fe:
        proc = subprocess.Popen(cmd, stdout=fo, stderr=fe, env=env)
        mon = CPUProcessMonitor(proc.pid, interval=0.2); mon.start()
        rc = proc.wait()
        mon.stop(); mon.join(timeout=1.0)
    wall = time.time() - t0

    logs = read_merged(stdout_path, stderr_path)
    mem = parse_memory_clues(logs)
    vmrss_peak_mib = (mon.peak_kib // 1024) if mon.peak_kib else 0

    parts = [mem.get("cpu_buf_mib") or 0.0, mem.get("kv_buf_mib") or 0.0, mem.get("compute_mib") or 0.0]
    sum_buffers = sum(parts)
    overhead = 256.0  # code/maps/etc
    est = max(sum_buffers + overhead, float(vmrss_peak_mib))

    return {
        "cpu_buf_mib": float(mem.get("cpu_buf_mib") or 0.0),
        "kv_buf_mib": float(mem.get("kv_buf_mib") or 0.0),
        "compute_mib": float(mem.get("compute_mib") or 0.0),
        "model_size_gib": float(mem.get("model_size_gib") or 0.0),
        "vmrss_peak_mib": float(vmrss_peak_mib),
        "per_instance_mem_mib": float(est),
        "warmup_wall_s": wall,
        "warmup_rc": rc,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "cmd": " ".join(shlex.quote(c) for c in cmd),
    }

# --------------------------- CPU affinity planning ---------------------------

def plan_cpu_groups(num_instances: int, threads_per_instance: int, reserve_cores: int) -> Optional[List[List[int]]]:
    logical = detect_logical_cpus()
    avail_total = max(0, logical - reserve_cores)
    need = num_instances * threads_per_instance
    if need > avail_total:
        return None
    cpus = list(range(avail_total))  # reserve the last 'reserve_cores'
    cpus = cpus[:need]
    groups = [[] for _ in range(num_instances)]
    for idx, cpu in enumerate(cpus):
        groups[idx % num_instances].append(cpu)
    for g in groups:
        if len(g) != threads_per_instance:
            return None
    return groups

# --------------------------- concurrent pack run ---------------------------

class RunningProc:
    def __init__(self, proc: subprocess.Popen, mon: CPUProcessMonitor, stdout_path: Path, stderr_path: Path,
                 cpu_affinity: List[int], threads: int, cmd: List[str]):
        self.proc = proc
        self.mon = mon
        self.stdout_path = str(stdout_path)
        self.stderr_path = str(stderr_path)
        self.cpu_affinity = cpu_affinity
        self.threads = threads
        self.cmd = cmd

class OneProcResult:
    def __init__(self, ok: bool, rc: int, tokps: Optional[float], wall_s: float,
                 stdout_path: Path, stderr_path: Path, cmd: List[str], cpu_peak_mib: Optional[int],
                 threads: int, cpu_affinity: List[int]):
        self.ok = ok
        self.rc = rc
        self.tokps = tokps
        self.wall_s = wall_s
        self.stdout_path = str(stdout_path)
        self.stderr_path = str(stderr_path)
        self.cmd = cmd
        self.cpu_peak_mib = cpu_peak_mib
        self.threads = threads
        self.cpu_affinity = cpu_affinity

def start_one(args, threads: int, run_tag: str, outdir: Path, cpu_affinity: List[int]) -> RunningProc:
    stdout_path = outdir / f"{run_tag}.stdout.txt"
    stderr_path = outdir / f"{run_tag}.stderr.txt"
    argv = build_base_argv(args, threads=threads)
    cmd = compose_command(args.exec_via, str(args.binary), argv)

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["LLAMA_NO_GPU"] = "1"

    def _preexec():
        try:
            os.sched_setaffinity(0, set(cpu_affinity))
        except Exception:
            pass

    fo = open(stdout_path, "w")
    fe = open(stderr_path, "w")
    proc = subprocess.Popen(cmd, stdout=fo, stderr=fe, env=env, preexec_fn=_preexec)
    mon = CPUProcessMonitor(proc.pid, interval=0.2); mon.start()
    # Parent can close file objects; child's fds remain open
    fo.close(); fe.close()
    return RunningProc(proc=proc, mon=mon, stdout_path=stdout_path, stderr_path=stderr_path,
                       cpu_affinity=cpu_affinity, threads=threads, cmd=cmd)

def finish_one(rp: RunningProc) -> OneProcResult:
    t0 = time.time()
    rc = rp.proc.wait()
    rp.mon.stop(); rp.mon.join(timeout=1.0)
    wall = time.time() - t0  # wait time; not full run wall (we aggregate separately)
    logs = read_merged(Path(rp.stdout_path), Path(rp.stderr_path))
    toks = parse_tokps(logs)
    tokps = toks["decode_tokps"] or toks["fallback_tokps"]
    ok = (rc == 0 and tokps is not None)
    cpu_peak_mib = (rp.mon.peak_kib // 1024) if rp.mon.peak_kib else None
    return OneProcResult(ok=ok, rc=rc, tokps=tokps, wall_s=wall,
                         stdout_path=Path(rp.stdout_path), stderr_path=Path(rp.stderr_path),
                         cmd=rp.cmd, cpu_peak_mib=cpu_peak_mib,
                         threads=rp.threads, cpu_affinity=rp.cpu_affinity)

class PackResult:
    def __init__(self, instances: int, threads_per_instance: int, procs: List[OneProcResult],
                 started_at: str, start_time: float, end_time: float):
        self.instances = instances
        self.threads_per_instance = threads_per_instance
        self.procs = procs
        self.started_at = started_at
        self.start_time = start_time
        self.end_time = end_time

    def aggregate(self) -> Dict[str, object]:
        ok_tok = [p.tokps for p in self.procs if p.ok and p.tokps is not None]
        walls = [p.wall_s for p in self.procs]
        rcs = [p.rc for p in self.procs]
        cpu_peaks = [p.cpu_peak_mib for p in self.procs if p.cpu_peak_mib is not None]
        return {
            "instances": self.instances,
            "threads_per_instance": self.threads_per_instance,
            "ok_count": len(ok_tok),
            "tokps_sum": float(sum(ok_tok)) if ok_tok else None,
            "tokps_median": float(stats.median(ok_tok)) if ok_tok else None,
            "tokps_min": float(min(ok_tok)) if ok_tok else None,
            "tokps_max": float(max(ok_tok)) if ok_tok else None,
            "wall_s_pack": float(self.end_time - self.start_time),
            "wall_s_wait_median": float(stats.median(walls)) if walls else None,
            "rcs": rcs,
            "cpu_peak_mib_median": (float(stats.median(cpu_peaks)) if cpu_peaks else None),
            "stdout_paths": [p.stdout_path for p in self.procs],
            "stderr_paths": [p.stderr_path for p in self.procs],
        }

def run_pack_concurrent(args, m: int, tpi: int, outdir: Path, groups: List[List[int]],
                        stagger_ms: int, pack_timeout: int) -> PackResult:
    run_tag_base = f"m{m}_t{tpi}_{uuid.uuid4().hex[:8]}"
    runners: List[RunningProc] = []
    t_pack_start = time.time()

    # Start all processes
    for i in range(m):
        tag = f"{run_tag_base}_p{i+1}"
        rp = start_one(args, threads=tpi, run_tag=tag, outdir=outdir, cpu_affinity=groups[i])
        runners.append(rp)
        if stagger_ms > 0:
            time.sleep(stagger_ms / 1000.0)

    # Wait for all or until pack_timeout expires
    deadline = t_pack_start + pack_timeout if pack_timeout > 0 else None
    finished: List[OneProcResult] = []
    alive = set(range(m))

    while alive:
        for idx in list(alive):
            p = runners[idx].proc
            rc = p.poll()
            if rc is not None:
                res = finish_one(runners[idx])
                finished.append(res)
                alive.remove(idx)
        if not alive:
            break
        if deadline and time.time() > deadline:
            # Kill all remaining
            for idx in alive:
                try:
                    runners[idx].proc.kill()
                except Exception:
                    pass
            # Finish them
            for idx in alive:
                try:
                    res = finish_one(runners[idx])
                except Exception:
                    # fabricate a failed result
                    rp = runners[idx]
                    res = OneProcResult(ok=False, rc=-9, tokps=None, wall_s=0.0,
                                        stdout_path=Path(rp.stdout_path), stderr_path=Path(rp.stderr_path),
                                        cmd=rp.cmd, cpu_peak_mib=None, threads=rp.threads, cpu_affinity=rp.cpu_affinity)
                finished.append(res)
            alive.clear()
            break
        time.sleep(0.05)

    t_pack_end = time.time()
    return PackResult(instances=m, threads_per_instance=tpi, procs=finished,
                      started_at=now_iso_utc(), start_time=t_pack_start, end_time=t_pack_end)

# --------------------------- plan instance counts ---------------------------

def parse_instances(s: str) -> List[int]:
    s = s.strip().lower()
    if s == "auto": return []
    if ":" in s:
        a, step, b = s.split(":"); a, step, b = int(a), int(step), int(b)
        if (b - a) * step <= 0: raise ValueError("bad range")
        return list(range(a, b + (1 if step > 0 else -1), step))
    if "-" in s and "," not in s:
        a, b = s.split("-"); a, b = int(a), int(b)
        return list(range(a, b + 1)) if a <= b else list(range(a, b - 1, -1))
    vals = [int(x) for x in s.split(",") if x.strip()]
    if not vals: raise ValueError("could not parse instances")
    return vals

def auto_instances(physical_cores: int) -> List[int]:
    base = max(1, round(physical_cores / 6))
    cand = {3, 4, 6, 7, base-2, base-1, base, base+1, base+2}
    return sorted([n for n in cand if n >= 1])

# --------------------------- main ---------------------------

def main():
    ap = argparse.ArgumentParser(description="Concurrent CPU-only LLM pack benchmark.")
    ap.add_argument("--binary", required=True, help="Path to .llamafile or llama.cpp CLI")
    ap.add_argument("--model", default=None, help="Path to .gguf (only for plain llama.cpp); ignored by llamafile.")
    ap.add_argument("--exec-via", choices=["auto","direct","sh","bash"], default="auto",
                    help="How to exec the binary (llamafile often needs 'sh').")

    # workload
    ap.add_argument("--prompt", default="CPU pack benchmark. Write one short sentence.")
    ap.add_argument("-n", "--n-predict", type=int, default=160)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ctx-size", type=int, default=4096)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--extra-args", default="")

    # planning
    ap.add_argument("--instances", default="auto",
                    help="Comma/range list or 'auto' (≈ physical/6 plus {3,4,6,7}).")
    ap.add_argument("--reserve-cores", type=int, default=2, help="Reserve cores for OS/IO (default 2).")
    ap.add_argument("--threads-min", type=int, default=2)
    ap.add_argument("--threads-max", type=int, default=None)
    ap.add_argument("--ladder-span", type=int, default=2, help="Ladder ±span around base threads/instance.")

    # system
    ap.add_argument("--outdir", default="cpu_pack_runs")
    ap.add_argument("--timeout", type=int, default=1800, help="Per-process timeout (seconds).")
    ap.add_argument("--pack-timeout", type=int, default=0, help="Optional group timeout for a whole pack (seconds). 0=disabled.")
    ap.add_argument("--stagger-ms", type=int, default=0, help="Delay between starting each process (ms).")
    ap.add_argument("--mem-headroom", type=float, default=0.90, help="Use ≤ this fraction of MemAvailable (default 0.90).")
    ap.add_argument("--no-preflight", action="store_true")

    args = ap.parse_args()

    if not args.no_preflight:
        preflight(args.binary, args.exec_via)

    physical = detect_physical_cores()
    logical = detect_logical_cpus()
    if args.threads_max is None:
        args.threads_max = physical

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # warm-up
    threads_probe = max(args.threads_min, min(round_to_even(max(2, physical // 2)), args.threads_max))
    probe = warmup_probe(args, outdir, threads_probe)
    mem_avail = mem_available_mib()
    per_inst_est = probe["per_instance_mem_mib"]
    print("[probe] per-instance RAM est MiB:", f"{per_inst_est:.1f}",
          "| buffers:", f"CPU={probe['cpu_buf_mib']:.1f}",
          f"KV={probe['kv_buf_mib']:.1f}", f"compute={probe['compute_mib']:.1f}",
          "| VmRSS_peak:", f"{probe['vmrss_peak_mib']:.1f}")
    print("[probe] model_size_gib (from log, if present):", probe.get("model_size_gib"))
    print("[probe] MemAvailable MiB:", mem_avail)

    # plan instances
    if args.instances.strip().lower() == "auto":
        inst_list = auto_instances(physical)
    else:
        inst_list = parse_instances(args.instances)

    cap_mib = int(args.mem_headroom * mem_avail)
    inst_fit = []
    for m in sorted(set(inst_list)):
        need = int(math.ceil(per_inst_est * m))
        if need <= cap_mib:
            inst_fit.append(m)
        else:
            print(f"[skip] instances={m} needs ~{need} MiB > cap {cap_mib} MiB; skipping.")
    inst_list = inst_fit
    if not inst_list:
        print("[bench] No instance counts fit memory headroom. Exiting.")
        (outdir / "config.json").write_text(json.dumps({
            **vars(args),
            "physical_cores": physical,
            "logical_cpus": logical,
            "probe": probe,
            "mem_available_mib": mem_avail
        }, indent=2))
        sys.exit(0)

    (outdir / "config.json").write_text(json.dumps({
        **vars(args),
        "physical_cores": physical,
        "logical_cpus": logical,
        "probe": probe,
        "mem_available_mib": mem_avail
    }, indent=2))

    print(f"[bench] CPU: physical={physical}, logical={logical}, threads_max={args.threads_max}, reserve={args.reserve_cores}")
    print(f"[bench] instance counts:", inst_list)

    results_rows: List[Dict[str, object]] = []
    best_by_instances: Dict[int, Dict[str, object]] = {}

    for m in inst_list:
        base_threads = max(args.threads_min, min(args.threads_max, (physical - args.reserve_cores) // m))
        ladder = sorted(set(t for t in [base_threads + d for d in range(-args.ladder_span, args.ladder_span + 1)]
                            if args.threads_min <= t <= args.threads_max))
        print(f"\n=== instances {m} ===")
        print(f"[plan] threads/instance ladder around base={base_threads}: {ladder}")

        per_m_runs: List[Dict[str, object]] = []
        for tpi in ladder:
            groups = plan_cpu_groups(m, tpi, args.reserve_cores)
            if groups is None:
                print(f"[skip] m={m}, tpi={tpi}: not enough CPUs after reserve")
                continue

            print(f"[run] m={m}, tpi={tpi} -> starting {m} procs concurrently ...")
            pack = run_pack_concurrent(args, m, tpi, outdir, groups,
                                       stagger_ms=args.stagger_ms,
                                       pack_timeout=(args.pack_timeout or args.timeout * 2))
            agg = pack.aggregate()
            agg.update({
                "timestamp": pack.started_at,
                "binary": str(args.binary),
                "prompt_len": len(args.prompt),
                "n_predict": int(args.n_predict),
                "per_instance_mem_mib_est": float(per_inst_est),
                "total_mem_mib_est": float(per_inst_est * m),
                "mem_cap_mib": int(cap_mib),
                "ok": (agg["ok_count"] == m)
            })
            per_m_runs.append(agg)

            print(f"[done] m={m}, tpi={tpi}: sum={agg['tokps_sum']} tok/s, "
                  f"median={agg['tokps_median']}, min={agg['tokps_min']}, "
                  f"max={agg['tokps_max']}, wall_pack_s={agg['wall_s_pack']}")

            results_rows.append({
                "timestamp": agg["timestamp"],
                "mode": "cpu-pack",
                "binary": agg["binary"],
                "instances": m,
                "threads_per_instance": tpi,
                "tokps_sum": agg["tokps_sum"],
                "tokps_median": agg["tokps_median"],
                "tokps_min": agg["tokps_min"],
                "tokps_max": agg["tokps_max"],
                "wall_s_pack": agg["wall_s_pack"],
                "ok_count": agg["ok_count"],
                "prompt_len": agg["prompt_len"],
                "n_predict": agg["n_predict"],
                "per_instance_mem_mib_est": agg["per_instance_mem_mib_est"],
                "total_mem_mib_est": agg["total_mem_mib_est"],
                "mem_cap_mib": agg["mem_cap_mib"],
                "stdout_paths": ";".join(agg["stdout_paths"]),
                "stderr_paths": ";".join(agg["stderr_paths"]),
            })

        if per_m_runs:
            per_m_runs.sort(key=lambda r: (r["tokps_sum"] if r["tokps_sum"] is not None else -1,
                                           -(r["wall_s_pack"] if r["wall_s_pack"] is not None else 1e9)), reverse=True)
            best_by_instances[m] = {
                "instances": m,
                "best_threads_per_instance": per_m_runs[0]["threads_per_instance"],
                "tokps_sum": per_m_runs[0]["tokps_sum"],
                "tokps_median": per_m_runs[0]["tokps_median"],
                "tokps_min": per_m_runs[0]["tokps_min"],
                "tokps_max": per_m_runs[0]["tokps_max"],
                "wall_s_pack": per_m_runs[0]["wall_s_pack"],
                "per_instance_mem_mib_est": per_m_runs[0]["per_instance_mem_mib_est"],
                "total_mem_mib_est": per_m_runs[0]["total_mem_mib_est"],
            }
            print(f"[best@m={m}] tpi={best_by_instances[m]['best_threads_per_instance']}  "
                  f"sum={best_by_instances[m]['tokps_sum']}  "
                  f"median={best_by_instances[m]['tokps_median']}")

    results_csv = outdir / "results.csv"
    best_csv = outdir / "best_by_instances.csv"
    results_json = outdir / "results.json"

    with results_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "timestamp","mode","binary","instances","threads_per_instance",
            "tokps_sum","tokps_median","tokps_min","tokps_max","wall_s_pack",
            "ok_count","prompt_len","n_predict",
            "per_instance_mem_mib_est","total_mem_mib_est","mem_cap_mib",
            "stdout_paths","stderr_paths"
        ])
        w.writeheader()
        for r in results_rows:
            w.writerow(r)

    with best_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "instances","best_threads_per_instance","tokps_sum","tokps_median",
            "tokps_min","tokps_max","wall_s_pack",
            "per_instance_mem_mib_est","total_mem_mib_est"
        ])
        w.writeheader()
        for m in sorted(best_by_instances.keys()):
            w.writerow(best_by_instances[m])

    with results_json.open("w") as f:
        json.dump(results_rows, f, indent=2)

    print("\n[pack] done.")
    print(f"[pack] all runs:       {results_csv}")
    print(f"[pack] best per m:     {best_csv}")
    print(f"[pack] all runs (json):{results_json}")

if __name__ == "__main__":
    main()
