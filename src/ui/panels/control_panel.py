import tkinter as tk


class ControlPanelMixin:
    """Mixin providing the Control + Log card and engine event handlers."""

    def _build_control_log(self):
        """Build combined controls + system log card."""
        log_card = tk.Frame(self.left_col, bg=self.theme["card_bg"], padx=15, pady=10)
        log_card.pack(fill="both", expand=True)

        tk.Label(
            log_card,
            text="CONTROL",
            font=self.fonts["section"],
            bg=self.theme["card_bg"],
            fg=self.theme["accent_color"]
        ).pack(anchor="w", pady=(0, 8))

        ctrl_frame = tk.Frame(log_card, bg=self.theme["card_bg"])
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = tk.Button(
            ctrl_frame,
            text="START",
            font=self.fonts["base"],
            bg=self.theme["btn_bg"],
            fg=self.theme["text_main"],
            activebackground=self.theme["ready_green"],
            activeforeground=self.theme["bg_color"],
            relief=tk.FLAT,
            pady=8,
            cursor="hand2",
            command=self._start_engine,
            state=tk.DISABLED
        )
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.stop_btn = tk.Button(
            ctrl_frame,
            text="STOP",
            font=self.fonts["base"],
            bg=self.theme["btn_bg"],
            fg=self.theme["text_dim"],
            activebackground=self.theme["stop_red"],
            activeforeground=self.theme["text_main"],
            relief=tk.FLAT,
            pady=8,
            cursor="hand2",
            command=self._stop_engine,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        term_frame = tk.Frame(log_card, bg=self.theme["term_bg"])
        term_frame.pack(fill="both", expand=True)

        self.terminal_text = tk.Text(
            term_frame,
            bg=self.theme["term_bg"],
            fg="#E2E2B6",
            font=self.fonts["mono"],
            wrap=tk.WORD,
            state=tk.DISABLED,
            borderwidth=0,
            padx=10,
            pady=8,
            height=12,
            width=30
        )
        self.terminal_text.pack(fill="both", expand=True)

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
        self.start_btn.config(state=tk.DISABLED, bg=self.theme["btn_bg"], fg=self.theme["text_dim"])
        self.stop_btn.config(state=tk.NORMAL, bg=self.theme["stop_red"], fg=self.theme["text_main"])
        self.rebind_btn.config(state=tk.DISABLED)
        self.engine.start(self.ptt_key)

    def _stop_engine(self):
        """Stop the voice engine."""
        self.engine.stop()
        self._update_status("OFFLINE", self.theme["text_dim"])
        self.start_btn.config(state=tk.NORMAL, bg=self.theme["ready_green"], fg=self.theme["bg_color"])
        self.stop_btn.config(state=tk.DISABLED, bg=self.theme["btn_bg"], fg=self.theme["text_dim"])
        self.rebind_btn.config(state=tk.NORMAL)
