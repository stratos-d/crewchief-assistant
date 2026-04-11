import tkinter as tk
from datetime import datetime


class TerminalRedirector:
    """Redirects stdout to a Tkinter Text widget with timestamps."""

    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        if string.strip():
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            self.text_widget.after(0, self._write, f"{timestamp}{string.strip()}\n")

    def _write(self, text):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def flush(self):
        pass


class StatusPill:
    """Status indicator pill widget."""

    def __init__(self, parent, fonts, colors):
        self.colors = colors
        self.label = tk.Label(
            parent,
            text="INITIALIZING",
            font=fonts["base"],
            bg=colors["card_bg"],
            fg=colors["proc_orange"],
            padx=15,
            pady=5
        )

    def pack(self, **kwargs):
        self.label.pack(**kwargs)

    def update(self, text, color):
        self.label.config(text=text, fg=color)


class SettingsRow:
    """Reusable row for settings card."""

    def __init__(self, parent, label_text, fonts, colors):
        self.frame = tk.Frame(parent, bg=colors["card_bg"])
        self.colors = colors
        self.fonts = fonts

        tk.Label(
            self.frame,
            text=label_text,
            font=fonts["sm"],
            bg=colors["card_bg"],
            fg=colors["text_dim"],
            width=18,
            anchor="w"
        ).pack(side=tk.LEFT)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def add_value_label(self, text, accent=False):
        """Add a value display label."""
        fg = self.colors["accent_color"] if accent else self.colors["text_main"]
        label = tk.Label(
            self.frame,
            text=text,
            font=self.fonts["key"],
            bg=self.colors["bg_color"],
            fg=fg,
            padx=10,
            pady=2,
            relief=tk.SOLID,
            bd=1
        )
        label.pack(side=tk.LEFT, padx=(4, 0))
        return label

    def add_status_label(self, is_set):
        """Add a SET/NOT SET status label."""
        text = "SET" if is_set else "NOT SET"
        fg = self.colors["ready_green"] if is_set else self.colors["stop_red"]
        label = tk.Label(
            self.frame,
            text=text,
            font=self.fonts["key"],
            bg=self.colors["bg_color"],
            fg=fg,
            padx=10,
            pady=2,
            relief=tk.SOLID,
            bd=1
        )
        label.pack(side=tk.LEFT, padx=(4, 0))
        return label

    def add_button(self, text, command, state=tk.NORMAL):
        """Add a button to the right side."""
        btn = tk.Button(
            self.frame,
            text=text,
            font=self.fonts["sm"],
            relief=tk.FLAT,
            bg=self.colors["btn_bg"],
            fg=self.colors["text_main"],
            width=10,
            pady=4,
            cursor="hand2",
            command=command,
            state=state
        )
        btn.pack(side=tk.RIGHT)
        return btn

    def add_entry(self, var, width=5):
        """Add an entry field."""
        entry = tk.Entry(
            self.frame,
            font=self.fonts["key"],
            bg=self.colors["bg_color"],
            fg=self.colors["accent_color"],
            insertbackground=self.colors["text_main"],
            relief=tk.FLAT,
            width=width,
            justify="center",
            textvariable=var
        )
        entry.pack(side=tk.LEFT, padx=(4, 0), ipady=2)
        return entry

    def add_suffix(self, text):
        """Add a suffix label (like %)."""
        tk.Label(
            self.frame,
            text=text,
            font=self.fonts["sm"],
            bg=self.colors["card_bg"],
            fg=self.colors["text_dim"]
        ).pack(side=tk.LEFT, padx=(2, 0))
