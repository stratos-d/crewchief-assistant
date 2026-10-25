"""Modern motorsport livery: palette, fonts and small widgets shared by every page."""
import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

# Palette
CREAM = "#f3eee2"
CARD = "#fffcf5"
LINE = "#d6ccb4"
NAVY = "#1b2440"
NAVY_2 = "#26315a"
BLUE = "#94c9e8"
ORANGE = "#f26a21"
ORANGE_HOVER = "#ff7f3a"
RED = "#c4161c"
GREEN = "#2e7d32"
TEXT = NAVY
MUTED = "#5d5a4f"
FAINT = "#8d8776"
SIDE_MUTED = "#aeb7cf"
HOVER = "#f4ead3"
OK_BG = "#dcebf6"
WARN_BG = "#f8dcd5"
CHIP_BG = "#fde3d3"
CHIP_FG = "#b34a10"
RADIUS = 4

# Fonts (Bahnschrift and Segoe ship with Windows 10/11)
HEAD = "Bahnschrift"
BODY = "Segoe UI"
MONO = "Consolas"
ICON = "Segoe Fluent Icons"

GLYPH_HOME = ""
GLYPH_COMMANDS = ""
GLYPH_SETTINGS = ""
GLYPH_ACTIVITY = ""
GLYPH_USAGE = ""
GLYPH_CHECK = ""
GLYPH_WARN = ""
GLYPH_CROSS = ""

# Status label, label colour and lamp colour per engine state
STATUS = {
    "off": ("NOT LISTENING", FAINT, "#b9b2a0"),
    "starting": ("STARTING", FAINT, "#b9b2a0"),
    "ready": ("READY", NAVY, GREEN),
    "recording": ("LISTENING", RED, RED),
    "processing": ("THINKING", ORANGE, ORANGE),
    "error": ("ERROR", RED, RED),
}

_scale = 1.0


def init(root):
    """Resolve fonts that differ between Windows 10 and 11, and read the DPI scale for canvas drawings."""
    global ICON, _scale
    if ICON not in tkfont.families(root):
        ICON = "Segoe MDL2 Assets"
    _scale = ctk.ScalingTracker.get_widget_scaling(root)


def px(value):
    """Scale a pixel size for plain Tk canvases, which CustomTkinter does not scale."""
    return int(round(value * _scale))


def font(family, size, weight="normal"):
    return ctk.CTkFont(family=family, size=size, weight=weight)


def tk_font(family, size, weight="normal"):
    return (family, size, weight)


def card(parent):
    """A cream card with a thin navy edge on the bottom-right. Returns (outer, inner); place outer, fill inner."""
    outer = ctk.CTkFrame(parent, fg_color=NAVY, corner_radius=RADIUS + 1)
    inner = ctk.CTkFrame(outer, fg_color=CARD, corner_radius=RADIUS, border_width=1, border_color=LINE)
    inner.pack(fill="both", expand=True, padx=(0, 3), pady=(0, 3))
    return outer, inner


def stripes(parent):
    """The orange, navy and blue livery stripes at the top of each page."""
    frame = ctk.CTkFrame(parent, fg_color=CREAM, height=15)
    frame.pack(fill="x", pady=(0, 12))
    for color in (ORANGE, NAVY, BLUE):
        ctk.CTkFrame(frame, fg_color=color, height=3, corner_radius=0).pack(fill="x", pady=(0, 2))
    return frame


def page_header(parent, title, subtitle):
    stripes(parent)
    ctk.CTkLabel(parent, text=title.upper(), font=font(HEAD, 24, "bold"), text_color=TEXT, height=30).pack(anchor="w")
    sub = ctk.CTkLabel(parent, text=subtitle, font=font(BODY, 13), text_color=MUTED, justify="left")
    sub.pack(anchor="w", pady=(0, 12))
    return sub


def section_title(parent, text):
    head = ctk.CTkFrame(parent, fg_color=CARD, height=20)
    head.pack(fill="x", padx=18, pady=(14, 8))
    ctk.CTkLabel(head, text=text.upper(), font=font(HEAD, 13, "bold"), text_color=TEXT, height=20).pack(side="left")
    ctk.CTkFrame(head, fg_color=ORANGE, height=3, corner_radius=0).pack(side="left", fill="x", expand=True, padx=(10, 0))
    return head


def primary_button(parent, text, command, **kw):
    kw.setdefault("height", 36)
    return ctk.CTkButton(parent, text=text, command=command, font=font(HEAD, 14, "bold"), fg_color=ORANGE,
                         hover_color=ORANGE_HOVER, text_color=NAVY, text_color_disabled=FAINT,
                         corner_radius=RADIUS, **kw)


def secondary_button(parent, text, command, bg=CARD, **kw):
    kw.setdefault("height", 28)
    return ctk.CTkButton(parent, text=text, command=command, font=font(BODY, 12), fg_color=bg, hover_color=HOVER,
                         text_color=TEXT, text_color_disabled=FAINT, border_width=1, border_color=NAVY,
                         corner_radius=RADIUS, **kw)


def chip(parent, text, kind="ok", bg=CARD):
    colors = {"ok": (CHIP_BG, CHIP_FG), "bad": (WARN_BG, RED), "info": (OK_BG, NAVY)}[kind]
    return tk.Label(parent, text=f" {text} ", font=tk_font(BODY, 9), bg=colors[0], fg=colors[1], bd=0, padx=4, pady=1)


def draw_lamp(canvas, lamp_color):
    """Status lamp: a solid dot in the status colour."""
    canvas.delete("all")
    size = int(canvas["width"])
    canvas.create_oval(px(2), px(2), size - px(2), size - px(2), fill=lamp_color, outline="")


def roundel(parent, text, bg=CARD, muted=False, size=30):
    """Race-number roundel used for vJoy button numbers."""
    s = px(size)
    canvas = tk.Canvas(parent, width=s, height=s, bg=bg, highlightthickness=0)
    outline = FAINT if muted else NAVY
    canvas.create_oval(px(2), px(2), s - px(2), s - px(2), fill="#ffffff", outline=outline, width=px(2))
    canvas.create_text(s / 2, s / 2, text=text, font=tk_font(HEAD, 10 if len(text) < 3 else 9, "bold"), fill=outline)
    return canvas


class RowButton(tk.Frame):
    """Lightweight outlined button for list rows (plain Tk keeps a 64-row list fast to build)."""

    def __init__(self, parent, text, command, bg=CARD):
        super().__init__(parent, bg=NAVY, padx=1, pady=1, cursor="hand2")
        self._bg = bg
        self.label = tk.Label(self, text=text, font=tk_font(BODY, 9), bg=bg, fg=NAVY, padx=10, pady=1, cursor="hand2")
        self.label.pack()
        for widget in (self, self.label):
            widget.bind("<Button-1>", lambda e: command())
            widget.bind("<Enter>", lambda e: self.label.config(bg=HOVER))
            widget.bind("<Leave>", lambda e: self.label.config(bg=self._bg))
