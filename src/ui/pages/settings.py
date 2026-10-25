import customtkinter as ctk
import keyboard

from src.audio import get_input_devices
from src.config_manager import get_setting, set_setting, get_api_key, save_api_key
from src.ui import theme as t

DEFAULT_MIC = "System default"
STT_MODELS = ["gpt-4o-mini-transcribe", "gpt-4o-transcribe", "whisper-1"]
ROUTER_MODELS = ["gpt-4o-mini", "gpt-4.1-mini"]


class SettingsPage:
    """Every setting saves as soon as it changes."""

    def __init__(self, master, app):
        self.app = app
        self._rebind_hook = None
        self._confidence_job = None
        self.frame = ctk.CTkFrame(master, fg_color=t.CREAM)
        t.page_header(self.frame, "Settings", "Changes save as you make them.")
        t.secondary_button(self.frame, "Run setup wizard", app.open_wizard, bg=t.CREAM, width=150, height=30).place(
            relx=1.0, y=30, anchor="ne")

        voice = self._card("Voice")
        self._ptt_row(voice)
        self._mic_row(voice)
        self._confidence_row(voice)
        self._beeps_row(voice)

        openai = self._card("OpenAI", pady=(14, 0))
        self._key_row(openai)
        self._model_row(openai, "Speech-to-text model", "models.stt", STT_MODELS, "gpt-4o-mini-transcribe",
                        "Turns your voice into text. The mini model is the fastest.")
        self._model_row(openai, "Command model", "models.router", ROUTER_MODELS, "gpt-4o-mini",
                        "Picks which command you meant.")

    # --- Layout helpers ---

    def _card(self, title, pady=(0, 0)):
        outer, card = t.card(self.frame)
        outer.pack(fill="x", pady=pady)
        t.section_title(card, title)
        form = ctk.CTkFrame(card, fg_color=t.CARD)
        form.pack(fill="x", padx=18, pady=(0, 12))
        form.grid_columnconfigure(1, weight=1)
        return form

    def _label(self, form, row, text, note=""):
        """Setting name with its description underneath; returns the description label so it can show status."""
        cell = ctk.CTkFrame(form, fg_color=t.CARD, width=10)
        cell.grid(row=row, column=0, sticky="w", pady=6, padx=(0, 24))
        ctk.CTkLabel(cell, text=text, font=t.font(t.HEAD, 14), text_color=t.TEXT, anchor="w", height=20).pack(anchor="w")
        note_label = ctk.CTkLabel(cell, text=note, font=t.font(t.BODY, 12), text_color=t.FAINT, anchor="w",
                                  justify="left", wraplength=260, height=16)
        note_label.pack(anchor="w")
        return note_label

    def _menu(self, parent, values, current, command, width=280):
        if current not in values:
            values = values + [current]
        menu = ctk.CTkOptionMenu(parent, values=values, command=command, width=width, height=32,
                                 fg_color=t.CREAM, button_color=t.ORANGE, button_hover_color=t.ORANGE_HOVER,
                                 text_color=t.TEXT, dropdown_fg_color=t.CARD, dropdown_hover_color=t.HOVER,
                                 dropdown_text_color=t.TEXT, corner_radius=t.RADIUS, font=t.font(t.BODY, 13),
                                 dropdown_font=t.font(t.BODY, 13), dynamic_resizing=False)
        menu.set(current)
        return menu

    # --- Voice ---

    def _ptt_row(self, form):
        self.ptt_note = self._label(form, 0, "Push-to-talk key", "Any keyboard key. Esc cancels.")
        box = ctk.CTkFrame(form, fg_color=t.CARD, width=10)
        box.grid(row=0, column=1, sticky="w")
        chip = ctk.CTkFrame(box, fg_color=t.CREAM, border_width=1, border_color=t.NAVY, corner_radius=t.RADIUS)
        chip.pack(side="left")
        self.key_chip = ctk.CTkLabel(chip, text=self.app.ptt_label(), font=t.font(t.HEAD, 14, "bold"),
                                     text_color=t.TEXT, width=150, height=28)
        self.key_chip.pack(padx=2, pady=2)
        self.rebind_button = t.secondary_button(box, "Change", self._start_rebind, width=90, height=32)
        self.rebind_button.pack(side="left", padx=(8, 0))

    def _mic_row(self, form):
        self._label(form, 1, "Microphone", "Used while listening. Changing it restarts listening.")
        names = list(dict.fromkeys(d["name"] for d in get_input_devices()))
        current = get_setting("audio.input_device", "") or DEFAULT_MIC
        self._menu(form, [DEFAULT_MIC] + names, current, self._on_mic_changed).grid(row=1, column=1, sticky="w")

    def _confidence_row(self, form):
        self._label(form, 2, "Minimum confidence", "Lower presses more guesses. Higher ignores unclear requests.")
        box = ctk.CTkFrame(form, fg_color=t.CARD, width=10)
        box.grid(row=2, column=1, sticky="w")
        value = get_setting("confidence_threshold", 50)
        self.confidence_value = ctk.CTkLabel(box, text=f"{value}%", font=t.font(t.HEAD, 14, "bold"),
                                             text_color=t.TEXT, width=48)
        slider = ctk.CTkSlider(box, from_=0, to=100, number_of_steps=20, width=220, command=self._on_confidence,
                               progress_color=t.ORANGE, button_color=t.NAVY, button_hover_color=t.NAVY_2,
                               fg_color=t.LINE)
        slider.set(value)
        slider.pack(side="left")
        self.confidence_value.pack(side="left", padx=(10, 0))

    def _beeps_row(self, form):
        self._label(form, 3, "Beeps", "Push-to-talk start and stop, and a double beep when no button was pressed.")
        self.beeps = ctk.BooleanVar(value=get_setting("audio.ptt_sound_enabled", True))
        ctk.CTkSwitch(form, text="", variable=self.beeps, command=self._on_beeps, progress_color=t.ORANGE,
                      button_color=t.NAVY, button_hover_color=t.NAVY_2, fg_color=t.LINE).grid(row=3, column=1, sticky="w")

    # --- OpenAI ---

    def _key_row(self, form):
        self.key_note = self._label(form, 0, "API key", "Stored encrypted in Windows Credential Manager.")
        box = ctk.CTkFrame(form, fg_color=t.CARD, width=10)
        box.grid(row=0, column=1, sticky="w")
        self.key_entry = ctk.CTkEntry(box, width=280, height=32, show="•", fg_color=t.CREAM, border_color=t.NAVY,
                                      border_width=1, corner_radius=t.RADIUS, text_color=t.TEXT,
                                      font=t.font(t.BODY, 13), placeholder_text="sk-…")
        self.key_entry.pack(side="left")
        if get_api_key():
            self.key_entry.insert(0, get_api_key())
        t.secondary_button(box, "Save", self._on_key_save, width=64, height=32).pack(side="left", padx=(8, 0))
        t.secondary_button(box, "Test", self.app.test_api_key, width=64, height=32).pack(side="left", padx=(6, 0))

    def _model_row(self, form, label, setting, options, default, note):
        row = form.grid_size()[1]
        self._label(form, row, label, note)
        self._menu(form, options, get_setting(setting, default),
                   lambda value, s=setting: (set_setting(s, value), print(f"{label}: {value}"))).grid(
            row=row, column=1, sticky="w")

    # --- Events ---

    def on_show(self):
        pass

    def render_listening(self, running):
        if self._rebind_hook is None:
            self.rebind_button.configure(state="disabled" if running else "normal")
            self.ptt_note.configure(text="Stop listening to change it." if running else "Any keyboard key. Esc cancels.")

    def render_key_status(self, message, ok):
        color = t.FAINT if ok is None else (t.GREEN if ok else t.RED)
        self.key_note.configure(text=message, text_color=color)

    def _on_mic_changed(self, selected):
        set_setting("audio.input_device", "" if selected == DEFAULT_MIC else selected)
        print(f"Input device: {selected}")
        self.app.restart_engine()
        self.app.refresh_setup()

    def _on_confidence(self, value):
        value = int(round(value))
        self.confidence_value.configure(text=f"{value}%")
        if self._confidence_job:
            self.frame.after_cancel(self._confidence_job)
        self._confidence_job = self.frame.after(400, lambda: (set_setting("confidence_threshold", value),
                                                              print(f"Confidence threshold set to {value}%.")))

    def _on_beeps(self):
        set_setting("audio.ptt_sound_enabled", self.beeps.get())
        print("Audio feedback enabled." if self.beeps.get() else "Audio feedback disabled.")

    def _on_key_save(self):
        key = self.key_entry.get().strip()
        try:
            save_api_key(key)
        except OSError as e:
            self.render_key_status(f"Windows couldn't save the key: {e.strerror or e}", False)
            return
        self.app.state.key_test = None
        self.render_key_status("Saved. Use Test to check it." if key else "Key removed.", None)
        print("API key saved." if key else "API key cleared.")
        self.app.refresh_setup()

    # --- Push-to-talk rebinding ---

    def _start_rebind(self):
        """The next key press becomes the PTT key; Esc or a second click cancels."""
        if self._rebind_hook is not None:
            self._finish_rebind(None)
            return

        self.key_chip.configure(text="Press a key…", text_color=t.ORANGE)
        self.rebind_button.configure(text="Cancel")
        self.app.set_start_enabled(False)

        # The hook fires on keyboard's listener thread, so the window stays responsive while waiting
        def on_key(event):
            self.app.events.post("rebind", key=event.name)

        self._rebind_hook = keyboard.on_press(on_key)

    def _finish_rebind(self, new_key):
        """Apply the captured key (None or Esc cancels) and stop listening for it."""
        if self._rebind_hook is None:
            return  # Already handled by an earlier key press
        keyboard.unhook(self._rebind_hook)
        self._rebind_hook = None

        if new_key and new_key != "esc":
            self.app.ptt_key = new_key
            set_setting("ptt_key", new_key)
            print(f"Trigger key: {new_key.upper()}")

        self.key_chip.configure(text=self.app.ptt_label(), text_color=t.TEXT)
        self.rebind_button.configure(text="Change")
        self.app.set_start_enabled(True)
        self.app.refresh_status()
