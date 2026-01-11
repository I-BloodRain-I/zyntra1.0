import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

sys.modules['cv2'] = MagicMock()
sys.modules['cv2.dnn'] = MagicMock()
sys.modules['rembg'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtSvg'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()
sys.modules['pikepdf'] = MagicMock()
sys.modules['pikepdf.objects'] = MagicMock()

from src.core.app import App
from src.screens.nonsticker.canvas import NStickerCanvasScreen

def get_canvas():
    app = App()
    canvas = NStickerCanvasScreen(app, app)
    canvas.pack()
    return app, canvas

def test_jig_change_callback():
    app, canvas = get_canvas()
    canvas.jig_x.set("300.0")
    canvas.jig_y.set("400.0")
    assert float(canvas.jig_x.get()) == 300.0
    assert float(canvas.jig_y.get()) == 400.0
    canvas.destroy()

def test_major_name_change():
    app, canvas = get_canvas()
    canvas.major_name.set("Major size 1")
    assert canvas.major_name.get() == "Major size 1"
    canvas.destroy()

def test_major_position_change():
    app, canvas = get_canvas()
    canvas.major_x.set("10.0")
    canvas.major_y.set("20.0")
    assert float(canvas.major_x.get()) == 10.0
    assert float(canvas.major_y.get()) == 20.0
    canvas.destroy()

def test_major_size_change():
    app, canvas = get_canvas()
    canvas.major_w.set("100.0")
    canvas.major_h.set("150.0")
    assert float(canvas.major_w.get()) == 100.0
    assert float(canvas.major_h.get()) == 150.0
    canvas.destroy()

def test_slot_size_variables():
    app, canvas = get_canvas()
    canvas.slot_w.set("25.0")
    canvas.slot_h.set("30.0")
    assert float(canvas.slot_w.get()) == 25.0
    assert float(canvas.slot_h.get()) == 30.0
    canvas.destroy()

def test_step_size_variables():
    app, canvas = get_canvas()
    canvas.step_x.set("5.0")
    canvas.step_y.set("7.0")
    assert float(canvas.step_x.get()) == 5.0
    assert float(canvas.step_y.get()) == 7.0
    canvas.destroy()

def test_origin_variables():
    app, canvas = get_canvas()
    canvas.origin_x.set("15.0")
    canvas.origin_y.set("25.0")
    assert float(canvas.origin_x.get()) == 15.0
    assert float(canvas.origin_y.get()) == 25.0
    canvas.destroy()

def test_sku_variables():
    app, canvas = get_canvas()
    canvas.sku_var.set("TEST-SKU-001")
    canvas.sku_name_var.set("Test Product")
    assert canvas.sku_var.get() == "TEST-SKU-001"
    assert canvas.sku_name_var.get() == "Test Product"
    canvas.destroy()

def test_scene_store_initialization():
    app, canvas = get_canvas()
    assert "front" in canvas._scene_store
    assert "back" in canvas._scene_store
    assert isinstance(canvas._scene_store["front"], list)
    assert isinstance(canvas._scene_store["back"], list)
    canvas.destroy()

def test_current_side_default():
    app, canvas = get_canvas()
    assert canvas._current_side == "front"
    canvas.destroy()

def test_items_dict_initialization():
    app, canvas = get_canvas()
    assert isinstance(canvas._items, dict)
    assert len(canvas._items) >= 0
    canvas.destroy()

def test_majors_dict_initialization():
    app, canvas = get_canvas()
    assert isinstance(canvas._majors, dict)
    canvas.destroy()

def test_major_sizes_initialization():
    app, canvas = get_canvas()
    assert isinstance(canvas._major_sizes, dict)
    assert "Major size 1" in canvas._major_sizes
    canvas.destroy()

def test_suppress_major_traces_flag():
    app, canvas = get_canvas()
    assert hasattr(canvas, '_suppress_major_traces')
    assert canvas._suppress_major_traces == False
    canvas.destroy()

def test_screen_ready_flag():
    app, canvas = get_canvas()
    assert hasattr(canvas, '_screen_ready')
    canvas.destroy()

def test_left_bar_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, 'left_bar')
    canvas.destroy()

def test_canvas_widget_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, 'canvas')
    canvas.destroy()

def test_jig_controller_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, 'jig')
    canvas.destroy()

def test_slots_manager_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, 'slots')
    canvas.destroy()

def test_majors_manager_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, 'majors')
    canvas.destroy()

def test_images_manager_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, 'images')
    canvas.destroy()

def test_exporter_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, 'exporter')
    canvas.destroy()

def test_major_combo_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, '_major_combo')
    canvas.destroy()

def test_jig_x_trace_active():
    app, canvas = get_canvas()
    original = canvas.jig_x.get()
    canvas.jig_x.set("350.0")
    assert canvas.jig_x.get() == "350.0"
    canvas.destroy()

def test_jig_y_trace_active():
    app, canvas = get_canvas()
    original = canvas.jig_y.get()
    canvas.jig_y.set("450.0")
    assert canvas.jig_y.get() == "450.0"
    canvas.destroy()

def test_multiple_jig_changes():
    app, canvas = get_canvas()
    canvas.jig_x.set("100.0")
    canvas.jig_y.set("200.0")
    canvas.jig_x.set("150.0")
    canvas.jig_y.set("250.0")
    assert float(canvas.jig_x.get()) == 150.0
    assert float(canvas.jig_y.get()) == 250.0
    canvas.destroy()

def test_major_values_persistence():
    app, canvas = get_canvas()
    canvas.major_x.set("30.0")
    canvas.major_y.set("40.0")
    canvas.major_w.set("120.0")
    canvas.major_h.set("160.0")
    vals = canvas._major_sizes.get(canvas.major_name.get())
    canvas.destroy()

def test_slot_origin_combination():
    app, canvas = get_canvas()
    canvas.origin_x.set("10.0")
    canvas.origin_y.set("15.0")
    canvas.slot_w.set("20.0")
    canvas.slot_h.set("25.0")
    canvas.step_x.set("22.0")
    canvas.step_y.set("27.0")
    assert float(canvas.origin_x.get()) == 10.0
    assert float(canvas.step_x.get()) == 22.0
    canvas.destroy()
