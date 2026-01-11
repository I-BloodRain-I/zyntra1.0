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

# Serialization tests
def test_serialize_empty():
    app, canvas = get_canvas()
    scene = canvas._serialize_scene()
    assert isinstance(scene, list)
    canvas.destroy()

def test_serialize_single_rect():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 50.0, 40.0, 10.0, 15.0)
    scene = canvas._serialize_scene()
    assert len(scene) >= 1
    canvas.destroy()

def test_serialize_multiple_objects():
    app, canvas = get_canvas()
    for i in range(20):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(i*50), float(i*40))
    scene = canvas._serialize_scene()
    assert len(scene) >= 20
    canvas.destroy()

def test_restore_empty():
    app, canvas = get_canvas()
    canvas._restore_scene([])
    canvas.destroy()

def test_restore_single_object():
    app, canvas = get_canvas()
    scene = [{"type": "rect", "label": "R1", "w_mm": 50.0, "h_mm": 40.0, "x_mm": 10.0, "y_mm": 15.0, "angle": 0, "z": 1}]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_multiple_objects():
    app, canvas = get_canvas()
    scene = []
    for i in range(20):
        scene.append({"type": "rect", "label": f"R{i}", "w_mm": 40.0, "h_mm": 30.0, "x_mm": float(i*50), "y_mm": float(i*40), "angle": 0, "z": i})
    canvas._restore_scene(scene)
    canvas.destroy()

def test_multiple_serialize_restore_cycles():
    app, canvas = get_canvas()
    for i in range(5):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(i*50), float(i*40))
    for _ in range(10):
        scene = canvas._serialize_scene()
        canvas._clear_scene()
        canvas._restore_scene(scene)
    canvas.destroy()

def test_serialize_with_angles():
    app, canvas = get_canvas()
    for i in range(10):
        cid = canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(i*50), float(i*40))
        canvas._items[cid]['angle'] = float(i * 36)
    scene = canvas._serialize_scene()
    canvas.destroy()

def test_restore_with_angles():
    app, canvas = get_canvas()
    scene = []
    for i in range(10):
        scene.append({"type": "rect", "label": f"R{i}", "w_mm": 40.0, "h_mm": 30.0, "x_mm": float(i*50), "y_mm": float(i*40), "angle": float(i*36), "z": i})
    canvas._restore_scene(scene)
    canvas.destroy()

def test_serialize_mixed_types():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 50.0, 40.0, 10.0, 10.0)
    canvas._create_text_at_mm("T1", 50.0, 50.0)
    scene = canvas._serialize_scene()
    types = set(obj.get('type') for obj in scene)
    assert 'rect' in types
    assert 'text' in types
    canvas.destroy()

def test_restore_mixed_types():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "label": "R1", "w_mm": 50.0, "h_mm": 40.0, "x_mm": 10.0, "y_mm": 10.0, "angle": 0, "z": 1},
        {"type": "text", "text": "T1", "x_mm": 50.0, "y_mm": 50.0, "z": 2}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()
