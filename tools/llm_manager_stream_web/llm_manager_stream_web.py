#!/usr/bin/env python3
"""
LLM Manager with Web Streaming UI
=================================

New in this build
-----------------
- Sticky header always visible with:
  • Active model
  • Connection status
  • Queue lengths by model (live)
  • Pause/Resume toggle
- Pause stops starting new requests (tailing continues; queued items accumulate)
- Process-group eviction: reliably frees VRAM (watch with `nvtop`)
- Binary-to-RAM preload (for .llamafile or other binaries)
- SSE streaming tokens to the browser
- Fairness scheduler to batch per-model briefly, but avoid starvation
- Per-request outputs & CSV logs

Endpoints
---------
GET /                  -> UI
GET /stream            -> SSE channel
GET /toggle_pause      -> toggle paused; returns {"paused": true/false}
GET /set_pause?value=  -> set paused; value in [true,false,1,0,on,off,yes,no]
GET /state             -> {"paused": bool, "active_model": str|None, "queue": [{model,count},...]}

Requests file format
--------------------
requests.txt lines: "<model_name>|<question>"

Configuration
-------------
- Reads `llm_manager_config.json` in CWD (or pass --config).
- Model names must match the left-hand side used in `requests.txt`.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
from dataclasses import dataclass, field
import json
import logging
import os
import platform
import queue
import re
import shutil
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import psutil  # optional
except ImportError:
    psutil = None

# ----------------------------- HTTP helpers -----------------------------

import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs

def http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 5.0) -> Tuple[Optional[int], Optional[str], Optional[dict]]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return status, body, json.loads(body)
            except Exception:
                return status, body, None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = None
        return e.code, body, None
    except Exception:
        return None, None, None

def http_post_json_stream(url: str, payload: dict, headers: Optional[Dict[str, str]] = None, timeout: float = 900.0):
    """
    Yield (kind, data) tuples from an OpenAI-compatible SSE stream.
      - ("data", json_str) for each chunk
      - ("done", "") at end
      - ("status", "<code>") once closed
    """
    data = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if headers: hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    resp = urllib.request.urlopen(req, timeout=timeout)
    status = resp.getcode()
    try:
        while True:
            raw = resp.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line or line.startswith(":"):  # keepalive or blank
                continue
            if line.lower().startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    yield ("done", "")
                    break
                yield ("data", data_str)
    finally:
        try:
            resp.close()
        except Exception:
            pass
    yield ("status", str(status))


# ------------------------------- utilities ------------------------------

def human_gb(x: float) -> float:
    return round(float(x), 2)

def clamp_nonneg(x: float) -> float:
    return max(0.0, float(x))

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H-%M-%S", time.localtime())

def sanitize_filename(s: str, max_len: int = 64) -> str:
    import string as _s
    valid = f"-_.() {_s.ascii_letters}{_s.digits}"
    cleaned = "".join(c if c in valid else "_" for c in s)
    return cleaned[:max_len] if len(cleaned) > max_len else cleaned

def file_exists_and_nonempty(p: Path) -> bool:
    return p.exists() and p.is_file() and p.stat().st_size > 0

def _try_run(cmd: List[str], timeout: float = 6.0) -> Tuple[bool, str]:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return True, out
    except Exception:
        return False, ""


# ----------------------------- system / GPU -----------------------------

@dataclass
class GPUInfo:
    vendor: str = "Unknown"
    name: str = "Unknown"
    vram_total_gb: float = 0.0
    vram_free_gb: float = 0.0

@dataclass
class SystemSpecs:
    os: str
    os_version: str
    machine: str
    cpu: str
    cpu_cores_logical: int
    cpu_cores_physical: int
    ram_total_gb: float
    ram_available_gb: float
    gpus: List[GPUInfo] = field(default_factory=list)

def detect_gpus_basic() -> List[GPUInfo]:
    gpus: List[GPUInfo] = []
    # NVIDIA
    if shutil.which("nvidia-smi"):
        ok, out = _try_run([
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free",
            "--format=csv,noheader,nounits"
        ])
        if ok:
            for line in out.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    name = parts[0]
                    try:
                        total_gb = float(parts[1]) / 1024.0
                        free_gb = float(parts[2]) / 1024.0
                    except Exception:
                        total_gb, free_gb = 0.0, 0.0
                    gpus.append(GPUInfo(vendor="NVIDIA", name=name,
                                        vram_total_gb=human_gb(total_gb),
                                        vram_free_gb=human_gb(free_gb)))
            if gpus:
                return gpus
    # AMD ROCm
    if shutil.which("rocm-smi"):
        ok, out = _try_run(["rocm-smi", "--showproductname", "--showmeminfo", "vram"])
        if ok:
            name = "AMD GPU"
            total_gb = 0.0
            free_gb = 0.0
            for line in out.splitlines():
                l = line.strip()
                if "ASIC" in l:
                    name = l.split(":", 1)[-1].strip()
                if "VRAM Total" in l or "total" in l.lower():
                    nums = re.findall(r"(\d+)", l)
                    if nums:
                        total_gb = float(nums[0]) / (1024**3)
                if "VRAM Free" in l or "free" in l.lower():
                    nums = re.findall(r"(\d+)", l)
                    if nums:
                        free_gb = float(nums[0]) / (1024**3)
            gpus.append(GPUInfo(vendor="AMD", name=name,
                                vram_total_gb=human_gb(total_gb), vram_free_gb=human_gb(free_gb)))
            if gpus:
                return gpus
    # Apple (no direct free VRAM here)
    if platform.system() == "Darwin" and shutil.which("system_profiler"):
        ok, out = _try_run(["system_profiler", "SPDisplaysDataType"], timeout=8.0)
        if ok:
            name = "Apple GPU"
            total_gb = 0.0
            for line in out.splitlines():
                l = line.strip()
                if l.startswith("Chipset Model:"):
                    name = l.split(":", 1)[-1].strip()
                if "VRAM" in l and ("Total" in l or "Shared" in l):
                    nums = re.findall(r"(\d+)\s*GB", l, flags=re.IGNORECASE)
                    if nums:
                        total_gb = float(nums[0])
            gpus.append(GPUInfo(vendor="Apple", name=name, vram_total_gb=human_gb(total_gb), vram_free_gb=0.0))
            if gpus:
                return gpus
    return [GPUInfo()]

def collect_system_specs() -> SystemSpecs:
    uname = platform.uname()
    os_name = uname.system
    os_version = uname.version
    machine = uname.machine
    cpu = uname.processor or platform.processor() or "Unknown CPU"
    cores_logical = os.cpu_count() or 0
    cores_physical = 0
    ram_total_gb = 0.0
    ram_available_gb = 0.0
    if psutil:
        try:
            cores_physical = psutil.cpu_count(logical=False) or 0
            vm = psutil.virtual_memory()
            ram_total_gb = vm.total / (1024**3)
            ram_available_gb = vm.available / (1024**3)
        except Exception:
            pass
    gpus = detect_gpus_basic()
    return SystemSpecs(
        os=os_name,
        os_version=os_version,
        machine=machine,
        cpu=cpu,
        cpu_cores_logical=cores_logical,
        cpu_cores_physical=cores_physical,
        ram_total_gb=human_gb(ram_total_gb),
        ram_available_gb=human_gb(ram_available_gb),
        gpus=gpus,
    )

def get_actual_vram_free_gb(logger: Optional[logging.Logger] = None) -> Optional[float]:
    """Query actual free VRAM using nvidia-smi or rocm-smi (first device)."""
    if shutil.which("nvidia-smi"):
        ok, out = _try_run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"])
        if ok:
            try:
                first = out.strip().splitlines()[0]
                return human_gb(float(first) / 1024.0)
            except Exception:
                pass
    if shutil.which("rocm-smi"):
        ok, out = _try_run(["rocm-smi", "--showmeminfo", "vram"])
        if ok:
            for line in out.splitlines():
                if "free" in line.lower():
                    nums = re.findall(r"(\d+)", line)
                    if nums:
                        return human_gb(float(nums[0]) / (1024**3))
    return None


# ------------------------------ configuration ---------------------------

@dataclass
class ModelSpec:
    name: str

    # Serving (OpenAI-compatible)
    api_type: str = "openai_compat"
    host: str = "127.0.0.1"
    port: int = 8900
    ready_path: str = "/v1/models"
    completion_path: str = "/v1/chat/completions"
    api_key: Optional[str] = None

    # Launch (supports {host} {port} {binary} {weights})
    launch_cmd: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    startup_timeout_s: float = 120.0
    shutdown_grace_s: float = 5.0

    # Inference defaults
    temperature: float = 0.7
    max_tokens: int = 512

    # VRAM budget (weights + compute + KV headroom)
    vram_gb: float = 8.0

    # Binary preload (optional)
    binary_path: Optional[str] = None
    preload_binary_to_ram: bool = True
    prefer_bin_copy_to_tmpfs: bool = True
    prepared_binary_path: Optional[str] = None

    # Weights preload (optional; safe to leave None for .llamafile builds)
    weights_path: Optional[str] = None
    preload_to_ram: bool = True
    prefer_ram_copy_to_tmpfs: bool = False
    prepared_weights_path: Optional[str] = None

@dataclass
class Config:
    models: List[ModelSpec]
    requests_file: str = "requests.txt"
    output_dir: str = "outputs"
    logs_dir: str = "logs"
    system_specs_path: str = "system_specs.json"

    # VRAM policy
    vram_reserve_gb: float = 1.0
    safety_vram_margin_gb: float = 0.5
    allow_oversubscription: bool = False
    evict_and_retry_on_start_failure: bool = True

    # Exclusive mode
    exclusive_mode: bool = False
    post_stop_wait_s: float = 0.4
    post_stop_check_retries: int = 25

    # Queue
    fairness_timeslice_s: float = 5.0
    starvation_avoidance_min_other: int = 1

    # Web
    web_host: str = "127.0.0.1"
    web_port: int = 8765
    web_title: str = "LLM Manager – Live Stream"

    # Behavior
    process_existing_requests_on_start: bool = True
    start_with_clean_outputs: bool = False

    # RAM preload globals
    ram_cache_tmpfs_dir: str = "/dev/shm/llm_cache"
    bin_cache_tmpfs_dir: str = "/dev/shm/llm_bin_cache"
    pagecache_warm_block_mb: int = 8

    # Optional GPU override
    gpu_override: Optional[Dict[str, float | str]] = None

def load_or_init_config(path: Path) -> Config:
    if file_exists_and_nonempty(path):
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        # backfill defaults without clobbering user's file
        raw.setdefault("safety_vram_margin_gb", 0.5)
        raw.setdefault("allow_oversubscription", False)
        raw.setdefault("evict_and_retry_on_start_failure", True)
        raw.setdefault("exclusive_mode", False)
        raw.setdefault("post_stop_wait_s", 0.4)
        raw.setdefault("post_stop_check_retries", 25)
        raw.setdefault("ram_cache_tmpfs_dir", "/dev/shm/llm_cache")
        raw.setdefault("bin_cache_tmpfs_dir", "/dev/shm/llm_bin_cache")
        raw.setdefault("pagecache_warm_block_mb", 8)
        for m in raw.get("models", []):
            m.setdefault("preload_binary_to_ram", True)
            m.setdefault("prefer_bin_copy_to_tmpfs", True)
        models = [ModelSpec(**m) for m in raw.get("models", [])]
        return Config(models=models, **{k: v for k, v in raw.items() if k != "models"})

    # Minimal default if no config exists
    default = Config(
        models=[
            ModelSpec(
                name="llava-v1.5-7b-q4",
                host="127.0.0.1",
                port=8900,
                launch_cmd="./llava-v1.5-7b-q4.llamafile --host {host} --port {port} --nobrowser --mlock -ngl 40 -c 4096",
                temperature=0.6,
                max_tokens=512,
                vram_gb=6.0,
                preload_binary_to_ram=True,
                prefer_bin_copy_to_tmpfs=True
            )
        ],
        exclusive_mode=True
    )
    with path.open("w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(default), f, indent=2)
    print(f"[init] Wrote default config to {path}")
    return default

def ensure_sample_requests(path: Path, model_names: List[str]) -> None:
    if file_exists_and_nonempty(path) or not model_names:
        return
    samples = [
        f"{model_names[0]}|Say hello and stream it.",
    ]
    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(samples) + "\n")
    print(f"[init] Wrote sample requests to {path}")


# -------------------------- VRAM tracker (logical) ----------------------

class VRAMTracker:
    def __init__(self, total_vram_gb: float, reserve_gb: float):
        self.total_vram_gb = float(total_vram_gb)
        self.reserve_gb = float(reserve_gb)
        self.loaded: Dict[str, float] = {}       # model_name -> vram_gb
        self.last_used_ts: Dict[str, float] = {} # model_name -> ts

    def free_gb(self) -> float:
        used = sum(self.loaded.values())
        return clamp_nonneg(self.total_vram_gb - self.reserve_gb - used)

    def is_loaded(self, model_name: str) -> bool:
        return model_name in self.loaded

    def touch(self, model_name: str):
        self.last_used_ts[model_name] = time.perf_counter()

    def list_lru(self) -> List[str]:
        return sorted(self.loaded.keys(), key=lambda m: self.last_used_ts.get(m, 0.0))

    def account_start(self, model_name: str, vram_gb: float):
        self.loaded[model_name] = vram_gb
        self.touch(model_name)

    def account_stop(self, model_name: str):
        self.loaded.pop(model_name, None)
        self.last_used_ts.pop(model_name, None)


# ----------------------- requests & fair scheduler ----------------------

@dataclass
class InferenceRequest:
    req_id: int
    model_name: str
    question: str
    arrival_ts: float

def parse_request_line(line: str) -> Optional[Tuple[str, str]]:
    s = line.strip()
    if not s or s.startswith("#") or s.startswith("//"):
        return None
    if "|" in s:
        model, q = s.split("|", 1)
        model = model.strip()
        q = q.strip()
        if model and q:
            return model, q
        return None
    parts = s.split(None, 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None

class RequestsTailer(threading.Thread):
    daemon = True
    def __init__(self, path: Path, process_existing: bool = True, poll_s: float = 0.5):
        super().__init__(name="RequestsTailer")
        self.path = path
        self.process_existing = process_existing
        self.poll_s = poll_s
        self.out_q: "queue.Queue[InferenceRequest]" = queue.Queue()
        self._stop = threading.Event()
        self._next_id = 1

    def stop(self):
        self._stop.set()

    def get_queue(self) -> "queue.Queue[InferenceRequest]":
        return self.out_q

    def run(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.touch(exist_ok=True)
            with self.path.open("r", encoding="utf-8") as f:
                if not self.process_existing:
                    f.seek(0, os.SEEK_END)
                while not self._stop.is_set():
                    pos = f.tell()
                    line = f.readline()
                    if not line:
                        time.sleep(self.poll_s)
                        f.seek(pos)
                        continue
                    parsed = parse_request_line(line)
                    if parsed:
                        model, question = parsed
                        req = InferenceRequest(self._next_id, model, question, time.perf_counter())
                        self._next_id += 1
                        self.out_q.put(req)
        except Exception as e:
            print(f"[tailer] Error: {e}", file=sys.stderr)

class FairScheduler:
    """
    Group-by-model batching up to timeslice_s, then give other models a turn.
    """
    def __init__(self, timeslice_s: float, starvation_avoidance_min_other: int = 1):
        self.timeslice_s = float(timeslice_s)
        self.starvation_avoidance_min_other = int(starvation_avoidance_min_other)
        self.queues: Dict[str, deque[InferenceRequest]] = defaultdict(deque)
        self.global_order: deque[str] = deque()
        self.current_model: Optional[str] = None
        self.slice_start_ts: float = 0.0

    def add(self, req: InferenceRequest):
        was_empty = len(self.queues[req.model_name]) == 0
        self.queues[req.model_name].append(req)
        if was_empty:
            self.global_order.append(req.model_name)

    def has_any(self) -> bool:
        return any(len(q) > 0 for q in self.queues.values())

    def _pop_from_model(self, model: str) -> Optional[InferenceRequest]:
        q = self.queues[model]
        if not q:
            return None
        req = q.popleft()
        if not q:
            try:
                self.global_order.remove(model)
            except ValueError:
                pass
        return req

    def next_request(self) -> Optional[InferenceRequest]:
        if not self.has_any():
            return None
        now = time.perf_counter()
        if self.current_model and self.queues[self.current_model]:
            if (now - self.slice_start_ts) < self.timeslice_s:
                return self._pop_from_model(self.current_model)
            else:
                for model in list(self.global_order):
                    if model != self.current_model and self.queues[model]:
                        self.current_model = model
                        self.slice_start_ts = now
                        return self._pop_from_model(model)
                # Still only current model
                self.slice_start_ts = now
                return self._pop_from_model(self.current_model)
        # Pick next available model
        if self.global_order:
            model = self.global_order[0]
            self.current_model = model
            self.slice_start_ts = now
            return self._pop_from_model(model)
        return None


# ------------------------------ SSE & web UI ----------------------------

class EventBus:
    def __init__(self):
        self.subscribers: List[queue.Queue] = []
        self.lock = threading.Lock()
        self.snap_active_model: Optional[str] = None
        self.snap_current_req: Optional[dict] = None
        self.snap_current_text: str = ""
        self.snap_paused: bool = False
        self.snap_queue_counts: List[dict] = []  # [{"model": str, "count": int}, ...]

    def subscribe(self) -> queue.Queue:
        q = queue.Queue()
        with self.lock:
            self.subscribers.append(q)
            # On connect, send latest snapshots so UI is consistent
            if self.snap_paused is not None:
                q.put_nowait({"type": "paused", "paused": self.snap_paused})
            if self.snap_active_model is not None:
                q.put_nowait({"type": "active_model", "model": self.snap_active_model})
            if self.snap_queue_counts:
                q.put_nowait({"type": "queue_update", "counts": self.snap_queue_counts})
            if self.snap_current_req is not None:
                q.put_nowait({"type": "request_start", **self.snap_current_req})
                if self.snap_current_text:
                    q.put_nowait({
                        "type": "token",
                        "req_id": self.snap_current_req["req_id"],
                        "model": self.snap_current_req["model"],
                        "token": self.snap_current_text
                    })
        return q

    def unsubscribe(self, q: queue.Queue):
        with self.lock:
            try:
                self.subscribers.remove(q)
            except ValueError:
                pass

    def publish(self, event: dict):
        et = event.get("type")
        if et == "active_model":
            self.snap_active_model = event.get("model")
        elif et == "request_start":
            self.snap_current_req = {
                "req_id": event.get("req_id"),
                "model": event.get("model"),
                "question": event.get("question", "")
            }
            self.snap_current_text = ""
        elif et == "token":
            tok = event.get("token", "")
            if tok and len(self.snap_current_text) < 200000:
                self.snap_current_text += tok
        elif et == "request_end":
            self.snap_current_req = None
            self.snap_current_text = ""
        elif et == "paused":
            self.snap_paused = bool(event.get("paused", False))
        elif et == "queue_update":
            counts = event.get("counts") or []
            if isinstance(counts, list):
                self.snap_queue_counts = counts

        with self.lock:
            dead = []
            for q in self.subscribers:
                try:
                    q.put_nowait(event)
                except Exception:
                    dead.append(q)
            for q in dead:
                try:
                    self.subscribers.remove(q)
                except ValueError:
                    pass

class ControlState:
    """Shared state for pause/resume, thread-safe."""
    def __init__(self):
        self._paused = False
        self._lock = threading.Lock()

    def set_paused(self, val: bool):
        with self._lock:
            self._paused = bool(val)
        return self._paused

    def toggle(self) -> bool:
        with self._lock:
            self._paused = not self._paused
            return self._paused

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

class WebServer(threading.Thread):
    daemon = True
    def __init__(self, host: str, port: int, title: str, bus: EventBus, control: ControlState, logger: logging.Logger):
        super().__init__(name="WebServer")
        self.host = host
        self.port = port
        self.title = title
        self.bus = bus
        self.control = control
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.logger = logger

    def _html(self) -> bytes:
        title = self.title
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
:root{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,sans-serif}}
body{{margin:0;background:#0b0d12;color:#e5e7eb}}
header{{position:sticky;top:0;background:#0f1220;border-bottom:1px solid #23263a;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;gap:12px;z-index:50}}
.hleft{{display:flex;align-items:center;gap:10px;min-width:0}} .hright{{display:flex;flex-direction:column;align-items:flex-end;gap:4px;min-width:0;max-width:70vw}}
.dot{{width:10px;height:10px;border-radius:50%;background:#ef4444;display:inline-block}} .dot.ok{{background:#22c55e}}
h1{{font-size:15px;margin:0;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
#activeModel{{font-weight:700;color:#93c5fd}} .muted{{color:#9ca3af}}
#status{{font-size:12px;color:#a1a1aa}}
.controls{{display:flex;gap:8px;align-items:center}}
button#pauseBtn{{background:#1f2342;border:1px solid #2c3158;color:#e5e7eb;border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}}
button#pauseBtn.paused{{background:#7c2d12;border-color:#b45309}}
.queue{{display:flex;gap:6px;align-items:center;overflow:auto;max-width:70vw}}
.pill{{background:#11162a;border:1px solid #1f2342;border-radius:999px;padding:2px 8px;font-size:12px;white-space:nowrap}}
main{{padding:16px 14px 36px;max-width:980px;margin:0 auto}}
.card{{background:#11162a;border:1px solid #1f2342;border-radius:10px;padding:14px 16px;margin-bottom:14px}}
.question{{color:#cbd5e1;font-weight:600;margin-bottom:8px;white-space:pre-wrap}}
.answer{{font-family:ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap}}
.meta{{margin-top:10px;font-size:12px;color:#a1a1aa}}
</style></head>
<body>
<header>
  <div class="hleft"><div class="dot" id="liveDot"></div><h1>{title}</h1></div>
  <div class="hright">
    <div class="controls">
      <div><span class="muted">Active:</span> <span id="activeModel">—</span></div>
      <button id="pauseBtn" title="Pause/Resume processing">Pause</button>
    </div>
    <div id="status">connecting…</div>
    <div id="queueBar" class="queue"><span class="muted">Queue: empty</span></div>
  </div>
</header>
<main>
  <div id="stream"></div>
</main>
<script>
(function(){{
  const streamEl=document.getElementById('stream');
  const activeModelEl=document.getElementById('activeModel');
  const statusEl=document.getElementById('status');
  const liveDot=document.getElementById('liveDot');
  const pauseBtn=document.getElementById('pauseBtn');
  const queueBar=document.getElementById('queueBar');

  let connected=false, paused=false;

  function renderStatus(){{
    statusEl.textContent=(connected?'live':'disconnected – retrying…') + (paused?' • paused':'');
  }}
  function setConnected(ok){{ connected=!!ok; if(ok) liveDot.classList.add('ok'); else liveDot.classList.remove('ok'); renderStatus(); }}
  function applyPaused(p){{ paused=!!p; if(paused) pauseBtn.textContent='Resume'; else pauseBtn.textContent='Pause'; if(paused) pauseBtn.classList.add('paused'); else pauseBtn.classList.remove('paused'); renderStatus(); }}

  pauseBtn.addEventListener('click', async () => {{
    try {{
      const res = await fetch('/toggle_pause');
      const data = await res.json();
      if (typeof data.paused !== 'undefined') applyPaused(!!data.paused);
    }} catch(e) {{}}
  }});

  function ensureCard(id, model, q){{ let card=document.getElementById('req-'+id); if(card) return card;
    card=document.createElement('div'); card.className='card'; card.id='req-'+id;
    const qEl=document.createElement('div'); qEl.className='question'; qEl.textContent=q||'(no question)';
    const ansEl=document.createElement('div'); ansEl.className='answer'; ansEl.id='ans-'+id; ansEl.textContent='';
    const metaEl=document.createElement('div'); metaEl.className='meta'; metaEl.id='meta-'+id; metaEl.textContent='Model: '+(model||'?')+' • Request #'+id;
    card.appendChild(qEl); card.appendChild(ansEl); card.appendChild(metaEl);
    streamEl.appendChild(card);
    return card;
  }}

  function appendToken(id, tok){{
    const el=document.getElementById('ans-'+id);
    if(!el) return;
    el.textContent+=tok;
    el.parentElement.scrollIntoView({{behavior:'smooth', block:'end'}});
  }}

  function renderQueue(items){{
    queueBar.innerHTML='';
    if(!items || !items.length){{
      const s=document.createElement('span'); s.className='muted'; s.textContent='Queue: empty'; queueBar.appendChild(s);
      return;
    }}
    const label=document.createElement('span'); label.className='muted'; label.textContent='Queue:'; queueBar.appendChild(label);
    for(const it of items){{
      const pill=document.createElement('span'); pill.className='pill'; pill.textContent=`${{it.model}} (${{it.count}})`;
      queueBar.appendChild(pill);
    }}
  }}

  const evts=new EventSource('/stream');
  evts.onopen=()=>setConnected(true);
  evts.onerror=()=>setConnected(false);
  evts.onmessage=(e)=>{{
    try {{
      const evt=JSON.parse(e.data);
      if(!evt||!evt.type) return;
      switch(evt.type){{
        case 'paused': applyPaused(!!evt.paused); break;
        case 'active_model': activeModelEl.textContent=evt.model||'—'; break;
        case 'queue_update': renderQueue(evt.counts||[]); break;
        case 'request_start': ensureCard(evt.req_id, evt.model, evt.question); break;
        case 'token': ensureCard(evt.req_id, evt.model||'?', '(loading…)'); appendToken(evt.req_id, evt.token||''); break;
        case 'request_end':
          const m=document.getElementById('meta-'+evt.req_id);
          if(m){{
            let s='Done';
            if(evt.status) s+=' • status '+evt.status;
            if(evt.load_time_s!==undefined) s+=' • loaded '+Number(evt.load_time_s).toFixed(2)+'s';
            if(evt.infer_time_s!==undefined) s+=' • infer '+Number(evt.infer_time_s).toFixed(2)+'s';
            m.textContent+=' • '+s;
          }}
          break;
      }}
    }} catch(err) {{
      console.error('Bad event', err, e.data);
    }}
  }};
}})();
</script>
</body></html>
""".encode("utf-8")

    def _make_handler(self):
        bus, html_bytes, logger, control = self.bus, self._html(), self.logger, self.control
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                logger.info("web: " + fmt, *args)

            def _json(self, obj: dict, status: int = 200):
                body = json.dumps(obj).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/" or self.path.startswith("/index.html"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(html_bytes)
                    return
                if self.path == "/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()
                    q = bus.subscribe()
                    try:
                        self.wfile.write(b": hello\n\n")
                        self.wfile.flush()
                        while True:
                            try:
                                evt = q.get(timeout=15.0)
                                payload = json.dumps(evt).encode("utf-8")
                                self.wfile.write(b"data: " + payload + b"\n\n")
                                self.wfile.flush()
                            except queue.Empty:
                                try:
                                    self.wfile.write(b": keepalive\n\n")
                                    self.wfile.flush()
                                except (BrokenPipeError, ConnectionResetError):
                                    break
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    finally:
                        bus.unsubscribe(q)
                    return
                if self.path.startswith("/toggle_pause"):
                    paused = control.toggle()
                    bus.publish({"type": "paused", "paused": paused})
                    return self._json({"paused": paused})
                if self.path.startswith("/set_pause"):
                    try:
                        qs = parse_qs(urlparse(self.path).query)
                        val = (qs.get("value", [""])[0] or "").strip().lower()
                        paused = val in ("true","1","on","yes")
                        paused = control.set_paused(paused)
                        bus.publish({"type": "paused", "paused": paused})
                        return self._json({"paused": paused})
                    except Exception as e:
                        return self._json({"error": str(e)}, status=400)
                if self.path.startswith("/state"):
                    try:
                        return self._json({
                            "paused": control.is_paused(),
                            "active_model": bus.snap_active_model,
                            "queue": bus.snap_queue_counts,
                        })
                    except Exception as e:
                        return self._json({"error": str(e)}, status=500)

                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not found")
        return Handler

    def run(self):
        Handler = self._make_handler()
        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self.logger.info("Web UI on http://%s:%d", self.host, self.port)
        try:
            self.httpd.serve_forever()
        except Exception as e:
            self.logger.error("Web server error: %s", e)

    def stop(self):
        try:
            if self.httpd:
                self.httpd.shutdown()
        except Exception:
            pass


