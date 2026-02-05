import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field, asdict
from typing import Optional
import copy


@dataclass
class HatchSettings:
    enable_contour: bool = True
    
    hatch1_enabled: bool = False
    hatch1_pen: int = 0
    hatch1_edge_dist: float = 0.0
    hatch1_line_dist: float = 0.05
    hatch1_start_offset: float = 0.0
    hatch1_end_offset: float = 0.0
    hatch1_angle: float = 0.0
    
    hatch2_enabled: bool = False
    hatch2_pen: int = 0
    hatch2_edge_dist: float = 0.0
    hatch2_line_dist: float = 0.05
    hatch2_start_offset: float = 0.0
    hatch2_end_offset: float = 0.0
    hatch2_angle: float = 90.0

    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "HatchSettings":
        return cls(
            enable_contour=data.get("enable_contour", True),
            hatch1_enabled=data.get("hatch1_enabled", False),
            hatch1_pen=data.get("hatch1_pen", 0),
            hatch1_edge_dist=data.get("hatch1_edge_dist", 0.0),
            hatch1_line_dist=data.get("hatch1_line_dist", 0.05),
            hatch1_start_offset=data.get("hatch1_start_offset", 0.0),
            hatch1_end_offset=data.get("hatch1_end_offset", 0.0),
            hatch1_angle=data.get("hatch1_angle", 0.0),
            hatch2_enabled=data.get("hatch2_enabled", False),
            hatch2_pen=data.get("hatch2_pen", 0),
            hatch2_edge_dist=data.get("hatch2_edge_dist", 0.0),
            hatch2_line_dist=data.get("hatch2_line_dist", 0.05),
            hatch2_start_offset=data.get("hatch2_start_offset", 0.0),
            hatch2_end_offset=data.get("hatch2_end_offset", 0.0),
            hatch2_angle=data.get("hatch2_angle", 90.0),
        )


