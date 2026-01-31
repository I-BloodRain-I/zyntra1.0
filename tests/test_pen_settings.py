import pytest
import tempfile
import json
from unittest.mock import patch
from dataclasses import asdict
from src.canvas.pen_settings import PenSettings, PenSettingsDialog, PenCollection, PenManager


class TestPenSettings:
    def test_default_values(self):
        settings = PenSettings()
        assert settings.jump_speed == 4000.0
        assert settings.jump_position_tc == 500.0
        assert settings.jump_dist_tc == 100.0
        assert settings.end_compensate == 0.0
        assert settings.acc_distance == 0.0
        assert settings.time_per_point == 0.100
        assert settings.vector_point_mode is False
        assert settings.pulse_per_point == 1
        assert settings.yag_optimized_mode is False
        
    def test_enabled_and_color_defaults(self):
        settings = PenSettings()
        assert settings.enabled is True
        assert settings.color == "#000000"
        
    def test_wobble_defaults(self):
        settings = PenSettings()
        assert settings.wobble_enabled is False
        assert settings.wobble_diameter == 1.000
        assert settings.wobble_distance == 0.500
        
    def test_end_add_points_defaults(self):
        settings = PenSettings()
        assert settings.end_add_points_enabled is False
        assert settings.end_add_points_count == 1
        assert settings.end_add_points_distance == 0.010
        assert settings.end_add_points_time_per_point == 1.000
        assert settings.end_add_points_cycles == 1
        
    def test_laser_params_defaults(self):
        settings = PenSettings()
        assert settings.loop_count == 1
        assert settings.speed == 1600.0
        assert settings.power == 5.0
        assert settings.frequency == 30.0
        assert settings.start_tc == -200.0
        assert settings.laser_off_tc == 200.0
        assert settings.end_tc == 300.0
        assert settings.polygon_tc == 100.0
        
    def test_custom_values(self):
        settings = PenSettings(
            jump_speed=5000.0,
            power=10.0,
            wobble_enabled=True,
            wobble_diameter=2.0
        )
        assert settings.jump_speed == 5000.0
        assert settings.power == 10.0
        assert settings.wobble_enabled is True
        assert settings.wobble_diameter == 2.0
        
    def test_asdict_conversion(self):
        settings = PenSettings()
        data = asdict(settings)
        assert isinstance(data, dict)
        assert "jump_speed" in data
        assert "power" in data
        assert "wobble_enabled" in data
        assert data["jump_speed"] == 4000.0
    
    def test_hatch_defaults(self):
        settings = PenSettings()
        assert settings.hatch_enable_contour is True
        assert settings.hatch1_enabled is False
        assert settings.hatch2_enabled is False
        assert settings.hatch1_pen == 0
        assert settings.hatch2_pen == 0
        assert settings.hatch1_attrib == 0
        assert settings.hatch2_attrib == 0
        assert settings.hatch1_edge_dist == 0.0
        assert settings.hatch2_edge_dist == 0.0
        assert settings.hatch1_line_dist == 0.05
        assert settings.hatch2_line_dist == 0.05
        assert settings.hatch1_start_offset == 0.0
        assert settings.hatch2_start_offset == 0.0
        assert settings.hatch1_end_offset == 0.0
        assert settings.hatch2_end_offset == 0.0
        assert settings.hatch1_angle == 0.0
        assert settings.hatch2_angle == 90.0
        
    def test_hatch_custom_values(self):
        settings = PenSettings(
            hatch_enable_contour=False,
            hatch1_enabled=True,
            hatch1_pen=5,
            hatch1_line_dist=0.5,
            hatch1_angle=45.0
        )
        assert settings.hatch_enable_contour is False
        assert settings.hatch1_enabled is True
        assert settings.hatch1_pen == 5
        assert settings.hatch1_line_dist == 0.5
        assert settings.hatch1_angle == 45.0


