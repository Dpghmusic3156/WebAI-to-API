# src/app/services/stats_collector.py
import time
import threading
from typing import Optional


class StatsCollector:
    """Thread-safe singleton for tracking request statistics."""

    _instance: Optional["StatsCollector"] = None

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._total_requests = 0
        self._success_count = 0
        self._error_count = 0
        self._endpoint_counts: dict[str, int] = {}
        self._last_request_time: Optional[float] = None

    @classmethod
    def get_instance(cls) -> "StatsCollector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_request(self, path: str, status_code: int) -> None:
        with self._lock:
            self._total_requests += 1
            self._last_request_time = time.time()
            if path not in self._endpoint_counts:
                self._endpoint_counts[path] = 0
            self._endpoint_counts[path] += 1
            if 200 <= status_code < 400:
                self._success_count += 1
            else:
                self._error_count += 1

    def get_stats(self) -> dict:
        with self._lock:
            uptime_seconds = time.time() - self._start_time
            hours, remainder = divmod(int(uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            return {
                "uptime": f"{hours}h {minutes}m {seconds}s",
                "uptime_seconds": uptime_seconds,
                "total_requests": self._total_requests,
                "success_count": self._success_count,
                "error_count": self._error_count,
                "endpoints": dict(self._endpoint_counts),
                "last_request_time": self._last_request_time,
            }
