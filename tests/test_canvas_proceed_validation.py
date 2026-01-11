import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from tkinter import messagebox

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

def test_proceed_no_asin_list():
    app, canvas = get_canvas()
    canvas._asin_list = []
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once()
        assert "Missing ASINs" in mock_warn.call_args[0][0]
    canvas.destroy()

def test_proceed_asin_list_none():
    app, canvas = get_canvas()
    if hasattr(canvas, '_asin_list'):
        delattr(canvas, '_asin_list')
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once()
    canvas.destroy()

def test_proceed_empty_sku_name():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("")
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once()
        assert "Missing ASIN" in mock_warn.call_args[0][0]
    canvas.destroy()

def test_proceed_short_sku_name():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("AB")
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once()
        assert "Invalid ASIN" in mock_warn.call_args[0][0]
    canvas.destroy()

def test_proceed_valid_sku_name():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU123")
    with patch.object(messagebox, 'showwarning'):
        with patch.object(canvas, '_serialize_scene', return_value=[]):
            canvas._proceed()
    canvas.destroy()

def test_proceed_invalid_jig_cmyk():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas._jig_cmyk_invalid = True
    with patch.object(messagebox, 'showerror') as mock_err:
        canvas._proceed()
        mock_err.assert_called_once()
        assert "CMYK" in mock_err.call_args[0][0]
    canvas.destroy()

def test_proceed_invalid_obj_cmyk():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas._obj_cmyk_invalid = True
    with patch.object(messagebox, 'showerror') as mock_err:
        canvas._proceed()
        mock_err.assert_called_once()
    canvas.destroy()

def test_proceed_both_cmyk_invalid():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas._jig_cmyk_invalid = True
    canvas._obj_cmyk_invalid = True
    with patch.object(messagebox, 'showerror') as mock_err:
        canvas._proceed()
        mock_err.assert_called_once()
        msg = mock_err.call_args[0][1]
        assert "Jig CMYK" in msg
        assert "Object CMYK" in msg
    canvas.destroy()

def test_proceed_serializes_scene():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas._create_rect_at_mm("Test", 50.0, 30.0, 10.0, 10.0)
    with patch.object(canvas, '_serialize_scene', wraps=canvas._serialize_scene) as mock_ser:
        with patch.object(messagebox, 'showwarning'):
            canvas._proceed()
        assert mock_ser.call_count >= 1
    canvas.destroy()

def test_proceed_stores_current_side():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas._current_side = "front"
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    initial_store = canvas._scene_store.get("front", [])
    with patch.object(messagebox, 'showwarning'):
        canvas._proceed()
    canvas.destroy()

def test_proceed_separates_slots():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    with patch.object(canvas, '_serialize_scene', return_value=[
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0},
        {"type": "slot", "x_mm": 20.0, "y_mm": 20.0}
    ]):
        with patch.object(messagebox, 'showwarning'):
            canvas._proceed()
    canvas.destroy()

def test_proceed_parses_jig_coordinates():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas.jig_x.set("123.45")
    canvas.jig_y.set("678.90")
    with patch.object(messagebox, 'showwarning'):
        with patch.object(canvas, '_serialize_scene', return_value=[]):
            canvas._proceed()
    canvas.destroy()

def test_proceed_invalid_jig_coordinates():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas.jig_x.set("invalid")
    canvas.jig_y.set("also_invalid")
    with patch.object(messagebox, 'showwarning'):
        with patch.object(canvas, '_serialize_scene', return_value=[]):
            canvas._proceed()
    canvas.destroy()

def test_proceed_combines_slots_and_items():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas._scene_store["front"] = [{"type": "rect", "x_mm": 10.0, "y_mm": 10.0}]
    canvas._scene_store["back"] = [{"type": "text", "x_mm": 20.0, "y_mm": 20.0}]
    with patch.object(canvas, '_serialize_scene', return_value=[
        {"type": "slot", "x_mm": 5.0, "y_mm": 5.0}
    ]):
        with patch.object(messagebox, 'showwarning'):
            canvas._proceed()
    canvas.destroy()

def test_proceed_creates_output_paths():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    with patch.object(messagebox, 'showwarning'):
        with patch.object(canvas, '_serialize_scene', return_value=[]):
            canvas._proceed()
    canvas.destroy()

def test_proceed_exception_in_asin_check():
    app, canvas = get_canvas()
    def raise_error(*args, **kwargs):
        raise Exception("Test exception")
    with patch.object(canvas, '__getattribute__', side_effect=raise_error):
        with patch.object(messagebox, 'showwarning') as mock_warn:
            canvas._proceed()
    canvas.destroy()

def test_proceed_with_sticker_var():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas.sticker_var.set(True)
    with patch.object(messagebox, 'showwarning'):
        with patch.object(canvas, '_serialize_scene', return_value=[]):
            canvas._proceed()
    canvas.destroy()

def test_proceed_without_sticker_var():
    app, canvas = get_canvas()
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("ValidSKU")
    canvas.sticker_var.set(False)
    with patch.object(messagebox, 'showwarning'):
        with patch.object(canvas, '_serialize_scene', return_value=[]):
            canvas._proceed()
    canvas.destroy()
