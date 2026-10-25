from datetime import datetime

import customtkinter as ctk

from src.ui import theme as t

MAX_LINES = 1000


class ActivityPage:
    """The full session log. Repeated lines collapse into one with a count."""

    def __init__(self, master, app):
        self.app = app
        self._last_text = None
        self._repeats = 0
        self._last_start = None
        self.frame = ctk.CTkFrame(master, fg_color=t.CREAM)
        t.page_header(self.frame, "Activity", "Everything the assistant did this session.")

        bar = ctk.CTkFrame(self.frame, fg_color=t.CREAM, height=32)
        bar.pack(fill="x", pady=(0, 12))
        t.secondary_button(bar, "Clear", self.clear, bg=t.CREAM, width=80, height=30).pack(side="right")
        t.secondary_button(bar, "Copy all", self.copy, bg=t.CREAM, width=90, height=30).pack(side="right", padx=(0, 8))

        outer, card = t.card(self.frame)
        outer.pack(fill="both", expand=True)
        self.text = ctk.CTkTextbox(card, fg_color=t.CARD, text_color=t.TEXT, font=t.font(t.MONO, 13), wrap="word",
                                   corner_radius=0, border_width=0, scrollbar_button_color=t.LINE)
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        self.text.configure(state="disabled")

    def on_show(self):
        self.text.see("end")

    def append(self, line):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.text.configure(state="normal")
        if line == self._last_text and self._last_start is not None:
            self._repeats += 1
            self.text.delete(self._last_start, "end-1c")
            self.text.insert("end", f"[{stamp}] {line}  (x{self._repeats})\n")
        else:
            if int(self.text.index("end-1c").split(".")[0]) > MAX_LINES:
                self.text.delete("1.0", "2.0")
            self._last_text, self._repeats = line, 1
            self._last_start = self.text.index("end-1c")
            self.text.insert("end", f"[{stamp}] {line}\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def copy(self):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(self.text.get("1.0", "end-1c"))

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._last_text, self._last_start = None, None
