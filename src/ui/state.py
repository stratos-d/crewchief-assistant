"""App-wide state. Worker threads only post events; the window applies them on the Tk thread."""
import queue
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CommandResult:
    """One push-to-talk command, as shown in Recent commands and the activity log."""
    heard: str
    outcome: str  # pressed | unknown | low_confidence | no_binding | no_speech | error
    command: str = ""
    confidence: int = 0
    exact: bool = False
    button: int = None
    seconds: float = None
    message: str = ""
    time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M"))


@dataclass
class AppState:
    status: str = "off"
    status_message: str = ""
    recent: deque = field(default_factory=lambda: deque(maxlen=6))
    vjoy: dict = None  # {"ok": bool, "buttons": int, "message": str} once startup has checked the driver
    key_test: tuple = None  # (ok, message) after the user tests the API key
    synced_this_session: bool = False


class EventQueue:
    """Thread-safe hand-off from the engine and worker threads to the Tk thread."""

    def __init__(self):
        self._queue = queue.Queue()

    def post(self, kind, **data):
        self._queue.put((kind, data))

    def drain(self):
        while True:
            try:
                yield self._queue.get_nowait()
            except queue.Empty:
                return


class LogWriter:
    """Replaces sys.stdout so print() output lands in the Activity log, one event per line."""

    def __init__(self, post):
        self._post = post
        self._buffer = ""
        self._lock = threading.Lock()  # the engine, worker threads and the UI all print

    def write(self, text):
        with self._lock:
            self._buffer += text
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                if line.strip():
                    self._post("log", text=line.strip())

    def flush(self):
        pass
