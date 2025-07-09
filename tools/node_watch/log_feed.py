# File: log_feed.py
"""
log_feed.py

Provides LogFeed class to subscribe to Docker container logs in-memory,
rather than re-reading files each interval. Buffers the last N lines per container.
"""
import threading
from collections import deque
import docker
import time

class LogFeed:
    def __init__(self, container_name, tail_lines=60):
        self.container_name = container_name
        self.tail_lines = tail_lines
        self.docker_client = docker.from_env()
        self.buffer = deque(maxlen=tail_lines)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._stream_logs, daemon=True)

    def start(self):
        """Begin background thread streaming logs into buffer."""
        self._stop_event.clear()
        self._thread.start()

    def stop(self):
        """Signal the background thread to stop."""
        self._stop_event.set()
        self._thread.join()

    def _stream_logs(self):
        while not self._stop_event.is_set():
            try:
                container = self.docker_client.containers.get(self.container_name)
                for raw in container.logs(stream=True, tail=self.tail_lines, timestamps=False):
                    if self._stop_event.is_set():
                        break
                    line = raw.decode('utf-8', errors='ignore').rstrip()
                    self.buffer.append(line)
            except Exception:
                time.sleep(5)

    def get_lines(self):
        """Return a list copy of the buffered log lines."""
        return list(self.buffer)