class TestPenCollection:
    def test_collection_size(self):
        collection = PenCollection()
        assert len(collection) == 256
        
    def test_first_pen_enabled(self):
        collection = PenCollection()
        assert collection.get_pen(0).enabled is True
        
    def test_other_pens_disabled(self):
        collection = PenCollection()
        for i in range(1, 256):
            assert collection.get_pen(i).enabled is False
            
    def test_pen_colors_cycle(self):
        collection = PenCollection()
        assert collection.get_pen(0).color == "#000000"
        assert collection.get_pen(1).color == "#FF0000"
        assert collection.get_pen(16).color == "#000000"
        
    def test_get_set_pen(self):
        collection = PenCollection()
        pen = collection.get_pen(5)
        pen.speed = 3000.0
        collection.set_pen(5, pen)
        assert collection.get_pen(5).speed == 3000.0
        
    def test_copy_independence(self):
        collection = PenCollection()
        collection.get_pen(0).speed = 5000.0
        collection.set_pen(0, collection.get_pen(0))
        
        copy = collection.copy()
        copy.get_pen(0).speed = 1000.0
        copy.set_pen(0, copy.get_pen(0))
        
        assert collection.get_pen(0).speed == 5000.0
        assert copy.get_pen(0).speed == 1000.0


class TestPenSettingsDialog:
    def test_dialog_creation(self, root):
        dialog = PenSettingsDialog(root, None)
        assert dialog._pens is not None
        assert isinstance(dialog._pens, PenCollection)
        
    def test_dialog_with_custom_collection(self, root):
        collection = PenCollection()
        pen = collection.get_pen(0)
        pen.speed = 2000.0
        pen.power = 15.0
        collection.set_pen(0, pen)
        
        dialog = PenSettingsDialog(root, collection)
        assert dialog._pens.get_pen(0).speed == 2000.0
        assert dialog._pens.get_pen(0).power == 15.0


class TestPenManager:
    def test_reset(self, root):
        collection = PenCollection()
        pen = collection.get_pen(0)
        pen.speed = 9999.0
        pen.hatch1_enabled = True
        pen.hatch1_angle = 45.0
        collection.set_pen(0, pen)
        
        container = {"collection": collection}
        manager = PenManager(
            lambda: container["collection"],
            lambda c: container.__setitem__("collection", c)
        )
        
        with patch("src.canvas.pen_settings.messagebox.askyesno", return_value=True), \
             patch("src.canvas.pen_settings.messagebox.showinfo"):
            manager.reset(root)
        
        assert container["collection"].get_pen(0).speed == 1600.0
        assert container["collection"].get_pen(0).hatch1_enabled is False
        assert container["collection"].get_pen(0).hatch1_angle == 0.0
        
    def test_export_import_with_hatch(self, tmp_path, root):
        collection = PenCollection()
        pen = collection.get_pen(0)
        pen.speed = 5000.0
        pen.hatch_enable_contour = False
        pen.hatch1_enabled = True
        pen.hatch1_pen = 5
        pen.hatch1_line_dist = 0.25
        pen.hatch1_angle = 45.0
        pen.hatch2_enabled = True
        pen.hatch2_angle = 135.0
        collection.set_pen(0, pen)
        
        container = {"collection": collection}
        manager = PenManager(
            lambda: container["collection"],
            lambda c: container.__setitem__("collection", c)
        )
        file_path = str(tmp_path / "pens.json")
        
        with patch("src.canvas.pen_settings.filedialog.asksaveasfilename", return_value=file_path), \
             patch("src.canvas.pen_settings.messagebox.showinfo"):
            manager.export_to_file(root)
        
        new_collection = PenCollection()
        new_container = {"collection": new_collection}
        new_manager = PenManager(
            lambda: new_container["collection"],
            lambda c: new_container.__setitem__("collection", c)
        )
        
        with patch("src.canvas.pen_settings.filedialog.askopenfilename", return_value=file_path), \
             patch("src.canvas.pen_settings.messagebox.showinfo"):
            new_manager.import_from_file(root)
        
        imported_pen = new_container["collection"].get_pen(0)
        assert imported_pen.speed == 5000.0
        assert imported_pen.hatch_enable_contour is False
        assert imported_pen.hatch1_enabled is True
        assert imported_pen.hatch1_pen == 5
        assert imported_pen.hatch1_line_dist == 0.25
        assert imported_pen.hatch1_angle == 45.0
        assert imported_pen.hatch2_enabled is True
        assert imported_pen.hatch2_angle == 135.0


@pytest.fixture
def root():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()
