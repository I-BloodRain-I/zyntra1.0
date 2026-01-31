import os
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

_app_instance = None
_canvas_instance = None

def get_app():
    global _app_instance
    if _app_instance is None:
        _app_instance = App()
    return _app_instance

def get_canvas():
    global _canvas_instance
    app = get_app()
    if _canvas_instance is None:
        _canvas_instance = NStickerCanvasScreen(app, app)
    return app, _canvas_instance

# Basic initialization tests
def test_canvas_initialization():
    app, canvas = get_canvas()
    assert canvas.jig is not None
    assert canvas.slots is not None
    assert canvas.majors is not None
    canvas.destroy()

def test_jig_size_variables():
    app, canvas = get_canvas()
    canvas.jig_x.set("300.0")
    assert canvas.jig_x.get() == "300.0"
    canvas.destroy()

def test_major_size_variables():
    app, canvas = get_canvas()
    canvas.major_w.set("100.0")
    canvas.major_h.set("90.0")
    assert canvas.major_w.get() == "100.0"
    assert canvas.major_h.get() == "90.0"
    canvas.destroy()

def test_slot_size_variables():
    app, canvas = get_canvas()
    canvas.slot_w.set("45.0")
    canvas.slot_h.set("32.0")
    assert canvas.slot_w.get() == "45.0"
    assert canvas.slot_h.get() == "32.0"
    canvas.destroy()

def test_state_initialization():
    app, canvas = get_canvas()
    assert isinstance(canvas._items, dict)
    assert isinstance(canvas._majors, dict)
    assert isinstance(canvas._scene_store, dict)
    canvas.destroy()

def test_managers_exist():
    app, canvas = get_canvas()
    managers = ['jig', 'slots', 'majors', 'images', 'exporter', 'fonts', 'custom_images', 'selection']
    for manager in managers:
        assert hasattr(canvas, manager)
    canvas.destroy()

def test_delegates_exist():
    app, canvas = get_canvas()
    delegates = ['_scaled_pt', '_update_all_text_fonts', '_redraw_jig', '_zoom_step',
                '_rotated_bounds_px', '_rotated_bounds_mm', '_create_slot_at_mm']
    for delegate in delegates:
        assert hasattr(canvas, delegate)
        assert callable(getattr(canvas, delegate))
    canvas.destroy()

def test_pen_collection_exist():
    app, canvas = get_canvas()
    from src.canvas.pen_settings import PenCollection
    assert hasattr(canvas, '_pen_collection')
    assert isinstance(canvas._pen_collection, PenCollection)
    assert hasattr(canvas, '_open_pen_settings')
    assert callable(canvas._open_pen_settings)
    canvas.destroy()
