import tkinter as tk
import tkinter.font as tkfont
import threading
import sys
import keyboard

from src.config_manager import (
    get_setting, set_setting,
    get_controllers, get_controller_bindings, get_all_commands,
    get_theme, get_api_key, save_api_key,
    rename_binding, add_controller, remove_controller
)
from src.gamepad import trigger_action, trigger_button, init_all_gamepads, get_gamepad, release_gamepad
from src.ui.widgets import TerminalRedirector, SettingsRow
from src.ui.modals import ApiKeyModal, RenameCommandModal
from src.ui.engine import VoiceEngine


class CrewChiefGUI:
    """Main application GUI."""

    def __init__(self, root):
        self.root = root
        self.root.title("CrewChief Assistant")
        self.root.geometry("520x700")

        self._load_theme()
        self._setup_fonts()
        self._setup_scrollable_window()
        self._load_settings()

        self.engine = VoiceEngine(on_status_change=self._on_engine_status)

        self._build_ui()

        sys.stdout = TerminalRedirector(self.terminal_text)
        threading.Thread(target=self._run_startup, daemon=True).start()

    # --- Setup ---

    def _load_theme(self):
        """Load theme colors from config."""
        self.theme = get_theme()
        self.root.configure(bg=self.theme["bg_color"])

    def _setup_fonts(self):
        """Initialize font definitions."""
        self.fonts = {
            "sm": tkfont.Font(family="Segoe UI", size=9),
            "base": tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            "lg": tkfont.Font(family="Segoe UI", size=14, weight="bold"),
            "key": tkfont.Font(family="Consolas", size=10, weight="bold"),
            "mono": tkfont.Font(family="Consolas", size=9)
        }

    def _setup_scrollable_window(self):
        """Create scrollable canvas container."""
        self.canvas = tk.Canvas(self.root, bg=self.theme["bg_color"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.theme["bg_color"])

        self.scrollable_frame.bind("<Configure>", lambda e: self._update_scroll_region())
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _load_settings(self):
        """Load current settings from config."""
        self.ptt_key = get_setting("ptt_key", "scroll lock")
        self.api_key = get_api_key()
        self.confidence_threshold = get_setting("confidence_threshold", 50)
        self.ptt_sound_enabled = get_setting("audio.ptt_sound_enabled", True)

    # --- Scroll Handling ---

    def _update_scroll_region(self):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        content_height = y2 - y1
        canvas_height = self.canvas.winfo_height()
        if content_height > canvas_height:
            self.canvas.configure(scrollregion=(0, 0, x2, y2))
            self.scrollbar.pack(side="right", fill="y")
            self._scroll_enabled = True
        else:
            self.canvas.configure(scrollregion=(0, 0, x2, canvas_height))
            self.canvas.yview_moveto(0)
            self.scrollbar.pack_forget()
            self._scroll_enabled = False

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self._update_scroll_region()

    def _on_mousewheel(self, event):
        if getattr(self, '_scroll_enabled', False):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # --- UI Building ---

    def _build_ui(self):
        """Build the main UI."""
        self.main_container = tk.Frame(self.scrollable_frame, bg=self.theme["bg_color"], padx=25, pady=20)
        self.main_container.pack(fill="both", expand=True)

        self._build_header()
        self._build_controls()
        self._build_system_log()
        self._build_settings()
        self._build_command_binder()

    def _build_header(self):
        header = tk.Frame(self.main_container, bg=self.theme["bg_color"])
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            header,
            text="CREWCHIEF",
            font=self.fonts["lg"],
            bg=self.theme["bg_color"],
            fg=self.theme["accent_color"]
        ).pack(side=tk.LEFT)

        self.status_pill = tk.Label(
            header,
            text="INITIALIZING",
            font=self.fonts["base"],
            bg=self.theme["card_bg"],
            fg=self.theme["proc_orange"],
            padx=15,
            pady=5
        )
        self.status_pill.pack(side=tk.RIGHT)

    def _build_controls(self):
        ctrl_frame = tk.Frame(self.main_container, bg=self.theme["bg_color"])
        ctrl_frame.pack(fill=tk.X, pady=(0, 15))

        self.start_btn = tk.Button(
            ctrl_frame,
            text="START",
            font=self.fonts["base"],
            bg=self.theme["btn_bg"],
            fg=self.theme["text_main"],
            relief=tk.FLAT,
            pady=10,
            command=self._start_engine,
            state=tk.DISABLED
        )
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_btn = tk.Button(
            ctrl_frame,
            text="STOP",
            font=self.fonts["base"],
            bg=self.theme["btn_bg"],
            fg=self.theme["text_main"],
            relief=tk.FLAT,
            pady=10,
            command=self._stop_engine,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    def _build_settings(self):
        settings_card = tk.Frame(self.main_container, bg=self.theme["card_bg"], padx=15, pady=10)
        settings_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            settings_card,
            text="SETTINGS",
            font=self.fonts["sm"],
            bg=self.theme["card_bg"],
            fg=self.theme["text_dim"]
        ).pack(anchor="w", pady=(0, 12))

        # --- API Section ---
        api_row = SettingsRow(settings_card, "OpenAI API Key", self.fonts, self.theme)
        api_row.pack(fill=tk.X, pady=(0, 6))
        self.api_status = api_row.add_status_label(bool(self.api_key))
        api_row.add_button("CONFIGURE", self._open_api_modal)

        # Divider
        tk.Frame(settings_card, bg=self.theme["bg_color"], height=1).pack(fill=tk.X, pady=10)

        # --- Voice Section ---
        tk.Label(
            settings_card,
            text="VOICE",
            font=self.fonts["sm"],
            bg=self.theme["card_bg"],
            fg=self.theme["text_dim"]
        ).pack(anchor="w", pady=(0, 8))

        # Input Device row
        device_row = SettingsRow(settings_card, "Input Device", self.fonts, self.theme)
        device_row.pack(fill=tk.X, pady=(0, 6))

        self.input_devices = self._get_input_devices()
        # Filter unique device names only
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

        # PTT Key row
        ptt_row = SettingsRow(settings_card, "Push to Talk Key", self.fonts, self.theme)
        ptt_row.pack(fill=tk.X, pady=(0, 6))
        self.key_display = ptt_row.add_value_label(self.ptt_key.upper(), accent=True)
        self.rebind_btn = ptt_row.add_button("CHANGE", self._start_rebind, state=tk.DISABLED)

        # Audio Feedback row
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

        # Confidence Threshold row
        threshold_row = SettingsRow(settings_card, "Min. Confidence", self.fonts, self.theme)
        threshold_row.pack(fill=tk.X)
        self.threshold_var = tk.StringVar(value=str(self.confidence_threshold))
        threshold_row.add_entry(self.threshold_var, width=4)
        threshold_row.add_suffix("%")
        threshold_row.add_button("APPLY", self._save_threshold)

    def _build_system_log(self):
        log_card = tk.Frame(self.main_container, bg=self.theme["card_bg"], padx=15, pady=10)
        log_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            log_card,
            text="SYSTEM LOG",
            font=self.fonts["sm"],
            bg=self.theme["card_bg"],
            fg=self.theme["text_dim"]
        ).pack(anchor="w", pady=(0, 8))

        term_frame = tk.Frame(log_card, bg=self.theme["term_bg"])
        term_frame.pack(fill=tk.X)

        self.terminal_text = tk.Text(
            term_frame,
            bg=self.theme["term_bg"],
            fg=self.theme["text_main"],
            font=self.fonts["mono"],
            wrap=tk.WORD,
            state=tk.DISABLED,
            borderwidth=0,
            padx=12,
            pady=10,
            height=6
        )
        self.terminal_text.pack(fill="both", expand=True)

    def _build_command_binder(self):
        self.binder_card = tk.Frame(self.main_container, bg=self.theme["card_bg"], padx=15, pady=10)
        self.binder_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            self.binder_card,
            text="VIRTUAL CONTROLLERS",
            font=self.fonts["sm"],
            bg=self.theme["card_bg"],
            fg=self.theme["text_dim"]
        ).pack(anchor="w", pady=(0, 12))

        # Container for all controllers
        self.controllers_frame = tk.Frame(self.binder_card, bg=self.theme["card_bg"])
        self.controllers_frame.pack(fill=tk.X)

    def _load_binding_buttons(self):
        """Load command binding buttons for all controllers."""
        for widget in self.controllers_frame.winfo_children():
            widget.destroy()

        controllers = get_controllers()
        for idx, controller in enumerate(controllers):
            self._build_controller_section(idx, controller, len(controllers))

    def _build_controller_section(self, idx, controller, total_controllers):
        """Build UI section for a single controller."""
        # Add divider before each controller except the first
        if idx > 0:
            tk.Frame(self.controllers_frame, bg=self.theme["bg_color"], height=1).pack(fill=tk.X, pady=(0, 10))

        ctrl_frame = tk.Frame(self.controllers_frame, bg=self.theme["card_bg"])
        ctrl_frame.pack(fill=tk.X, pady=(0, 6))

        # Controller header with name and +/- buttons
        header = tk.Frame(ctrl_frame, bg=self.theme["card_bg"])
        header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            header,
            text=controller.get("name", f"Controller {idx + 1}").upper(),
            font=self.fonts["sm"],
            bg=self.theme["card_bg"],
            fg=self.theme["text_dim"]
        ).pack(side=tk.LEFT)

        # +/- buttons on the right of each controller header
        btn_frame = tk.Frame(header, bg=self.theme["card_bg"])
        btn_frame.pack(side=tk.RIGHT)

        # Show - button only for non-first controllers
        if idx > 0:
            remove_btn = tk.Button(
                btn_frame,
                text="✕",
                font=("Segoe UI", 8),
                bg=self.theme["card_bg"],
                fg=self.theme["stop_red"],
                activebackground=self.theme["card_bg"],
                activeforeground=self.theme["stop_red"],
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                command=lambda i=idx: self._remove_controller(i)
            )
            remove_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Show + button only on last controller and if < 3 total
        if idx == total_controllers - 1 and total_controllers < 3:
            add_btn = tk.Button(
                btn_frame,
                text="+",
                font=("Segoe UI", 10),
                bg=self.theme["card_bg"],
                fg=self.theme["ready_green"],
                activebackground=self.theme["card_bg"],
                activeforeground=self.theme["ready_green"],
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                command=self._add_new_controller
            )
            add_btn.pack(side=tk.LEFT)

        # Button grid
        btn_grid = tk.Frame(ctrl_frame, bg=self.theme["card_bg"])
        btn_grid.pack(fill=tk.X)

        num_cols = 3
        for col in range(num_cols):
            btn_grid.grid_columnconfigure(col, weight=1)

        bindings = controller.get("bindings", {})
        row, col = 0, 0
        for button_key, command in bindings.items():
            btn = tk.Button(
                btn_grid,
                text=command.upper(),
                font=("Segoe UI", 8, "bold"),
                relief=tk.FLAT,
                bg=self.theme["bg_color"],
                fg=self.theme["text_dim"],
                activebackground=self.theme["accent_color"],
                activeforeground=self.theme["bg_color"],
                pady=5,
                command=lambda i=idx, c=command: self._manual_trigger_controller(i, c)
            )
            btn.grid(row=row, column=col, sticky=tk.EW, padx=1, pady=1)

            # Right-click to rename
            btn.bind("<Button-3>", lambda e, i=idx, b=button_key, c=command: self._open_rename_modal(i, b, c))

            col += 1
            if col >= num_cols:
                col, row = 0, row + 1

    def _add_new_controller(self):
        """Add a new controller with default bindings."""
        from src.config_manager import get_available_buttons
        controllers = get_controllers()
        if len(controllers) >= 3:
            print("Maximum 3 controllers allowed.")
            return

        new_idx = add_controller()
        if new_idx >= 0:
            # Generate default bindings like "button 1", "button 2", etc.
            buttons = get_available_buttons()
            for i, btn_key in enumerate(buttons):
                cmd_name = f"button {new_idx * len(buttons) + i + 1}"
                rename_binding(new_idx, btn_key, cmd_name)

            # Initialize the virtual gamepad for this controller
            threading.Thread(
                target=lambda: get_gamepad(new_idx),
                daemon=True
            ).start()

            print(f"Added Controller {new_idx + 1}")
            self._load_binding_buttons()

    def _remove_controller(self, controller_index):
        """Remove a specific controller."""
        if remove_controller(controller_index):
            # Release the virtual gamepad
            release_gamepad(controller_index)
            print(f"Removed Controller {controller_index + 1}")
            self._load_binding_buttons()

    def _open_rename_modal(self, controller_index, button_key, command):
        """Open modal to rename a command."""
        existing_commands = get_all_commands()
        RenameCommandModal(
            self.root,
            self.fonts,
            self.theme,
            command,
            button_key,
            existing_commands,
            on_save=lambda old, new, btn: self._on_command_renamed(controller_index, old, new, btn)
        )

    def _on_command_renamed(self, controller_index, old_command, new_command, button_key):
        """Handle command rename."""
        rename_binding(controller_index, button_key, new_command)
        self._load_binding_buttons()
        print(f"Renamed '{old_command}' to '{new_command}'")

    def _manual_trigger_controller(self, controller_index, command):
        """Manually trigger a command on a specific controller."""
        from src.config_manager import find_command_controller
        result = find_command_controller(command)
        if result:
            idx, button_key = result
            trigger_button(idx, button_key)
            print(f"Manual trigger: {command} (Controller {idx + 1})")

    # --- Event Handlers ---

    def _run_startup(self):
        """Run startup tasks in background."""
        init_all_gamepads()
        self.root.after(0, self._finish_startup)

    def _finish_startup(self):
        """Complete startup on main thread."""
        print("Initialization complete.")
        self._update_status("READY", self.theme["ready_green"])
        self.start_btn.config(state=tk.NORMAL, bg=self.theme["ready_green"])
        self.rebind_btn.config(state=tk.NORMAL)
        self._load_binding_buttons()

    def _update_status(self, text, color):
        """Update status pill."""
        self.root.after(0, lambda: self.status_pill.config(text=text, fg=color))

    def _on_engine_status(self, status, color_key):
        """Callback for engine status changes."""
        color = self.theme.get(color_key, self.theme["text_main"])
        self._update_status(status, color)

    def _start_engine(self):
        """Start the voice engine."""
        self._update_status("READY", self.theme["ready_green"])
        self.start_btn.config(state=tk.DISABLED, bg=self.theme["btn_bg"])
        self.stop_btn.config(state=tk.NORMAL, bg=self.theme["stop_red"])
        self.rebind_btn.config(state=tk.DISABLED)
        self.engine.start(self.ptt_key)

    def _stop_engine(self):
        """Stop the voice engine."""
        self.engine.stop()
        self._update_status("OFFLINE", self.theme["text_dim"])
        self.start_btn.config(state=tk.NORMAL, bg=self.theme["ready_green"])
        self.stop_btn.config(state=tk.DISABLED, bg=self.theme["btn_bg"])
        self.rebind_btn.config(state=tk.NORMAL)

    def _start_rebind(self):
        """Start PTT key rebinding."""
        self.rebind_btn.config(text="LISTENING...", bg=self.theme["proc_orange"])
        self.key_display.config(text="???", fg=self.theme["proc_orange"])
        self.root.update()
        new_key = keyboard.read_key()
        self.ptt_key = new_key
        set_setting("ptt_key", self.ptt_key)
        self.key_display.config(text=self.ptt_key.upper(), fg=self.theme["accent_color"])
        self.rebind_btn.config(text="CHANGE", bg=self.theme["btn_bg"])
        print(f"Trigger key: {self.ptt_key.upper()}")

    def _get_input_devices(self):
        """Get list of available audio input devices."""
        from src.audio import get_input_devices
        return get_input_devices()

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

    def _manual_trigger(self, intent):
        """Manually trigger a command."""
        print(f"EVENT: Manual trigger: {intent}")
        trigger_action(intent)
