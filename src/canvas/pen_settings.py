import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Callable
import copy
import json


DEFAULT_PEN_COLORS = [
    "#000000", "#FF0000", "#FFFF00", "#00FF00",
    "#00FFFF", "#0000FF", "#FF00FF", "#808080",
    "#800000", "#808000", "#008000", "#008080",
    "#000080", "#800080", "#C0C0C0", "#FFFFFF"
]


@dataclass
class PenSettings:
    enabled: bool = True
    color: str = "#000000"
    
    jump_speed: float = 4000.0
    jump_position_tc: float = 500.0
    jump_dist_tc: float = 100.0
    end_compensate: float = 0.0
    acc_distance: float = 0.0
    time_per_point: float = 0.100
    vector_point_mode: bool = False
    pulse_per_point: int = 1
    yag_optimized_mode: bool = False
    
    wobble_enabled: bool = False
    wobble_diameter: float = 1.000
    wobble_distance: float = 0.500
    
    end_add_points_enabled: bool = False
    end_add_points_count: int = 1
    end_add_points_distance: float = 0.010
    end_add_points_time_per_point: float = 1.000
    end_add_points_cycles: int = 1
    
    loop_count: int = 1
    speed: float = 1600.0
    power: float = 5.0
    frequency: float = 30.0
    start_tc: float = -200.0
    laser_off_tc: float = 200.0
    end_tc: float = 300.0
    polygon_tc: float = 100.0
    
    hatch_enable_contour: bool = True
    hatch_contour_first: bool = True
    
    hatch1_enabled: bool = False
    hatch1_pen: int = 0
    hatch1_attrib: int = 0
    hatch1_edge_dist: float = 0.0
    hatch1_line_dist: float = 0.05
    hatch1_start_offset: float = 0.0
    hatch1_end_offset: float = 0.0
    hatch1_angle: float = 0.0
    
    hatch2_enabled: bool = False
    hatch2_pen: int = 0
    hatch2_attrib: int = 0
    hatch2_edge_dist: float = 0.0
    hatch2_line_dist: float = 0.05
    hatch2_start_offset: float = 0.0
    hatch2_end_offset: float = 0.0
    hatch2_angle: float = 90.0


class PenCollection:
    TOTAL_PENS = 256
    
    def __init__(self):
        self._pens: List[PenSettings] = []
        for i in range(self.TOTAL_PENS):
            color = DEFAULT_PEN_COLORS[i % len(DEFAULT_PEN_COLORS)]
            self._pens.append(PenSettings(enabled=(i == 0), color=color))
    
    def get_pen(self, index: int) -> PenSettings:
        if 0 <= index < self.TOTAL_PENS:
            return self._pens[index]
        return PenSettings()
    
    def set_pen(self, index: int, settings: PenSettings):
        if 0 <= index < self.TOTAL_PENS:
            self._pens[index] = settings
    
    def copy(self) -> "PenCollection":
        new_collection = PenCollection.__new__(PenCollection)
        new_collection._pens = [copy.deepcopy(p) for p in self._pens]
        return new_collection
    
    def __len__(self) -> int:
        return self.TOTAL_PENS


