import os
import tkinter as tk
import webbrowser

import customtkinter as ctk
import keyboard
from tkinter import filedialog

from src.audio import LevelMeter, get_input_devices
from src.config_manager import get_setting, set_setting, get_api_key, save_api_key
from src.crewchief_sync import sees_vjoy
from src.ui import theme as t

STEPS = [("welcome", "Welcome"), ("vjoy", "vJoy driver"), ("openai", "OpenAI key"), ("mic", "Microphone"),
         ("ptt", "Push-to-talk"), ("crewchief", "CrewChief"), ("try", "Try it")]
VJOY_DOWNLOAD = "https://sourceforge.net/projects/vjoystick/"
OPENAI_KEYS = "https://platform.openai.com/api-keys"
DEFAULT_MIC = "System default"
HEARD_LEVEL = 0.08  # peak level that counts as the microphone working


def vjoy_config_tool():
    """Path to vJoy's "Configure vJoy" program, if installed."""
    for arch in ("x64", "x86"):
        path = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "vJoy", arch, "vJoyConf.exe")
        if os.path.exists(path):
            return path
    return None


class SetupWizard:
    """First-run setup, one step per screen, drawn over the main window."""

    def __init__(self, app):
        self.app = app
        self.step = 0
        self.visited = set()
        self.meter = None
        self.heard = False
        self.last_seen = None  # newest result before the Try it step opened
        self._tick_job = None
        self._ticks = 0
        self.crewchief_restarted = False
        self._crewchief_seen = None

        self.frame = ctk.CTkFrame(app.root, fg_color=t.CREAM, corner_radius=0)
        self._build_rail()
        main = ctk.CTkFrame(self.frame, fg_color=t.CREAM)
        main.pack(side="left", fill="both", expand=True, padx=40, pady=24)
        t.stripes(main)
        self.counter = ctk.CTkLabel(main, text="", font=t.font(t.HEAD, 12), text_color=t.FAINT, height=16)
        self.counter.pack(anchor="w")
        self.title = ctk.CTkLabel(main, text="", font=t.font(t.HEAD, 26, "bold"), text_color=t.TEXT, height=34)
        self.title.pack(anchor="w")
        self.intro = ctk.CTkLabel(main, text="", font=t.font(t.BODY, 14), text_color=t.MUTED, justify="left",
                                  anchor="w", wraplength=640)
        self.intro.pack(anchor="w", pady=(2, 16))

        footer = ctk.CTkFrame(main, fg_color=t.CREAM, height=40)
        footer.pack(side="bottom", fill="x", pady=(16, 0))
        ctk.CTkButton(footer, text="Skip setup", command=lambda: self.close(completed=False), fg_color="transparent",
                      hover_color=t.HOVER, text_color=t.MUTED, font=t.font(t.BODY, 13), width=90).pack(side="left")
        self.next_button = t.primary_button(footer, "Next", self.next, width=140)
        self.next_button.pack(side="right")
        self.back_button = t.secondary_button(footer, "Back", self.back, bg=t.CREAM, width=100, height=36)
        self.back_button.pack(side="right", padx=(0, 10))

        outer, card = t.card(main)
        outer.pack(fill="both", expand=True)
        self.body = tk.Frame(card, bg=t.CARD)
        self.body.pack(fill="both", expand=True, padx=26, pady=22)

    def _build_rail(self):
        rail = ctk.CTkFrame(self.frame, fg_color=t.NAVY, corner_radius=0, width=250)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        for color in (t.ORANGE, t.BLUE):
            ctk.CTkFrame(self.frame, fg_color=color, corner_radius=0, width=4).pack(side="left", fill="y")
        ctk.CTkLabel(rail, text="CREWCHIEF", font=t.font(t.HEAD, 20, "bold"), text_color="#ffffff", height=24).pack(
            anchor="w", padx=20, pady=(20, 0))
        ctk.CTkLabel(rail, text="SETUP", font=t.font(t.HEAD, 12), text_color=t.ORANGE, height=14).pack(anchor="w", padx=20)
        ctk.CTkFrame(rail, fg_color=t.NAVY, height=20).pack()
        self.rail_items = []
        for i, (_, name) in enumerate(STEPS):
            row = ctk.CTkFrame(rail, fg_color=t.NAVY, corner_radius=t.RADIUS, height=38)
            row.pack(fill="x", padx=12, pady=1)
            mark = tk.Canvas(row, width=t.px(26), height=t.px(26), bg=t.NAVY, highlightthickness=0)
            mark.pack(side="left", padx=(8, 10), pady=6)
            label = ctk.CTkLabel(row, text=name, font=t.font(t.HEAD, 14), height=26)
            label.pack(side="left")
            self.rail_items.append((row, mark, label))

    # --- Flow ---

    def show(self):
        self.frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.frame.lift()
        self.go(0)
        self._tick()

    def go(self, index):
        self._leave_step()
        self.step = index
        key = STEPS[index][0]
        self.visited.add(key)
        if key == "mic":
            self._open_meter()
        if key == "openai" and get_api_key() and self.app.state.key_test is None:
            self.app.test_api_key()
        if key == "try":
            self.last_seen = self.app.state.recent[0] if self.app.state.recent else None
            if not self.app.engine.is_running and get_api_key():
                self.app.toggle_listening()
        self.render()

    def next(self):
        if self.step == len(STEPS) - 1:
            self.close(completed=True)
        else:
            self.go(self.step + 1)

    def back(self):
        if self.step > 0:
            self.go(self.step - 1)

    def close(self, completed):
        set_setting("setup_complete", True)
        self._leave_step()
        if self._tick_job:
            self.frame.after_cancel(self._tick_job)
        self.frame.destroy()
        self.app.wizard = None
        self.app.refresh_counts()
        self.app.refresh_setup()
        self.app.refresh_status()
        print("Setup finished." if completed else "Setup skipped. You can run it again from Settings.")

    def _leave_step(self):
        if self.meter is not None:
            self.meter.close()
            self.meter = None
        settings = self.app.pages["settings"]
        if settings._rebind_hook is not None:
            settings._finish_rebind(None)

    def refresh(self):
        """Called by the app when something the current step shows has changed."""
        if STEPS[self.step][0] == "openai" and hasattr(self, "key_status"):
            self._render_key_status()
            self._render_footer()
            self._render_rail()
        else:
            self.render()

    # --- Rendering ---

    def done(self, key):
        state = self.app.state
        return {
            "welcome": "welcome" in self.visited,
            "vjoy": bool(state.vjoy and state.vjoy["ok"] and (state.vjoy["buttons"] or 64) >= 64),
            "openai": bool(state.key_test and state.key_test[0]),
            "mic": self.heard,
            "ptt": "ptt" in self.visited,
            "crewchief": bool(state.synced_this_session or get_setting("crewchief_last_sync", "")),
            "try": any(r.outcome == "pressed" for r in self._new_results()),
        }[key]

    def _new_results(self):
        """Results that arrived after the Try it step opened, newest first."""
        new = []
        for result in self.app.state.recent:
            if result is self.last_seen:
                break
            new.append(result)
        return new

    def render(self):
        for child in self.body.winfo_children():
            child.destroy()
        key, name = STEPS[self.step]
        self.counter.configure(text=f"STEP {self.step + 1} OF {len(STEPS)}")
        title, intro = getattr(self, f"_step_{key}")()
        self.title.configure(text=title.upper())
        self.intro.configure(text=intro)
        self._render_rail()
        self._render_footer()

    def _render_rail(self):
        for i, (row, mark, label) in enumerate(self.rail_items):
            key = STEPS[i][0]
            current = i == self.step
            bg = t.NAVY_2 if current else t.NAVY
            row.configure(fg_color=bg)
            ticked = self.done(key) and not current
            fill = t.ORANGE if ticked or current else t.NAVY_2
            mark.configure(bg=bg)
            mark.delete("all")
            size, pad = int(mark["width"]), t.px(1)
            mark.create_oval(pad, pad, size - pad, size - pad, fill=fill, outline=fill)
            mark.create_text(size / 2, size / 2, text="✓" if ticked else str(i + 1),
                             fill=t.NAVY if ticked or current else t.SIDE_MUTED,
                             font=t.tk_font(t.BODY if ticked else t.HEAD, 10, "bold"))
            label.configure(text_color="#ffffff" if current else t.SIDE_MUTED)

    def _render_footer(self):
        key = STEPS[self.step][0]
        last = self.step == len(STEPS) - 1
        self.next_button.configure(text="Finish" if last else ("Start" if key == "welcome" else "Next"))
        blocked = key == "openai" and not self.done("openai")
        self.next_button.configure(state="disabled" if blocked else "normal")
        self.back_button.configure(state="disabled" if self.step == 0 else "normal")

    # --- Small building blocks ---

    def _text(self, text, size=11, color=None, bold=False, pady=(0, 6), parent=None):
        label = tk.Label(parent or self.body, text=text, font=t.tk_font(t.BODY, size, "bold" if bold else "normal"),
                         fg=color or t.TEXT, bg=t.CARD, justify="left", anchor="w", wraplength=t.px(620))
        label.pack(anchor="w", pady=pady)
        return label

    def _status(self, kind, text, parent=None):
        """Coloured status line: ok, todo or bad."""
        row = tk.Frame(parent or self.body, bg=t.CARD)
        row.pack(anchor="w", pady=(0, 12))
        glyph, fg, bg = {"ok": (t.GLYPH_CHECK, t.NAVY, t.OK_BG), "todo": (t.GLYPH_WARN, t.CHIP_FG, t.CHIP_BG),
                         "bad": (t.GLYPH_WARN, t.RED, t.WARN_BG)}[kind]
        tk.Label(row, text=glyph, font=t.tk_font(t.ICON, 10), fg=fg, bg=bg, width=3).pack(side="left", padx=(0, 10))
        label = tk.Label(row, text=text, font=t.tk_font(t.BODY, 11, "bold"), fg=t.TEXT, bg=t.CARD, justify="left",
                         anchor="w", wraplength=t.px(560))
        label.pack(side="left")
        return label

    def _buttons(self, *buttons):
        row = tk.Frame(self.body, bg=t.CARD)
        row.pack(anchor="w", pady=(4, 0))
        for text, command in buttons:
            t.secondary_button(row, text, command, height=32).pack(side="left", padx=(0, 8))
        return row

    def _link(self, text, url):
        label = tk.Label(self.body, text=text, font=t.tk_font(t.BODY, 10, "underline"), fg=t.CHIP_FG, bg=t.CARD,
                         cursor="hand2")
        label.pack(anchor="w", pady=(0, 8))
        label.bind("<Button-1>", lambda e: webbrowser.open(url))
        return label

    def _numbered(self, items):
        for i, text in enumerate(items, 1):
            row = tk.Frame(self.body, bg=t.CARD)
            row.pack(anchor="w", fill="x", pady=3)
            t.roundel(row, str(i), size=26).pack(side="left", padx=(0, 12), anchor="n")
            tk.Label(row, text=text, font=t.tk_font(t.BODY, 11), fg=t.TEXT, bg=t.CARD, justify="left", anchor="w",
                     wraplength=t.px(560)).pack(side="left", fill="x")

    # --- Steps: each fills the body and returns (title, intro) ---

    def _step_welcome(self):
        self._text("You'll need three things:", bold=True, pady=(0, 10))
        self._numbered([
            "vJoy, a free virtual joystick driver. The assistant presses its buttons for you.",
            "An OpenAI API key. It turns your voice into the right CrewChief command.",
            "CrewChief, installed on this PC.",
        ])
        self._text("Each step checks itself, so you'll see right away if something needs fixing.", color=t.MUTED, pady=(14, 0))
        return "Welcome to CrewChief Assistant", "Talk to CrewChief in your own words. Setup takes about two minutes."

    def _step_vjoy(self):
        vjoy = self.app.state.vjoy
        if vjoy is None:
            self._status("todo", "Checking for vJoy…")
        elif not vjoy["ok"]:
            self._status("bad", "vJoy isn't installed, or device 1 is disabled.")
            self._text("Install vJoy, restart your PC if the installer asks, then check again.", color=t.MUTED)
            self._buttons(("Download vJoy", lambda: webbrowser.open(VJOY_DOWNLOAD)), ("Check again", self.app.recheck_vjoy))
        elif (vjoy["buttons"] or 64) < 64:
            self._status("todo", f"vJoy device 1 has only {vjoy['buttons']} buttons. Set it to 64 so every CrewChief "
                                 "action gets one.")
            self._numbered(["Click Open Configure vJoy.", "Select device 1 and set Buttons to 64.",
                            "Click Apply, then Check again."])
            tool = vjoy_config_tool()
            buttons = [("Check again", self.app.recheck_vjoy)]
            if tool:
                buttons.insert(0, ("Open Configure vJoy", lambda: os.startfile(tool)))
            self._buttons(*buttons)
        else:
            self._status("ok", f"Found vJoy device 1 with {vjoy['buttons'] or 64} buttons.")
            self._text("Nothing to do here.", color=t.MUTED)
        return "vJoy driver", "The assistant presses buttons on a virtual joystick, and CrewChief reacts to those buttons."

    def _step_openai(self):
        row = tk.Frame(self.body, bg=t.CARD)
        row.pack(anchor="w", pady=(0, 10))
        self.key_entry = ctk.CTkEntry(row, width=380, height=34, show="•", fg_color=t.CREAM, border_color=t.NAVY,
                                      border_width=1, corner_radius=t.RADIUS, text_color=t.TEXT,
                                      font=t.font(t.BODY, 13), placeholder_text="Paste your key, sk-…")
        self.key_entry.pack(side="left")
        if get_api_key():
            self.key_entry.insert(0, get_api_key())
        t.secondary_button(row, "Save and test", self._save_key, height=34, width=120).pack(side="left", padx=(8, 0))
        self.key_status = tk.Frame(self.body, bg=t.CARD)
        self.key_status.pack(anchor="w", fill="x")
        self._render_key_status()
        self._link("Create a key at platform.openai.com/api-keys", OPENAI_KEYS)
        self._text("Tip: give the key only audio and chat permissions, and set a monthly budget limit in your OpenAI "
                   "project.", color=t.MUTED, size=10)
        return "OpenAI API key", ("Your key turns speech into text and picks the command. "
                                  "It's stored encrypted in Windows Credential Manager.")

    def _render_key_status(self):
        for child in self.key_status.winfo_children():
            child.destroy()
        test = self.app.state.key_test
        if not get_api_key():
            self._status("todo", "Paste your key, then Save and test.", parent=self.key_status)
        elif test is None or test[0] is None:
            self._status("todo", "Testing your key…", parent=self.key_status)
        elif test[0]:
            self._status("ok", "Your key works.", parent=self.key_status)
        else:
            self._status("bad", test[1], parent=self.key_status)

    def _save_key(self):
        key = self.key_entry.get().strip()
        if not key:
            return
        try:
            save_api_key(key)
        except OSError as e:
            self.app.state.key_test = (False, f"Windows couldn't save the key: {e.strerror or e}")
            self.refresh()
            return
        print("API key saved.")
        self.app.test_api_key()
        self.refresh()

    def _step_mic(self):
        names = list(dict.fromkeys(d["name"] for d in get_input_devices()))
        current = get_setting("audio.input_device", "") or DEFAULT_MIC
        values = [DEFAULT_MIC] + names + ([current] if current not in names and current != DEFAULT_MIC else [])
        menu = ctk.CTkOptionMenu(self.body, values=values, command=self._on_mic, width=380, height=34,
                                 fg_color=t.CREAM, button_color=t.ORANGE, button_hover_color=t.ORANGE_HOVER,
                                 text_color=t.TEXT, dropdown_fg_color=t.CARD, dropdown_hover_color=t.HOVER,
                                 dropdown_text_color=t.TEXT, corner_radius=t.RADIUS, font=t.font(t.BODY, 13),
                                 dropdown_font=t.font(t.BODY, 13), dynamic_resizing=False)
        menu.set(current)
        menu.pack(anchor="w", pady=(0, 16))
        self.meter_canvas = tk.Canvas(self.body, width=t.px(20 * 18), height=t.px(22), bg=t.CARD, highlightthickness=0)
        self.meter_canvas.pack(anchor="w", pady=(0, 12))
        self.mic_status = tk.Frame(self.body, bg=t.CARD)
        self.mic_status.pack(anchor="w", fill="x")
        self._render_mic_status()
        return "Microphone", "Pick the microphone you race with, then say something. The bar should move."

    def _render_mic_status(self):
        for child in self.mic_status.winfo_children():
            child.destroy()
        if self.meter is None:
            self._status("bad", "This microphone can't be opened. Pick another one.", parent=self.mic_status)
        elif self.heard:
            self._status("ok", "Microphone works.", parent=self.mic_status)
        else:
            self._status("todo", "Say something to test the microphone.", parent=self.mic_status)

    def _open_meter(self):
        try:
            self.meter = LevelMeter()
        except Exception as e:
            self.meter = None
            print(f"ERROR: couldn't open the microphone: {e}")

    def _on_mic(self, selected):
        set_setting("audio.input_device", "" if selected == DEFAULT_MIC else selected)
        print(f"Input device: {selected}")
        if self.meter is not None:
            self.meter.close()
        self.heard = False
        self._open_meter()
        self.app.restart_engine()
        self._render_mic_status()

    def _draw_meter(self):
        level = self.meter.level if self.meter else 0.0
        lit = int(min(1.0, (level ** 0.5) * 1.4) * 20)
        c = self.meter_canvas
        c.delete("all")
        for i in range(20):
            color = (t.ORANGE if i >= 15 else t.NAVY) if i < lit else t.LINE
            c.create_rectangle(i * t.px(18), 0, i * t.px(18) + t.px(14), t.px(22), fill=color, outline="")
        if level > HEARD_LEVEL and not self.heard:
            self.heard = True
            self._render_mic_status()
            self._render_rail()

    def _step_ptt(self):
        settings = self.app.pages["settings"]
        waiting = settings._rebind_hook is not None
        chip = ctk.CTkFrame(self.body, fg_color=t.CREAM, border_width=1, border_color=t.NAVY, corner_radius=t.RADIUS)
        chip.pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(chip, text="Press a key…" if waiting else self.app.ptt_label(), font=t.font(t.HEAD, 22, "bold"),
                     text_color=t.ORANGE if waiting else t.TEXT, width=260, height=48).pack(padx=2, pady=2)
        self._buttons(("Cancel" if waiting else "Change key", settings._start_rebind))
        self.key_down = tk.Label(self.body, text="", font=t.tk_font(t.BODY, 11, "bold"), bg=t.CARD, fg=t.MUTED)
        self.key_down.pack(anchor="w", pady=(14, 0))
        return "Push-to-talk key", ("Hold this key while you speak. Pick one that's easy to reach mid-corner. "
                                    "Only keyboard keys work.")

    def _draw_key_down(self):
        try:
            down = keyboard.is_pressed(self.app.ptt_key)
        except ValueError:
            down = False
        self.key_down.configure(text=("Key is down. Let go when you've finished speaking." if down else
                                      f"Press and hold {self.app.ptt_label()} to check it works."),
                                fg=t.GREEN if down else t.MUTED)

    def _crewchief_progress(self):
        """(settings path, file exists, CrewChief sees vJoy, synced, synced in this session)."""
        path = self.app.crewchief_settings_path()
        found = os.path.exists(path)
        state = self.app.state
        synced = state.synced_this_session or bool(get_setting("crewchief_last_sync", ""))
        return path, found, found and sees_vjoy(path), synced, state.synced_this_session

    def _task(self, number, title, detail, status, kind, action=None, primary=False):
        """One task panel. kind is done, active (the one to do now) or waiting."""
        panel = tk.Frame(self.body, bg=t.NAVY if kind == "active" else t.LINE, padx=1, pady=1)
        panel.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(panel, bg=t.CARD)
        inner.pack(fill="x")
        tk.Frame(inner, bg=t.ORANGE if kind == "active" else t.CARD, width=t.px(4)).pack(side="left", fill="y")
        size, pad = t.px(30), t.px(2)
        badge = tk.Canvas(inner, width=size, height=size, bg=t.CARD, highlightthickness=0)
        if kind == "done":
            badge.create_oval(pad, pad, size - pad, size - pad, fill=t.ORANGE, outline=t.ORANGE)
            badge.create_text(size / 2, size / 2, text="✓", fill=t.NAVY, font=t.tk_font(t.BODY, 12, "bold"))
        else:
            color = t.NAVY if kind == "active" else t.FAINT
            badge.create_oval(pad, pad, size - pad, size - pad, fill="#ffffff", outline=color, width=pad)
            badge.create_text(size / 2, size / 2, text=str(number), fill=color, font=t.tk_font(t.HEAD, 11, "bold"))
        badge.pack(side="left", padx=(12, 14), pady=12)

        right = tk.Frame(inner, bg=t.CARD)
        right.pack(side="right", padx=14)
        if action:
            make = t.primary_button if primary else t.secondary_button
            make(right, action[0], action[1], width=110, height=30).pack(side="right", padx=(10, 0))
        if status:
            tk.Label(right, text=status, font=t.tk_font(t.BODY, 10, "bold"), bg=t.CARD,
                     fg={"done": t.GREEN, "active": t.CHIP_FG}.get(kind, t.FAINT)).pack(side="right")

        text = tk.Frame(inner, bg=t.CARD)
        text.pack(side="left", fill="x", expand=True, pady=10)
        faded = kind == "waiting"
        tk.Label(text, text=title, font=t.tk_font(t.HEAD, 13, "bold"), fg=t.FAINT if faded else t.TEXT, bg=t.CARD,
                 anchor="w").pack(anchor="w")
        tk.Label(text, text=detail, font=t.tk_font(t.BODY, 10), fg=t.FAINT if faded else t.MUTED, bg=t.CARD,
                 anchor="w", justify="left", wraplength=t.px(320)).pack(anchor="w")

    def _step_crewchief(self):
        path, found, seen, synced, just_synced = self._crewchief_progress()
        self._crewchief_seen = seen
        done = [seen, synced, synced and (not just_synced or self.crewchief_restarted)]
        active = next((i for i, d in enumerate(done) if not d), None)

        def kind(i):
            return "done" if done[i] else ("active" if i == active else "waiting")

        if found:
            self._task(1, "Let CrewChief find vJoy",
                       "In CrewChief, open Controllers and click Scan for controllers. This ticks off by itself.",
                       "Found" if seen else "Waiting for CrewChief", kind(0))
        else:
            self._task(1, "Let CrewChief find vJoy",
                       "Open CrewChief once so it creates its settings, then click Scan for controllers.",
                       "Settings not found", kind(0), ("Choose file…", self._choose_crewchief_file))
        count = len(self.app.bound_buttons())
        self._task(2, "Sync your commands", "One button and voice command for every CrewChief action.",
                   f"{count} commands synced" if synced else "", kind(1),
                   (("Sync again" if synced else "Sync now"), lambda: self.app.sync_with_crewchief(path)) if seen else None,
                   primary=kind(1) == "active")
        self._task(3, "Restart CrewChief", "Close CrewChief and open it again so it uses the new buttons.",
                   "Do this now" if kind(2) == "active" else ("Done" if done[2] else ""), kind(2),
                   ("Done", self._restarted) if kind(2) == "active" else None, primary=True)
        self._text("Binding buttons by hand instead? Skip this step and use Test on the Commands page.",
                   color=t.MUTED, size=10, pady=(6, 0))
        return "CrewChief", "Three quick tasks link your commands to CrewChief. They tick off as you go."

    def _choose_crewchief_file(self):
        path = filedialog.askopenfilename(title="Select CrewChief defaultSettings.json",
                                          filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            set_setting("crewchief_config_path", path)
            self.render()

    def _restarted(self):
        self.crewchief_restarted = True
        self.render()

    def _step_try(self):
        if not get_api_key():
            self._status("bad", "Add your OpenAI key first.")
            self._buttons(("Go to OpenAI key", lambda: self.go(2)))
            return "Try it", "Almost there."
        label, color, lamp = t.STATUS[self.app.state.status]
        gauge = tk.Frame(self.body, bg=t.CARD)
        gauge.pack(anchor="w", pady=(0, 14))
        canvas = tk.Canvas(gauge, width=t.px(56), height=t.px(56), bg=t.CARD, highlightthickness=0)
        t.draw_gauge(canvas, lamp)
        canvas.pack(side="left", padx=(0, 14))
        tk.Label(gauge, text=label, font=t.tk_font(t.HEAD, 18, "bold"), fg=color, bg=t.CARD).pack(side="left")

        new = self._new_results()
        if not new:
            self._text(f"Waiting for your first command. Hold {self.app.ptt_label()} and speak.", color=t.MUTED)
        else:
            r = new[0]
            heard = f"“{r.heard}”" if r.heard else "Nothing heard"
            if r.outcome == "pressed":
                self._status("ok", f"{heard} pressed button {r.button}: {r.command[:1].upper() + r.command[1:]}. You're all set.")
            elif r.outcome == "error":
                self._status("bad", r.message)
            else:
                self._status("todo", f"{heard} didn't match a command. Try saying one from the Commands page.")
        return "Try it", f"Hold {self.app.ptt_label()} and say a command, like “radio check” or “how's my fuel”."

    # --- Live updates ---

    def _tick(self):
        key = STEPS[self.step][0]
        if key == "mic" and hasattr(self, "meter_canvas") and self.meter_canvas.winfo_exists():
            self._draw_meter()
        if key == "ptt" and hasattr(self, "key_down") and self.key_down.winfo_exists():
            self._draw_key_down()
        self._ticks += 1
        if key == "crewchief" and self._ticks % 12 == 0:  # about once a second, watch for CrewChief's scan
            if self._crewchief_progress()[2] != self._crewchief_seen:
                self.render()
        self._tick_job = self.frame.after(80, self._tick)
