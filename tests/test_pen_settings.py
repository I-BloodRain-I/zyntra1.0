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
        
    def test_wobble_defaults(self):
        settings = PenSettings()
        assert settings.wobble_enabled is False
        assert settings.wobble_diameter == 1.000
        assert settings.wobble_distance == 0.500
        
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


class TestPenCollection:
    def test_collection_size(self):
        collection = PenCollection()
        assert len(collection) == 256
        
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
        pen = collection.get_pen(42)
        pen.speed = 2000.0
        pen.power = 15.0
        collection.set_pen(42, pen)
        
        dialog = PenSettingsDialog(root, collection)
        assert dialog._pens.get_pen(42).speed == 2000.0
        assert dialog._pens.get_pen(42).power == 15.0


class TestPenManager:
    def test_reset(self, root):
        collection = PenCollection()
        pen = collection.get_pen(99)
        pen.speed = 9999.0
        collection.set_pen(99, pen)
        
        container = {"collection": collection}
        manager = PenManager(
            lambda: container["collection"],
            lambda c: container.__setitem__("collection", c)
        )
        
        with patch("src.canvas.pen_settings.messagebox.askyesno", return_value=True), \
             patch("src.canvas.pen_settings.messagebox.showinfo"):
            manager.reset(root)
        
        assert container["collection"].get_pen(99).speed == 1600.0
        
    def test_export_import(self, tmp_path, root):
        collection = PenCollection()
        pen = collection.get_pen(123)
        pen.speed = 5000.0
        collection.set_pen(123, pen)
        
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
        
        imported_pen = new_container["collection"].get_pen(123)
        assert imported_pen.speed == 5000.0


@pytest.fixture
def root():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()