class PenManager:
    def __init__(self, get_collection: Callable[[], PenCollection], set_collection: Callable[[PenCollection], None]):
        self._get_collection = get_collection
        self._set_collection = set_collection
    
    def reset(self, parent: tk.Widget):
        confirmed = messagebox.askyesno(
            "Reset Pens",
            "Are you sure you want to reset all pen settings to default values?\n\nThis action cannot be undone.",
            icon="warning",
            parent=parent
        )
        if confirmed:
            self._set_collection(PenCollection())
            messagebox.showinfo("Reset Complete", "All pen settings have been reset to default values.", parent=parent)
    
    def import_from_file(self, parent: tk.Widget):
        file_path = filedialog.askopenfilename(
            title="Import Pen Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=parent
        )
        if not file_path:
            return
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "pens" not in data or not isinstance(data["pens"], list):
            messagebox.showerror("Import Error", "The file is corrupted or has an invalid format.", parent=parent)
            return
        if len(data["pens"]) != PenCollection.TOTAL_PENS:
            messagebox.showerror("Import Error", "The file is corrupted or has an invalid format.", parent=parent)
            return
        new_collection = PenCollection()
        for i, pen_data in enumerate(data["pens"]):
            if not isinstance(pen_data, dict):
                messagebox.showerror("Import Error", "The file is corrupted or has an invalid format.", parent=parent)
                return
            pen = PenSettings(
                enabled=pen_data.get("enabled", False),
                color=pen_data.get("color", "#000000"),
                jump_speed=pen_data.get("jump_speed", 4000.0),
                jump_position_tc=pen_data.get("jump_position_tc", 500.0),
                jump_dist_tc=pen_data.get("jump_dist_tc", 100.0),
                end_compensate=pen_data.get("end_compensate", 0.0),
                acc_distance=pen_data.get("acc_distance", 0.0),
                time_per_point=pen_data.get("time_per_point", 0.1),
                vector_point_mode=pen_data.get("vector_point_mode", False),
                pulse_per_point=pen_data.get("pulse_per_point", 1),
                yag_optimized_mode=pen_data.get("yag_optimized_mode", False),
                wobble_enabled=pen_data.get("wobble_enabled", False),
                wobble_diameter=pen_data.get("wobble_diameter", 1.0),
                wobble_distance=pen_data.get("wobble_distance", 0.5),
                end_add_points_enabled=pen_data.get("end_add_points_enabled", False),
                end_add_points_count=pen_data.get("end_add_points_count", 1),
                end_add_points_distance=pen_data.get("end_add_points_distance", 0.01),
                end_add_points_time_per_point=pen_data.get("end_add_points_time_per_point", 1.0),
                end_add_points_cycles=pen_data.get("end_add_points_cycles", 1),
                loop_count=pen_data.get("loop_count", 1),
                speed=pen_data.get("speed", 1600.0),
                power=pen_data.get("power", 5.0),
                frequency=pen_data.get("frequency", 30.0),
                start_tc=pen_data.get("start_tc", -200.0),
                laser_off_tc=pen_data.get("laser_off_tc", 200.0),
                end_tc=pen_data.get("end_tc", 300.0),
                polygon_tc=pen_data.get("polygon_tc", 100.0),
                hatch_enable_contour=pen_data.get("hatch_enable_contour", True),
                hatch_contour_first=pen_data.get("hatch_contour_first", True),
                hatch1_enabled=pen_data.get("hatch1_enabled", False),
                hatch1_pen=pen_data.get("hatch1_pen", 0),
                hatch1_attrib=pen_data.get("hatch1_attrib", 0),
                hatch1_edge_dist=pen_data.get("hatch1_edge_dist", 0.0),
                hatch1_line_dist=pen_data.get("hatch1_line_dist", 0.05),
                hatch1_start_offset=pen_data.get("hatch1_start_offset", 0.0),
                hatch1_end_offset=pen_data.get("hatch1_end_offset", 0.0),
                hatch1_angle=pen_data.get("hatch1_angle", 0.0),
                hatch2_enabled=pen_data.get("hatch2_enabled", False),
                hatch2_pen=pen_data.get("hatch2_pen", 0),
                hatch2_attrib=pen_data.get("hatch2_attrib", 0),
                hatch2_edge_dist=pen_data.get("hatch2_edge_dist", 0.0),
                hatch2_line_dist=pen_data.get("hatch2_line_dist", 0.05),
                hatch2_start_offset=pen_data.get("hatch2_start_offset", 0.0),
                hatch2_end_offset=pen_data.get("hatch2_end_offset", 0.0),
                hatch2_angle=pen_data.get("hatch2_angle", 90.0),
            )
            new_collection.set_pen(i, pen)
        self._set_collection(new_collection)
        messagebox.showinfo("Import Complete", "Pen settings have been imported successfully.", parent=parent)
    
    def export_to_file(self, parent: tk.Widget):
        file_path = filedialog.asksaveasfilename(
            title="Export Pen Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=parent
        )
        if not file_path:
            return
        collection = self._get_collection()
        pens_data = []
        for i in range(PenCollection.TOTAL_PENS):
            pen = collection.get_pen(i)
            pens_data.append({
                "enabled": pen.enabled,
                "color": pen.color,
                "jump_speed": pen.jump_speed,
                "jump_position_tc": pen.jump_position_tc,
                "jump_dist_tc": pen.jump_dist_tc,
                "end_compensate": pen.end_compensate,
                "acc_distance": pen.acc_distance,
                "time_per_point": pen.time_per_point,
                "vector_point_mode": pen.vector_point_mode,
                "pulse_per_point": pen.pulse_per_point,
                "yag_optimized_mode": pen.yag_optimized_mode,
                "wobble_enabled": pen.wobble_enabled,
                "wobble_diameter": pen.wobble_diameter,
                "wobble_distance": pen.wobble_distance,
                "end_add_points_enabled": pen.end_add_points_enabled,
                "end_add_points_count": pen.end_add_points_count,
                "end_add_points_distance": pen.end_add_points_distance,
                "end_add_points_time_per_point": pen.end_add_points_time_per_point,
                "end_add_points_cycles": pen.end_add_points_cycles,
                "loop_count": pen.loop_count,
                "speed": pen.speed,
                "power": pen.power,
                "frequency": pen.frequency,
                "start_tc": pen.start_tc,
                "laser_off_tc": pen.laser_off_tc,
                "end_tc": pen.end_tc,
                "polygon_tc": pen.polygon_tc,
                "hatch_enable_contour": pen.hatch_enable_contour,
                "hatch_contour_first": pen.hatch_contour_first,
                "hatch1_enabled": pen.hatch1_enabled,
                "hatch1_pen": pen.hatch1_pen,
                "hatch1_attrib": pen.hatch1_attrib,
                "hatch1_edge_dist": pen.hatch1_edge_dist,
                "hatch1_line_dist": pen.hatch1_line_dist,
                "hatch1_start_offset": pen.hatch1_start_offset,
                "hatch1_end_offset": pen.hatch1_end_offset,
                "hatch1_angle": pen.hatch1_angle,
                "hatch2_enabled": pen.hatch2_enabled,
                "hatch2_pen": pen.hatch2_pen,
                "hatch2_attrib": pen.hatch2_attrib,
                "hatch2_edge_dist": pen.hatch2_edge_dist,
                "hatch2_line_dist": pen.hatch2_line_dist,
                "hatch2_start_offset": pen.hatch2_start_offset,
                "hatch2_end_offset": pen.hatch2_end_offset,
                "hatch2_angle": pen.hatch2_angle,
            })
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"pens": pens_data}, f, separators=(",", ":"))
        messagebox.showinfo("Export Complete", "Pen settings have been exported successfully.", parent=parent)


