import os
import tkinter as tk

from src.config_manager import (
    get_controllers, get_all_commands,
    add_controller, remove_controller, rename_binding,
    get_available_buttons, load_config, save_config, get_setting, set_setting
)
from src.gamepad import trigger_button, get_gamepad, release_gamepad
from src.constants import ControllerType
from src.ui.modals import RenameCommandModal, ControllerTypeModal


class ControllersPanel:
    """Mixin providing the Virtual Controllers panel and all controller event handlers."""

    def _build_command_binder(self):
        self.binder_card = tk.Frame(self.bottom_row, bg=self.theme["card_bg"], padx=15, pady=10)
        self.binder_card.pack(fill="both", expand=True)

        header_frame = tk.Frame(self.binder_card, bg=self.theme["card_bg"])
        header_frame.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            header_frame,
            text="VIRTUAL CONTROLLERS",
            font=self.fonts["section"],
            bg=self.theme["card_bg"],
            fg=self.theme["accent_color"]
        ).pack(side=tk.LEFT)

        self.sync_btn = tk.Button(
            header_frame,
            text="SYNC WITH CREWCHIEF",
            font=self.fonts["sm"],
            bg=self.theme["accent_color"],
            fg=self.theme["bg_color"],
            activebackground=self.theme["accent_color"],
            activeforeground=self.theme["bg_color"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            command=self._sync_crewchief
        )
        self.sync_btn.pack(side=tk.RIGHT)

        self.add_ctrl_btn = tk.Button(
            header_frame,
            text="ADD CONTROLLER",
            font=self.fonts["sm"],
            bg=self.theme["btn_bg"],
            fg=self.theme["text_main"],
            activebackground=self.theme["ready_green"],
            activeforeground=self.theme["bg_color"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            command=self._add_new_controller
        )
        self.add_ctrl_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self.controllers_frame = tk.Frame(self.binder_card, bg=self.theme["card_bg"])
        self.controllers_frame.pack(fill=tk.X)

    def _load_binding_buttons(self):
        """Load command binding buttons for all controllers."""
        for widget in self.controllers_frame.winfo_children():
            widget.destroy()

        controllers = get_controllers()
        for idx, controller in enumerate(controllers):
            self._build_controller_section(idx, controller, len(controllers))

        gamepad_count = sum(1 for c in controllers if ControllerType(c.get("type", ControllerType.X360)).is_virtual)
        if gamepad_count >= 3:
            self.add_ctrl_btn.pack_forget()
        else:
            self.add_ctrl_btn.pack(side=tk.RIGHT, padx=(0, 6))

    def _build_controller_section(self, idx, controller, total_controllers):
        """Build UI section for a single controller."""
        if idx > 0:
            tk.Frame(self.controllers_frame, bg=self.theme["bg_color"], height=1).pack(fill=tk.X, pady=(0, 10))

        ctrl_frame = tk.Frame(self.controllers_frame, bg=self.theme["card_bg"])
        ctrl_frame.pack(fill=tk.X, pady=(0, 6))

        header = tk.Frame(ctrl_frame, bg=self.theme["card_bg"])
        header.pack(fill=tk.X, pady=(0, 6))

        ctrl_type = controller.get("type", ControllerType.X360.value)
        ctrl_type_enum = ControllerType(ctrl_type)

        tk.Label(
            header,
            text=controller.get("name", f"Controller {idx + 1}").upper(),
            font=self.fonts["sm"],
            bg=self.theme["card_bg"],
            fg=self.theme["text_dim"]
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text=ctrl_type_enum.label,
            font=("Segoe UI", 7),
            bg=self.theme["card_bg"],
            fg=self.theme["text_dim"]
        ).pack(side=tk.LEFT, padx=(6, 0))

        btn_frame = tk.Frame(header, bg=self.theme["card_bg"])
        btn_frame.pack(side=tk.RIGHT)

        if ctrl_type_enum.is_virtual:
            tk.Button(
                btn_frame,
                text="REMOVE",
                font=("Segoe UI", 8),
                bg=self.theme["card_bg"],
                fg=self.theme["stop_red"],
                activebackground=self.theme["stop_red"],
                activeforeground=self.theme["text_main"],
                relief=tk.FLAT,
                bd=0,
                cursor="hand2",
                command=lambda i=idx: self._remove_controller(i)
            ).pack(side=tk.LEFT, padx=(0, 8))

        btn_grid = tk.Frame(ctrl_frame, bg=self.theme["card_bg"])
        btn_grid.pack(fill=tk.X)

        num_cols = 3
        for col in range(num_cols):
            btn_grid.grid_columnconfigure(col, weight=1)

        bindings = controller.get("bindings", {})
        row, col, prev_group = 0, 0, None
        for button_key, command in bindings.items():
            group = self._get_command_group(command)
            if prev_group is not None and group != prev_group and col == 0:
                spacer = tk.Frame(btn_grid, bg=self.theme["card_bg"], height=6)
                spacer.grid(row=row, column=0, columnspan=num_cols, sticky=tk.EW)
                row += 1
            prev_group = group

            btn = tk.Button(
                btn_grid,
                text=command.replace("_", " ").capitalize(),
                font=self.fonts["cmd"],
                relief=tk.FLAT,
                bg=self.theme["bg_color"],
                fg=self.theme["text_dim"],
                activebackground=self.theme["accent_color"],
                activeforeground=self.theme["bg_color"],
                pady=5,
                command=lambda i=idx, c=command: self._manual_trigger_controller(i, c)
            )
            btn.grid(row=row, column=col, sticky=tk.EW, padx=1, pady=1)
            btn.bind("<Button-3>", lambda e, i=idx, b=button_key, c=command: self._open_rename_modal(i, b, c))

            col += 1
            if col >= num_cols:
                col, row = 0, row + 1

    @staticmethod
    def _get_command_group(command):
        """Categorize a command for visual clustering."""
        cmd = command.lower().replace("_", " ")
        if any(cmd.startswith(p) for p in ["hows my", "how are my", "how is my"]):
            return "status"
        if any(cmd.startswith(p) for p in ["whats my", "what was my", "whats the", "what are my"]):
            return "info"
        if any(p in cmd for p in ["pit", "fuel", "tyre", "tire"]):
            return "pit_tyre"
        if any(p in cmd for p in ["gap", "ahead", "behind", "position", "front", "leading"]):
            return "position"
        if any(p in cmd for p in ["lap time", "best lap", "fastest"]):
            return "timing"
        if any(cmd.startswith(p) for p in ["toggle", "set"]):
            return "toggle"
        return "other"

    def _add_new_controller(self):
        """Add a new gamepad controller with default bindings."""
        import threading
        controllers = get_controllers()
        gamepad_count = sum(1 for c in controllers if ControllerType(c.get("type", ControllerType.X360)).is_virtual)
        if gamepad_count >= 3:
            print("Maximum 3 gamepad controllers allowed.")
            return

        modal = ControllerTypeModal(self.root, self.fonts, self.theme)
        if not modal.result:
            return
        gamepad_type = modal.result

        new_idx = add_controller(gamepad_type)
        if new_idx >= 0:
            buttons = get_available_buttons(gamepad_type)
            for i, btn_key in enumerate(buttons):
                rename_binding(new_idx, btn_key, f"command {gamepad_count * len(buttons) + i + 1}")

            threading.Thread(target=lambda: get_gamepad(new_idx), daemon=True).start()
            print(f"Added Controller {new_idx + 1}")
            self._load_binding_buttons()

    def _remove_controller(self, controller_index):
        """Remove a specific controller."""
        if remove_controller(controller_index):
            release_gamepad(controller_index)
            print(f"Removed Controller {controller_index + 1}")
            self._load_binding_buttons()

    def _open_rename_modal(self, controller_index, button_key, command):
        """Open modal to rename a command."""
        RenameCommandModal(
            self.root,
            self.fonts,
            self.theme,
            command,
            button_key,
            get_all_commands(),
            on_save=lambda old, new, btn: self._on_command_renamed(controller_index, old, new, btn)
        )

    def _on_command_renamed(self, controller_index, old_command, new_command, button_key):
        """Handle command rename."""
        rename_binding(controller_index, button_key, new_command)
        self._load_binding_buttons()
        print(f"Renamed '{old_command}' to '{new_command}'")

    def _sync_crewchief(self):
        """Sync bindings with CrewChief's config file."""
        from tkinter import filedialog, messagebox
        from src.crewchief_sync import sync_crewchief_config

        default_path = get_setting("crewchief_config_path", "")
        if not default_path:
            default_path = os.path.join(
                os.path.expanduser("~"),
                "Documents", "CrewChiefV4", "Profiles", "ControllerData", "defaultSettings.json"
            )

        config_path = filedialog.askopenfilename(
            title="Select CrewChief defaultSettings.json",
            initialdir=os.path.dirname(default_path),
            initialfile=os.path.basename(default_path),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not config_path:
            return

        set_setting("crewchief_config_path", config_path)

        if not messagebox.askyesno(
            "Sync with CrewChief",
            "This will overwrite CrewChief's button assignments for actions marked as available.\n\n"
            "A backup of the original file will be created.\n\nContinue?"
        ):
            return

        config = load_config()
        result = sync_crewchief_config(config_path, config.get("controllers", []))

        if not result["success"]:
            messagebox.showerror("Sync Failed", result["message"])
            print(f"Sync failed: {result['message']}")
            return

        config = load_config()
        config["controllers"] = result["bindings"]
        save_config(config)

        self._load_binding_buttons()
        print(f"CrewChief sync complete: {result['message']}")

        if result["truncated"]:
            messagebox.showwarning("Sync Warning", result["message"])

    def _manual_trigger_controller(self, controller_index, command):
        """Manually trigger a command on a specific controller."""
        import traceback
        from src.config_manager import find_command_controller
        try:
            result = find_command_controller(command)
            if not result:
                print(f"Manual trigger: command '{command}' not found in bindings")
                return
            idx, button_key = result
            print(f"Manual trigger: {command} → {button_key} (Controller {idx + 1})")
            trigger_button(idx, button_key)
        except Exception:
            traceback.print_exc()
