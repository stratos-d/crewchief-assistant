import tkinter as tk
import tkinter.font as tkfont
import threading
import sys

from src.config_manager import get_setting, get_theme, get_api_key
from src.gamepad import trigger_action, init_all_gamepads
from src.ui.widgets import TerminalRedirector
from src.ui.engine import VoiceEngine
from src.ui.panels.control_panel import ControlPanelMixin
from src.ui.panels.settings_panel import SettingsPanelMixin
from src.ui.panels.controllers_panel import ControllersPanel


class CrewChiefGUI(ControlPanelMixin, SettingsPanelMixin, ControllersPanel):
    """Main application GUI."""

    def __init__(self, root):
        self.root = root
        self.root.title("CrewChief Assistant")
        self.root.geometry("960x700")
        self.root.minsize(800, 500)

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
            "section": tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            "lg": tkfont.Font(family="Segoe UI", size=14, weight="bold"),
            "key": tkfont.Font(family="Consolas", size=10, weight="bold"),
            "mono": tkfont.Font(family="Consolas", size=9),
            "cmd": tkfont.Font(family="Segoe UI", size=8)
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
        """Build the main UI: top row (Control + Settings), bottom row (Controllers)."""
        self.main_container = tk.Frame(self.scrollable_frame, bg=self.theme["bg_color"], padx=20, pady=15)
        self.main_container.pack(fill="both", expand=True)

        # Header spans full width
        self._build_header()

        # Top row: Control + Settings side by side
        top_row = tk.Frame(self.main_container, bg=self.theme["bg_color"])
        top_row.pack(fill=tk.X, pady=(0, 12))
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=1)
        top_row.grid_rowconfigure(0, weight=1)

        self.left_col = tk.Frame(top_row, bg=self.theme["bg_color"])
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.right_top = tk.Frame(top_row, bg=self.theme["bg_color"])
        self.right_top.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._build_control_log()
        self._build_settings()

        # Bottom row: Virtual Controllers full width
        self.bottom_row = tk.Frame(self.main_container, bg=self.theme["bg_color"])
        self.bottom_row.pack(fill="both", expand=True)

        self._build_command_binder()

    def _build_header(self):
        header = tk.Frame(self.main_container, bg=self.theme["bg_color"])
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            header,
            text="CREWCHIEF ASSISTANT",
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
            pady=5,
            relief=tk.SOLID,
            bd=1
        )
        self.status_pill.pack(side=tk.RIGHT)

    # --- Event Handlers ---

    def _run_startup(self):
        """Run startup tasks in background."""
        init_all_gamepads()
        self.root.after(0, self._finish_startup)

    def _finish_startup(self):
        """Complete startup on main thread."""
        print("Initialization complete.")
        self._update_status("READY", self.theme["ready_green"])
        self.start_btn.config(state=tk.NORMAL, bg=self.theme["ready_green"], fg=self.theme["bg_color"])
        self.rebind_btn.config(state=tk.NORMAL)
        self._load_binding_buttons()

    def _manual_trigger(self, intent):
        """Manually trigger a command."""
        print(f"EVENT: Manual trigger: {intent}")
        trigger_action(intent)
