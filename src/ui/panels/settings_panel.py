import tkinter as tk
import keyboard

from src.config_manager import get_setting, set_setting, get_api_key, save_api_key
from src.ui.widgets import SettingsRow
from src.ui.modals import ApiKeyModal


class SettingsPanelMixin:
    """Mixin providing the Settings card and all settings event handlers."""

    def _build_settings(self):
        settings_card = tk.Frame(self.right_top, bg=self.theme["card_bg"], padx=15, pady=10)
        settings_card.pack(fill="both", expand=True)

        tk.Label(
            settings_card,
            text="SETTINGS",
            font=self.fonts["section"],
            bg=self.theme["card_bg"],
            fg=self.theme["accent_color"]
        ).pack(anchor="w", pady=(0, 12))

        api_row = SettingsRow(settings_card, "OpenAI API Key", self.fonts, self.theme)
        api_row.pack(fill=tk.X, pady=(0, 6))
        self.api_status = api_row.add_status_label(bool(self.api_key))
        api_row.add_button("CONFIGURE", self._open_api_modal)

        tk.Frame(settings_card, bg=self.theme["bg_color"], height=1).pack(fill=tk.X, pady=10)

        tk.Label(
            settings_card,
            text="VOICE",
            font=self.fonts["section"],
            bg=self.theme["card_bg"],
            fg=self.theme["accent_color"]
        ).pack(anchor="w", pady=(0, 8))

        device_row = SettingsRow(settings_card, "Input Device", self.fonts, self.theme)
        device_row.pack(fill=tk.X, pady=(0, 6))

        self.input_devices = self._get_input_devices()
        seen = set()
        device_names = []
        for d in self.input_devices:
            if d['name'] not in seen:
                seen.add(d['name'])
                device_names.append(d['name'])

        current_device = get_setting("audio.input_device", "")
        self.device_var = tk.StringVar(value=current_device if current_device else "Default")
        self.device_menu = tk.OptionMenu(
            device_row.frame,
            self.device_var,
            "Default",
            *device_names,
            command=self._on_device_changed
        )
        self.device_menu.config(
            font=self.fonts["sm"],
            bg=self.theme["btn_bg"],
            fg=self.theme["text_main"],
            activebackground=self.theme["accent_color"],
            activeforeground=self.theme["bg_color"],
            highlightthickness=0,
            relief=tk.FLAT,
            indicatoron=0,
            compound=tk.RIGHT,
            padx=10
        )
        self.device_menu["menu"].config(
            bg=self.theme["card_bg"],
            fg=self.theme["text_main"],
            activebackground=self.theme["accent_color"],
            activeforeground=self.theme["bg_color"]
        )
        self.device_menu.pack(side=tk.RIGHT)

        ptt_row = SettingsRow(settings_card, "Push to Talk Key", self.fonts, self.theme)
        ptt_row.pack(fill=tk.X, pady=(0, 6))
        self.key_display = ptt_row.add_value_label(self.ptt_key.upper(), accent=True)
        self.rebind_btn = ptt_row.add_button("CHANGE", self._start_rebind, state=tk.DISABLED)

        sound_row = SettingsRow(settings_card, "Audio Feedback", self.fonts, self.theme)
        sound_row.pack(fill=tk.X, pady=(0, 6))
        self.sound_toggle_btn = tk.Button(
            sound_row.frame,
            text="ON" if self.ptt_sound_enabled else "OFF",
            font=self.fonts["sm"],
            width=4,
            bg=self.theme["ready_green"] if self.ptt_sound_enabled else self.theme["btn_bg"],
            fg=self.theme["bg_color"] if self.ptt_sound_enabled else self.theme["text_dim"],
            activebackground=self.theme["ready_green"] if self.ptt_sound_enabled else self.theme["btn_bg"],
            relief=tk.FLAT,
            cursor="hand2",
            command=self._toggle_ptt_sound
        )
        self.sound_toggle_btn.pack(side=tk.RIGHT)

        threshold_row = SettingsRow(settings_card, "Min. Confidence", self.fonts, self.theme)
        threshold_row.pack(fill=tk.X)
        self.threshold_var = tk.StringVar(value=str(self.confidence_threshold))
        threshold_row.add_entry(self.threshold_var, width=4)
        threshold_row.add_suffix("%")
        threshold_row.add_button("APPLY", self._save_threshold)

    def _get_input_devices(self):
        """Get list of available audio input devices."""
        from src.audio import get_input_devices
        return get_input_devices()

    def _start_rebind(self):
        """Start PTT key rebinding."""
        self.rebind_btn.config(text="LISTENING...", bg=self.theme["proc_orange"], fg=self.theme["bg_color"])
        self.key_display.config(text="???", fg=self.theme["proc_orange"])
        self.root.update()
        new_key = keyboard.read_key()
        self.ptt_key = new_key
        set_setting("ptt_key", self.ptt_key)
        self.key_display.config(text=self.ptt_key.upper(), fg=self.theme["accent_color"])
        self.rebind_btn.config(text="CHANGE", bg=self.theme["btn_bg"], fg=self.theme["text_main"])
        print(f"Trigger key: {self.ptt_key.upper()}")

    def _on_device_changed(self, selected):
        """Handle input device selection change."""
        if selected == "Default":
            set_setting("audio.input_device", "")
            print("Input device: System Default")
        else:
            set_setting("audio.input_device", selected)
            print(f"Input device: {selected}")

    def _save_threshold(self):
        """Save confidence threshold."""
        try:
            val = int(self.threshold_var.get())
            val = max(0, min(100, val))
            self.confidence_threshold = val
            self.threshold_var.set(str(val))
            set_setting("confidence_threshold", val)
            print(f"Confidence threshold set to {val}%.")
        except ValueError:
            self.threshold_var.set(str(self.confidence_threshold))
            print("Invalid threshold value.")

    def _toggle_ptt_sound(self):
        """Toggle PTT sound on/off."""
        self.ptt_sound_enabled = not self.ptt_sound_enabled
        set_setting("audio.ptt_sound_enabled", self.ptt_sound_enabled)
        if self.ptt_sound_enabled:
            self.sound_toggle_btn.config(
                text="ON",
                bg=self.theme["ready_green"],
                fg=self.theme["bg_color"],
                activebackground=self.theme["ready_green"]
            )
            print("Audio feedback enabled.")
        else:
            self.sound_toggle_btn.config(
                text="OFF",
                bg=self.theme["btn_bg"],
                fg=self.theme["text_dim"],
                activebackground=self.theme["btn_bg"]
            )
            print("Audio feedback disabled.")

    def _open_api_modal(self):
        """Open API key configuration modal."""
        ApiKeyModal(
            self.root,
            self.fonts,
            self.theme,
            self.api_key,
            on_save=self._on_api_key_saved
        )

    def _on_api_key_saved(self, key):
        """Handle API key save."""
        self.api_key = key
        save_api_key(key)
        is_set = bool(key)
        self.api_status.config(
            text="SET" if is_set else "NOT SET",
            fg=self.theme["ready_green"] if is_set else self.theme["stop_red"]
        )
        print("API key saved." if is_set else "API key cleared.")