# --------------------------- RAM preload helpers ------------------------

def warm_page_cache(path: Path, block_mb: int, logger: logging.Logger):
    try:
        bs = max(1, int(block_mb)) * 1024 * 1024
        with path.open("rb") as f:
            while True:
                chunk = f.read(bs)
                if not chunk:
                    break
        logger.info("Page-cache warmed: %s", path)
    except Exception as e:
        logger.warning("Page-cache warm failed for %s: %s", path, e)

def copy_to_tmpfs(src: Path, dst_dir: Path, logger: logging.Logger) -> Optional[Path]:
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            logger.info("RAM copy exists: %s", dst)
            # Ensure executable bit for binaries
            try:
                dst.chmod(dst.stat().st_mode | 0o111)
            except Exception:
                pass
            return dst
        try:
            usage = shutil.disk_usage(str(dst_dir))
            if usage.free < src.stat().st_size:
                logger.warning("Not enough free tmpfs space to copy %s -> %s", src, dst_dir)
                return None
        except Exception:
            pass
        logger.info("Copying to tmpfs: %s -> %s", src, dst)
        with src.open("rb") as fsrc, dst.open("wb") as fdst:
            shutil.copyfileobj(fsrc, fdst, length=16 * 1024 * 1024)
        try:
            dst.chmod(dst.stat().st_mode | 0o111)
        except Exception:
            pass
        return dst
    except Exception as e:
        logger.warning("RAM copy failed for %s: %s", src, e)
        return None

