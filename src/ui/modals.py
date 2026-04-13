import tkinter as tk


class ApiKeyModal:
    """Modal dialog for configuring OpenAI API key."""

    def __init__(self, parent, fonts, colors, current_key, on_save):
        self.parent = parent
        self.fonts = fonts
        self.colors = colors
        self.on_save = on_save

        self.modal = tk.Toplevel(parent)
        self.modal.title("Configure API Key")
        self.modal.geometry("400x180")
        self.modal.configure(bg=colors["bg_color"])
        self.modal.resizable(False, False)
        self.modal.transient(parent)
        self.modal.grab_set()

        self._center_on_parent()
        self._build_ui(current_key)

    def _center_on_parent(self):
        self.modal.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - 400) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - 180) // 2
        self.modal.geometry(f"+{x}+{y}")

    def _build_ui(self, current_key):
        frame = tk.Frame(self.modal, bg=self.colors["bg_color"], padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Enter your OpenAI API Key:",
            font=self.fonts["base"],
            bg=self.colors["bg_color"],
            fg=self.colors["text_main"]
        ).pack(anchor="w", pady=(0, 10))

        self.entry = tk.Entry(
            frame,
            font=self.fonts["mono"],
            bg=self.colors["card_bg"],
            fg=self.colors["text_main"],
            insertbackground=self.colors["text_main"],
            relief=tk.FLAT,
            width=50
        )
        self.entry.pack(fill=tk.X, ipady=8)
        self.entry.insert(0, current_key)
        self.entry.focus_set()

        btn_frame = tk.Frame(frame, bg=self.colors["bg_color"])
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        tk.Button(
            btn_frame,
            text="CANCEL",
            font=self.fonts["sm"],
            relief=tk.FLAT,
            bg=self.colors["btn_bg"],
            fg=self.colors["text_main"],
            padx=20,
            pady=8,
            command=self.modal.destroy
        ).pack(side=tk.RIGHT, padx=(10, 0))

        tk.Button(
            btn_frame,
            text="SAVE",
            font=self.fonts["sm"],
            relief=tk.FLAT,
            bg=self.colors["ready_green"],
            fg=self.colors["bg_color"],
            padx=20,
            pady=8,
            command=self._save_and_close
        ).pack(side=tk.RIGHT)

    def _save_and_close(self):
        key = self.entry.get().strip()
        self.on_save(key)
        self.modal.destroy()


class RenameCommandModal:
    """Modal dialog for renaming a command binding."""

    def __init__(self, parent, fonts, colors, current_name, button_key, existing_names, on_save):
        self.parent = parent
        self.fonts = fonts
        self.colors = colors
        self.current_name = current_name
        self.button_key = button_key
        self.existing_names = existing_names
        self.on_save = on_save

        self.modal = tk.Toplevel(parent)
        self.modal.title("Rename Command")
        self.modal.geometry("350x210")
        self.modal.configure(bg=colors["bg_color"])
        self.modal.resizable(False, False)
        self.modal.transient(parent)
        self.modal.grab_set()

        self._center_on_parent()
        self._build_ui()

    def _center_on_parent(self):
        self.modal.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - 350) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - 210) // 2
        self.modal.geometry(f"+{x}+{y}")

    def _build_ui(self):
        frame = tk.Frame(self.modal, bg=self.colors["bg_color"], padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text=f"Rename command (Button: {self.button_key}):",
            font=self.fonts["base"],
            bg=self.colors["bg_color"],
            fg=self.colors["text_main"]
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            frame,
            text="(e.g., fuel status)",
            font=self.fonts["sm"],
            bg=self.colors["bg_color"],
            fg=self.colors["text_dim"]
        ).pack(anchor="w", pady=(0, 10))

        self.entry = tk.Entry(
            frame,
            font=self.fonts["key"],
            bg=self.colors["card_bg"],
            fg=self.colors["accent_color"],
            insertbackground=self.colors["text_main"],
            relief=tk.FLAT,
            width=30
        )
        self.entry.pack(fill=tk.X, ipady=8)
        self.entry.insert(0, self.current_name)
        self.entry.select_range(0, tk.END)
        self.entry.focus_set()

        # Error label for validation messages
        self.error_label = tk.Label(
            frame,
            text="",
            font=self.fonts["sm"],
            bg=self.colors["bg_color"],
            fg=self.colors["stop_red"]
        )
        self.error_label.pack(anchor="w", pady=(5, 0))

        # Bind Enter key to save
        self.entry.bind("<Return>", lambda e: self._save_and_close())

        btn_frame = tk.Frame(frame, bg=self.colors["bg_color"])
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(
            btn_frame,
            text="CANCEL",
            font=self.fonts["sm"],
            relief=tk.FLAT,
            bg=self.colors["btn_bg"],
            fg=self.colors["text_main"],
            padx=20,
            pady=8,
            command=self.modal.destroy
        ).pack(side=tk.RIGHT, padx=(10, 0))

        tk.Button(
            btn_frame,
            text="SAVE",
            font=self.fonts["sm"],
            relief=tk.FLAT,
            bg=self.colors["ready_green"],
            fg=self.colors["bg_color"],
            padx=20,
            pady=8,
            command=self._save_and_close
        ).pack(side=tk.RIGHT)

    def _save_and_close(self):
        new_name = self.entry.get().strip().lower()

        # Validation: cannot be empty
        if not new_name:
            self.error_label.config(text="Name cannot be empty")
            return

        # Validation: cannot use existing name (unless same as current)
        if new_name != self.current_name and new_name in self.existing_names:
            self.error_label.config(text=f"'{new_name}' already exists")
            return

        # If same name, just close
        if new_name == self.current_name:
            self.modal.destroy()
            return

        self.on_save(self.current_name, new_name, self.button_key)
        self.modal.destroy()

