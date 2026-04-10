import threading
from src.audio import record_command
from src.stt import transcribe_audio
from src.router import get_intent
from src.gamepad import trigger_action
from src.config_manager import get_setting


class VoiceEngine:
    """Handles the voice command processing loop."""

    def __init__(self, on_status_change):
        self.on_status_change = on_status_change
        self.stop_event = threading.Event()
        self.stop_event.set()  # Start in stopped state
        self._thread = None

    @property
    def is_running(self):
        return not self.stop_event.is_set()

    def start(self, ptt_key):
        """Start the voice processing engine."""
        if self.is_running:
            return

        self.ptt_key = ptt_key
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("Assistant active.")

    def stop(self):
        """Stop the voice processing engine."""
        self.stop_event.set()
        print("Assistant stopped.")

    def _run_loop(self):
        """Main processing loop."""
        while not self.stop_event.is_set():
            audio_buffer = record_command(
                self.ptt_key,
                self.stop_event,
                on_start=lambda: self.on_status_change("LISTENING", "stop_red"),
                on_stop=lambda: self.on_status_change("PROCESSING", "proc_orange")
            )

            if not audio_buffer or self.stop_event.is_set():
                continue

            text = transcribe_audio(audio_buffer)
            if text:
                print(f"STT: {text}")
                result = get_intent(text)
                intent = result.get("intent", "unknown")
                conf = result.get("confidence", 0)
                print(f"ROUTER: {intent.upper()} ({conf}%)")

                threshold = get_setting("confidence_threshold", 50)
                if intent != "unknown" and conf >= threshold:
                    trigger_action(intent)

            if not self.stop_event.is_set():
                self.on_status_change("READY", "ready_green")
