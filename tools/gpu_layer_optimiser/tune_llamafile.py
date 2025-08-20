#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tune_llamafile.py  (v4.0)
Benchmark a llamafile or llama.cpp binary across -ngl (GPU-offloaded layers) and CPU threads.

New in v4.0
- AUTO NGL detection:
    * If --ngl is 'auto' (default), run fast probes with ngl=1 and (if possible) ngl=2 to detect:
      - total transformer layers (parsed from logs like "offloaded X/Y layers to GPU")
      - model size (e.g., "model size = 3.80 GiB")
      - per-layer VRAM cost (approx) and constant VRAM overhead
    * Choose an ngl test range automatically (default 10..total_layers; if total_layers < 10, 1..total_layers)
- VRAM-aware capping:
    * --vram-cap <size> (e.g., 10GiB, 10240MiB, 10GB) limits the maximum ngl we test
      based on probe-estimated per-layer VRAM + constant GPU overhead.
- Keeps all previous goodness:
    * Auto CPU thread plan (start ~50% physical cores, then +2,+4,+6)
    * Hill-climb around prior best with ±1 (default)
    * Parses BOTH stdout and stderr (llamafile often logs timings to stderr)
    * Captures decode tok/s (eval), prompt/sample tok/s, wall time, peak GPU VRAM, peak CPU RSS
    * Writes results.csv, results.json, best_by_ngl.csv

Example:
  python3 tune_llamafile.py --binary ./llava-v1.5-7b-q4.llamafile --exec-via sh --vram-cap 10GiB
