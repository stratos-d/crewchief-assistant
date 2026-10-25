import threading
import tkinter as tk

import customtkinter as ctk

from src.config_manager import get_controllers, get_all_commands, rename_binding, _parse_binding
from src.constants import MAX_BUTTONS, crewchief_number
from src.crewchief_actions import vjoy_actions
from src.gamepad import trigger_button
from src.ui import theme as t
from src.ui.dialogs import RenameDialog
from src.ui.engine import friendly_error

GROUPS = ["Car status", "Pit and tyres", "Race", "Timing", "Other", "Unassigned"]


def group_of(command):
    """Rough grouping by wording, so 60-odd CrewChief commands are easy to scan."""
    c = command.lower()
    if not c:
        return "Unassigned"
    if c.startswith(("hows my", "how are my", "how is my", "get car", "get damage")):
        return "Car status"
    if c.startswith("pit stop") or "fuel" in c or "tyre" in c or "tire" in c:
        return "Pit and tyres"
    if any(p in c for p in ("gap", "ahead", "behind", "position", "leading", "reputation", "monitor", "watching",
                            "penalty", "incident")):
        return "Race"
    if any(p in c for p in ("lap time", "best lap", "fastest", "how long", "left")):
        return "Timing"
    return "Other"


class CommandsPage:
    """Every vJoy button, grouped and searchable, with rename and test-press.

    Buttons are numbered the way CrewChief numbers them, and each row shows the CrewChief action on that button,
    read from CrewChief's own settings, so renaming a voice command never loses track of what it does.
    The list is drawn on a single canvas: one widget instead of ~450 keeps the page instant to open and scroll.
    """

    ROW, HEADER, BUTTON_W, BUTTON_H = 46, 34, 64, 24

    def __init__(self, master, app):
        self.app = app
        self.frame = ctk.CTkFrame(master, fg_color=t.CREAM)
        self.subtitle = t.page_header(self.frame, "Commands", "")
        self.entries = []
        self.cc_actions = None  # {vJoy button: CrewChief action name}, None if CrewChief's settings can't be read
        self._loaded = False

        bar = ctk.CTkFrame(self.frame, fg_color=t.CREAM, height=36)
        bar.pack(fill="x", pady=(0, 12))
        self.search = ctk.CTkEntry(bar, placeholder_text="Search", width=300, height=32,
                                   fg_color=t.CARD, border_color=t.LINE, border_width=1, corner_radius=t.RADIUS,
                                   text_color=t.TEXT, font=t.font(t.BODY, 13))
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda e: self.draw())
        self.show_empty = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(bar, text="Show empty buttons", variable=self.show_empty, command=self.draw,
                      font=t.font(t.BODY, 13), text_color=t.TEXT, progress_color=t.ORANGE, button_color=t.NAVY,
                      button_hover_color=t.NAVY_2, fg_color=t.LINE).pack(side="left", padx=18)
        t.secondary_button(bar, "Sync with CrewChief", app.sync_with_crewchief, bg=t.CREAM, width=170,
                           height=32).pack(side="right")

        outer, card = t.card(self.frame)
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(card, bg=t.CARD, highlightthickness=0, yscrollincrement=t.px(18))
        scrollbar = ctk.CTkScrollbar(card, command=self.canvas.yview, button_color=t.LINE,
                                     button_hover_color=t.FAINT, fg_color=t.CARD)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=6)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120) * 3, "units"))

    def on_show(self):
        if not self._loaded:
            self.rebuild()
            return
        # CrewChief may have been rebound since the page was last open
        actions = vjoy_actions(self.app.crewchief_settings_path())
        if actions != self.cc_actions:
            self.cc_actions = actions
            self.draw()

    def rebuild(self):
        """Reload bindings from the config and CrewChief's settings, and redraw."""
        controllers = get_controllers()
        bindings = controllers[0].get("bindings", {}) if controllers else {}
        self.entries = []
        for key in range(1, MAX_BUTTONS + 1):
            b = _parse_binding(bindings.get(str(key), {}))
            self.entries.append((key, b["command"] if b["enabled"] and b["command"] else ""))
        self.cc_actions = vjoy_actions(self.app.crewchief_settings_path())
        count = sum(1 for _, command in self.entries if command)
        self.subtitle.configure(text=f"{count} commands")
        self._loaded = True
        self.draw()

    def cc_action(self, key):
        return (self.cc_actions or {}).get(key, "")

    # --- Drawing ---

    def _visible(self):
        query = self.search.get().strip().lower()
        show_empty = self.show_empty.get()
        groups = {name: [] for name in GROUPS}
        for key, command in self.entries:
            matches = (not query or query in command.lower() or query in self.cc_action(key).lower()
                       or query == str(crewchief_number(key)))
            if (command or show_empty) and matches:
                groups[group_of(command)].append((key, command))
        return [(name, groups[name]) for name in GROUPS if groups[name]]

    def draw(self):
        if not self._loaded:
            return
        c, px = self.canvas, t.px
        c.delete("all")
        width = max(c.winfo_width(), px(400))
        y = px(8)
        visible = self._visible()
        for name, rows in visible:
            c.create_text(px(14), y + px(self.HEADER) / 2, text=name.upper(), anchor="w", fill=t.TEXT,
                          font=t.tk_font(t.HEAD, 10, "bold"))
            text_width = px(len(name) * 8 + 24)
            c.create_line(px(14) + text_width, y + px(self.HEADER) / 2, width - px(14), y + px(self.HEADER) / 2,
                          fill=t.ORANGE, width=px(2))
            y += px(self.HEADER)
            for key, command in rows:
                self._draw_row(key, command, y, width)
                y += px(self.ROW)
            y += px(8)
        if not visible:
            c.create_text(width / 2, px(60), text="No matches.", fill=t.MUTED,
                          font=t.tk_font(t.BODY, 10))
        c.configure(scrollregion=(0, 0, width, max(y, c.winfo_height())))

    def _draw_row(self, key, command, y, width):
        c, px = self.canvas, t.px
        tag = f"row{key}"
        mid = y + px(self.ROW) / 2
        c.create_rectangle(0, y, width, y + px(self.ROW), fill=t.CARD, outline="", tags=(tag, f"bg{key}"))
        r = px(13)
        outline = t.NAVY if command else t.FAINT
        c.create_oval(px(28) - r, mid - r, px(28) + r, mid + r, fill="#ffffff", outline=outline, width=px(2), tags=tag)
        c.create_text(px(28), mid, text=str(crewchief_number(key)), fill=outline, font=t.tk_font(t.HEAD, 10, "bold"),
                      tags=tag)

        # Second line: what CrewChief does with this button, whatever the voice command is called
        action = self.cc_action(key)
        if action:
            detail, detail_color = f"CrewChief: {action}", t.MUTED
        elif command and self.cc_actions is not None:
            detail, detail_color = "Not bound in CrewChief", t.RED
        else:
            detail = ""
        text_y = mid - px(8) if detail else mid
        c.create_text(px(54), text_y, text=command[:1].upper() + command[1:] if command else "Unassigned", anchor="w",
                      fill=t.TEXT if command else t.FAINT, font=t.tk_font(t.BODY, 10, "normal" if command else "italic"),
                      tags=tag)
        if detail:
            c.create_text(px(54), mid + px(9), text=detail, anchor="w", fill=detail_color, font=t.tk_font(t.BODY, 8),
                          tags=tag)
        c.tag_bind(tag, "<Double-Button-1>", lambda e: self._rename(key, command))

        right = width - px(14)
        for label, action in (("Test", lambda: self._test(key)), ("Rename" if command else "Assign", lambda: self._rename(key, command))):
            left = right - px(self.BUTTON_W)
            btn = f"btn{key}{label}"
            c.create_rectangle(left, mid - px(self.BUTTON_H) / 2, right, mid + px(self.BUTTON_H) / 2, fill=t.CARD,
                               outline=t.NAVY, width=1, tags=(btn, f"{btn}box"))
            c.create_text((left + right) / 2, mid, text=label, fill=t.NAVY, font=t.tk_font(t.BODY, 9), tags=btn)
            c.tag_bind(btn, "<Button-1>", lambda e, a=action: a())
            c.tag_bind(btn, "<Enter>", lambda e, b=btn: (c.itemconfigure(f"{b}box", fill=t.HOVER), c.configure(cursor="hand2")))
            c.tag_bind(btn, "<Leave>", lambda e, b=btn: (c.itemconfigure(f"{b}box", fill=t.CARD), c.configure(cursor="")))
            right = left - px(6)

    # --- Actions ---

    def _test(self, key):
        def press():
            try:
                trigger_button(key)
                print(f"Test press: button {crewchief_number(key)}")
            except Exception as e:
                print(f"ERROR: {friendly_error(e)}")

        threading.Thread(target=press, daemon=True).start()
        self.canvas.itemconfigure(f"bg{key}", fill=t.CHIP_BG)
        self.app.root.after(350, lambda: self.canvas.itemconfigure(f"bg{key}", fill=t.CARD))

    def _rename(self, key, command):
        RenameDialog(self.app, crewchief_number(key), self.cc_action(key), command, get_all_commands(),
                     on_save=lambda new: self._save(key, command, new))

    def _save(self, key, old, new):
        rename_binding(0, str(key), new)
        number = crewchief_number(key)
        print(f"Button {number}: '{old}' renamed to '{new}'" if old and new else
              f"Button {number}: assigned '{new}'" if new else f"Button {number}: '{old}' removed")
        self.rebuild()
        self.app.refresh_counts()
        self.app.refresh_setup()
