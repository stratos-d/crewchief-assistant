import threading
import time
from src.audio import Microphone, record_command
from src.stt import transcribe_audio
from src.router import get_intent
from src.gamepad import trigger_action
from src.config_manager import get_setting
from src.sounds import play_not_understood
from src.ui.state import CommandResult

# Nobody says more than this many words per second; a longer transcript is the model
# returning its hint list for a clip with no speech in it
MAX_WORDS_PER_SECOND = 5


def friendly_error(error):
    """Turn library exceptions into a sentence a driver can act on."""
    name, text = type(error).__name__, str(error)
    if "API key not configured" in text:
        return "Add your OpenAI API key in Settings."
    if name == "AuthenticationError":
        return "Invalid OpenAI API key."
    if name in ("APIConnectionError", "APITimeoutError", "ConnectError", "ConnectTimeout"):
        return "Can't reach OpenAI."
    if name == "RateLimitError":
        return "OpenAI rate limit or quota reached."
    if name == "PortAudioError":
        return "Microphone not available."
    if name == "RuntimeError" and "vJoy" in text:
        return "vJoy not available."
    return text


class VoiceEngine:
    """Handles the voice command processing loop. Reports progress through on_event(kind, **data)."""

    def __init__(self, on_event):
        self.on_event = on_event
        self.stop_event = threading.Event()
        self.stop_event.set()  # Start in stopped state
        self._released_at = None

    @property
    def is_running(self):
        return not self.stop_event.is_set()

    def start(self, ptt_key):
        """Start the voice processing engine."""
        if self.is_running:
            return

        # Each run gets its own event, so a previous run still waiting on an API call
        # stays stopped instead of being revived when this run clears its event
        self.stop_event = threading.Event()
        threading.Thread(target=self._run_loop, args=(ptt_key, self.stop_event), daemon=True).start()
        print("Assistant active.")

    def stop(self):
        """Stop the voice processing engine."""
        self.stop_event.set()
        print("Assistant stopped.")

    def _status(self, stop_event, state, message=""):
        if not stop_event.is_set():
            self.on_event("status", state=state, message=message)

    def _run_loop(self, ptt_key, stop_event):
        """Main processing loop."""
        mic = None
        last_error = None
        while not stop_event.is_set():
            try:
                if mic is None:
                    mic = Microphone()
                    self._status(stop_event, "ready")
                self._process_command(mic, ptt_key, stop_event)
                last_error = None
            except Exception as e:
                message = friendly_error(e)
                if message != last_error:  # a persistent failure is reported once, not every second
                    print(f"ERROR: {e}")
                    if mic is not None:
                        self.on_event("result", result=CommandResult(heard="", outcome="error", message=message))
                        play_not_understood()
                last_error = message
                self._status(stop_event, "error", message)
                # Back off so a persistent failure (bad PTT key, missing mic) doesn't spin
                stop_event.wait(1)
                if mic is None:
                    continue

            self._status(stop_event, "ready")

        if mic is not None:
            mic.close()

    def _on_ptt_pressed(self, stop_event):
        self._status(stop_event, "recording")

    def _on_ptt_released(self, stop_event):
        self._released_at = time.perf_counter()
        self._status(stop_event, "processing")

    def _process_command(self, mic, ptt_key, stop_event):
        """Record one push-to-talk command and trigger the matching action."""
        clip = record_command(
            mic,
            ptt_key,
            stop_event,
            on_start=lambda: self._on_ptt_pressed(stop_event),
            on_stop=lambda: self._on_ptt_released(stop_event)
        )

        if not clip or stop_event.is_set():
            return

        text = transcribe_audio(clip.wav)
        if stop_event.is_set():
            return
        if not text or not text.strip() or len(text.split()) > 4 + MAX_WORDS_PER_SECOND * clip.seconds:
            self._report(CommandResult(heard="", outcome="no_speech"))
            return

        print(f"STT: {text}")
        result = get_intent(text)
        intent = result.get("intent", "unknown")
        conf = result.get("confidence", 0)
        print(f"ROUTER: {intent.upper()} ({conf}%)")

        threshold = get_setting("confidence_threshold", 50)
        outcome = CommandResult(heard=text.strip(), outcome="unknown", command=intent, confidence=conf,
                                exact=result.get("exact", False))
        if intent != "unknown" and conf < threshold:
            outcome.outcome = "low_confidence"
        elif intent != "unknown" and not stop_event.is_set():
            outcome.button = trigger_action(intent)
            outcome.outcome = "pressed" if outcome.button else "no_binding"
        self._report(outcome)

    def _report(self, result):
        if self._released_at is not None:
            result.seconds = time.perf_counter() - self._released_at
        if result.outcome != "pressed":
            play_not_understood()  # the driver can't look at the screen; no button was pressed, so try again
        self.on_event("result", result=result)
