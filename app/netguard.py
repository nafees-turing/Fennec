import threading
import time


class NetworkGuard:
    """One outbound scan at a time, plus a short cooldown on the same query."""

    def __init__(self, cooldown: float = 45.0) -> None:
        self.cooldown = cooldown
        self._busy = False
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def begin(self, key: str) -> str | None:
        with self._lock:
            if self._busy:
                return "A network scan is already running. Wait for it to finish."
            last = self._last.get(key, 0.0)
            if self.cooldown and (time.monotonic() - last) < self.cooldown:
                return "That same network query just ran. Wait before repeating it."
            self._busy = True
            return None

    def end(self, key: str) -> None:
        with self._lock:
            self._busy = False
            self._last[key] = time.monotonic()