class PenSettingsDialog:
    def __init__(self, parent: tk.Widget, pens: Optional[PenCollection] = None):
        self._parent = parent
        self._pens = pens.copy() if pens else PenCollection()
        self._result: Optional[PenCollection] = None
        self._vars: dict = {}
        self._current_pen_index: int = 0
        self._settings_widgets: list = []
        self._settings_frame: Optional[tk.Frame] = None
        self._hatch_widgets: dict = {}
        
    def show(self) -> Optional[PenCollection]:
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Marking parameter")
        self._dialog.configure(bg="#f0f0f0")
        self._dialog.resizable(False, False)
        
        self._dialog.attributes("-topmost", True)
        
        parent_x = self._parent.winfo_rootx()
        parent_y = self._parent.winfo_rooty()
        self._dialog.geometry(f"+{parent_x + 50}+{parent_y + 50}")
        
        self._create_widgets()
        
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._parent.wait_window(self._dialog)
        
        return self._result
    
    def _create_widgets(self):
        main_frame = tk.Frame(self._dialog, bg="#f0f0f0")
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        left_frame = tk.Frame(main_frame, bg="#f0f0f0")
        left_frame.pack(side="left", anchor="n", padx=5, fill="y")
        
        self._create_pen_list(left_frame)
        
        separator = tk.Frame(main_frame, bg="#999999", width=2)
        separator.pack(side="left", fill="y", padx=10)
        
        right_frame = tk.Frame(main_frame, bg="#f0f0f0")
        right_frame.pack(side="left", anchor="n", padx=5, fill="both", expand=True)
        
        self._settings_frame = right_frame
        self._create_settings_section(right_frame)
        
        btn_frame = tk.Frame(self._dialog, bg="#f0f0f0")
        btn_frame.pack(pady=10)
        
        ok_btn = tk.Button(btn_frame, text="OK", width=10, command=self._on_ok)
        ok_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", width=10, command=self._on_cancel)
        cancel_btn.pack(side="left", padx=5)
        
        self._select_pen(0, save_current=False)
    
    def _create_pen_list(self, parent):
        header_frame = tk.Frame(parent, bg="#f0f0f0")
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="Pen", bg="#f0f0f0", width=5, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(header_frame, text="Color", bg="#f0f0f0", width=6, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(header_frame, text="On/Off", bg="#f0f0f0", width=6, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
        
        list_container = tk.Frame(parent, bg="#f0f0f0")
        list_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(list_container, bg="white", width=150, height=300, highlightthickness=1, highlightbackground="#999999")
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        
        self._pen_list_frame = tk.Frame(canvas, bg="white")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        canvas_window = canvas.create_window((0, 0), window=self._pen_list_frame, anchor="nw")
        
        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        
        self._pen_list_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        def on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        self._pen_rows = []
        for i in range(PenCollection.TOTAL_PENS):
            self._create_pen_row(i)
    
    def _create_pen_row(self, index: int):
        pen = self._pens.get_pen(index)
        
        row_frame = tk.Frame(self._pen_list_frame, bg="white", cursor="hand2")
        row_frame.pack(fill="x", padx=2, pady=1)
        
        id_label = tk.Label(row_frame, text=str(index), bg="white", width=4, anchor="w", font=("Segoe UI", 9))
        id_label.pack(side="left", padx=2)
        
        color_frame = tk.Frame(row_frame, bg=pen.color, width=20, height=16, 
                               highlightbackground="#999999", highlightthickness=1)
        color_frame.pack(side="left", padx=4, pady=2)
        color_frame.pack_propagate(False)
        
        cb_container = tk.Frame(row_frame, bg="white")
        cb_container.pack(side="left", fill="x", expand=True)
        
        enabled_var = tk.BooleanVar(value=pen.enabled)
        enabled_cb = tk.Checkbutton(cb_container, variable=enabled_var, bg="white",
                                     command=lambda idx=index, var=enabled_var: self._on_pen_enabled_change(idx, var))
        enabled_cb.pack(anchor="center")
        
        def on_row_click(e, idx=index):
            self._select_pen(idx)
        
        def on_color_click(e, idx=index, cf=color_frame):
            self._change_pen_color(idx, cf)
        
        row_frame.bind("<Button-1>", on_row_click)
        id_label.bind("<Button-1>", on_row_click)
        color_frame.bind("<Button-1>", on_color_click)
        cb_container.bind("<Button-1>", on_row_click)
        
        self._pen_rows.append({
            "frame": row_frame,
            "id_label": id_label,
            "color_frame": color_frame,
            "enabled_var": enabled_var,
            "enabled_cb": enabled_cb
        })
    
    def _select_pen(self, index: int, save_current: bool = True):
        if save_current:
            self._save_current_pen_settings()
        
        for i, row in enumerate(self._pen_rows):
            if i == index:
                row["frame"].configure(bg="#cce5ff")
                row["id_label"].configure(bg="#cce5ff")
            else:
                row["frame"].configure(bg="white")
                row["id_label"].configure(bg="white")
        
        self._current_pen_index = index
        self._load_pen_settings(index)
    
    def _on_pen_enabled_change(self, index: int, var: tk.BooleanVar):
        pen = self._pens.get_pen(index)
        pen.enabled = var.get()
        self._pens.set_pen(index, pen)
        
        if index == self._current_pen_index:
            self._update_settings_state()
    
    def _change_pen_color(self, index: int, color_frame: tk.Frame):
        pen = self._pens.get_pen(index)
        color = colorchooser.askcolor(color=pen.color, title=f"Choose color for Pen {index}")
        if color[1]:
            pen.color = color[1]
            self._pens.set_pen(index, pen)
            color_frame.configure(bg=color[1])
    
    def _create_settings_section(self, parent):
        top_frame = tk.Frame(parent, bg="#f0f0f0")
        top_frame.pack(fill="x", pady=(0, 10))
        
        settings_container = tk.Frame(parent, bg="#f0f0f0")
        settings_container.pack(fill="both", expand=True)
        
        right_col = tk.Frame(settings_container, bg="#f0f0f0")
        right_col.pack(side="left", anchor="n", padx=5)
        
        self._create_right_settings(right_col)
        
        sep1 = tk.Frame(settings_container, bg="#999999", width=1)
        sep1.pack(side="left", fill="y", padx=8)
        
        left_col = tk.Frame(settings_container, bg="#f0f0f0")
        left_col.pack(side="left", anchor="n", padx=5)
        
        self._create_left_settings(left_col)
        
        sep2 = tk.Frame(settings_container, bg="#999999", width=1)
        sep2.pack(side="left", fill="y", padx=8)
        
        middle_col = tk.Frame(settings_container, bg="#f0f0f0")
        middle_col.pack(side="left", anchor="n", padx=5)
        
        self._create_middle_settings(middle_col)
        
        sep3 = tk.Frame(settings_container, bg="#999999", width=1)
        sep3.pack(side="left", fill="y", padx=8)
        
        hatch_col = tk.Frame(settings_container, bg="#f0f0f0")
        hatch_col.pack(side="left", anchor="n", padx=5)
        
        self._create_hatch_settings(hatch_col)
    
    def _create_left_settings(self, parent):
        row = 0
        self._create_labeled_entry(parent, "Jump Speed", "jump_speed", 4000.0, "MM/Sec", row)
        row += 1
        self._create_labeled_entry(parent, "Jump Position TC", "jump_position_tc", 500.0, "US", row)
        row += 1
        self._create_labeled_entry(parent, "Jump Dist TC", "jump_dist_tc", 100.0, "US", row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_labeled_entry(parent, "End compensate", "end_compensate", 0.0, "MM", row)
        row += 1
        self._create_labeled_entry(parent, "Acc. Distance", "acc_distance", 0.0, "MM", row)
        row += 1
        self._create_labeled_entry(parent, "Time per point", "time_per_point", 0.100, "ms", row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_checkbox(parent, "Vector point mode", "vector_point_mode", False, row)
        row += 1
        self._create_labeled_entry(parent, "Pulse per point", "pulse_per_point", 1, "", row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_checkbox(parent, "Yag Optimized mode", "yag_optimized_mode", False, row)
    
    def _create_middle_settings(self, parent):
        row = 0
        self._create_checkbox(parent, "Wobble", "wobble_enabled", False, row)
        row += 1
        self._create_labeled_entry(parent, "Diameter", "wobble_diameter", 1.000, "MM", row)
        row += 1
        self._create_labeled_entry(parent, "Distance", "wobble_distance", 0.500, "MM", row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_checkbox(parent, "End Add Points", "end_add_points_enabled", False, row)
        row += 1
        self._create_labeled_entry(parent, "Count", "end_add_points_count", 1, "", row)
        row += 1
        self._create_labeled_entry(parent, "Distance", "end_add_points_distance", 0.010, "MM", row)
        row += 1
        self._create_labeled_entry(parent, "Time per point", "end_add_points_time_per_point", 1.000, "ms", row)
        row += 1
        self._create_labeled_entry(parent, "Point Cycles", "end_add_points_cycles", 1, "", row)
    
    def _create_hatch_settings(self, parent):
        row = 0
        self._create_checkbox(parent, "Enable Contour", "hatch_enable_contour", True, row)
        self._vars["hatch_enable_contour"].trace_add("write", lambda *_: self._update_hatch_state())
        row += 1
        self._hatch_widgets["contour_first"] = self._create_checkbox(parent, "Contour First", "hatch_contour_first", True, row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_checkbox(parent, "Hatch 1", "hatch1_enabled", False, row)
        self._vars["hatch1_enabled"].trace_add("write", lambda *_: self._update_hatch_state())
        row += 1
        self._hatch_widgets["hatch1_pen"] = self._create_labeled_entry(parent, "Pen", "hatch1_pen", 0, "", row)
        row += 1
        self._hatch_widgets["hatch1_attrib"] = self._create_labeled_entry(parent, "Attrib", "hatch1_attrib", 0, "", row)
        row += 1
        self._hatch_widgets["hatch1_edge_dist"] = self._create_labeled_entry(parent, "Edge Dist", "hatch1_edge_dist", 0.0, "MM", row)
        row += 1
        self._hatch_widgets["hatch1_line_dist"] = self._create_labeled_entry(parent, "Line Dist", "hatch1_line_dist", 0.05, "MM", row)
        row += 1
        self._hatch_widgets["hatch1_start_offset"] = self._create_labeled_entry(parent, "Start Offset", "hatch1_start_offset", 0.0, "MM", row)
        row += 1
        self._hatch_widgets["hatch1_end_offset"] = self._create_labeled_entry(parent, "End Offset", "hatch1_end_offset", 0.0, "MM", row)
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
        self._hatch_widgets["hatch2_attrib"] = self._create_labeled_entry(parent, "Attrib", "hatch2_attrib", 0, "", row)
        row += 1
        self._hatch_widgets["hatch2_edge_dist"] = self._create_labeled_entry(parent, "Edge Dist", "hatch2_edge_dist", 0.0, "MM", row)
        row += 1
        self._hatch_widgets["hatch2_line_dist"] = self._create_labeled_entry(parent, "Line Dist", "hatch2_line_dist", 0.05, "MM", row)
        row += 1
        self._hatch_widgets["hatch2_start_offset"] = self._create_labeled_entry(parent, "Start Offset", "hatch2_start_offset", 0.0, "MM", row)
        row += 1
        self._hatch_widgets["hatch2_end_offset"] = self._create_labeled_entry(parent, "End Offset", "hatch2_end_offset", 0.0, "MM", row)
        row += 1
        self._hatch_widgets["hatch2_angle"] = self._create_labeled_entry(parent, "Angle", "hatch2_angle", 90.0, "°", row)
        
        self._update_hatch_state()
    
    def _create_right_settings(self, parent):
        row = 0
        self._create_labeled_entry(parent, "Loop Count", "loop_count", 1, "", row)
        row += 1
        self._create_labeled_entry(parent, "Speed(MM/Second)", "speed", 1600.0, "", row)
        row += 1
        self._create_labeled_entry(parent, "Power(%)", "power", 5.0, "", row)
        row += 1
        self._create_labeled_entry(parent, "Frequency(KHz)", "frequency", 30.0, "", row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
        row += 1
        
        self._create_labeled_entry(parent, "Start TC(US)", "start_tc", -200.0, "", row)
        row += 1
        self._create_labeled_entry(parent, "Laser Off TC(US)", "laser_off_tc", 200.0, "", row)
        row += 1
        self._create_labeled_entry(parent, "End TC(US)", "end_tc", 300.0, "", row)
        row += 1
        self._create_labeled_entry(parent, "Polygon TC(US)", "polygon_tc", 100.0, "", row)
        row += 1
        
        tk.Frame(parent, height=10, bg="#f0f0f0").grid(row=row, column=0, columnspan=3)
    
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
        
        widget_info = {"type": "entry", "label": lbl, "widget": entry, "unit": unit_lbl, "var": var, "name": var_name}
        self._settings_widgets.append(widget_info)
        return widget_info
    
    def _create_checkbox(self, parent, label: str, var_name: str, default_value: bool, row: int = 0):
        var = tk.BooleanVar(value=default_value)
        self._vars[var_name] = var
        
        cb = tk.Checkbutton(parent, text=label, variable=var, bg="#f0f0f0")
        cb.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        
        widget_info = {"type": "checkbox", "widget": cb, "var": var, "name": var_name}
        self._settings_widgets.append(widget_info)
        return widget_info
    
    def _update_hatch_state(self):
        if not self._hatch_widgets:
            return
        
        pen = self._pens.get_pen(self._current_pen_index)
        pen_enabled = pen.enabled
        
        contour_enabled = self._vars.get("hatch_enable_contour", tk.BooleanVar(value=True)).get()
        hatch1_enabled = self._vars.get("hatch1_enabled", tk.BooleanVar(value=False)).get()
        hatch2_enabled = self._vars.get("hatch2_enabled", tk.BooleanVar(value=False)).get()
        
        contour_first = self._hatch_widgets.get("contour_first")
        if contour_first:
            state = "normal" if (pen_enabled and contour_enabled) else "disabled"
            contour_first["widget"].configure(state=state)
        
        hatch1_fields = ["hatch1_pen", "hatch1_attrib", "hatch1_edge_dist", "hatch1_line_dist", 
                         "hatch1_start_offset", "hatch1_end_offset", "hatch1_angle"]
        for field in hatch1_fields:
            widget_info = self._hatch_widgets.get(field)
            if widget_info:
                state = "normal" if (pen_enabled and hatch1_enabled) else "disabled"
                widget_info["widget"].configure(state=state)
                if widget_info.get("label"):
                    widget_info["label"].configure(state=state)
        
        hatch2_fields = ["hatch2_pen", "hatch2_attrib", "hatch2_edge_dist", "hatch2_line_dist", 
                         "hatch2_start_offset", "hatch2_end_offset", "hatch2_angle"]
        for field in hatch2_fields:
            widget_info = self._hatch_widgets.get(field)
            if widget_info:
                state = "normal" if (pen_enabled and hatch2_enabled) else "disabled"
                widget_info["widget"].configure(state=state)
                if widget_info.get("label"):
                    widget_info["label"].configure(state=state)
    
    def _load_pen_settings(self, index: int):
        pen = self._pens.get_pen(index)
        
        self._vars["jump_speed"].set(str(pen.jump_speed))
        self._vars["jump_position_tc"].set(str(pen.jump_position_tc))
        self._vars["jump_dist_tc"].set(str(pen.jump_dist_tc))
        self._vars["end_compensate"].set(str(pen.end_compensate))
        self._vars["acc_distance"].set(str(pen.acc_distance))
        self._vars["time_per_point"].set(str(pen.time_per_point))
        self._vars["vector_point_mode"].set(pen.vector_point_mode)
        self._vars["pulse_per_point"].set(str(pen.pulse_per_point))
        self._vars["yag_optimized_mode"].set(pen.yag_optimized_mode)
        
        self._vars["wobble_enabled"].set(pen.wobble_enabled)
        self._vars["wobble_diameter"].set(str(pen.wobble_diameter))
        self._vars["wobble_distance"].set(str(pen.wobble_distance))
        
        self._vars["end_add_points_enabled"].set(pen.end_add_points_enabled)
        self._vars["end_add_points_count"].set(str(pen.end_add_points_count))
        self._vars["end_add_points_distance"].set(str(pen.end_add_points_distance))
        self._vars["end_add_points_time_per_point"].set(str(pen.end_add_points_time_per_point))
        self._vars["end_add_points_cycles"].set(str(pen.end_add_points_cycles))
        
        self._vars["loop_count"].set(str(pen.loop_count))
        self._vars["speed"].set(str(pen.speed))
        self._vars["power"].set(str(pen.power))
        self._vars["frequency"].set(str(pen.frequency))
        self._vars["start_tc"].set(str(pen.start_tc))
        self._vars["laser_off_tc"].set(str(pen.laser_off_tc))
        self._vars["end_tc"].set(str(pen.end_tc))
        self._vars["polygon_tc"].set(str(pen.polygon_tc))
        
        self._vars["hatch_enable_contour"].set(pen.hatch_enable_contour)
        self._vars["hatch_contour_first"].set(pen.hatch_contour_first)
        self._vars["hatch1_enabled"].set(pen.hatch1_enabled)
        self._vars["hatch1_pen"].set(str(pen.hatch1_pen))
        self._vars["hatch1_attrib"].set(str(pen.hatch1_attrib))
        self._vars["hatch1_edge_dist"].set(str(pen.hatch1_edge_dist))
        self._vars["hatch1_line_dist"].set(str(pen.hatch1_line_dist))
        self._vars["hatch1_start_offset"].set(str(pen.hatch1_start_offset))
        self._vars["hatch1_end_offset"].set(str(pen.hatch1_end_offset))
        self._vars["hatch1_angle"].set(str(pen.hatch1_angle))
        self._vars["hatch2_enabled"].set(pen.hatch2_enabled)
        self._vars["hatch2_pen"].set(str(pen.hatch2_pen))
        self._vars["hatch2_attrib"].set(str(pen.hatch2_attrib))
        self._vars["hatch2_edge_dist"].set(str(pen.hatch2_edge_dist))
        self._vars["hatch2_line_dist"].set(str(pen.hatch2_line_dist))
        self._vars["hatch2_start_offset"].set(str(pen.hatch2_start_offset))
        self._vars["hatch2_end_offset"].set(str(pen.hatch2_end_offset))
        self._vars["hatch2_angle"].set(str(pen.hatch2_angle))
        
        self._update_settings_state()
        self._update_hatch_state()
    
    def _save_current_pen_settings(self):
        if not self._vars:
            return
        
        pen = self._pens.get_pen(self._current_pen_index)
        
        pen.jump_speed = self._parse_float("jump_speed", pen.jump_speed)
        pen.jump_position_tc = self._parse_float("jump_position_tc", pen.jump_position_tc)
        pen.jump_dist_tc = self._parse_float("jump_dist_tc", pen.jump_dist_tc)
        pen.end_compensate = self._parse_float("end_compensate", pen.end_compensate)
        pen.acc_distance = self._parse_float("acc_distance", pen.acc_distance)
        pen.time_per_point = self._parse_float("time_per_point", pen.time_per_point)
        pen.vector_point_mode = self._vars["vector_point_mode"].get()
        pen.pulse_per_point = self._parse_int("pulse_per_point", pen.pulse_per_point)
        pen.yag_optimized_mode = self._vars["yag_optimized_mode"].get()
        
        pen.wobble_enabled = self._vars["wobble_enabled"].get()
        pen.wobble_diameter = self._parse_float("wobble_diameter", pen.wobble_diameter)
        pen.wobble_distance = self._parse_float("wobble_distance", pen.wobble_distance)
        
        pen.end_add_points_enabled = self._vars["end_add_points_enabled"].get()
        pen.end_add_points_count = self._parse_int("end_add_points_count", pen.end_add_points_count)
        pen.end_add_points_distance = self._parse_float("end_add_points_distance", pen.end_add_points_distance)
        pen.end_add_points_time_per_point = self._parse_float("end_add_points_time_per_point", pen.end_add_points_time_per_point)
        pen.end_add_points_cycles = self._parse_int("end_add_points_cycles", pen.end_add_points_cycles)
        
        pen.loop_count = self._parse_int("loop_count", pen.loop_count)
        pen.speed = self._parse_float("speed", pen.speed)
        pen.power = self._parse_float("power", pen.power)
        pen.frequency = self._parse_float("frequency", pen.frequency)
        pen.start_tc = self._parse_float("start_tc", pen.start_tc)
        pen.laser_off_tc = self._parse_float("laser_off_tc", pen.laser_off_tc)
        pen.end_tc = self._parse_float("end_tc", pen.end_tc)
        pen.polygon_tc = self._parse_float("polygon_tc", pen.polygon_tc)
        
        pen.hatch_enable_contour = self._vars["hatch_enable_contour"].get()
        pen.hatch_contour_first = self._vars["hatch_contour_first"].get()
        pen.hatch1_enabled = self._vars["hatch1_enabled"].get()
        pen.hatch1_pen = self._parse_int("hatch1_pen", pen.hatch1_pen)
        pen.hatch1_attrib = self._parse_int("hatch1_attrib", pen.hatch1_attrib)
        pen.hatch1_edge_dist = self._parse_float("hatch1_edge_dist", pen.hatch1_edge_dist)
        pen.hatch1_line_dist = self._parse_float("hatch1_line_dist", pen.hatch1_line_dist)
        pen.hatch1_start_offset = self._parse_float("hatch1_start_offset", pen.hatch1_start_offset)
        pen.hatch1_end_offset = self._parse_float("hatch1_end_offset", pen.hatch1_end_offset)
        pen.hatch1_angle = self._parse_float("hatch1_angle", pen.hatch1_angle)
        pen.hatch2_enabled = self._vars["hatch2_enabled"].get()
        pen.hatch2_pen = self._parse_int("hatch2_pen", pen.hatch2_pen)
        pen.hatch2_attrib = self._parse_int("hatch2_attrib", pen.hatch2_attrib)
        pen.hatch2_edge_dist = self._parse_float("hatch2_edge_dist", pen.hatch2_edge_dist)
        pen.hatch2_line_dist = self._parse_float("hatch2_line_dist", pen.hatch2_line_dist)
        pen.hatch2_start_offset = self._parse_float("hatch2_start_offset", pen.hatch2_start_offset)
        pen.hatch2_end_offset = self._parse_float("hatch2_end_offset", pen.hatch2_end_offset)
        pen.hatch2_angle = self._parse_float("hatch2_angle", pen.hatch2_angle)
        
        self._pens.set_pen(self._current_pen_index, pen)
    
    def _update_settings_state(self):
        pen = self._pens.get_pen(self._current_pen_index)
        state = "normal" if pen.enabled else "disabled"
        
        for item in self._settings_widgets:
            widget = item["widget"]
            if item["type"] == "entry":
                widget.configure(state=state)
            elif item["type"] == "checkbox":
                widget.configure(state=state)
    
    def _on_ok(self):
        self._save_current_pen_settings()
        self._result = self._pens
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