def detect_binary_from_cmd(launch_cmd: str) -> Optional[Path]:
    try:
        argv = shlex.split(launch_cmd)
        if not argv:
            return None
        cand = argv[0]
        # If bare command (no path), we can’t reliably preload it
        if os.path.sep not in cand and not cand.startswith("."):
            return None
        return Path(cand).resolve()
    except Exception:
        return None

def rewrite_cmd_binary(launch_cmd: str, new_binary_path: str) -> str:
    """Replace argv[0] with prepared binary path; return a shell-safe string."""
    try:
        argv = shlex.split(launch_cmd)
        if not argv:
            return launch_cmd
        argv[0] = new_binary_path
        return " ".join(shlex.quote(a) for a in argv)
    except Exception:
        return shlex.quote(new_binary_path) + " " + launch_cmd


# --------------------------- server management --------------------------

@dataclass
class ServerProcess:
    model_name: str
    popen: subprocess.Popen
    host: str
    port: int
    base_url: str
    log_path: Path
    start_ts: float
    last_used_ts: float

def build_base_url(host: str, port: int) -> str:
    if host.startswith("http://") or host.startswith("https://"):
        return f"{host}:{port}"
    return f"http://{host}:{port}"

def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# -------------------------------- Manager -------------------------------

class LLMManager:
    def __init__(self, cfg: Config, sys_specs: SystemSpecs, bus: EventBus, control: ControlState):
        self.cfg = cfg
        self.sys_specs = sys_specs
        self.bus = bus
        self.control = control

        self.output_dir = Path(cfg.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = Path(cfg.logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        if cfg.start_with_clean_outputs:
            for p in self.output_dir.glob("*.txt"):
                try:
                    p.unlink()
                except Exception:
                    pass

        self._init_logging()
        self.csv_path = self.logs_dir / "requests_log.csv"
        self._ensure_csv_header()

        # VRAM totals
        if cfg.gpu_override:
            total_vram = float(cfg.gpu_override.get("vram_total_gb", 0.0))
            gpu_name = str(cfg.gpu_override.get("name", "Override GPU"))
        else:
            total_vram = float(self.sys_specs.gpus[0].vram_total_gb) if self.sys_specs.gpus else 0.0
            gpu_name = self.sys_specs.gpus[0].name if self.sys_specs.gpus else "Unknown GPU"

        self.vram = VRAMTracker(total_vram_gb=total_vram, reserve_gb=cfg.vram_reserve_gb)
        self.logger.info(
            "GPU: %s | VRAM total: %.2f GB (reserve %.2f GB) | safety margin: %.2f GB | exclusive_mode=%s | allow_oversubscription=%s",
            gpu_name, self.vram.total_vram_gb, self.vram.reserve_gb, self.cfg.safety_vram_margin_gb,
            self.cfg.exclusive_mode, self.cfg.allow_oversubscription
        )

        # Models
        self.models: Dict[str, ModelSpec] = {m.name: m for m in cfg.models}
        if not self.models:
            raise RuntimeError("No models configured.")

        # RAM preload for binaries & weights before any server starts
        self._prepare_ram_cache_for_binaries_and_weights()

        # Scheduler & tailer
        self.scheduler = FairScheduler(cfg.fairness_timeslice_s, cfg.starvation_avoidance_min_other)
        self.tailer = RequestsTailer(Path(cfg.requests_file), cfg.process_existing_requests_on_start, 0.5)
        self.tailer_q = self.tailer.get_queue()

        # Running servers
        self.servers: Dict[str, ServerProcess] = {}
        self._stop = threading.Event()

        # Web
        self.web = WebServer(cfg.web_host, cfg.web_port, cfg.web_title, self.bus, self.control, self.logger)
        self.web.start()

        # Publish initial paused state
        self.bus.publish({"type": "paused", "paused": self.control.is_paused()})

    # ----- logging & CSV -----

    def _init_logging(self):
        self.logger = logging.getLogger("manager")
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self.logs_dir / "manager.log", encoding="utf-8")
        ch = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(fmt)
        ch.setFormatter(fmt)
        self.logger.handlers.clear()
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def _ensure_csv_header(self):
        header = [
            "request_id",
            "received_ts",
            "start_ts",
            "end_ts",
            "model",
            "question",
            "load_time_s",
            "inference_time_s",
            "server_was_running",
            "evicted_models",
            "answer_path",
            "endpoint_status",
        ]
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(header)

    def _append_csv(self, row: List):
        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    # ----- queue snapshot publishing -----

    def _queue_counts(self) -> List[dict]:
        items = []
        for model, dq in self.scheduler.queues.items():
            n = len(dq)
            if n > 0:
                items.append((model, n))
        items.sort(key=lambda kv: (-kv[1], kv[0]))
        return [{"model": name, "count": n} for name, n in items]

    def _publish_queue_snapshot(self):
        counts = self._queue_counts()
        self.bus.publish({"type": "queue_update", "counts": counts})

    # ----- RAM preload -----

    def _prepare_ram_cache_for_binaries_and_weights(self):
        # Binaries
        for m in self.models.values():
            bin_src: Optional[Path] = None
            if m.binary_path:
                p = Path(m.binary_path)
                if p.exists():
                    bin_src = p.resolve()
            if not bin_src and m.launch_cmd:
                inferred = detect_binary_from_cmd(m.launch_cmd)
                if inferred and inferred.exists():
                    bin_src = inferred
            if bin_src and m.preload_binary_to_ram:
                if m.prefer_bin_copy_to_tmpfs and os.path.isdir("/dev/shm"):
                    dst = copy_to_tmpfs(bin_src, Path(self.cfg.bin_cache_tmpfs_dir), self.logger)
                    if dst and dst.exists():
                        m.prepared_binary_path = str(dst.resolve())
                        self.logger.info("Prepared BIN RAM copy for '%s': %s", m.name, m.prepared_binary_path)
                    else:
                        warm_page_cache(bin_src, self.cfg.pagecache_warm_block_mb, self.logger)
                        m.prepared_binary_path = str(bin_src)
                else:
                    warm_page_cache(bin_src, self.cfg.pagecache_warm_block_mb, self.logger)
                    m.prepared_binary_path = str(bin_src)
            else:
                if m.preload_binary_to_ram and not bin_src:
                    self.logger.warning("Binary path not set/inferable for '%s'; skipping binary preload.", m.name)

        # Weights (optional)
        for m in self.models.values():
            if not m.weights_path:
                if m.preload_to_ram:
                    self.logger.info("Model '%s' has no weights_path; skipping weights preload.", m.name)
                continue
            src = Path(m.weights_path)
            if not src.exists():
                self.logger.warning("weights_path for '%s' not found: %s", m.name, src)
                continue
            if m.prefer_ram_copy_to_tmpfs and os.path.isdir("/dev/shm"):
                dst = copy_to_tmpfs(src, Path(self.cfg.ram_cache_tmpfs_dir), self.logger)
                if dst and dst.exists():
                    m.prepared_weights_path = str(dst.resolve())
                    self.logger.info("Prepared WEIGHTS RAM copy for '%s': %s", m.name, m.prepared_weights_path)
                else:
                    warm_page_cache(src, self.cfg.pagecache_warm_block_mb, self.logger)
                    m.prepared_weights_path = str(src.resolve())
            else:
                warm_page_cache(src, self.cfg.pagecache_warm_block_mb, self.logger)
                m.prepared_weights_path = str(src.resolve())

    # ----- lifecycle -----

    def start(self):
        self.logger.info("Starting RequestsTailer on %s", self.cfg.requests_file)
        self.tailer.start()
        try:
            while not self._stop.is_set():
                # Bring in new requests from the tailer
                try:
                    changed = False
                    while True:
                        req = self.tailer_q.get_nowait()
                        if req.model_name not in self.models:
                            self.logger.warning("Unknown model '%s' (req %s). Skipping.", req.model_name, req.req_id)
                            continue
                        self.scheduler.add(req)
                        changed = True
                    # fallthrough if empty
                except queue.Empty:
                    pass
                # Publish queue if changed
                # (lightweight; OK to publish on each loop too)
                self._publish_queue_snapshot()

                # Respect pause
                if self.control.is_paused():
                    time.sleep(0.1)
                    continue

                if not self.scheduler.has_any():
                    time.sleep(0.05)
                    continue

                next_req = self.scheduler.next_request()
                if not next_req:
                    time.sleep(0.02)
                    continue

                # Popped one => queue length changed
                self._publish_queue_snapshot()

                self._handle_request(next_req)
        except KeyboardInterrupt:
            self.logger.info("Interrupted; shutting down.")
        except Exception as e:
            self.logger.exception("Fatal error in manager loop: %s", e)
        finally:
            self.stop()

    def stop(self):
        if self._stop.is_set():
            return
        self._stop.set()
        try:
            self.tailer.stop()
        except Exception:
            pass
        for name in list(self.servers.keys()):
            self._stop_server(name)
        try:
            self.web.stop()
        except Exception:
            pass

    # ----- exclusivity & VRAM waits -----

    def _enforce_exclusive(self, target_name: str):
        if not self.cfg.exclusive_mode:
            return
        victims = [name for name in list(self.servers.keys()) if name != target_name]
        if victims:
            self.logger.info("exclusive_mode=True -> stopping other servers: %s", victims)
        for v in victims:
            self._stop_server(v)

    def _wait_for_vram_free(self, required_gb: float) -> bool:
        retries = int(max(1, self.cfg.post_stop_check_retries))
        delay = max(0.05, float(self.cfg.post_stop_wait_s))
        last = None
        for _ in range(retries):
            free_actual = get_actual_vram_free_gb(self.logger)
            last = free_actual
            if free_actual is not None and free_actual >= required_gb:
                self.logger.info("VRAM free OK: %.2f GB >= %.2f GB", free_actual, required_gb)
                return True
            time.sleep(delay)
        self.logger.warning("VRAM free timed out. Last: %s GB; required: %.2f GB", last, required_gb)
        return False

    # ----- command resolution -----

    def _resolve_launch_cmd(self, m: ModelSpec) -> str:
        cmd_tmpl = (m.launch_cmd or "")
        filled = cmd_tmpl.format(
            host=m.host,
            port=m.port,
            binary=(m.prepared_binary_path or m.binary_path or ""),
            weights=(m.prepared_weights_path or m.weights_path or "")
        )
        # If {binary} not in template but we have a prepared binary path, rewrite argv[0]
        if "{binary}" not in cmd_tmpl and (m.prepared_binary_path or m.binary_path):
            prepared = m.prepared_binary_path or m.binary_path
            if prepared:
                return rewrite_cmd_binary(filled, prepared)
        return filled

    # ----- server controls -----

    def _ensure_server_running(self, m: ModelSpec) -> Tuple[bool, float, List[str]]:
        # Hard gate: exclusive mode stops others first
        self._enforce_exclusive(m.name)

        if m.name in self.servers:
            self.vram.touch(m.name)
            return True, 0.0, []

        required_gb = float(m.vram_gb) + float(self.cfg.safety_vram_margin_gb)
        evicted: List[str] = []

        # If not exclusive, proactively evict LRU until free meets requirement
        if not self.cfg.exclusive_mode:
            for _ in range(10):
                free_actual = get_actual_vram_free_gb(self.logger)
                free_est = self.vram.free_gb()
                free_cons = min(
                    free_actual if free_actual is not None else float("inf"),
                    free_est if free_est is not None else float("inf")
                )
                if free_cons >= required_gb or self.cfg.allow_oversubscription:
                    break
                lru = [x for x in self.vram.list_lru() if x != m.name]
                if not lru:
                    break
                victim = lru[0]
                self._stop_server(victim)
                evicted.append(victim)

        # After any stops (or exclusive mode), wait for VRAM to be truly free
        self._wait_for_vram_free(required_gb)

        # Try start
        t0 = time.perf_counter()
        ok = self._start_server(m)
        load_time = time.perf_counter() - t0

        # If start fails, evict & retry once
        if not ok and self.cfg.evict_and_retry_on_start_failure:
            self.logger.warning("Start failed for '%s'. Evicting others and retrying once...", m.name)
            for victim in list(self.servers.keys()):
                if victim != m.name:
                    self._stop_server(victim)
            self._wait_for_vram_free(required_gb)
            t1 = time.perf_counter()
            ok = self._start_server(m)
            load_time = time.perf_counter() - t1

        if not ok:
            self.vram.account_stop(m.name)
            raise RuntimeError(f"Failed to start server for model '{m.name}' on {m.host}:{m.port}")

        self.vram.account_start(m.name, m.vram_gb)
        return False, load_time, evicted

    def _start_server(self, m: ModelSpec) -> bool:
        """
        Start the server in its own process group/session so we can terminate
        the entire tree on eviction (shell + child).
        """
        if not m.launch_cmd:
            self.logger.error("Model '%s' missing launch_cmd.", m.name)
            return False

        host = m.host
        port = int(m.port)
        base_url = build_base_url(host, port)
        log_path = self.logs_dir / f"server_{sanitize_filename(m.name)}.log"
        cmd = self._resolve_launch_cmd(m)
        self.logger.info("Starting server for '%s' -> %s | cmd: %s", m.name, base_url, cmd)

        log_fh = open(log_path, "a", encoding="utf-8")
        env = os.environ.copy()
        env.update({k: str(v) for k, v in (m.env or {}).items()})
        env.setdefault("HOST", str(host))
        env.setdefault("PORT", str(port))

        popen_kwargs = {
            "stdout": log_fh,
            "stderr": subprocess.STDOUT,
            "cwd": str(Path(".").resolve()),
            "shell": True,  # keep shell for user-provided commands
            "env": env,
        }

        if os.name == "posix":
            popen_kwargs["start_new_session"] = True  # new session = new process group
        else:
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        try:
            pop = subprocess.Popen(cmd, **popen_kwargs)
        except Exception as e:
            self.logger.error("Popen failed for '%s': %s", m.name, e)
            try:
                log_fh.close()
            except Exception:
                pass
            return False

        # Wait for TCP port or early exit
        deadline = time.time() + float(m.startup_timeout_s)
        while time.time() < deadline:
            if pop.poll() is not None:
                self.logger.error("Server '%s' exited early (code %s).", m.name, pop.returncode)
                try:
                    log_fh.close()
                except Exception:
                    pass
                return False
            if is_port_open(host, port, timeout=0.3):
                break
            time.sleep(0.2)

        # HTTP readiness probe
        headers = {}
        if m.api_key:
            headers["Authorization"] = f"Bearer {m.api_key}"
        http_ready = False
        for _ in range(int(max(1, m.startup_timeout_s / 0.4))):
            if pop.poll() is not None:
                self.logger.error("Server '%s' exited during readiness (code %s).", m.name, pop.returncode)
                break
            for path in [m.ready_path, "/health", "/"]:
                status, _, _ = http_get(f"{base_url}{path}", headers=headers, timeout=2.0)
                if status and 200 <= status < 500:
                    http_ready = True
                    break
            if http_ready:
                break
            time.sleep(0.4)

        if not http_ready:
            self.logger.error("Server '%s' did not become HTTP-ready.", m.name)
            self._terminate_popen(pop, m.shutdown_grace_s)
            try:
                log_fh.close()
            except Exception:
                pass
            return False

        sp = ServerProcess(
            model_name=m.name,
            popen=pop,
            host=host,
            port=port,
            base_url=base_url,
            log_path=log_path,
            start_ts=time.perf_counter(),
            last_used_ts=time.perf_counter(),
        )
        self.servers[m.name] = sp
        self.logger.info("Server '%s' is ready at %s", m.name, base_url)
        try:
            log_fh.flush()
        except Exception:
            pass
        return True

    def _terminate_popen(self, pop: subprocess.Popen, grace_s: float):
        """
        Stop a server process reliably:
        - POSIX: SIGTERM the *process group* (killpg), wait, then SIGKILL if needed.
        - Windows: terminate/kill, and best-effort child cleanup via psutil if available.
        """
        try:
            if pop.poll() is not None:
                return  # already exited

            if os.name == "posix":
                try:
                    pgid = os.getpgid(pop.pid)
                except Exception:
                    pgid = None

                if pgid is not None:
                    try:
                        self.logger.info("Sending SIGTERM to process group %s", pgid)
                        os.killpg(pgid, signal.SIGTERM)
                    except ProcessLookupError:
                        pgid = None
                    except Exception as e:
                        self.logger.warning("killpg(SIGTERM) failed: %s; falling back to terminate()", e)
                        try:
                            pop.terminate()
                        except Exception:
                            pass
                else:
                    try:
                        pop.terminate()
                    except Exception:
                        pass

                # bounded wait
                t0 = time.time()
                while time.time() - t0 < grace_s:
                    if pop.poll() is not None:
                        break
                    time.sleep(0.2)

                if pop.poll() is None:
                    if pgid is not None:
                        try:
                            self.logger.info("Process group still alive; sending SIGKILL to %s", pgid)
                            os.killpg(pgid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        except Exception as e:
                            self.logger.warning("killpg(SIGKILL) failed: %s; falling back to kill()", e)
                            try:
                                pop.kill()
                            except Exception:
                                pass
                    else:
                        try:
                            pop.kill()
                        except Exception:
                            pass

            else:
                # Windows fallback
                try:
                    pop.terminate()
                except Exception:
                    pass
                t0 = time.time()
                while time.time() - t0 < grace_s:
                    if pop.poll() is not None:
                        break
                    time.sleep(0.2)
                if pop.poll() is None:
                    try:
                        pop.kill()
                    except Exception:
                        pass

            # Optional: best-effort child cleanup
            try:
                import psutil  # type: ignore
                p = psutil.Process(pop.pid)
                for child in p.children(recursive=True):
                    try:
                        child.kill()
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception as e:
            self.logger.warning("Error while terminating process: %s", e)

    def _stop_server(self, model_name: str):
        sp = self.servers.get(model_name)
        if not sp:
            self.vram.account_stop(model_name)
            return
        self.logger.info("Stopping server for '%s' (port %s)", model_name, sp.port)
        try:
            self._terminate_popen(sp.popen, grace_s=self.models[model_name].shutdown_grace_s)
        finally:
            self.servers.pop(model_name, None)
            self.vram.account_stop(model_name)

    # ----- inference streaming -----

    @staticmethod
    def _extract_token(obj: dict) -> str:
        if not isinstance(obj, dict):
            return ""
        choices = obj.get("choices") or []
        if choices:
            c0 = choices[0] or {}
            delta = c0.get("delta") or {}
            if isinstance(delta, dict):
                tok = delta.get("content") or ""
                if tok:
                    return str(tok)
            txt = c0.get("text") or ""
            if txt:
                return str(txt)
        return str(obj.get("content") or "")

    def _send_inference_stream(self, m: ModelSpec, question: str, req_id: int) -> Tuple[str, int]:
        sp = self.servers.get(m.name)
        if not sp:
            raise RuntimeError(f"Server for '{m.name}' not running.")
        headers = {}
        if m.api_key:
            headers["Authorization"] = f"Bearer {m.api_key}"
        if m.api_type != "openai_compat":
            raise NotImplementedError(f"api_type '{m.api_type}' not implemented.")
        url = f"{sp.base_url}{m.completion_path}"
        payload = {
            "model": m.name,
            "messages": [{"role": "user", "content": question}],
            "temperature": float(m.temperature),
            "max_tokens": int(m.max_tokens),
            "stream": True
        }
        full = []
        status = 0
        for kind, data_str in http_post_json_stream(url, payload, headers=headers, timeout=900.0):
            if kind == "data":
                try:
                    obj = json.loads(data_str)
                    tok = self._extract_token(obj)
                    if tok:
                        full.append(tok)
                        self.bus.publish({"type": "token", "req_id": req_id, "model": m.name, "token": tok})
                except Exception:
                    pass
            elif kind == "done":
                break
            elif kind == "status":
                try:
                    status = int(data_str)
                except Exception:
                    status = 0
        return ("".join(full), status)

    # ----- outputs -----

    def _write_answer_file(self, model: str, req_id: int, question: str, answer: str) -> Path:
        ts = now_iso()
        fname = f"{ts}_{sanitize_filename(model)}_{req_id}.txt"
        out_path = self.output_dir / fname
        with out_path.open("w", encoding="utf-8") as f:
            f.write(f"Model: {model}\nRequest ID: {req_id}\nTimestamp: {ts}\n\n")
            f.write("Question:\n" + question.strip() + "\n\n")
            f.write("Answer:\n" + (answer or "").strip() + "\n")
        return out_path

    # ----- per-request handling -----

    def _handle_request(self, req: InferenceRequest):
        m = self.models[req.model_name]
        self.bus.publish({"type": "active_model", "model": m.name})
        self.bus.publish({"type": "request_start", "req_id": req.req_id, "model": m.name, "question": req.question})
        start_ts = time.perf_counter()

        # Ensure server running (exclusive enforcement & evictions inside)
        try:
            was_running, load_time_s, evicted = self._ensure_server_running(m)
        except Exception as e:
            self.logger.error("Request %d: failed to start model '%s': %s", req.req_id, m.name, e)
            end_ts = time.perf_counter()
            self._append_csv([req.req_id, f"{req.arrival_ts:.6f}", f"{start_ts:.6f}", f"{end_ts:.6f}",
                              m.name, req.question, f"{0.0:.3f}", f"{0.0:.3f}", 0, "", "", "start_failed"])
            self.bus.publish({"type": "request_end", "req_id": req.req_id, "model": m.name,
                              "status": "start_failed", "load_time_s": 0.0, "infer_time_s": 0.0})
            # Queue snapshot may be unchanged here, but publish anyway
            self._publish_queue_snapshot()
            return

        # Stream inference
        infer_t0 = time.perf_counter()
        answer = ""
        status_label = ""
        try:
            answer, http_status = self._send_inference_stream(m, req.question, req.req_id)
            status_label = str(http_status)
        except Exception as e:
            self.logger.error("Inference error for req %d on '%s': %s", req.req_id, m.name, e)
            status_label = "inference_error"
        infer_time_s = time.perf_counter() - infer_t0

        # Write output
        out_path = Path("")
        try:
            out_path = self._write_answer_file(m.name, req.req_id, req.question, answer)
        except Exception as e:
            self.logger.error("Failed writing output for req %d: %s", req.req_id, e)

        end_ts = time.perf_counter()
        self.vram.touch(m.name)
        if m.name in self.servers:
            self.servers[m.name].last_used_ts = time.perf_counter()

        self._append_csv([req.req_id, f"{req.arrival_ts:.6f}", f"{start_ts:.6f}", f"{end_ts:.6f}",
                          m.name, req.question, f"{load_time_s:.3f}", f"{infer_time_s:.3f}",
                          int(was_running), ";".join(evicted) if evicted else "", str(out_path) if out_path else "", status_label])

        self.logger.info("Completed req %d on '%s' -> %s (load=%.2fs, infer=%.2fs, status=%s)",
                         req.req_id, m.name, out_path.name if out_path else "(no file)", load_time_s, infer_time_s, status_label)

        self.bus.publish({"type": "request_end", "req_id": req.req_id, "model": m.name,
                          "status": status_label, "load_time_s": load_time_s, "infer_time_s": infer_time_s})

        # Queue snapshot after completion (in case UI missed the pop event)
        self._publish_queue_snapshot()


# ------------------------------- top-level ------------------------------

def write_system_specs_json(sys_specs: SystemSpecs, path: Path):
    data = dataclasses.asdict(sys_specs)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def main():
    ap = argparse.ArgumentParser(description="LLM Manager – Web Streaming + Process-Group Eviction (Sticky Header + Queue + Pause)")
    ap.add_argument("--config", type=str, default="llm_manager_config.json", help="Path to config JSON")
    ap.add_argument("--requests-file", type=str, default=None, help="Requests file to watch (overrides config)")
    ap.add_argument("--exclusive", action="store_true", help="Force exclusive_mode=True (one server at a time)")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = load_or_init_config(cfg_path)
    if args.requests_file:
        cfg.requests_file = args.requests_file
    if args.exclusive:
        cfg.exclusive_mode = True

    sys_specs = collect_system_specs()
    if cfg.gpu_override:
        if sys_specs.gpus:
            sys_specs.gpus[0].name = str(cfg.gpu_override.get("name", sys_specs.gpus[0].name))
            sys_specs.gpus[0].vram_total_gb = float(cfg.gpu_override.get("vram_total_gb", sys_specs.gpus[0].vram_total_gb))
        else:
            sys_specs.gpus = [GPUInfo(vendor="Override",
                                      name=str(cfg.gpu_override.get("name", "Override GPU")),
                                      vram_total_gb=float(cfg.gpu_override.get("vram_total_gb", 0.0)),
                                      vram_free_gb=0.0)]
    Path(cfg.system_specs_path).parent.mkdir(parents=True, exist_ok=True)
    write_system_specs_json(sys_specs, Path(cfg.system_specs_path))
    print(f"[init] Wrote system specs to {cfg.system_specs_path}")

    ensure_sample_requests(Path(cfg.requests_file), [m.name for m in cfg.models])
    Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)
    Path(cfg.logs_dir).mkdir(parents=True, exist_ok=True)

    bus = EventBus()
    control = ControlState()
    mgr = LLMManager(cfg, sys_specs, bus, control)
    mgr.start()

if __name__ == "__main__":
    main()
