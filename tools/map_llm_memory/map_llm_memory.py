#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
map_llm_memory.py — robust VRAM/CPU/KV/compute mapping vs -ngl for llamafile / llama.cpp

Key features
------------
- Auto mode chooses Server vs CLI correctly:
    * If extra args include server flags (--host/--port/--nobrowser), use Server mode
    * Else use CLI mode. Server-only flags are stripped in CLI mode to avoid early exits.
- Server mode:
    * Launch server, watch logs for "HTTP server listening" (readiness)
    * Sample GPU VRAM for a short window while server is up
    * Parse weights/compute/KV/CLIP buffers from logs
    * Shutdown cleanly, wait for port-close, proceed to next -ngl
- CLI mode:
    * Run a tiny generation (-p "probe" -n 1, configurable)
    * Write BOTH stdout and stderr to files (avoid drop due to buffering)
    * Monitor peak GPU VRAM and peak CPU RSS while the process is running
    * Parse same buffer/metadata lines from merged logs
- Common:
    * Detect total layers (from "offloaded X/Y" and/or meta)
    * Compute per-layer deltas, avg per-layer VRAM, overhead estimate
    * Print non-zero return codes for quick diagnosis
    * Write a single log: <binary>.log

This script borrows proven ideas (per-PID GPU/CPU monitors, merged-log parsing,
NVML/nvidia-smi use, offload+buffer regexes) from the user's tuner script. :contentReference[oaicite:1]{index=1}
"""

import argparse
import datetime as dt
import errno
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------- small utils ---------------------------

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s or "")

def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")

def cmd_exists(name: str) -> bool:
    from shutil import which
    return which(name) is not None

def parse_size_to_mib(s: str) -> Optional[float]:
    """
    Accept strings like:
      "353.00 MiB", "2048.00 MiB", "3.80 GiB", "3891.24 MiB", "169.18 MB", "4.84 GB"
    Returns MiB as float.
    """
    if not s:
        return None
    s = s.strip()
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGT]?i?B)\s*$", s, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()

    if unit == "mib":
        return val
    if unit == "gib":
        return val * 1024.0
    if unit == "tib":
        return val * 1024.0 * 1024.0
    if unit == "kb" or unit == "kib":
        return val / 1024.0
    if unit == "mb":
        # decimal MB to MiB
        return val * (1000.0**2) / (1024.0**2)
    if unit == "gb":
        return val * (1000.0**3) / (1024.0**2)
    if unit == "tb":
        return val * (1000.0**4) / (1024.0**2)
    return None

def round2(x: Optional[float]) -> Optional[float]:
    return None if x is None else float(f"{x:.2f}")

def safe_chmod_exec(p: Path):
    try:
        st = p.stat()
        os.chmod(p, st.st_mode | 0o111)
    except Exception:
        pass

def is_port_open(host: str, port: int, timeout_s: float = 0.25) -> bool:
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False
    for family, socktype, proto, canonname, sockaddr in infos:
        if socktype != socket.SOCK_STREAM:
            continue
        try:
            s = socket.socket(family, socktype, proto)
            s.settimeout(timeout_s)
            s.connect(sockaddr)
            s.close()
            return True
        except Exception:
            pass
    return False

def wait_port_closed(host: str, port: int, timeout_s: float = 10.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        if not is_port_open(host, port, timeout_s=0.15):
            return True
        time.sleep(0.2)
    return False

# --------------------------- CPU RSS monitor ---------------------------

def _parse_kib_from_status_val(s: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*kB", s or "")
    return int(m.group(1)) if m else None

class CPUProcessMonitor(threading.Thread):
    """
    Polls /proc/<pid>/status for VmRSS / VmHWM and keeps the peak (KiB).
    """
    def __init__(self, pid: int, interval: float = 0.2):
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

# --------------------------- GPU memory monitor (sum across GPUs) ---------------------------

class GPUMonitorAll(threading.Thread):
    """
    Polls NVML (if available) or `nvidia-smi` (compute-apps) to track total GPU memory
    used by the target PID (summed across GPUs). Records peak (MiB).
    """
    def __init__(self, pid: int, interval: float = 0.1):
        super().__init__(daemon=True)
        self.pid = pid
        self.interval = interval
        self._stop_event = threading.Event()
        self.peak_total_mib = 0
        self._use_nvml = False
        try:
            import pynvml  # type: ignore
            self.pynvml = pynvml
            self.pynvml.nvmlInit()
            self._nvml_device_count = self.pynvml.nvmlDeviceGetCount()
            self._use_nvml = True
        except Exception:
            self._use_nvml = False

    def stop(self):
        self._stop_event.set()

    def _poll_nvml(self):
        total = 0
        try:
            for i in range(self._nvml_device_count):
                try:
                    h = self.pynvml.nvmlDeviceGetHandleByIndex(i)
                    try:
                        procs = self.pynvml.nvmlDeviceGetComputeRunningProcesses_v2(h)
                    except Exception:
                        procs = self.pynvml.nvmlDeviceGetComputeRunningProcesses(h)
                    for p in procs:
                        if int(p.pid) == int(self.pid):
                            used = getattr(p, "usedGpuMemory", 0) or 0
                            total += int(used // (1024 * 1024))
                except Exception:
                    continue
        except Exception:
            return
        if total > self.peak_total_mib:
            self.peak_total_mib = total

    def _run_with_timeout(self, cmd: List[str], timeout_s: float = 0.8) -> Optional[str]:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
            if res.returncode == 0:
                return res.stdout
        except Exception:
            pass
        return None

    def _poll_nvidia_smi(self):
        if not cmd_exists("nvidia-smi"):
            return
        out = self._run_with_timeout(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            timeout_s=0.8
        )
        if not out:
            return
        total = 0
        for line in out.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 2:
                continue
            pid_str, mem_mib_str = parts
            try:
                if int(pid_str) == int(self.pid):
                    total += int(mem_mib_str)
            except Exception:
                continue
        if total > self.peak_total_mib:
            self.peak_total_mib = total

    def run(self):
        while not self._stop_event.is_set():
            if self._use_nvml:
                self._poll_nvml()
            else:
                self._poll_nvidia_smi()
            self._stop_event.wait(self.interval)

# ------------------------------ parsing --------------------------------

# Layers
RE_N_LAYER          = re.compile(r"\bn_layer\s*=\s*(\d+)", re.IGNORECASE)
RE_BLOCK_COUNT      = re.compile(r"llama\.block_count\s*u32\s*=\s*(\d+)", re.IGNORECASE)
RE_OFFLOADED        = re.compile(r"offloaded\s+(\d+)\s*/\s*(\d+)\s+layers\s+to\s+GPU", re.IGNORECASE)

# Buffers & meta (LLM)
RE_CPU_BUFFER       = re.compile(r"CPU buffer size\s*=\s*([0-9.]+\s*[KMGT]?i?B)", re.IGNORECASE)
RE_WEIGHTS_BUF      = re.compile(r"(?:CUDA0|GPU\d+)\s+buffer size\s*=\s*([0-9.]+\s*[KMGT]?i?B)", re.IGNORECASE)
RE_COMPUTE_BUF      = re.compile(r"(?:CUDA0|CUDA_Host|CPU)\s+compute buffer size\s*=\s*([0-9.]+\s*[KMGT]?i?B)", re.IGNORECASE)
RE_KV_GPU_BUF       = re.compile(r"(?:CUDA0)\s+KV buffer size\s*=\s*([0-9.]+\s*[KMGT]?i?B)", re.IGNORECASE)
RE_KV_CPU_BUF       = re.compile(r"(?:CPU KV buffer size|KV self size)\s*=\s*([0-9.]+\s*[KMGT]?i?B)", re.IGNORECASE)

# CLIP (mmproj)
RE_CLIP_USING_CUDA  = re.compile(r"clip_model_load:\s*CLIP using CUDA backend", re.IGNORECASE)
RE_CLIP_PARAMS_BACK = re.compile(r"params backend buffer size\s*=\s*([0-9.]+\s*[KMGT]?i?B)", re.IGNORECASE)
RE_CLIP_COMPUTE     = re.compile(r"compute allocated memory:\s*([0-9.]+\s*[KMGT]?i?B)", re.IGNORECASE)

# Model meta
RE_MODEL_SIZE       = re.compile(r"model size\s*=\s*([0-9.]+\s*GiB)", re.IGNORECASE)
RE_MODEL_PARAMS_B   = re.compile(r"model params\s*=\s*([0-9.]+)\s*B\b", re.IGNORECASE)  # "6.74 B" (billions)

# Readiness (server)
RE_READY            = re.compile(r"(HTTP server listening|server listening at http)", re.IGNORECASE)

def parse_layers(text: str) -> Tuple[Optional[int], Optional[int]]:
    t = strip_ansi(text)
    n_layer = None
    m = RE_N_LAYER.search(t)
    if m:
        try: n_layer = int(m.group(1))
        except Exception: pass
    m2 = RE_BLOCK_COUNT.search(t)
    if m2:
        try:
            blk = int(m2.group(1))
            n_layer = max(n_layer or 0, blk) if n_layer is not None else blk
        except Exception:
            pass
    off_total = None
    m3 = RE_OFFLOADED.search(t)
    if m3:
        try:
            _off = int(m3.group(1))
            off_total = int(m3.group(2))
            if off_total and (n_layer is None or off_total > n_layer):
                n_layer = off_total
        except Exception:
            pass
    return n_layer, off_total

def parse_buffers_and_meta(text: str) -> Dict[str, Optional[float]]:
    """
    Parse sizes; returns MiB floats (or None).
    gpu_weights_mib includes only LLM 'CUDA0 buffer size'.
    gpu_compute_mib combines any 'CUDA0 compute buffer size' lines (usually one).
    gpu_kv_mib parses CUDA KV; cpu_kv_mib parses CPU KV mentions.
    clip_* fields parsed only if CLIP uses CUDA backend (heuristic).
    """
    t = strip_ansi(text)
    clip_cuda = bool(RE_CLIP_USING_CUDA.search(t))

    out: Dict[str, Optional[float]] = {
        "cpu_buffer_mib": None,
        "gpu_weights_mib": None,
        "gpu_compute_mib": None,
        "gpu_kv_mib": None,
        "cpu_kv_mib": None,
        "clip_params_mib": None,
        "clip_compute_mib": None,
        "model_size_mib": None,
        "model_params_b": None,
    }

    m = RE_CPU_BUFFER.search(t)
    if m:
        out["cpu_buffer_mib"] = round2(parse_size_to_mib(m.group(1)))

    m = RE_WEIGHTS_BUF.search(t)
    if m:
        out["gpu_weights_mib"] = round2(parse_size_to_mib(m.group(1)))

    # If multiple compute lines exist, take the largest (usually CUDA0 compute)
    compute_vals = [parse_size_to_mib(m.group(1)) for m in RE_COMPUTE_BUF.finditer(t)]
    compute_vals = [x for x in compute_vals if x is not None]
    if compute_vals:
        out["gpu_compute_mib"] = round2(max(compute_vals))

    m = RE_KV_GPU_BUF.search(t)
    if m:
        out["gpu_kv_mib"] = round2(parse_size_to_mib(m.group(1)))

    m = RE_KV_CPU_BUF.search(t)
    if m:
        out["cpu_kv_mib"] = round2(parse_size_to_mib(m.group(1)))

    if clip_cuda:
        m = RE_CLIP_PARAMS_BACK.search(t)
        if m:
            out["clip_params_mib"] = round2(parse_size_to_mib(m.group(1)))
        m = RE_CLIP_COMPUTE.search(t)
        if m:
            out["clip_compute_mib"] = round2(parse_size_to_mib(m.group(1)))

    m = RE_MODEL_SIZE.search(t)
    if m:
        out["model_size_mib"] = round2(parse_size_to_mib(m.group(1)))

    m = RE_MODEL_PARAMS_B.search(t)
    if m:
        try:
            out["model_params_b"] = float(m.group(1))
        except Exception:
            pass

    return out

# ------------------------------ exec helpers --------------------------------

def compose_command(exec_via: str, binary: str, argv: List[str]) -> List[str]:
    if exec_via == "direct":
        return [binary] + argv
    elif exec_via == "sh":
        return ["sh", binary] + argv
    elif exec_via == "bash":
        return ["bash", binary] + argv
    else:  # auto/direct
        return [binary] + argv

# ------------------------------ CLI mode ------------------------------------

def run_cli_once(binary: Path,
                 ngl: int,
                 ctx_size: int,
                 prompt: str,
                 n_predict: int,
                 extra_args_cli: str,
                 exec_via: str,
                 timeout_s: int) -> Dict:
    """
    Run a tiny CLI generation; capture stdout+stderr to memory;
    record peak GPU VRAM and peak CPU RSS while running.
    """
    # Build argv (CLI flags only)
    argv = ["-ngl", str(ngl), "-c", str(ctx_size), "-p", prompt, "-n", str(n_predict)]
    if extra_args_cli:
        argv += shlex.split(extra_args_cli)

    env = os.environ.copy()
    env.setdefault("LLAMA_LOG_COLORS", "0")
    env.setdefault("LLAMA_LOG_LEVEL", "INFO")

    cmd = compose_command(exec_via, str(binary), argv)

    # Start process
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )
    except OSError as e:
        if e.errno == errno.ENOEXEC and exec_via in ("auto", "direct"):
            # fall back to sh for APE llamafiles
            cmd = compose_command("sh", str(binary), argv)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True, env=env
            )
        else:
            raise

    # start monitors
    gpu_mon = GPUMonitorAll(proc.pid, interval=0.05)
    gpu_mon.start()
    cpu_mon = CPUProcessMonitor(proc.pid, interval=0.05)
    cpu_mon.start()

    # Collect output (both streams)
    out_lines: List[str] = []
    err_lines: List[str] = []

    def reader(fh, buf: List[str]):
        try:
            for line in iter(fh.readline, ''):
                buf.append(line)
        except Exception:
            pass

    t_out = threading.Thread(target=reader, args=(proc.stdout, out_lines), daemon=True)
    t_err = threading.Thread(target=reader, args=(proc.stderr, err_lines), daemon=True)
    t_out.start(); t_err.start()

    # wait with timeout
    rc = -1
    try:
        rc = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            pass
        rc = -9

    # stop monitors
    gpu_mon.stop(); gpu_mon.join(timeout=1.0)
    cpu_mon.stop(); cpu_mon.join(timeout=1.0)

    try:
        proc.stdout.close()
        proc.stderr.close()
    except Exception:
        pass

    t_out.join(timeout=1.0)
    t_err.join(timeout=1.0)

    merged_text = strip_ansi("".join(out_lines) + "\n" + "".join(err_lines))

    return {
        "cmd": cmd,
        "rc": rc,
        "text": merged_text,
        "peak_gpu_mib": gpu_mon.peak_total_mib or None,
        "peak_cpu_mib": int(cpu_mon.peak_kib/1024) if cpu_mon.peak_kib else None,
    }

# ------------------------------ Server mode ----------------------------------

def run_server_once(binary: Path,
                    ngl: int,
                    ctx_size: int,
                    extra_args_srv: str,
                    host: str,
                    port: int,
                    sample_seconds: float,
                    exec_via: str,
                    timeout_s: int) -> Dict:
    """
    Start server; detect readiness from logs; sample VRAM while running; parse logs; shutdown.
    """
    argv = []
    # pass server args first, then ctx/ngl
    if extra_args_srv:
        argv += shlex.split(extra_args_srv)
    # add host/port only if not already present
    toks = shlex.split(extra_args_srv or "")
    if "--host" not in toks:
        argv += ["--host", host]
    if "--port" not in toks and "-p" not in toks:
        argv += ["--port", str(port)]

    # Pass ctx and ngl
    if "--ctx-size" not in toks and "-c" not in toks:
        argv += ["--ctx-size", str(ctx_size)]
    argv += ["-ngl", str(ngl)]

    env = os.environ.copy()
    env.setdefault("LLAMA_LOG_COLORS", "0")
    env.setdefault("LLAMA_LOG_LEVEL", "INFO")

    cmd = compose_command(exec_via, str(binary), argv)

    # Launch
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )
    except OSError as e:
        if e.errno == errno.ENOEXEC and exec_via in ("auto", "direct"):
            cmd = compose_command("sh", str(binary), argv)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, universal_newlines=True, env=env
            )
        else:
            raise

    # Read logs + readiness detection
    lines: List[str] = []
    ready_evt = threading.Event()

    def reader():
        try:
            for line in iter(proc.stdout.readline, ''):
                lines.append(line)
                if not ready_evt.is_set() and RE_READY.search(line):
                    ready_evt.set()
        except Exception:
            pass

    t_reader = threading.Thread(target=reader, daemon=True)
    t_reader.start()

    # wait for readiness or early exit
    start_t = time.time()
    server_ready = False
    while time.time() - start_t < timeout_s:
        if proc.poll() is not None:
            break
        if ready_evt.is_set():
            server_ready = True
            break
        time.sleep(0.05)

    # if ready, sample VRAM for sample_seconds
    gpu_peak = None
    cpu_peak = None
    if server_ready:
        gpu_mon = GPUMonitorAll(proc.pid, interval=0.05)
        gpu_mon.start()
        cpu_mon = CPUProcessMonitor(proc.pid, interval=0.05)
        cpu_mon.start()
        time.sleep(max(0.1, sample_seconds))
        gpu_mon.stop(); gpu_mon.join(timeout=1.0)
        cpu_mon.stop(); cpu_mon.join(timeout=1.0)
        gpu_peak = gpu_mon.peak_total_mib or None
        cpu_peak = int(cpu_mon.peak_kib/1024) if cpu_mon.peak_kib else None

    # shutdown
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    # close reader
    try:
        proc.stdout.close()
    except Exception:
        pass
    t_reader.join(timeout=1.0)

    merged_text = strip_ansi("".join(lines))

    return {
        "cmd": cmd,
        "rc": proc.returncode,
        "text": merged_text,
        "server_ready": server_ready,
        "peak_gpu_mib": gpu_peak,
        "peak_cpu_mib": cpu_peak,
        "host": host,
        "port": port,
    }

# ------------------------------ main -----------------------------------------

SERVER_FLAGS = {"--host", "--port", "-p", "--nobrowser"}

def looks_like_server_args(extra_args: str) -> bool:
    if not extra_args:
        return False
    toks = set(shlex.split(extra_args))
    return any(f in toks or any(tok.startswith(f + "=") for tok in toks) for f in SERVER_FLAGS)

def filter_server_only_flags(extra_args: str) -> str:
    """
    Remove flags that are server-only so CLI runs don't exit early.
    Keep --mlock (it’s valid for CLI).
    """
    if not extra_args:
        return ""
    toks = shlex.split(extra_args)
    out = []
    skip_next = False
    for i, tok in enumerate(toks):
        if skip_next:
            skip_next = False
            continue
        if tok in ("--host", "--port", "-p", "--nobrowser"):
            # skip value if provided separately
            if tok in ("--host", "--port", "-p"):
                # lookahead
                if i + 1 < len(toks) and not toks[i+1].startswith("-"):
                    skip_next = True
            continue
        if tok.startswith("--host=") or tok.startswith("--port=") or tok.startswith("-p"):
            continue
        out.append(tok)
    return " ".join(out)

def main():
    ap = argparse.ArgumentParser(description="Map GPU/CPU/KV/compute memory vs -ngl for llamafile / llama.cpp.")
    ap.add_argument("--binary", required=True, help="Path to llamafile/llama.cpp binary (e.g., ./llava-v1.5-7b-q4.llamafile)")
    ap.add_argument("--mode", choices=["auto","server","cli"], default="auto",
                    help="auto picks server if server flags are present; otherwise CLI.")
    ap.add_argument("--extra-args", default="",
                    help="Additional args passed to the binary. "
                         "If server flags appear (--host/--port/--nobrowser), server mode is used.")
    ap.add_argument("--ctx-size", type=int, default=4096, help="Context size; passed as --ctx-size (server) or -c (cli).")
    ap.add_argument("--min-ngl", type=int, default=0, help="Start -ngl.")
    ap.add_argument("--max-ngl", type=int, default=33, help="End -ngl.")
    ap.add_argument("--prompt", default="probe", help="CLI mode prompt text.")
    ap.add_argument("--n-predict", type=int, default=1, help="CLI mode tokens to generate.")
    ap.add_argument("--server-host", default="127.0.0.1", help="Server mode default host (used if not in extra-args).")
    ap.add_argument("--server-port", type=int, default=8900, help="Server mode default port (used if not in extra-args).")
    ap.add_argument("--server-sample-seconds", type=float, default=2.0, help="How long to sample VRAM after readiness (server mode).")
    ap.add_argument("--timeout", type=int, default=300, help="Per run timeout seconds.")
    ap.add_argument("--exec-via", choices=["auto","direct","sh","bash"], default="auto",
                    help="How to execute the binary. 'auto' falls back to 'sh' on ENOEXEC.")
    args = ap.parse_args()

    binary = Path(args.binary).resolve()
    if not binary.exists():
        print(f"ERROR: binary not found: {binary}", file=sys.stderr)
        sys.exit(1)
    safe_chmod_exec(binary)

    # Decide mode
    mode = args.mode
    auto_server = looks_like_server_args(args.extra_args)
    if mode == "auto":
        mode = "server" if auto_server else "cli"

    # Prepare log file
    log_path = binary.with_suffix(binary.suffix + ".log")
    header = []
    header.append("="*80)
    header.append(f"LLM Memory Mapping for: {binary.name}")
    header.append(f"Path           : {binary}")
    header.append(f"Started        : {now_iso()}")
    header.append(f"Mode           : {mode}  (auto_server_detected={auto_server})")
    header.append(f"Extra args     : {args.extra_args or '(none)'}")
    header.append(f"Context Size   : {args.ctx_size}")
    header.append(f"NGL range      : {args.min_ngl}..{args.max_ngl}")
    if mode == "server":
        header.append(f"Server probe   : host={args.server_host}, port={args.server_port}, sample={args.server_sample_seconds}s")
    else:
        header.append(f"CLI probe      : prompt={args.prompt!r}, n_predict={args.n_predict}")
    header.append(f"Exec Via       : {args.exec_via}")
    header.append("="*80)
    header_txt = "\n".join(header) + "\n\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(header_txt)
    except Exception as e:
        print(f"ERROR: cannot write log file at {log_path}: {e}", file=sys.stderr)
        sys.exit(1)
    print(header_txt, end="")

    results = []
    detected_layers = None

    for ngl in range(args.min_ngl, args.max_ngl + 1):
        print(f"[*] -ngl {ngl} ...")
        if mode == "cli":
            extra_cli = filter_server_only_flags(args.extra_args)
            res = run_cli_once(
                binary=binary,
                ngl=ngl,
                ctx_size=args.ctx_size,
                prompt=args.prompt,
                n_predict=args.n_predict,
                extra_args_cli=extra_cli,
                exec_via=args.exec_via,
                timeout_s=args.timeout,
            )
        else:
            # server
            res = run_server_once(
                binary=binary,
                ngl=ngl,
                ctx_size=args.ctx_size,
                extra_args_srv=args.extra_args,
                host=args.server_host,
                port=args.server_port,
                sample_seconds=args.server_sample_seconds,
                exec_via=args.exec_via,
                timeout_s=args.timeout,
            )

        text = res.get("text","")
        rc = res.get("rc")
        gpu_peak = res.get("peak_gpu_mib")
        cpu_peak = res.get("peak_cpu_mib")

        # parse
        layers, off_total = parse_layers(text)
        bufs = parse_buffers_and_meta(text)

        if layers and (detected_layers is None or layers > detected_layers):
            detected_layers = layers

        # log chunk
        def fmt(x):
            return "N/A" if x is None else (f"{x:.2f}" if isinstance(x, float) else str(x))

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[Run -ngl {ngl}]\n")
            f.write(f"  cmd               : {' '.join(shlex.quote(c) for c in res.get('cmd', []))}\n")
            f.write(f"  return_code       : {rc}\n")
            if mode == "server":
                f.write(f"  server_ready      : {res.get('server_ready')}\n")
                f.write(f"  effective_host    : {res.get('host')}\n")
                f.write(f"  effective_port    : {res.get('port')}\n")
            f.write(f"  peak_gpu_mib      : {fmt(gpu_peak)}\n")
            f.write(f"  peak_cpu_mib      : {fmt(cpu_peak)}\n")
            f.write(f"  parsed.n_layer    : {fmt(layers)}\n")
            f.write(f"  parsed.off_total  : {fmt(off_total)}\n")
            f.write(f"  parsed.cpu_buffer : {fmt(bufs.get('cpu_buffer_mib'))} MiB\n")
            f.write(f"  parsed.gpu_weights: {fmt(bufs.get('gpu_weights_mib'))} MiB\n")
            f.write(f"  parsed.gpu_compute: {fmt(bufs.get('gpu_compute_mib'))} MiB\n")
            f.write(f"  parsed.gpu_kv     : {fmt(bufs.get('gpu_kv_mib'))} MiB\n")
            f.write(f"  parsed.cpu_kv     : {fmt(bufs.get('cpu_kv_mib'))} MiB\n")
            f.write(f"  parsed.clip_params: {fmt(bufs.get('clip_params_mib'))} MiB\n")
            f.write(f"  parsed.clip_compute: {fmt(bufs.get('clip_compute_mib'))} MiB\n")
            f.write(f"  parsed.model_size : {fmt(bufs.get('model_size_mib'))} MiB\n")
            f.write(f"  parsed.params(B)  : {fmt(bufs.get('model_params_b'))}\n")
            f.write("\n")

        # Print quick status (include rc if nonzero)
        rc_str = "" if rc == 0 else f" rc={rc}"
        print(f"    VRAM={fmt(gpu_peak)} MiB | CPU={fmt(cpu_peak)} MiB | {('ready' if res.get('server_ready') else 'done')} {rc_str}")

        results.append({
            "ngl": ngl,
            "gpu_peak_mib": gpu_peak,
            "cpu_peak_mib": cpu_peak,
            "bufs": bufs,
        })

        # For server: ensure port closes before next run if port fixed
        if mode == "server":
            wait_port_closed(args.server_host if args.server_host != "0.0.0.0" else "127.0.0.1",
                             args.server_port, timeout_s=10.0)

    # Compute deltas (prefer GPU measured peak; if none, fall back to parsed sums)
    def measured_or_estimate(r: Dict) -> Optional[float]:
        if r["gpu_peak_mib"] is not None:
            return float(r["gpu_peak_mib"])
        b = r["bufs"]
        # estimate = weights + compute + kv + clip params/compute (when present)
        parts = []
        for k in ("gpu_weights_mib","gpu_compute_mib","gpu_kv_mib","clip_params_mib","clip_compute_mib"):
            if b.get(k) is not None:
                parts.append(float(b[k]))
        return sum(parts) if parts else None

    start = args.min_ngl
    last  = args.max_ngl
    v_by_ngl: Dict[int, Optional[float]] = {r["ngl"]: measured_or_estimate(r) for r in results}
    deltas = []
    for ngl in range(start + 1, last + 1):
        a = v_by_ngl.get(ngl - 1)
        b = v_by_ngl.get(ngl)
        deltas.append(None if (a is None or b is None) else (b - a))

    real = [d for d in deltas if d is not None]
    avg_delta = sum(real)/len(real) if real else None

    baseline = v_by_ngl.get(start)
    full     = v_by_ngl.get(last)
    weights_on_gpu_est = (full - baseline) if (full is not None and baseline is not None) else None

    # heuristic overhead
    per_layer_est = None
    if v_by_ngl.get(start) is not None and v_by_ngl.get(start + 1) is not None:
        per_layer_est = v_by_ngl[start + 1] - v_by_ngl[start]
    overhead_est = None
    if per_layer_est is not None and v_by_ngl.get(start + 1) is not None:
        overhead_est = v_by_ngl[start + 1] - per_layer_est

    def fmt2(x):
        return "N/A" if x is None else f"{x:.2f}"

    summary = []
    summary.append("-"*80)
    summary.append(f"Summary @ {now_iso()}")
    summary.append(f"  Mode               : {mode}")
    summary.append(f"  Binary             : {binary.name}")
    summary.append(f"  n_layer (detected) : {detected_layers if detected_layers is not None else 'unknown'}")
    summary.append(f"  NGL swept          : {start}..{last}")
    summary.append(f"  Baseline VRAM      : {fmt2(baseline)} MiB (-ngl {start})")
    summary.append(f"  Max VRAM           : {fmt2(full)} MiB (-ngl {last})")
    summary.append(f"  Est. weights-on-GPU: {fmt2(weights_on_gpu_est)} MiB (Max - Baseline)")
    summary.append(f"  Avg per-layer VRAM : {fmt2(avg_delta)} MiB (from successive deltas)")
    summary.append(f"  Per-layer (early)  : {fmt2(per_layer_est)} MiB (ngl {start}->{start+1})")
    summary.append(f"  Overhead (heuristic): {fmt2(overhead_est)} MiB (VRAM(1) - per_layer)")
    summary.append("")
    summary.append("  Per-layer VRAM deltas (MiB):")
    for i, d in enumerate(deltas, start=start + 1):
        summary.append(f"    - layer {i:>3}: {fmt2(d)}")
    summary.append("")
    summary.append("  Per-run peaks:")
    for r in results:
        summary.append(f"    - -ngl {r['ngl']:>3}: GPU={fmt2(r['gpu_peak_mib'])} MiB | CPU={fmt2(r['cpu_peak_mib'])} MiB")
    summary.append("-"*80)
    summary.append("")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(summary))

    print("\n".join(summary))
    print(f"[✔] Log written to: {log_path}")

if __name__ == "__main__":
    main()
