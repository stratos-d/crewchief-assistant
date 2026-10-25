import tkinter as tk

import customtkinter as ctk

from src.config_manager import get_setting
from src.constants import crewchief_number
from src.ui import theme as t


def pretty(command):
    return command[:1].upper() + command[1:]


class HomePage:
    """Status, the last few commands, and the setup checklist."""

    def __init__(self, master, app):
        self.app = app
        self.frame = ctk.CTkFrame(master, fg_color=t.CREAM)
        t.page_header(self.frame, "Home", "")

        outer, card = t.card(self.frame)
        outer.pack(fill="x")
        size = t.px(64)
        self.gauge = tk.Canvas(card, width=size, height=size, bg=t.CARD, highlightthickness=0)
        self.gauge.pack(side="left", padx=18, pady=16)
        text = ctk.CTkFrame(card, fg_color=t.CARD, width=10)
        text.pack(side="left", fill="x", expand=True)
        self.state_label = ctk.CTkLabel(text, text="", font=t.font(t.HEAD, 22, "bold"), height=28)
        self.state_label.pack(anchor="w")
        self.detail_label = ctk.CTkLabel(text, text="", font=t.font(t.BODY, 13), text_color=t.MUTED, anchor="w",
                                         justify="left", wraplength=480)
        self.detail_label.pack(anchor="w")
        self.button = t.primary_button(card, "Start listening", app.toggle_listening, width=160)
        self.button.pack(side="right", padx=18)

        grid = ctk.CTkFrame(self.frame, fg_color=t.CREAM)
        grid.pack(fill="both", expand=True, pady=(14, 0))
        grid.grid_columnconfigure(0, weight=5, uniform="cols")
        grid.grid_columnconfigure(1, weight=4, uniform="cols")
        grid.grid_rowconfigure(0, weight=1)

        rec_outer, rec = t.card(grid)
        rec_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        t.section_title(rec, "Recent commands")
        self.recent_box = tk.Frame(rec, bg=t.CARD)
        self.recent_box.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        setup_outer, setup = t.card(grid)
        setup_outer.grid(row=0, column=1, sticky="nsew")
        t.section_title(setup, "Setup")
        self.setup_box = tk.Frame(setup, bg=t.CARD)
        self.setup_box.pack(fill="both", expand=True, padx=18, pady=(0, 12))

    def on_show(self):
        pass

    def render_status(self, label, color, lamp, detail, running):
        t.draw_gauge(self.gauge, lamp)
        self.state_label.configure(text=label, text_color=color)
        self.detail_label.configure(text=detail)
        if detail:
            self.detail_label.pack(anchor="w")
        else:
            self.detail_label.pack_forget()
        self.button.configure(text="Stop listening" if running else "Start listening")

    def render_recent(self, results):
        for child in self.recent_box.winfo_children():
            child.destroy()
        if not results:
            tk.Label(self.recent_box, text="No commands yet.",
                     font=t.tk_font(t.BODY, 10), fg=t.MUTED, bg=t.CARD, justify="left", wraplength=t.px(360),
                     anchor="w").pack(anchor="w", pady=4)
            return

        threshold = get_setting("confidence_threshold", 50)
        for r in results:
            row = tk.Frame(self.recent_box, bg=t.CARD)
            row.pack(fill="x", pady=4)
            if r.outcome == "pressed":
                t.roundel(row, str(crewchief_number(r.button))).pack(side="left", padx=(0, 10), anchor="n")
            else:
                tk.Label(row, text="!" if r.outcome == "error" else "?", font=t.tk_font(t.HEAD, 15, "bold"),
                         fg=t.RED, bg=t.CARD, width=2).pack(side="left", padx=(0, 10), anchor="n")
            tk.Label(row, text=r.time, font=t.tk_font(t.BODY, 9), fg=t.FAINT, bg=t.CARD).pack(side="right", anchor="n")

            body = tk.Frame(row, bg=t.CARD)
            body.pack(side="left", fill="x", expand=True)
            heard = f"“{r.heard}”" if r.heard else ("Error" if r.outcome == "error" else "Nothing heard")
            tk.Label(body, text=heard, font=t.tk_font(t.BODY, 10), fg=t.TEXT, bg=t.CARD, anchor="w", justify="left",
                     wraplength=t.px(340)).pack(anchor="w")
            line = tk.Frame(body, bg=t.CARD)
            line.pack(anchor="w", pady=(2, 0))
            seconds = f"{r.seconds:.2f} s" if r.seconds is not None else ""
            chip, kind, meta = {
                "pressed": (pretty(r.command), "ok", ("exact match" if r.exact else f"{r.confidence}%") + f" · {seconds}"),
                "unknown": ("Not understood", "bad", seconds),
                "low_confidence": (f"Unsure: {pretty(r.command)}", "bad", f"{r.confidence}%, minimum {threshold}%"),
                "no_binding": (f"No button for {pretty(r.command)}", "bad", seconds),
                "no_speech": ("No speech", "bad", seconds),
                "error": ("Failed", "bad", r.message),
            }[r.outcome]
            t.chip(line, chip, kind).pack(side="left")
            tk.Label(line, text=meta, font=t.tk_font(t.BODY, 9), fg=t.FAINT, bg=t.CARD, justify="left",
                     wraplength=t.px(260)).pack(side="left", padx=(6, 0))

    def render_setup(self, checks):
        for child in self.setup_box.winfo_children():
            child.destroy()
        for kind, name, detail, action, callback in checks:
            row = tk.Frame(self.setup_box, bg=t.CARD)
            row.pack(fill="x", pady=6)
            glyph, fg, bg = {"ok": (t.GLYPH_CHECK, t.NAVY, t.OK_BG), "todo": (t.GLYPH_WARN, t.CHIP_FG, t.CHIP_BG),
                             "bad": (t.GLYPH_WARN, t.RED, t.WARN_BG)}[kind]
            tk.Label(row, text=glyph, font=t.tk_font(t.ICON, 10), fg=fg, bg=bg, width=3).pack(side="left", padx=(0, 12), anchor="n", pady=2)
            if action:
                t.RowButton(row, action, callback).pack(side="right", anchor="n", pady=2)
            text = tk.Frame(row, bg=t.CARD)
            text.pack(side="left", fill="x", expand=True)
            tk.Label(text, text=name.upper(), font=t.tk_font(t.HEAD, 11, "bold"), fg=t.TEXT, bg=t.CARD, anchor="w").pack(anchor="w")
            tk.Label(text, text=detail, font=t.tk_font(t.BODY, 9), fg=t.MUTED, bg=t.CARD, anchor="w", justify="left",
                     wraplength=t.px(220)).pack(anchor="w")
        t.RowButton(self.setup_box, "Run setup wizard", self.app.open_wizard).pack(anchor="w", pady=(12, 0))
