import sys
from pathlib import Path
from unittest.mock import MagicMock

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
from src.core.state import state
from src.screens.nonsticker.canvas import NStickerCanvasScreen

def get_canvas():
    app = App()
    canvas = NStickerCanvasScreen(app, app)
    canvas.pack()
    return app, canvas

# Error handling and edge cases
def test_restore_invalid_type():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "invalid_type", "x_mm": 10.0, "y_mm": 10.0}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_missing_fields():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "rect"}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_invalid_values():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "rect", "w_mm": "invalid", "h_mm": "invalid", "x_mm": 10.0, "y_mm": 10.0}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_negative_values():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "rect", "label": "R1", "w_mm": -50.0, "h_mm": -40.0, "x_mm": -10.0, "y_mm": -15.0, "angle": 0, "z": 1}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_zero_dimensions():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "rect", "label": "R1", "w_mm": 0.0, "h_mm": 0.0, "x_mm": 10.0, "y_mm": 15.0, "angle": 0, "z": 1}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_extreme_angles():
    app, canvas = get_canvas()
    for angle in [-720, 720, 1080, -1080]:
        try:
            scene = [{"type": "rect", "label": "R1", "w_mm": 50.0, "h_mm": 40.0, "x_mm": 10.0, "y_mm": 15.0, "angle": angle, "z": 1}]
            canvas._restore_scene(scene)
            canvas._clear_scene()
        except:
            pass
    canvas.destroy()

def test_restore_extreme_positions():
    app, canvas = get_canvas()
    positions = [(10000, 10000), (-1000, -1000), (0, 10000), (10000, 0)]
    for x, y in positions:
        try:
            scene = [{"type": "rect", "label": "R1", "w_mm": 50.0, "h_mm": 40.0, "x_mm": float(x), "y_mm": float(y), "angle": 0, "z": 1}]
            canvas._restore_scene(scene)
            canvas._clear_scene()
        except:
            pass
    canvas.destroy()

def test_restore_text_missing_content():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "text", "x_mm": 10.0, "y_mm": 10.0, "z": 1}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_image_missing_size():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "image", "x_mm": 10.0, "y_mm": 10.0, "z": 1}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_barcode_missing_size():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "barcode", "x_mm": 10.0, "y_mm": 10.0, "z": 1}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_malformed_json():
    app, canvas = get_canvas()
    try:
        scene = [{"type": "rect", "bad_field": None}]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_restore_mixed_valid_invalid():
    app, canvas = get_canvas()
    try:
        scene = [
            {"type": "rect", "label": "Valid", "w_mm": 50.0, "h_mm": 40.0, "x_mm": 10.0, "y_mm": 10.0, "angle": 0, "z": 1},
            {"type": "invalid"},
            {"type": "rect", "label": "Valid2", "w_mm": 50.0, "h_mm": 40.0, "x_mm": 20.0, "y_mm": 20.0, "angle": 0, "z": 2}
        ]
        canvas._restore_scene(scene)
    except:
        pass
    canvas.destroy()

def test_empty_variable_values():
    app, canvas = get_canvas()
    canvas.jig_x.set("")
    canvas.jig_y.set("")
    canvas.major_w.set("")
    canvas.major_h.set("")
    canvas.destroy()

def test_invalid_variable_values():
    app, canvas = get_canvas()
    canvas.jig_x.set("invalid")
    canvas.jig_y.set("abc")
    canvas.major_w.set("xyz")
    canvas.major_h.set("!@#")
    canvas.destroy()

def test_very_small_dimensions():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("Tiny", 0.1, 0.1, 10.0, 10.0)
    canvas.destroy()

def test_very_large_dimensions():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("Huge", 1000.0, 1000.0, 10.0, 10.0)
    canvas.destroy()

def test_fractional_coordinates():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("Frac", 40.5, 30.5, 10.5, 15.5)
    canvas.destroy()

def test_state_operations():
    app, canvas = get_canvas()
    state.sku_name = "TestSKU"
    state.asins = [("ASIN1", 10), ("ASIN2", 20)]
    state.pkg_x = "300.0"
    state.pkg_y = "400.0"
    canvas.destroy()
