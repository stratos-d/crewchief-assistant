import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from src import usage
from src.ui import theme as t

MONTHS_SHOWN = 12


def dollars(cost):
    return "< $0.01" if 0 < cost < 0.005 else f"${cost:.2f}"


def tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1000:.0f}k"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


class UsagePage:
    """What the assistant has spent on OpenAI: this month, all time, and month by month."""

    def __init__(self, master, app):
        self.app = app
        self.frame = ctk.CTkFrame(master, fg_color=t.CREAM)
        t.page_header(self.frame, "Usage", "Estimated from OpenAI prices.")

        bar = ctk.CTkFrame(self.frame, fg_color=t.CREAM, height=32)
        bar.pack(fill="x", pady=(0, 12))
        t.secondary_button(bar, "Reset totals", self.reset, bg=t.CREAM, width=110, height=30).pack(side="right")

        tiles = ctk.CTkFrame(self.frame, fg_color=t.CREAM)
        tiles.pack(fill="x")
        self.tiles = {}
        for column, key in enumerate(("month", "total")):
            tiles.grid_columnconfigure(column, weight=1, uniform="tiles")
            outer, card = t.card(tiles)
            outer.grid(row=0, column=column, sticky="nsew", padx=(0, 14) if column == 0 else 0)
            t.section_title(card, "This month" if key == "month" else "All time")
            body = tk.Frame(card, bg=t.CARD)
            body.pack(fill="x", padx=18, pady=(0, 14))
            cost = tk.Label(body, font=t.tk_font(t.HEAD, 26, "bold"), fg=t.TEXT, bg=t.CARD, anchor="w")
            cost.pack(anchor="w")
            detail = tk.Label(body, font=t.tk_font(t.BODY, 10), fg=t.MUTED, bg=t.CARD, anchor="w", justify="left")
            detail.pack(anchor="w", pady=(2, 0))
            self.tiles[key] = (cost, detail)

        outer, card = t.card(self.frame)
        outer.pack(fill="both", expand=True, pady=(14, 0))
        t.section_title(card, "By month")
        self.table = tk.Frame(card, bg=t.CARD)
        self.table.pack(fill="x", padx=18, pady=(0, 12))

    def on_show(self):
        self.render()

    def render(self):
        totals = usage.summary()
        for key, (cost, detail) in self.tiles.items():
            values = totals[key]
            cost.configure(text=dollars(values["cost"]))
            lines = [f"{plural(values['commands'], 'command')} · {tokens(values['tokens'])} tokens"]
            if values["commands"] and values["cost"]:
                lines.append(f"{values['cost'] / values['commands'] * 100:.2f}¢ per command")
            if values["unpriced"]:
                lines.append(f"{tokens(values['unpriced'])} tokens not priced")
            detail.configure(text="\n".join(lines))

        for child in self.table.winfo_children():
            child.destroy()
        months = usage.history()[:MONTHS_SHOWN]
        if not months:
            tk.Label(self.table, text="No usage yet.",
                     font=t.tk_font(t.BODY, 10), fg=t.MUTED, bg=t.CARD).grid(row=0, column=0, columnspan=4, sticky="w",
                                                                             pady=4)
            return
        for column, (heading, anchor) in enumerate((("Month", "w"), ("Commands", "e"), ("Tokens", "e"), ("Cost", "e"))):
            self.table.grid_columnconfigure(column, weight=2 if column == 0 else 1, uniform="cols")
            tk.Label(self.table, text=heading.upper(), font=t.tk_font(t.HEAD, 10, "bold"), fg=t.MUTED,
                     bg=t.CARD).grid(row=0, column=column, sticky=anchor, pady=(0, 6))
        for row, (month, values) in enumerate(months, start=1):
            cells = (datetime.strptime(month, "%Y-%m").strftime("%B %Y"), f"{values.get('commands', 0):,}",
                     tokens(values.get("tokens", 0)), dollars(values.get("cost", 0.0)))
            for column, text in enumerate(cells):
                tk.Label(self.table, text=text, font=t.tk_font(t.BODY, 10), fg=t.TEXT, bg=t.CARD).grid(
                    row=row, column=column, sticky="w" if column == 0 else "e", pady=3)

    def reset(self):
        if messagebox.askyesno("Reset usage", "Reset the usage totals?"):
            usage.reset()
            self.render()