class HatchSettingsDialog:
    def __init__(self, parent: tk.Widget, hatch_settings: Optional[HatchSettings] = None):
        self._parent = parent
        self._settings = copy.deepcopy(hatch_settings) if hatch_settings else HatchSettings()
        self._result: Optional[HatchSettings] = None
        self._vars: dict = {}
        self._hatch_widgets: dict = {}
        
    def show(self) -> Optional[HatchSettings]:
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Hatch Settings")
        self._dialog.configure(bg="#f0f0f0")
        self._dialog.resizable(False, False)
        
        self._dialog.attributes("-topmost", True)
        
        parent_x = self._parent.winfo_rootx()
        parent_y = self._parent.winfo_rooty()
        self._dialog.geometry(f"+{parent_x + 50}+{parent_y + 50}")
        
        self._create_widgets()
        self._load_settings()
        
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._parent.wait_window(self._dialog)
        
        return self._result
    
    def _create_widgets(self):
        main_frame = tk.Frame(self._dialog, bg="#f0f0f0")
        main_frame.pack(padx=15, pady=15, fill="both", expand=True)
        
        self._create_hatch_section(main_frame)
        
        btn_frame = tk.Frame(self._dialog, bg="#f0f0f0")
        btn_frame.pack(pady=10)
        
        ok_btn = tk.Button(btn_frame, text="OK", width=10, command=self._on_ok)
        ok_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", width=10, command=self._on_cancel)
        cancel_btn.pack(side="left", padx=5)
    
    def _create_hatch_section(self, parent):
        row = 0
        self._create_checkbox(parent, "Mark Contour", "enable_contour", True, row)
        self._vars["enable_contour"].trace_add("write", lambda *_: self._update_hatch_state())
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_checkbox(parent, "Hatch 1", "hatch1_enabled", False, row)
        self._vars["hatch1_enabled"].trace_add("write", lambda *_: self._update_hatch_state())
        row += 1
        self._hatch_widgets["hatch1_pen"] = self._create_labeled_entry(parent, "Pen", "hatch1_pen", 0, "", row)
        row += 1
        self._hatch_widgets["hatch1_edge_dist"] = self._create_labeled_entry(parent, "Edge Offset", "hatch1_edge_dist", 0.0, "mm", row)
        row += 1
        self._hatch_widgets["hatch1_line_dist"] = self._create_labeled_entry(parent, "Line Space", "hatch1_line_dist", 0.05, "mm", row)
        row += 1
        self._hatch_widgets["hatch1_start_offset"] = self._create_labeled_entry(parent, "Start Offset", "hatch1_start_offset", 0.0, "mm", row)
        row += 1
        self._hatch_widgets["hatch1_end_offset"] = self._create_labeled_entry(parent, "End Offset", "hatch1_end_offset", 0.0, "mm", row)
        row += 1
        self._hatch_widgets["hatch1_angle"] = self._create_labeled_entry(parent, "Angle", "hatch1_angle", 0.0, "°", row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_checkbox(parent, "Hatch 2", "hatch2_enabled", False, row)
        self._vars["hatch2_enabled"].trace_add("write", lambda *_: self._update_hatch_state())
        row += 1
        self._hatch_widgets["hatch2_pen"] = self._create_labeled_entry(parent, "Pen", "hatch2_pen", 0, "", row)
        row += 1
        self._hatch_widgets["hatch2_edge_dist"] = self._create_labeled_entry(parent, "Edge Offset", "hatch2_edge_dist", 0.0, "mm", row)
        row += 1
        self._hatch_widgets["hatch2_line_dist"] = self._create_labeled_entry(parent, "Line Space", "hatch2_line_dist", 0.05, "mm", row)
        row += 1
        self._hatch_widgets["hatch2_start_offset"] = self._create_labeled_entry(parent, "Start Offset", "hatch2_start_offset", 0.0, "mm", row)
        row += 1
        self._hatch_widgets["hatch2_end_offset"] = self._create_labeled_entry(parent, "End Offset", "hatch2_end_offset", 0.0, "mm", row)
        row += 1
        self._hatch_widgets["hatch2_angle"] = self._create_labeled_entry(parent, "Angle", "hatch2_angle", 90.0, "°", row)
        
        self._update_hatch_state()
    
    def _create_labeled_entry(self, parent, label: str, var_name: str, default_value, unit: str = "", row: int = 0, width: int = 8):
        lbl = tk.Label(parent, text=label, bg="#f0f0f0", anchor="w")
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        
        var = tk.StringVar(value=str(default_value))
        self._vars[var_name] = var
        
        entry = tk.Entry(parent, textvariable=var, width=width, justify="right")
        entry.grid(row=row, column=1, sticky="w", pady=2, padx=2)
        
        unit_lbl = None
        if unit:
            unit_lbl = tk.Label(parent, text=unit, bg="#f0f0f0", anchor="w")
            unit_lbl.grid(row=row, column=2, sticky="w", pady=2)
        
        return {"type": "entry", "label": lbl, "widget": entry, "unit": unit_lbl, "var": var, "name": var_name}
    
    def _create_checkbox(self, parent, label: str, var_name: str, default_value: bool, row: int = 0):
        var = tk.BooleanVar(value=default_value)
        self._vars[var_name] = var
        
        cb = tk.Checkbutton(parent, text=label, variable=var, bg="#f0f0f0")
        cb.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        
        return {"type": "checkbox", "widget": cb, "var": var, "name": var_name}
    
    def _update_hatch_state(self):
        if not self._hatch_widgets:
            return
        
        hatch1_enabled = self._vars.get("hatch1_enabled", tk.BooleanVar(value=False)).get()
        hatch2_enabled = self._vars.get("hatch2_enabled", tk.BooleanVar(value=False)).get()
        
        hatch1_fields = ["hatch1_pen", "hatch1_edge_dist", "hatch1_line_dist", 
                         "hatch1_start_offset", "hatch1_end_offset", "hatch1_angle"]
        for field_name in hatch1_fields:
            widget_info = self._hatch_widgets.get(field_name)
            if widget_info:
                state = "normal" if hatch1_enabled else "disabled"
                widget_info["widget"].configure(state=state)
                if widget_info.get("label"):
                    widget_info["label"].configure(state=state)
        
        hatch2_fields = ["hatch2_pen", "hatch2_edge_dist", "hatch2_line_dist", 
                         "hatch2_start_offset", "hatch2_end_offset", "hatch2_angle"]
        for field_name in hatch2_fields:
            widget_info = self._hatch_widgets.get(field_name)
            if widget_info:
                state = "normal" if hatch2_enabled else "disabled"
                widget_info["widget"].configure(state=state)
                if widget_info.get("label"):
                    widget_info["label"].configure(state=state)
    
    def _load_settings(self):
        self._vars["enable_contour"].set(self._settings.enable_contour)
        self._vars["hatch1_enabled"].set(self._settings.hatch1_enabled)
        self._vars["hatch1_pen"].set(str(self._settings.hatch1_pen))
        self._vars["hatch1_edge_dist"].set(str(self._settings.hatch1_edge_dist))
        self._vars["hatch1_line_dist"].set(str(self._settings.hatch1_line_dist))
        self._vars["hatch1_start_offset"].set(str(self._settings.hatch1_start_offset))
        self._vars["hatch1_end_offset"].set(str(self._settings.hatch1_end_offset))
        self._vars["hatch1_angle"].set(str(self._settings.hatch1_angle))
        self._vars["hatch2_enabled"].set(self._settings.hatch2_enabled)
        self._vars["hatch2_pen"].set(str(self._settings.hatch2_pen))
        self._vars["hatch2_edge_dist"].set(str(self._settings.hatch2_edge_dist))
        self._vars["hatch2_line_dist"].set(str(self._settings.hatch2_line_dist))
        self._vars["hatch2_start_offset"].set(str(self._settings.hatch2_start_offset))
        self._vars["hatch2_end_offset"].set(str(self._settings.hatch2_end_offset))
        self._vars["hatch2_angle"].set(str(self._settings.hatch2_angle))
        
        self._update_hatch_state()
    
    def _save_settings(self):
        self._settings.enable_contour = self._vars["enable_contour"].get()
        self._settings.hatch1_enabled = self._vars["hatch1_enabled"].get()
        self._settings.hatch1_pen = self._parse_pen("hatch1_pen", self._settings.hatch1_pen)
        self._settings.hatch1_edge_dist = self._parse_float("hatch1_edge_dist", self._settings.hatch1_edge_dist)
        self._settings.hatch1_line_dist = self._parse_float("hatch1_line_dist", self._settings.hatch1_line_dist)
        self._settings.hatch1_start_offset = self._parse_float("hatch1_start_offset", self._settings.hatch1_start_offset)
        self._settings.hatch1_end_offset = self._parse_float("hatch1_end_offset", self._settings.hatch1_end_offset)
        self._settings.hatch1_angle = self._parse_float("hatch1_angle", self._settings.hatch1_angle)
        self._settings.hatch2_enabled = self._vars["hatch2_enabled"].get()
        self._settings.hatch2_pen = self._parse_pen("hatch2_pen", self._settings.hatch2_pen)
        self._settings.hatch2_edge_dist = self._parse_float("hatch2_edge_dist", self._settings.hatch2_edge_dist)
        self._settings.hatch2_line_dist = self._parse_float("hatch2_line_dist", self._settings.hatch2_line_dist)
        self._settings.hatch2_start_offset = self._parse_float("hatch2_start_offset", self._settings.hatch2_start_offset)
        self._settings.hatch2_end_offset = self._parse_float("hatch2_end_offset", self._settings.hatch2_end_offset)
        self._settings.hatch2_angle = self._parse_float("hatch2_angle", self._settings.hatch2_angle)
    
    def _validate_pen(self, var_name: str, label: str) -> bool:
        val = self._vars.get(var_name)
        if val is None:
            return True
        s = val.get().strip()
        if not s:
            return True
        pen_val = int(float(s))
        if pen_val < 0 or pen_val > 255:
            from tkinter import messagebox
            messagebox.showerror("Invalid Pen", f"{label} must be between 0 and 255")
            return False
        return True

    def _on_ok(self):
        if not self._validate_pen("hatch1_pen", "Hatch 1 Pen"):
            return
        if not self._validate_pen("hatch2_pen", "Hatch 2 Pen"):
            return
        self._save_settings()
        self._result = self._settings
        self._dialog.destroy()
    
    def _on_cancel(self):
        self._result = None
        self._dialog.destroy()
    
    def _parse_float(self, var_name: str, default: float) -> float:
        val = self._vars.get(var_name)
        if val is None:
            return default
        s = val.get().strip()
        if not s:
            return default
        return float(s)
    
    def _parse_int(self, var_name: str, default: int) -> int:
        val = self._vars.get(var_name)
        if val is None:
            return default
        s = val.get().strip()
        if not s:
            return default
        return int(float(s))

    def _parse_pen(self, var_name: str, default: int) -> int:
        val = self._vars.get(var_name)
        if val is None:
            return default
        s = val.get().strip()
        if not s:
            return default
        pen_val = int(float(s))
        return max(0, min(255, pen_val))