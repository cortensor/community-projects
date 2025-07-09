# File: restarter.py
"""
restarter.py

Contains RestartManager to encapsulate all restart logic, cooldowns, and logging.
"""
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import docker

class RestartManager:
    def __init__(self, log_dir='restart_logs', master_log='watcher.log', cooldown_minutes=10):
        self.docker_client = docker.from_env()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.master_log = Path(master_log)
        if not self.master_log.exists():
            self.master_log.write_text('')
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.last_restart = {}

    def attempt_restart(self, container_name, container_obj, reason_key):
        now = datetime.now(timezone.utc)
        last = self.last_restart.get(container_name, datetime.fromtimestamp(0, timezone.utc))
        if now - last < self.cooldown:
            print(f"[{container_name}] ⚠ Restart skipped (cooldown)")
            return False
        ts = now.strftime('%Y%m%dT%H%M%S')
        buf = '[ERROR capturing logs]\n'
        try:
            raw = container_obj.logs(tail=500, timestamps=False)
            buf = raw.decode('utf-8', errors='ignore')
        except Exception:
            pass
        fname = f"{container_name}_{reason_key}_{ts}.log"
        self.log_dir.joinpath(fname).write_text(buf, encoding='utf-8')
        entry = f"{now.isoformat()} UTC  Restarted '{container_name}' ({reason_key}) → '{fname}'\n"
        self.master_log.write_text(self.master_log.read_text() + entry, encoding='utf-8')
        try:
            container_obj.restart()
            print(f"[{container_name}] ✔ Restarted ({reason_key})")
        except Exception as e:
            print(f"[{container_name}] ✘ Restart failed: {e}")
        self.last_restart[container_name] = now
        return True
