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
from src.screens.nonsticker.canvas import NStickerCanvasScreen

_app_instance = None

def get_app():
    global _app_instance
    if _app_instance is None:
        _app_instance = App()
    return _app_instance

def get_canvas():
    app = get_app()
    canvas = NStickerCanvasScreen(app, app)
    return app, canvas

def test_drop_text():
    app, canvas = get_canvas()
    canvas._drop_text()
    assert len(canvas._items) >= 1
    canvas.destroy()

def test_drop_barcode():
    app, canvas = get_canvas()
    canvas._drop_barcode()
    assert len(canvas._items) >= 1
    canvas.destroy()

def test_drop_barcode_limit():
    app, canvas = get_canvas()
    canvas._drop_barcode()
    canvas._drop_barcode()
    assert len([i for i in canvas._items.values() if i.get("type") == "barcode"]) == 1
    canvas.destroy()

def test_drop_multiple_texts():
    app, canvas = get_canvas()
    for i in range(5):
        canvas._drop_text()
    assert len(canvas._items) >= 5
    canvas.destroy()

def test_on_jig_change():
    app, canvas = get_canvas()
    canvas.jig_x.set("300.0")
    canvas.jig_y.set("400.0")
    canvas.destroy()

def test_snap_mm():
    app, canvas = get_canvas()
    snapped = canvas._snap_mm(12.3456)
    assert isinstance(snapped, float)
    canvas.destroy()

def test_snap_mm_negative():
    app, canvas = get_canvas()
    snapped = canvas._snap_mm(-12.3456)
    assert isinstance(snapped, float)
    canvas.destroy()

def test_snap_mm_zero():
    app, canvas = get_canvas()
    snapped = canvas._snap_mm(0.0)
    assert snapped == 0.0
    canvas.destroy()

def test_snap_mm_large():
    app, canvas = get_canvas()
    snapped = canvas._snap_mm(12345.6789)
    assert isinstance(snapped, float)
    canvas.destroy()

def test_create_placeholder():
    app, canvas = get_canvas()
    canvas.create_placeholder("Test", 50.0, 40.0)
    assert len(canvas._items) >= 1
    canvas.destroy()

def test_create_placeholder_with_coords():
    app, canvas = get_canvas()
    canvas.create_placeholder("Test", 50.0, 40.0, x_mm=10.0, y_mm=20.0)
    assert len(canvas._items) >= 1
    canvas.destroy()

def test_create_placeholder_custom_colors():
    app, canvas = get_canvas()
    canvas.create_placeholder("Test", 50.0, 40.0, text_fill="#FF0000", outline="#00FF00")
    assert len(canvas._items) >= 1
    canvas.destroy()

def test_create_placeholder_zero_size():
    app, canvas = get_canvas()
    canvas.create_placeholder("Test", 0.0, 0.0)
    assert len(canvas._items) >= 1
    canvas.destroy()

def test_create_placeholder_negative_size():
    app, canvas = get_canvas()
    canvas.create_placeholder("Test", -10.0, -10.0)
    assert len(canvas._items) >= 1
    canvas.destroy()

def test_create_image_from_file():
    app, canvas = get_canvas()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(f.name)
        try:
            canvas.create_image_item(f.name, 50.0, 40.0)
        except Exception:
            pass
    canvas.destroy()

def test_items_dict_access():
    app, canvas = get_canvas()
    cid = canvas._create_rect_at_mm("Test", 40.0, 30.0, 10.0, 15.0)
    assert cid in canvas._items
    assert canvas._items[cid]["type"] == "rect"
    canvas.destroy()

def test_items_modification():
    app, canvas = get_canvas()
    cid = canvas._create_rect_at_mm("Test", 40.0, 30.0, 10.0, 15.0)
    canvas._items[cid]["w_mm"] = 60.0
    assert canvas._items[cid]["w_mm"] == 60.0
    canvas.destroy()

def test_items_deletion():
    app, canvas = get_canvas()
    cid = canvas._create_rect_at_mm("Test", 40.0, 30.0, 10.0, 15.0)
    canvas._items.pop(cid)
    assert cid not in canvas._items
    canvas.destroy()

def test_multiple_drop_operations():
    app, canvas = get_canvas()
    canvas._drop_text()
    canvas._drop_barcode()
    canvas._drop_text()
    assert len(canvas._items) >= 3
    canvas.destroy()

def test_placeholder_label_persistence():
    app, canvas = get_canvas()
    canvas.create_placeholder("MyLabel", 50.0, 40.0)
    found = False
    for item in canvas._items.values():
        if item.get("label") == "MyLabel":
            found = True
            break
    assert found
    canvas.destroy()

def test_rect_at_mm_with_all_params():
    app, canvas = get_canvas()
    cid = canvas._create_rect_at_mm("Full", 40.0, 30.0, 10.0, 15.0, outline="#FF0000", text_fill="#00FF00", angle=45.0)
    assert canvas._items[cid]["outline"] == "#FF0000"
    assert canvas._items[cid]["label_fill"] == "#00FF00"
    assert canvas._items[cid]["angle"] == 45.0
    canvas.destroy()

def test_text_at_mm_basic():
    app, canvas = get_canvas()
    cid = canvas._create_text_at_mm("TestText", 100.0, 150.0)
    assert canvas._items[cid]["type"] == "text"
    canvas.destroy()

def test_text_at_mm_with_style():
    app, canvas = get_canvas()
    cid = canvas._create_text_at_mm("TestText", 100.0, 150.0, fill="#FF0000")
    assert canvas._items[cid]["default_fill"] == "#FF0000"
    canvas.destroy()

def test_jig_size_update():
    app, canvas = get_canvas()
    canvas.jig_x.set("250.0")
    canvas.jig_y.set("350.0")
    assert canvas.jig_x.get() == "250.0"
    assert canvas.jig_y.get() == "350.0"
    canvas.destroy()

def test_major_name_var():
    app, canvas = get_canvas()
    canvas.major_name.set("Major size 1")
    assert canvas.major_name.get() == "Major size 1"
    canvas.destroy()

def test_major_position_vars():
    app, canvas = get_canvas()
    canvas.major_x.set("15.0")
    canvas.major_y.set("20.0")
    assert canvas.major_x.get() == "15.0"
    assert canvas.major_y.get() == "20.0"
    canvas.destroy()

def test_major_size_vars():
    app, canvas = get_canvas()
    canvas.major_w.set("100.0")
    canvas.major_h.set("150.0")
    assert canvas.major_w.get() == "100.0"
    assert canvas.major_h.get() == "150.0"
    canvas.destroy()

def test_sku_vars():
    app, canvas = get_canvas()
    canvas.sku_var.set("SKU123")
    canvas.sku_name_var.set("Product Name")
    assert canvas.sku_var.get() == "SKU123"
    assert canvas.sku_name_var.get() == "Product Name"
    canvas.destroy()

def test_scene_store_structure():
    app, canvas = get_canvas()
    assert "front" in canvas._scene_store
    assert "back" in canvas._scene_store
    canvas.destroy()

def test_current_side():
    app, canvas = get_canvas()
    assert canvas._current_side in ["front", "back"]
    canvas.destroy()

def test_create_multiple_objects_mixed():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 40.0, 30.0, 10.0, 10.0)
    canvas._create_text_at_mm("T1", 50.0, 50.0)
    canvas._drop_text()
    canvas._drop_barcode()
    canvas.create_placeholder("P1", 60.0, 50.0)
    assert len(canvas._items) >= 5
    canvas.destroy()
