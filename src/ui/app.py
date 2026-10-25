import os
import sys
import threading
import traceback
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.audio import get_input_devices
from src.config_manager import (
    get_setting, set_setting, get_api_key, get_controllers, load_config, save_config,
    get_openai_client, preload_openai, migrate_api_key, _parse_binding
)
from src.gamepad import init_vjoy, release_vjoy
from src.ui import theme as t
from src.ui.engine import VoiceEngine, friendly_error
from src.ui.state import AppState, EventQueue, LogWriter
from src.ui.pages.home import HomePage
from src.ui.pages.commands import CommandsPage
from src.ui.pages.settings import SettingsPage
from src.ui.pages.activity import ActivityPage
from src.ui.wizard import SetupWizard

NAV = [("home", "Home", t.GLYPH_HOME), ("commands", "Commands", t.GLYPH_COMMANDS),
       ("settings", "Settings", t.GLYPH_SETTINGS), ("activity", "Activity", t.GLYPH_ACTIVITY)]
VJOY_URL = "https://sourceforge.net/projects/vjoystick/"


class CrewChiefGUI:
    """Main window: sidebar navigation, four pages, and the event pump that keeps them in sync."""

    def __init__(self, root):
        self.root = root
        t.init(root)
        self.root.title("CrewChief Assistant")
        self._set_window_icon()
        self.root.geometry("1100x720")
        self.root.minsize(940, 620)
        self.root.configure(fg_color=t.CREAM)

        self.state = AppState()
        self.events = EventQueue()
        self.engine = VoiceEngine(on_event=self.events.post)
        self.ptt_key = get_setting("ptt_key", "scroll lock")
        self.wizard = None

        self._build_sidebar()
        self.content = content = ctk.CTkFrame(self.root, fg_color=t.CREAM)
        content.pack(side="left", fill="both", expand=True, padx=28, pady=18)
        self.root.bind("<Configure>", self._limit_content_width, add="+")
        self.pages = {
            "home": HomePage(content, self),
            "commands": CommandsPage(content, self),
            "settings": SettingsPage(content, self),
            "activity": ActivityPage(content, self),
        }
        self.current_page = None

        sys.stdout = LogWriter(self.events.post)
        self.root.report_callback_exception = self._on_ui_error
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        migrate_api_key()

        self.show("home")
        self.refresh_status()
        self.refresh_counts()
        self.refresh_setup()
        self.pages["home"].render_recent(self.state.recent)
        self._pump()
        threading.Thread(target=self._run_startup, daemon=True).start()
        if not get_setting("setup_complete", False) and not get_api_key():
            self.open_wizard()  # first launch

    # --- Setup ---

    def _set_window_icon(self):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.icon_path = os.path.join(base_path, "resources", "app.ico")
        if os.path.exists(self.icon_path):
            self.root.iconbitmap(self.icon_path)

    def _build_sidebar(self):
        side = ctk.CTkFrame(self.root, fg_color=t.NAVY, corner_radius=0, width=224)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        for color in (t.ORANGE, t.BLUE):
            ctk.CTkFrame(self.root, fg_color=color, corner_radius=0, width=4).pack(side="left", fill="y")

        logo = ctk.CTkFrame(side, fg_color=t.NAVY, width=10)
        logo.pack(anchor="w", padx=16, pady=(20, 22))
        ctk.CTkLabel(logo, text="CREWCHIEF", font=t.font(t.HEAD, 20, "bold"), text_color="#ffffff", height=24).pack(anchor="w")
        ctk.CTkLabel(logo, text="ASSISTANT", font=t.font(t.HEAD, 12), text_color=t.ORANGE, height=14).pack(anchor="w")

        self.nav_items = {}
        for key, name, glyph in NAV:
            row = ctk.CTkFrame(side, fg_color=t.NAVY, corner_radius=t.RADIUS, height=36, cursor="hand2")
            row.pack(fill="x", padx=12, pady=1)
            bar = ctk.CTkFrame(row, fg_color=t.NAVY, width=3, height=22, corner_radius=1)
            bar.pack(side="left", padx=(4, 0))
            icon = ctk.CTkLabel(row, text=glyph, font=t.font(t.ICON, 15), width=22, height=34, cursor="hand2")
            icon.pack(side="left", padx=(8, 8))
            label = ctk.CTkLabel(row, text=name, font=t.font(t.HEAD, 14), height=34, cursor="hand2")
            label.pack(side="left")
            count = ctk.CTkLabel(row, text="", font=t.font(t.HEAD, 12), height=34, cursor="hand2")
            count.pack(side="right", padx=10)
            for widget in (row, icon, label, count):
                widget.bind("<Button-1>", lambda e, k=key: self.show(k))
            self.nav_items[key] = (row, bar, icon, label, count)

        mini = ctk.CTkFrame(side, fg_color=t.NAVY_2, corner_radius=t.RADIUS + 2)
        mini.pack(side="bottom", fill="x", padx=12, pady=14)
        top = ctk.CTkFrame(mini, fg_color=t.NAVY_2, width=10)
        top.pack(anchor="w", padx=12, pady=(12, 0))
        self.mini_dot = ctk.CTkLabel(top, text="●", font=t.font(t.BODY, 13), height=20)
        self.mini_dot.pack(side="left")
        self.mini_label = ctk.CTkLabel(top, text="", font=t.font(t.HEAD, 14, "bold"), text_color="#ffffff", height=20)
        self.mini_label.pack(side="left", padx=(4, 0))
        self.mini_hint = ctk.CTkLabel(mini, text="", font=t.font(t.BODY, 12), text_color=t.SIDE_MUTED, height=18,
                                      wraplength=170, justify="left")
        self.mini_hint.pack(anchor="w", padx=(30, 12))
        self.mini_button = t.primary_button(mini, "Start listening", self.toggle_listening, height=30)
        self.mini_button.pack(fill="x", padx=12, pady=(10, 12))

    def _limit_content_width(self, event):
        """Keep pages readable on wide screens: cap them at ~1200 px and centre them."""
        if event.widget is not self.root:
            return
        available = event.width - t.px(232)
        pad = max(28, (available - t.px(1200)) // 2)
        if self.content.pack_info().get("padx") != pad:
            self.content.pack_configure(padx=pad)

    def _run_startup(self):
        """Run startup tasks in background."""
        vjoy = init_vjoy()
        self.events.post("vjoy", **vjoy)
        preload_openai()

    # --- Navigation ---

    def show(self, key):
        if self.current_page:
            self.pages[self.current_page].frame.pack_forget()
        self.current_page = key
        page = self.pages[key]
        page.on_show()
        page.frame.pack(fill="both", expand=True)
        for name, (row, bar, icon, label, count) in self.nav_items.items():
            selected = name == key
            row.configure(fg_color=t.NAVY_2 if selected else t.NAVY)
            bar.configure(fg_color=t.ORANGE if selected else t.NAVY)
            color = "#ffffff" if selected else t.SIDE_MUTED
            for widget in (icon, label, count):
                widget.configure(text_color=color)

    # --- Event pump: everything from worker threads is applied here, on the Tk thread ---

    def _pump(self):
        for kind, data in self.events.drain():
            getattr(self, f"_on_{kind}")(**data)
        self.root.after(50, self._pump)

    def _on_log(self, text):
        self.pages["activity"].append(text)

    def _on_status(self, state, message=""):
        # A stopped run can still have a status update in flight; ignore it
        if not self.engine.is_running:
            return
        self.set_status(state, message)

    def _on_result(self, result):
        self.state.recent.appendleft(result)
        self.pages["home"].render_recent(self.state.recent)
        self._refresh_wizard()

    def _on_vjoy(self, ok, buttons):
        self.state.vjoy = {"ok": ok, "buttons": buttons}
        self.refresh_setup()

    def _on_rebind(self, key):
        self.pages["settings"]._finish_rebind(key)

    def _on_key_test(self, ok, message):
        self.state.key_test = (ok, message)
        self.pages["settings"].render_key_status(message, ok)
        self.refresh_setup()

    def _on_ui_error(self, exc, value, tb):
        print(f"ERROR: {value}")
        for line in traceback.format_exception(exc, value, tb):
            for part in line.rstrip().splitlines():
                print(part)

    # --- Listening ---

    def toggle_listening(self):
        if self.engine.is_running:
            self.engine.stop()
            self.set_status("off")
            return
        if not get_api_key():
            self.set_status("error", "Add your OpenAI API key in Settings first.")
            self.show("settings")
            return
        self.engine.start(self.ptt_key)
        self.set_status("starting")

    def restart_engine(self):
        """Reopen the microphone and key hook with the current settings."""
        if self.engine.is_running:
            self.engine.stop()
            self.engine.start(self.ptt_key)
            self.set_status("starting")

    def set_status(self, state, message=""):
        self.state.status, self.state.status_message = state, message
        self.refresh_status()

    def set_start_enabled(self, enabled):
        for button in (self.mini_button, self.pages["home"].button):
            button.configure(state="normal" if enabled else "disabled")

    def ptt_label(self):
        return self.ptt_key.title()

    def mic_label(self):
        return get_setting("audio.input_device", "") or "System default microphone"

    def status_detail(self):
        state, key = self.state.status, self.ptt_label()
        return {
            "off": f"Press Start, then hold {key} and speak.",
            "starting": "Opening the microphone…",
            "ready": f"Hold {key} to talk  ·  {self.mic_label()}",
            "recording": f"Release {key} to send",
            "processing": "Working out what you said…",
        }.get(state, self.state.status_message)

    def mini_detail(self):
        """Short hint for the sidebar card."""
        state, key = self.state.status, self.ptt_label()
        message = self.state.status_message
        return {
            "off": "Press Start to listen",
            "starting": "Opening the microphone…",
            "ready": f"Hold {key} to talk",
            "recording": f"Release {key} to send",
            "processing": "Working…",
        }.get(state, message if len(message) < 48 else message[:45] + "…")

    def refresh_status(self):
        label, color, lamp = t.STATUS[self.state.status]
        running = self.engine.is_running
        detail = self.status_detail()
        self.mini_dot.configure(text_color=lamp)
        self.mini_label.configure(text=label.capitalize())
        self.mini_hint.configure(text=self.mini_detail())
        self.mini_button.configure(text="Stop listening" if running else "Start listening")
        self.pages["home"].render_status(label, color, lamp, detail, running)
        self.pages["settings"].render_listening(running)
        self._refresh_wizard()

    # --- Setup wizard ---

    def open_wizard(self):
        if self.wizard is None:
            self.wizard = SetupWizard(self)
            self.wizard.show()

    def _refresh_wizard(self):
        if self.wizard is not None:
            self.wizard.refresh()

    def recheck_vjoy(self):
        """Look for vJoy again, e.g. after installing it or changing its button count."""
        self.state.vjoy = None
        self.refresh_setup()

        def run():
            release_vjoy()
            self.events.post("vjoy", **init_vjoy())

        threading.Thread(target=run, daemon=True).start()

    # --- Setup checklist ---

    def bound_buttons(self):
        controllers = get_controllers()
        if not controllers:
            return []
        return [int(k) for k, v in controllers[0].get("bindings", {}).items()
                if _parse_binding(v)["enabled"] and _parse_binding(v)["command"]]

    def refresh_counts(self):
        self.nav_items["commands"][4].configure(text=str(len(self.bound_buttons())))

    def refresh_setup(self):
        checks = []
        vjoy = self.state.vjoy
        if vjoy is None:
            checks.append(("todo", "vJoy driver", "Checking…", None, None))
        elif not vjoy["ok"]:
            checks.append(("bad", "vJoy driver", "Not found. Install vJoy and enable device 1.", "Get vJoy",
                           lambda: os.startfile(VJOY_URL)))
        else:
            buttons, needed = vjoy["buttons"], max(self.bound_buttons(), default=0)
            if buttons and needed > buttons:
                checks.append(("bad", "vJoy driver", f"Only {buttons} buttons enabled, commands use up to {needed}. "
                                                     "Raise it in Configure vJoy.", None, None))
            else:
                checks.append(("ok", "vJoy driver", f"Device 1, {buttons or 64} buttons", None, None))

        if not get_api_key():
            checks.append(("bad", "OpenAI key", "Not set", "Add key", lambda: self.show("settings")))
        elif self.state.key_test is None:
            checks.append(("todo", "OpenAI key", "Saved, not tested yet", "Test", self.test_api_key))
        else:
            ok, message = self.state.key_test
            checks.append(("ok" if ok else "bad", "OpenAI key", message, "Test", self.test_api_key))

        mic = get_setting("audio.input_device", "")
        if mic and mic not in {d["name"] for d in get_input_devices()}:
            checks.append(("bad", "Microphone", f"{mic} not found, using the default", "Choose", lambda: self.show("settings")))
        else:
            checks.append(("ok", "Microphone", mic or "System default", None, None))

        last_sync = get_setting("crewchief_last_sync", "")
        if self.state.synced_this_session:
            checks.append(("todo", "CrewChief", "Synced. Restart CrewChief to load the bindings.", "Sync", self.sync_with_crewchief))
        elif last_sync:
            checks.append(("ok", "CrewChief", f"Synced {last_sync}", "Sync", self.sync_with_crewchief))
        else:
            checks.append(("todo", "CrewChief", "Not synced yet", "Sync", self.sync_with_crewchief))
        self.pages["home"].render_setup(checks)
        self._refresh_wizard()

    def test_api_key(self):
        self.state.key_test = (None, "Testing…")
        self.pages["settings"].render_key_status("Testing…", None)

        def run():
            try:
                get_openai_client().models.list()
                self.events.post("key_test", ok=True, message="Working")
            except Exception as e:
                self.events.post("key_test", ok=False, message=friendly_error(e))

        threading.Thread(target=run, daemon=True).start()

    # --- CrewChief sync ---

    def sync_with_crewchief(self):
        """Sync bindings with CrewChief's config file."""
        from src.crewchief_sync import sync_crewchief_config

        default_path = get_setting("crewchief_config_path", "")
        if not default_path:
            default_path = os.path.join(
                os.path.expanduser("~"),
                "Documents", "CrewChiefV4", "Profiles", "ControllerData", "defaultSettings.json"
            )

        config_path = filedialog.askopenfilename(
            title="Select CrewChief defaultSettings.json",
            initialdir=os.path.dirname(default_path),
            initialfile=os.path.basename(default_path),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not config_path:
            return

        set_setting("crewchief_config_path", config_path)

        if not messagebox.askyesno(
            "Sync with CrewChief",
            "This will overwrite CrewChief's button assignments for actions marked as available.\n\n"
            "Voice commands on buttons the sync doesn't use will be cleared.\n\n"
            "A backup of the original file will be created.\n\nContinue?"
        ):
            return

        config = load_config()
        result = sync_crewchief_config(config_path, config.get("controllers", []))

        if not result["success"]:
            messagebox.showerror("Sync failed", result["message"])
            print(f"Sync failed: {result['message']}")
            return

        config = load_config()
        config["controllers"] = result["bindings"]
        save_config(config)
        set_setting("crewchief_last_sync", datetime.now().strftime("%d %b %Y, %H:%M"))
        self.state.synced_this_session = True

        self.pages["commands"].rebuild()
        self.refresh_counts()
        self.refresh_setup()
        print(f"CrewChief sync complete: {result['message']}")
        messagebox.showinfo("Sync complete", result["message"] + "\n\nRestart CrewChief to load the new bindings.")

    # --- Shutdown ---

    def _on_close(self):
        self.engine.stop()
        release_vjoy()
        self.root.destroy()
