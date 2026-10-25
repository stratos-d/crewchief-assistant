import customtkinter as ctk

from src.ui import theme as t


class RenameDialog:
    """Name (or clear) the voice command on one vJoy button."""

    def __init__(self, app, button_number, cc_action, current_name, existing_names, on_save):
        self.current_name = current_name
        self.existing_names = existing_names
        self.on_save = on_save

        self.top = ctk.CTkToplevel(app.root, fg_color=t.CREAM)
        self.top.title(f"Button {button_number}")
        self.top.resizable(False, False)
        self.top.transient(app.root)
        if getattr(app, "icon_path", None):
            # CustomTkinter sets its own icon on new windows shortly after creation
            self.top.after(250, lambda: self.top.iconbitmap(app.icon_path))

        frame = ctk.CTkFrame(self.top, fg_color=t.CREAM)
        frame.pack(fill="both", expand=True, padx=22, pady=18)
        verb = "Rename" if current_name else "Assign"
        ctk.CTkLabel(frame, text=f"{verb} button {button_number}".upper(), font=t.font(t.HEAD, 17, "bold"),
                     text_color=t.TEXT).pack(anchor="w")
        ctk.CTkLabel(frame, text=f"CrewChief: {cc_action}" if cc_action else "", font=t.font(t.BODY, 13),
                     text_color=t.MUTED, wraplength=360, justify="left").pack(anchor="w", pady=(0, 10))
        self.entry = ctk.CTkEntry(frame, width=360, height=34, fg_color=t.CARD, border_color=t.NAVY, border_width=1,
                                  corner_radius=t.RADIUS, text_color=t.TEXT, font=t.font(t.BODY, 14))
        self.entry.pack(fill="x")
        self.entry.insert(0, current_name)
        self.error = ctk.CTkLabel(frame, text="", font=t.font(t.BODY, 12), text_color=t.RED, height=18)
        self.error.pack(anchor="w", pady=(4, 8))

        buttons = ctk.CTkFrame(frame, fg_color=t.CREAM)
        buttons.pack(fill="x")
        t.primary_button(buttons, "Save", self._save, width=100, height=32).pack(side="right")
        t.secondary_button(buttons, "Cancel", self.top.destroy, bg=t.CREAM, width=90, height=32).pack(side="right", padx=(0, 8))
        if current_name:
            t.secondary_button(buttons, "Remove", self._remove, bg=t.CREAM, width=90, height=32).pack(side="left")

        self.top.bind("<Return>", lambda e: self._save())
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        self._center_on(app.root)
        self.top.after(100, self._focus)

    def _center_on(self, root):
        self.top.update_idletasks()
        w, h = self.top.winfo_reqwidth(), self.top.winfo_reqheight()
        x = root.winfo_rootx() + (root.winfo_width() - w) // 2
        y = root.winfo_rooty() + (root.winfo_height() - h) // 3
        self.top.geometry(f"+{x}+{y}")

    def _focus(self):
        self.top.grab_set()
        self.entry.focus_set()
        self.entry.select_range(0, "end")

    def _save(self):
        new_name = self.entry.get().strip().lower()
        if not new_name:
            self.error.configure(text="Type a command.")
            return
        if new_name != self.current_name and new_name in self.existing_names:
            self.error.configure(text=f"“{new_name}” is already in use.")
            return
        self.top.destroy()
        if new_name != self.current_name:
            self.on_save(new_name)

    def _remove(self):
        self.top.destroy()
        self.on_save("")
