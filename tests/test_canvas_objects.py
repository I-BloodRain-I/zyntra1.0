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

def get_canvas():
    app = App()
    canvas = NStickerCanvasScreen(app, app)
    canvas.pack()
    return app, canvas

# Object creation tests
def test_create_single_rect():
    app, canvas = get_canvas()
    cid = canvas._create_rect_at_mm("Test1", 50.0, 40.0, 10.0, 15.0)
    assert cid in canvas._items
    canvas.destroy()

def test_create_single_text():
    app, canvas = get_canvas()
    cid = canvas._create_text_at_mm("TestText", 20.0, 25.0)
    assert cid in canvas._items
    canvas.destroy()

def test_create_multiple_rects():
    app, canvas = get_canvas()
    for i in range(20):
        cid = canvas._create_rect_at_mm(f"Rect{i}", 40.0, 30.0, float(i*50), float(i*40))
        assert cid in canvas._items
    canvas.destroy()

def test_create_multiple_texts():
    app, canvas = get_canvas()
    for i in range(20):
        cid = canvas._create_text_at_mm(f"Text{i}", float(i*50), float(i*40))
        assert cid in canvas._items
    canvas.destroy()

def test_create_with_angle():
    app, canvas = get_canvas()
    cid = canvas._create_rect_at_mm("Rotated", 40.0, 30.0, 10.0, 15.0, angle=45.0)
    assert canvas._items[cid].get('angle') == 45.0
    canvas.destroy()

def test_create_with_colors():
    app, canvas = get_canvas()
    cid = canvas._create_rect_at_mm("Colored", 40.0, 30.0, 10.0, 15.0, outline="#FF0000", text_fill="#00FF00")
    assert canvas._items[cid].get('outline') == "#FF0000"
    assert canvas._items[cid].get('label_fill') == "#00FF00"
    canvas.destroy()

def test_objects_different_sizes():
    app, canvas = get_canvas()
    sizes = [(20, 15), (40, 30), (60, 50), (80, 60), (100, 80)]
    for i, (w, h) in enumerate(sizes):
        canvas._create_rect_at_mm(f"Size{i}", float(w), float(h), 10.0, 10.0)
    canvas.destroy()

def test_objects_different_positions():
    app, canvas = get_canvas()
    positions = [(0, 0), (50, 50), (100, 100), (150, 150), (200, 200)]
    for i, (x, y) in enumerate(positions):
        canvas._create_rect_at_mm(f"Pos{i}", 40.0, 30.0, float(x), float(y))
    canvas.destroy()

def test_objects_different_angles():
    app, canvas = get_canvas()
    for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
        cid = canvas._create_rect_at_mm(f"Angle{angle}", 40.0, 30.0, 10.0, 10.0)
        canvas._items[cid]['angle'] = angle
    canvas.destroy()

def test_mixed_rect_and_text():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(i*50), 10.0)
        canvas._create_text_at_mm(f"T{i}", float(i*50), 50.0)
    canvas.destroy()