"""

import argparse
import csv
import datetime as dt
import json
import os
import platform
import re
import shlex
import statistics as stats
import subprocess
import sys
import threading
import time
import errno
from types import SimpleNamespace
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------- small utils ---------------------------

def cmd_exists(name: str) -> bool:
    from shutil import which
    return which(name) is not None

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s or "")

def _parse_kib_from_status_val(s: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*kB", s or "")
    return int(m.group(1)) if m else None

def round_to_even(x: int) -> int:
    return x if x % 2 == 0 else x - 1 if x > 1 else x

def parse_size_to_mib(s: str) -> Optional[int]:
    """
    Accepts e.g. "10GiB", "10GB", "10240MiB", "10240MB", "10240".
    Returns MiB (int). GiB uses 1024^3, GB uses 1000^3; MiB=1024^2; MB=1000^2.
    """
    if s is None:
        return None
    s = s.strip().lower()
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([a-z]*)\s*$", s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit in ("gib", "gi", "g"):
        bytes_ = val * (1024**3)
    elif unit in ("gb",):
        bytes_ = val * (1000**3)
    elif unit in ("mib", "mi", "m"):
        bytes_ = val * (1024**2)
    elif unit in ("mb",):
        bytes_ = val * (1000**2)
    elif unit == "" or unit is None:
        # assume MiB if bare number
        bytes_ = val * (1024**2)
    else:
        return None
    return int(bytes_ / (1024**2))

# --------------------------- CPU core detection ---------------------------

def detect_physical_cores() -> int:
    """
    Try to detect physical core count on Linux.
    Order:
      1) lscpu -p=CPU,CORE,SOCKET
      2) /sys/devices/system/cpu/cpu*/topology/{core_id,physical_package_id}
      3) Fallback: logical // 2 (heuristic)
    """
    try:
        out = subprocess.run(["lscpu", "-p=CPU,CORE,SOCKET"],
                             capture_output=True, text=True, timeout=2.0)
        if out.returncode == 0 and out.stdout:
            combos = set()
            for ln in out.stdout.splitlines():
                if not ln or ln.startswith("#"):
                    continue
                parts = ln.split(",")
                if len(parts) >= 3:
                    combos.add((int(parts[1]), int(parts[2])))
            if combos:
                return len(combos)
    except Exception:
        pass

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

    logical = os.cpu_count() or 1
    return max(1, logical // 2)

# --------------------------- CPU RSS monitor ---------------------------

class CPUProcessMonitor(threading.Thread):
    """
    Polls /proc/<pid>/status for VmRSS / VmHWM and keeps the peak (KiB).
    """
    def __init__(self, pid: int, interval: float = 0.25):
        super().__init__(daemon=True)
        self.pid = pid
        self.interval = interval
        self._stop_event = threading.Event()
        self.peak_kib = 0

    def stop(self):
        self._stop_event.set()

    def run(self):
        status_path = Path(f"/proc/{self.pid}/status")
        while not self._stop_event.is_set():
            try:
                txt = status_path.read_text()
                m_hwm = re.search(r"^VmHWM:\s*(.+)$", txt, re.MULTILINE)
                m_rss = re.search(r"^VmRSS:\s*(.+)$", txt, re.MULTILINE)
                kib = None
                if m_hwm:
                    kib = _parse_kib_from_status_val(m_hwm.group(1))
                if kib is None and m_rss:
                    kib = _parse_kib_from_status_val(m_rss.group(1))
                if kib is not None and kib > self.peak_kib:
                    self.peak_kib = kib
            except Exception:
                pass
            self._stop_event.wait(self.interval)

# --------------------------- GPU memory monitor + VRAM total ---------------------------

class GPUMonitor(threading.Thread):
    """
    Polls nvidia-smi (or NVML if available) to track per-process GPU memory.
    Records peak used memory (MiB) for the target pid on a given GPU index.
    """
    def __init__(self, pid: int, gpu_index: int = 0, interval: float = 0.25):
        super().__init__(daemon=True)
        self.pid = pid
        self.gpu_index = gpu_index
        self.interval = interval
        self._stop_event = threading.Event()
        self.peak_mib = 0
        self._use_nvml = False
        try:
            import pynvml  # optional
            self.pynvml = pynvml
            self.pynvml.nvmlInit()
            self._handle = self.pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
            self._use_nvml = True
        except Exception:
            self._use_nvml = False

    def stop(self):
        self._stop_event.set()

    def _poll_nvml(self):
        try:
            try:
                procs = self.pynvml.nvmlDeviceGetComputeRunningProcesses_v2(self._handle)
            except Exception:
                procs = self.pynvml.nvmlDeviceGetComputeRunningProcesses(self._handle)
            for p in procs:
                if int(p.pid) == int(self.pid):
                    used = getattr(p, "usedGpuMemory", 0)
                    if used and used > self.peak_mib * 1024 * 1024:
                        self.peak_mib = int(used // (1024 * 1024))
        except Exception:
            pass

    def _poll_nvidia_smi(self):
        try:
            out = subprocess.run(
                ["nvidia-smi",
                 f"--id={self.gpu_index}",
                 "--query-compute-apps=pid,used_memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=1.0
            )
            if out.returncode != 0:
                return
            for line in out.stdout.strip().splitlines():
                parts = [x.strip() for x in line.split(",")]
                if len(parts) != 2:
                    continue
                pid_str, mem_str = parts
                try:
                    if int(pid_str) == int(self.pid):
                        used_mib = int(mem_str)
                        if used_mib > self.peak_mib:
                            self.peak_mib = used_mib
                except Exception:
                    continue
        except Exception:
            pass

    def run(self):
        while not self._stop_event.is_set():
            if self._use_nvml:
                self._poll_nvml()
            elif cmd_exists("nvidia-smi"):
                self._poll_nvidia_smi()
            self._stop_event.wait(self.interval)

def detect_total_vram_mib(gpu_index: int = 0) -> Optional[int]:
    # NVML first
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        return int(info.total // (1024 * 1024))
    except Exception:
        pass
    # nvidia-smi fallback
    if cmd_exists("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", f"--id={gpu_index}",
                 "--query-gpu=memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2.0
            )
            if out.returncode == 0 and out.stdout.strip():
                return int(out.stdout.strip().splitlines()[0].strip())
        except Exception:
            pass
    return None

# ------------------------------ output parsing --------------------------------

# Specific lines from llama_print_timings
PROMPT_TOKPS = re.compile(r"prompt\s*eval\s*time\s*=\s*.*?\(\s*[0-9.]+\s*ms per token,\s*([0-9.]+)\s*tokens per second\)", re.IGNORECASE)
DECODE_TOKPS = re.compile(r"\beval\s*time\s*=\s*.*?\(\s*[0-9.]+\s*ms per token,\s*([0-9.]+)\s*tokens per second\)", re.IGNORECASE)
SAMPLE_TOKPS = re.compile(r"\bsample\s*time\s*=\s*.*?\(\s*(?:[0-9.]+)\s*ms per token,\s*([0-9.]+)\s*tokens per second\)", re.IGNORECASE)  # keep but rarely used

GENERIC_TOKPS = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(?:tok/s|tokens/s|tokens per second)\b", re.IGNORECASE)
OFFLOAD_LAYERS = re.compile(r"offloaded\s+(\d+)\s*/\s*(\d+)\s+layers\s+to\s+GPU", re.IGNORECASE)

# weights / compute / kv buffer sizes in logs
WEIGHTS_BUF = re.compile(r"llm_load_tensors:.*CUDA0 buffer size\s*=\s*([0-9.]+)\s*MiB", re.IGNORECASE)
COMPUTE_BUF = re.compile(r"CUDA0 compute buffer size\s*=\s*([0-9.]+)\s*MiB", re.IGNORECASE)
KV_BUF      = re.compile(r"CUDA0 KV buffer size\s*=\s*([0-9.]+)\s*MiB", re.IGNORECASE)

# meta
MODEL_SIZE_GIB = re.compile(r"llm_load_print_meta:\s*model size\s*=\s*([0-9.]+)\s*GiB", re.IGNORECASE)
MODEL_PARAMS   = re.compile(r"llm_load_print_meta:\s*model params\s*=\s*([0-9.]+)\s*B\b", re.IGNORECASE)

def parse_tokps_all(text: str) -> Dict[str, Optional[float]]:
    text = strip_ansi(text)
    out = {"decode_tokps": None, "prompt_tokps": None, "sample_tokps": None, "fallback_tokps": None}
    m = DECODE_TOKPS.search(text)
    if m:
        try: out["decode_tokps"] = float(m.group(1))
        except Exception: pass
    m = PROMPT_TOKPS.search(text)
    if m:
        try: out["prompt_tokps"] = float(m.group(1))
        except Exception: pass
    # sample is rarely present/useful; keep generic fallback
    last = None
    for m in GENERIC_TOKPS.finditer(text):
        try: last = float(m.group(1))
        except Exception: pass
    out["fallback_tokps"] = last
    return out

def parse_offload_info(text: str) -> Tuple[Optional[int], Optional[int]]:
    text = strip_ansi(text)
    m = OFFLOAD_LAYERS.search(text)
    if not m:
        return (None, None)
    try:
        return (int(m.group(1)), int(m.group(2)))
    except Exception:
        return (None, None)

def parse_buffers_and_meta(text: str) -> Dict[str, Optional[float]]:
    text = strip_ansi(text)
    d = {
        "weights_mib": None,
        "compute_mib": None,
        "kv_mib": None,
        "model_size_gib": None,
        "model_params_b": None,
    }
    m = WEIGHTS_BUF.search(text)
    if m:
        try: d["weights_mib"] = float(m.group(1))
        except Exception: pass
    m = COMPUTE_BUF.search(text)
    if m:
        try: d["compute_mib"] = float(m.group(1))
        except Exception: pass
    m = KV_BUF.search(text)
    if m:
        try: d["kv_mib"] = float(m.group(1))
        except Exception: pass
    m = MODEL_SIZE_GIB.search(text)
    if m:
        try: d["model_size_gib"] = float(m.group(1))
        except Exception: pass
    m = MODEL_PARAMS.search(text)
    if m:
        try:
            # the log prints "6.74 B" meaning billions; store as billions
            d["model_params_b"] = float(m.group(1))
        except Exception:
            pass
    return d

# ------------------------------ result struct ---------------------------------

class RunResult:
    def __init__(self, ok: bool, rc: int, wall_s: float,
                 ngl: int, threads: int,
                 decode_tokps: Optional[float], prompt_tokps: Optional[float], fallback_tokps: Optional[float],
                 gpu_peak_mib: Optional[int], cpu_peak_kib: Optional[int],
                 offloaded_layers: Optional[int], total_layers: Optional[int],
                 n_predict: int, prompt_len: int,
                 stdout_path: Path, stderr_path: Path, cmd: List[str], started_at: str):
        self.ok = ok
        self.rc = rc
        self.wall_s = wall_s
        self.ngl = ngl
        self.threads = threads
        self.decode_tokps = decode_tokps
        self.prompt_tokps = prompt_tokps
        self.fallback_tokps = fallback_tokps
        self.gpu_peak_mib = gpu_peak_mib
        self.cpu_peak_kib = cpu_peak_kib
        self.offloaded_layers = offloaded_layers
        self.total_layers = total_layers
        self.n_predict = n_predict
        self.prompt_len = prompt_len
        self.stdout_path = str(stdout_path)
        self.stderr_path = str(stderr_path)
        self.cmd = cmd
        self.started_at = started_at

    def main_tokps(self) -> Optional[float]:
        return self.decode_tokps or self.fallback_tokps

    def as_row(self, model_name: str) -> Dict[str, object]:
        return {
            "timestamp": self.started_at,
            "model": model_name,
            "ngl": self.ngl,
            "threads": self.threads,
            "decode_tokps": round(self.decode_tokps, 4) if self.decode_tokps is not None else None,
            "prompt_tokps": round(self.prompt_tokps, 4) if self.prompt_tokps is not None else None,
            "tokps_main": round(self.main_tokps(), 4) if self.main_tokps() is not None else None,
            "wall_s": round(self.wall_s, 3),
            "gpu_peak_mib": self.gpu_peak_mib,
            "cpu_peak_mib": int(self.cpu_peak_kib/1024) if self.cpu_peak_kib else None,
            "offloaded_layers": self.offloaded_layers,
            "total_layers": self.total_layers,
            "n_predict": self.n_predict,
            "prompt_len": self.prompt_len,
            "return_code": self.rc,
            "ok": self.ok,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "cmd": " ".join(shlex.quote(c) for c in self.cmd),
        }

# ------------------------------ command build ---------------------------------

def build_base_argv(args, ngl: int, threads: int, n_predict_override: Optional[int] = None, prompt_override: Optional[str] = None) -> List[str]:
    argv = []
    if args.model:
        argv += ["-m", str(args.model)]
    argv += [
        "-ngl", str(ngl),
        "-t", str(threads),
        "-n", str(n_predict_override if n_predict_override is not None else args.n_predict),
        "-s", str(args.seed),
        "-p", (prompt_override if prompt_override is not None else args.prompt),
    ]
    if args.ctx_size:
        argv += ["-c", str(args.ctx_size)]
    if args.temp is not None:
        argv += ["--temp", str(args.temp)]
    if args.top_p is not None:
        argv += ["--top-p", str(args.top_p)]
    if args.top_k is not None:
        argv += ["--top-k", str(args.top_k)]
    if args.extra_args:
        argv += shlex.split(args.extra_args)
    return argv

def compose_command(exec_via: str, binary: str, base_argv: List[str]) -> List[str]:
    if exec_via == "direct":
        return [binary] + base_argv
    elif exec_via == "sh":
        return ["sh", binary] + base_argv
    elif exec_via == "bash":
        return ["bash", binary] + base_argv
    else:  # auto
        return [binary] + base_argv

# ------------------------------ run once --------------------------------------

class ProcessLogs:
    def __init__(self, out_path: Path, err_path: Path):
        self.out_path = Path(out_path)
        self.err_path = Path(err_path)
    def read_merged(self) -> str:
        try:
            a = self.out_path.read_text(errors="ignore")
        except Exception:
            a = ""
        try:
            b = self.err_path.read_text(errors="ignore")
        except Exception:
            b = ""
        return (a + "\n" + b)

def run_once(args, ngl: int, threads: int, run_id: str, outdir: Path,
             n_predict_override: Optional[int] = None, prompt_override: Optional[str] = None) -> RunResult:
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    base_argv = build_base_argv(args, ngl, threads, n_predict_override, prompt_override)
    tag = f"ngl{ngl}_t{threads}_{run_id}"
    stdout_path = outdir / f"{tag}.stdout.txt"
    stderr_path = outdir / f"{tag}.stderr.txt"

    env = os.environ.copy()
    if args.gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env.setdefault("CUDA_DEVICE_MAX_CONNECTIONS", "1")

    cmd = compose_command(args.exec_via, str(args.binary), base_argv)

    t0 = time.time()
    rc = -1
    gpu_peak_mib = None
    cpu_peak_kib = None

    with open(stdout_path, "w") as f_out, open(stderr_path, "w") as f_err:
        try:
            proc = subprocess.Popen(cmd, stdout=f_out, stderr=f_err, env=env)
        except OSError as e:
            if e.errno == errno.ENOEXEC and args.exec_via in ("auto", "direct"):
                cmd = compose_command("sh", str(args.binary), base_argv)
                proc = subprocess.Popen(cmd, stdout=f_out, stderr=f_err, env=env)
            else:
                raise

        gpu_mon = None if args.no_gpu_mon else GPUMonitor(proc.pid, gpu_index=args.gpu or 0, interval=0.2)
        if gpu_mon: gpu_mon.start()
        cpu_mon = CPUProcessMonitor(proc.pid, interval=0.2)
        cpu_mon.start()

        try:
            rc = proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = -9

        if gpu_mon:
            gpu_mon.stop()
            gpu_mon.join(timeout=1.0)
            gpu_peak_mib = gpu_mon.peak_mib
        cpu_mon.stop()
        cpu_mon.join(timeout=1.0)
        cpu_peak_kib = cpu_mon.peak_kib

    wall = time.time() - t0

    logs = ProcessLogs(stdout_path, stderr_path).read_merged()
    logs = strip_ansi(logs)
    toks = parse_tokps_all(logs)
    off_gpu, off_total = parse_offload_info(logs)

    tok_main = toks["decode_tokps"] or toks["fallback_tokps"]
    ok = (rc == 0 and tok_main is not None)

    return RunResult(
        ok=ok, rc=rc, wall_s=wall,
        ngl=ngl, threads=threads,
        decode_tokps=toks["decode_tokps"], prompt_tokps=toks["prompt_tokps"], fallback_tokps=toks["fallback_tokps"],
        gpu_peak_mib=gpu_peak_mib, cpu_peak_kib=cpu_peak_kib,
        offloaded_layers=off_gpu, total_layers=off_total,
        n_predict=(n_predict_override if n_predict_override is not None else args.n_predict),
        prompt_len=len(prompt_override if prompt_override is not None else args.prompt),
        stdout_path=stdout_path, stderr_path=stderr_path,
        cmd=cmd, started_at=started_at
    )

# ----------------------------- search strategy --------------------------------

def parse_range(s: str) -> List[int]:
    s = s.strip().lower()
    if s == "auto":
        return []  # sentinel; caller handles auto
    if ":" in s:
        a, step, b = s.split(":"); a, step, b = int(a), int(step), int(b)
        if (b - a) * step <= 0: raise ValueError("bad range")
        return list(range(a, b + (1 if step > 0 else -1), step))
    if "-" in s and "," not in s:
        a, b = s.split("-"); a, b = int(a), int(b)
        return list(range(a, b + 1)) if a <= b else list(range(a, b - 1, -1))
    vals = [int(x) for x in s.split(",") if x.strip()]
    if not vals: raise ValueError("could not parse range")
    return vals

def best_of(results: List[RunResult]) -> Optional[RunResult]:
    ok_res = [r for r in results if r.ok and r.main_tokps() is not None]
    if not ok_res: return None
    ok_res.sort(key=lambda r: (r.main_tokps(), -r.wall_s), reverse=True)
    return ok_res[0]

def median_tokps(results: List[RunResult]) -> Optional[float]:
    vals = [r.main_tokps() for r in results if r.ok and r.main_tokps() is not None]
    return stats.median(vals) if vals else None

def run_repeats(args, ngl: int, threads: int, outdir: Path, repeats: int) -> List[RunResult]:
    res = []
    for i in range(repeats):
        r = run_once(args, ngl, threads, f"rep{i+1}", outdir)
        res.append(r)
        if not r.ok and i == 0:
            break
    return res

def hill_climb(args, ngl: int, base_threads: int, step: int, outdir: Path) -> Tuple[int, List[RunResult]]:
    tried: Dict[int, List[RunResult]] = {}

    def do_threads(t: int):
        if t < args.threads_min or t > args.threads_max: return
        if t in tried: return
        tried[t] = run_repeats(args, ngl, t, outdir, args.repeats)

    for t in [base_threads - step, base_threads, base_threads + step]:
        do_threads(t)

    def med(t: int) -> float:
        m = median_tokps(tried.get(t, []))
        return m if m is not None else -1.0

    base_med, minus_med, plus_med = med(base_threads), med(base_threads - step), med(base_threads + step)

    if base_med >= minus_med and base_med >= plus_med:
        all_runs = [r for runs in tried.values() for r in runs]
        return base_threads, all_runs

    direction = step if plus_med > minus_med else -step
    best_t, best_med = base_threads + direction, max(plus_med, minus_med)
    t = best_t + direction
    while args.threads_min <= t <= args.threads_max:
        do_threads(t)
        m = med(t)
        if m > best_med:
            best_t, best_med = t, m
            t += direction
        else:
            break
    all_runs = [r for runs in tried.values() for r in runs]
    return best_t, all_runs

# ------------------------------- preflight ------------------------------------

def preflight(args) -> None:
    bin_path = Path(args.binary)
    if not bin_path.exists():
        raise SystemExit(f"[preflight] binary not found: {args.binary}")

    arch = platform.machine().lower()
    if arch not in ("x86_64", "amd64"):
        print(f"[preflight] WARNING: host arch is {arch}; most llamafiles target x86_64.", file=sys.stderr)

    if not os.access(bin_path, os.X_OK):
        try:
            os.chmod(bin_path, os.stat(bin_path).st_mode | 0o111)
        except Exception:
            print(f"[preflight] couldn't chmod +x; run: chmod +x {args.binary}", file=sys.stderr)

    if cmd_exists("file"):
        try:
            out = subprocess.run(["file", "-b", str(bin_path)], capture_output=True, text=True, timeout=2.0)
            print(f"[preflight] file: {out.stdout.strip()}")
        except Exception:
            pass

    help_cmd = compose_command(args.exec_via, str(args.binary), ["-h"])
    try:
        sm = subprocess.run(help_cmd, capture_output=True, text=True, timeout=6.0)
        if sm.returncode not in (0, 1):
            print(f"[preflight] '-h' rc={sm.returncode}; continuing.", file=sys.stderr)
        else:
            print("[preflight] binary ran and printed help (good).")
    except subprocess.TimeoutExpired:
        print("[preflight] help timed out; continuing.", file=sys.stderr)
    except OSError as e:
        if e.errno == errno.ENOEXEC and args.exec_via in ("auto", "direct"):
            print("[preflight] got ENOEXEC; will run via 'sh' fallback automatically.", file=sys.stderr)
        else:
            raise

# ---------------------------- auto NGL + VRAM cap -----------------------------

def read_merged_paths(stdout_path: str, stderr_path: str) -> str:
    try:
        a = Path(stdout_path).read_text(errors="ignore")
    except Exception:
        a = ""
    try:
        b = Path(stderr_path).read_text(errors="ignore")
    except Exception:
        b = ""
    return strip_ansi(a + "\n" + b)

def probe_ngl_bounds(args, outdir: Path, physical_cores: int) -> Dict[str, object]:
    """
    Run two tiny probes (ngl=1 and ngl=2 if possible) to detect:
     - total_layers
     - model size (GiB)
     - VRAM peak at ngl=1 (MiB)
     - per-layer VRAM (MiB) estimated from (peak2 - peak1) and/or weights buffer differences
     - constant overhead (MiB) estimated as peak1 - per_layer
    """
    # choose a modest thread count for probe
    t_probe = max(args.threads_min, min(round_to_even(max(2, physical_cores // 2)), args.threads_max))
    # probe prompt is trivial; 1 token
    prompt_probe = "probe"
    # ngl=1
    r1 = run_once(args, ngl=1, threads=t_probe, run_id="probe1", outdir=outdir,
                  n_predict_override=1, prompt_override=prompt_probe)
    logs1 = read_merged_paths(r1.stdout_path, r1.stderr_path)
    bufs1 = parse_buffers_and_meta(logs1)
    off1, total_layers = parse_offload_info(logs1)
    peak1 = r1.gpu_peak_mib or 0
    model_size_gib = bufs1.get("model_size_gib")

    per_layer_mib = None
    peak2 = None
    weights1 = bufs1.get("weights_mib")
    weights2 = None

    # Try ngl=2 only if total_layers >= 2
    if total_layers and total_layers >= 2:
        r2 = run_once(args, ngl=2, threads=t_probe, run_id="probe2", outdir=outdir,
                      n_predict_override=1, prompt_override=prompt_probe)
        logs2 = read_merged_paths(r2.stdout_path, r2.stderr_path)
        bufs2 = parse_buffers_and_meta(logs2)
        peak2 = r2.gpu_peak_mib or 0
        weights2 = bufs2.get("weights_mib")
        # prefer weights delta if present; otherwise fall back on peak delta
        if weights1 is not None and weights2 is not None and weights2 > weights1:
            per_layer_mib = max(1.0, weights2 - weights1)
        elif peak2 and peak2 > peak1:
            per_layer_mib = max(1.0, float(peak2 - peak1))

    # If we couldn't get per-layer from ngl=2, approximate from ngl=1 weights_mib (often weights1 ~= cost of 1 layer)
    if per_layer_mib is None and weights1 is not None:
        per_layer_mib = max(1.0, float(weights1))

    # Estimate constant overhead (compute+KV+runtime+1st-layer extras)
    # Heuristic: overhead ≈ peak1 - per_layer_mib
    overhead_mib = None
    if per_layer_mib is not None and peak1:
        overhead_mib = max(0.0, float(peak1 - per_layer_mib))

    return {
        "total_layers": total_layers,
        "model_size_gib": model_size_gib,
        "peak1_mib": peak1,
        "peak2_mib": peak2,
        "per_layer_mib": per_layer_mib,
        "overhead_mib": overhead_mib,
        "threads_probe": t_probe,
        "weights1_mib": weights1,
        "weights2_mib": weights2,
    }

def plan_ngl_list_auto(args, physical_cores: int, outdir: Path) -> Tuple[List[int], Dict[str, object]]:
    """
    Decide an ngl list when args.ngl == 'auto', optionally respecting --vram-cap.
    Returns (ngl_list, probe_info).
    """
    probe = probe_ngl_bounds(args, outdir, physical_cores)
    total_layers = probe.get("total_layers") or 0
    per_layer_mib = probe.get("per_layer_mib")
    overhead_mib = probe.get("overhead_mib") or 0.0

    # Decide upper bound
    upper_by_layers = total_layers if total_layers > 0 else 33  # fallback
    upper_by_vram = None

    if args.vram_cap is not None:
        cap_mib = parse_size_to_mib(args.vram_cap)
        if cap_mib is None and str(args.vram_cap).lower() == "auto":
            total_vram = detect_total_vram_mib(args.gpu or 0)
            cap_mib = int(total_vram * 0.9) if total_vram else None
        if cap_mib and per_layer_mib:
            # NGL=1 consumption ≈ overhead + per_layer
            # For N ≥ 1: approx_vram(N) = overhead + per_layer * N
            # Solve for N: overhead + per_layer*N <= cap  =>  N <= (cap - overhead)/per_layer
            nmax = int((cap_mib - overhead_mib) // per_layer_mib)
            # clamp
            if nmax < 0:
                nmax = 0
            upper_by_vram = nmax

    # choose final upper
    upper = upper_by_layers
    if upper_by_vram is not None:
        upper = min(upper, upper_by_vram)

    # lower bound policy:
    # default to 10 if possible; otherwise 1 (so we still test something on tiny caps)
    if upper >= 10:
        lower = 10
    else:
        lower = 1

    if upper < lower:
        # Degenerate case (cap too small). At least test ngl=0/1 if possible.
        # We'll test ngl=1 if upper>=1 else skip offload tests.
        ngl_list = [1] if upper >= 1 else [0]
    else:
        ngl_list = list(range(lower, upper + 1))

    probe["ngl_upper_by_layers"] = upper_by_layers
    probe["ngl_upper_by_vram"] = upper_by_vram
    probe["ngl_auto_list"] = ngl_list
    return ngl_list, probe

# ------------------------------- main -----------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Tune llamafile/llama.cpp -ngl and CPU threads.")
    ap.add_argument("--binary", required=True, help="Path to .llamafile or llama.cpp binary (e.g., ./llava-v1.5-7b-q4.llamafile or ./llama-cli)")
    ap.add_argument("--model", default=None, help="Path to .gguf (only for plain llama.cpp binaries). Not used for .llamafile.")

    # NEW: default ngl 'auto' (detect layer count; choose range; respect --vram-cap if provided)
    ap.add_argument("--ngl", default="auto", help="NGL range or 'auto' (default). E.g., '10-33', '8,12,16', 'auto'.")

    # Thread search controls
    ap.add_argument("--threads", default=None, help="Thread sweep for FIRST ngl, e.g. '16:4:40' or '16,20,24,28,32'. If omitted, auto-plan is used.")
    ap.add_argument("--threads-min", type=int, default=4)
    ap.add_argument("--threads-max", type=int, default=None)

    # Auto-thread plan knobs (used only if --threads not provided)
    ap.add_argument("--reserve-cores", type=int, default=2, help="Reserve N cores for OS/IO when auto-planning (default 2).")
    ap.add_argument("--auto-start-frac", type=float, default=0.5, help="Start at this fraction of physical cores (default 0.5).")
    ap.add_argument("--auto-increment", type=int, default=2, help="Auto-plan increment (thread count) between points (default 2).")
    ap.add_argument("--auto-steps", type=int, default=3, help="Number of increments after start (default 3 → start,+2,+4,+6).")

    # Hill climb + repeats
    ap.add_argument("--step", type=int, default=1, help="Hill-climb step around previous best (default 1).")
    ap.add_argument("--repeats", type=int, default=2, help="Repeats per (ngl,threads) to median.")

    # Generation knobs
    ap.add_argument("--prompt", default="Benchmark hybrid CPU/GPU offload. Write one concise sentence.")
    ap.add_argument("-n", "--n-predict", type=int, default=160)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ctx-size", type=int, default=4096)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--extra-args", default="")

    # I/O & environment
    ap.add_argument("--outdir", default="tune_runs")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--no-gpu-mon", action="store_true")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--no-preflight", action="store_true")
    ap.add_argument("--exec-via", choices=["auto","direct","sh","bash"], default="auto",
                    help="How to execute the binary. 'auto' falls back to sh on ENOEXEC.")

    # NEW: VRAM cap
    ap.add_argument("--vram-cap", default=None, help="Limit ngl by VRAM cap (e.g., '10GiB', '10240MiB', 'auto' = 90% of total).")

    args = ap.parse_args()

    # Detect cores and set sane defaults
    physical = detect_physical_cores()
    logical = os.cpu_count() or physical
    if args.threads_max is None:
        args.threads_max = physical  # cap to physical cores by default

    if not args.no_preflight:
        preflight(args)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Decide ngl list
    ngl_list: List[int]
    probe_info: Dict[str, object] = {}
    if args.ngl.strip().lower() == "auto":
        ngl_list, probe_info = plan_ngl_list_auto(args, physical, outdir)
        print("[auto-ngl] probe results:")
        print("  total_layers:          ", probe_info.get("total_layers"))
        print("  model_size_gib:        ", probe_info.get("model_size_gib"))
        print("  per_layer_mib (est):   ", probe_info.get("per_layer_mib"))
        print("  overhead_mib (est):    ", probe_info.get("overhead_mib"))
        print("  peak1_mib:             ", probe_info.get("peak1_mib"))
        if probe_info.get("peak2_mib") is not None:
            print("  peak2_mib:             ", probe_info.get("peak2_mib"))
        if args.vram_cap:
            print("  vram_cap:              ", args.vram_cap)
            print("  ngl_upper_by_layers:   ", probe_info.get("ngl_upper_by_layers"))
            print("  ngl_upper_by_vram:     ", probe_info.get("ngl_upper_by_vram"))
        print("  ngl_auto_list:         ", ngl_list)
    else:
        ngl_list = parse_range(args.ngl)
        # If VRAM cap specified, just trim anything above calculated cap using a quick probe (1 layer only)
        if args.vram_cap:
            probe = probe_ngl_bounds(args, outdir, physical)
            per_layer_mib = probe.get("per_layer_mib")
            overhead_mib = probe.get("overhead_mib") or 0.0
            cap_mib = parse_size_to_mib(args.vram_cap) if args.vram_cap.lower() != "auto" else None
            if cap_mib is None and args.vram_cap.lower() == "auto":
                total_vram = detect_total_vram_mib(args.gpu or 0)
                cap_mib = int(total_vram * 0.9) if total_vram else None
            if cap_mib and per_layer_mib:
                nmax = int((cap_mib - overhead_mib) // per_layer_mib)
                nmax = max(0, nmax)
                before = list(ngl_list)
                ngl_list = [n for n in ngl_list if n <= nmax]
                print(f"[vram-cap] trimmed ngl list from {before} to {ngl_list} using cap ~{cap_mib} MiB")

    if not ngl_list:
        print("[tune] No NGL values to test after auto/cap planning. Exiting.")
        # write config snapshot and bail
        (outdir / "config.json").write_text(json.dumps(vars(args) | {
            "physical_cores": physical, "logical_cpus": logical, "probe_info": probe_info
        }, indent=2))
        sys.exit(0)

    # Build FIRST-NGL sweep thread list
    if args.threads:
        first_threads_list = parse_range(args.threads)
    else:
        start = max(args.threads_min, int(round(physical * args.auto_start_frac)))
        start = min(start, physical - args.reserve_cores)
        start = max(start, args.threads_min)
        start = round_to_even(start)
        upper = min(physical - args.reserve_cores, args.threads_max)
        points = [start]
        for i in range(1, args.auto_steps + 1):
            t = start + i * args.auto_increment
            if t <= upper:
                points.append(round_to_even(t))
        first_threads_list = sorted({t for t in points if args.threads_min <= t <= args.threads_max})
        if not first_threads_list:
            fallback = max(args.threads_min, min(upper, physical - args.reserve_cores))
            first_threads_list = [round_to_even(fallback)]

    results_csv = outdir / "results.csv"
    results_json = outdir / "results.json"
    best_csv = outdir / "best_by_ngl.csv"

    # Save config snapshot
    (outdir / "config.json").write_text(json.dumps(
        vars(args) | {"physical_cores": physical, "logical_cpus": logical, "probe_info": probe_info},
        indent=2
    ))

    print(f"[tune] Binary: {args.binary}")
    if args.model:
        print(f"[tune] Model:  {args.model}")
    print(f"[tune] CPU: physical={physical}, logical={logical}, threads_max={args.threads_max}, reserve={args.reserve_cores}")
    print(f"[tune] NGLs:   {ngl_list}")
    print(f"[tune] First NGL thread sweep: {first_threads_list}  (min={args.threads_min}, max={args.threads_max})")
    print(f"[tune] Hill-climb step: ±{args.step}, repeats: {args.repeats}, exec-via: {args.exec_via}")

    all_results: List[RunResult] = []
    best_per_ngl: Dict[int, Dict[str, object]] = {}
    first = True
    prev_best_threads = None

    for ngl in ngl_list:
        print(f"\n=== NGL {ngl} ===")
        if first:
            tried_runs: List[RunResult] = []
            for t in first_threads_list:
                print(f"[ngl {ngl}] testing threads={t} (x{args.repeats}) ...")
                tried_runs.extend(run_repeats(args, ngl, t, outdir, args.repeats))
            by_threads: Dict[int, List[RunResult]] = {}
            for r in tried_runs:
                by_threads.setdefault(r.threads, []).append(r)

            best_t = None
            best_med = -1.0
            for t, runs in by_threads.items():
                med = median_tokps(runs)
                if med is None:
                    continue
                if med > best_med:
                    best_med = med
                    best_t = t
            if best_t is None:
                print(f"[ngl {ngl}] no successful runs, skipping.")
                first = False
                prev_best_threads = None
                all_results.extend(tried_runs)
                continue

            all_results.extend(tried_runs)
            best_run = best_of(by_threads[best_t])
            best_per_ngl[ngl] = {
                "ngl": ngl, "best_threads": best_t,
                "median_tokps": round(best_med, 4),
                "best_tokps_main": (round(best_run.main_tokps(), 4) if best_run and best_run.main_tokps() else None),
                "wall_s": (round(best_run.wall_s, 3) if best_run else None),
                "gpu_peak_mib": best_run.gpu_peak_mib if best_run else None,
                "cpu_peak_mib": int(best_run.cpu_peak_kib/1024) if best_run and best_run.cpu_peak_kib else None,
                "offloaded_layers": best_run.offloaded_layers if best_run else None,
                "total_layers": best_run.total_layers if best_run else None,
            }
            print(f"[ngl {ngl}] best threads={best_t}  median tok/s={best_med:.2f}")
            prev_best_threads = best_t
            first = False
        else:
            base = prev_best_threads or first_threads_list[-1]
            best_t, runs = hill_climb(args, ngl, base, args.step, outdir)
            all_results.extend(runs)
            by_t: Dict[int, List[RunResult]] = {}
            for r in runs:
                by_t.setdefault(r.threads, []).append(r)
            med = median_tokps(by_t[best_t]) if best_t in by_t else None
            best_run = best_of(by_t[best_t]) if best_t in by_t else None
            best_per_ngl[ngl] = {
                "ngl": ngl, "best_threads": best_t,
                "median_tokps": round(med, 4) if med else None,
                "best_tokps_main": (round(best_run.main_tokps(), 4) if best_run and best_run.main_tokps() else None),
                "wall_s": (round(best_run.wall_s, 3) if best_run else None),
                "gpu_peak_mib": best_run.gpu_peak_mib if best_run else None,
                "cpu_peak_mib": int(best_run.cpu_peak_kib/1024) if best_run and best_run.cpu_peak_kib else None,
                "offloaded_layers": best_run.offloaded_layers if best_run else None,
                "total_layers": best_run.total_layers if best_run else None,
            }
            print(f"[ngl {ngl}] best threads={best_t}  median tok/s={(med if med else -1):.2f}")
            prev_best_threads = best_t

    # write outputs
    with (outdir / "results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "timestamp", "model", "ngl", "threads",
            "decode_tokps", "prompt_tokps", "tokps_main",
            "wall_s", "gpu_peak_mib", "cpu_peak_mib",
            "offloaded_layers", "total_layers",
            "n_predict", "prompt_len",
            "return_code", "ok", "stdout_path", "stderr_path", "cmd"
        ])
        w.writeheader()
        for r in all_results:
            w.writerow(r.as_row(model_name=(args.model or Path(args.binary).name)))

    with (outdir / "results.json").open("w") as f:
        json.dump([r.as_row(model_name=(args.model or Path(args.binary).name)) for r in all_results], f, indent=2)

    with (outdir / "best_by_ngl.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "ngl","best_threads","median_tokps","best_tokps_main","wall_s",
            "gpu_peak_mib","cpu_peak_mib","offloaded_layers","total_layers"
        ])
        w.writeheader()
        for ngl in ngl_list:
            row = best_per_ngl.get(ngl, {})
            if row:
                w.writerow(row)

    print("\n[tune] done.")
    print(f"[tune] all runs:      {outdir / 'results.csv'}")
    print(f"[tune] all runs JSON: {outdir / 'results.json'}")
    print(f"[tune] best per ngl:  {outdir / 'best_by_ngl.csv'}")

if __name__ == "__main__":
    main()
