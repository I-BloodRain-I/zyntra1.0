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

def test_restore_rect_with_all_params():
    app, canvas = get_canvas()
    scene = [{
        "type": "rect",
        "x_mm": 10.0,
        "y_mm": 15.0,
        "w_mm": 50.0,
        "h_mm": 40.0,
        "angle": 30.0,
        "outline": "#FF0000",
        "text_fill": "#00FF00",
        "variable": "test_var"
    }]
    canvas._restore_scene(scene)
    assert len(canvas._items) > 0
    canvas.destroy()

def test_restore_text_with_all_params():
    app, canvas = get_canvas()
    scene = [{
        "type": "text",
        "x_mm": 20.0,
        "y_mm": 25.0,
        "text": "TestText",
        "fill": "#0000FF",
        "variable": "text_var"
    }]
    canvas._restore_scene(scene)
    assert len(canvas._items) > 0
    canvas.destroy()

def test_restore_image_with_path():
    app, canvas = get_canvas()
    scene = [{
        "type": "image",
        "x_mm": 30.0,
        "y_mm": 35.0,
        "w_mm": 60.0,
        "h_mm": 80.0,
        "img_path": "test.png",
        "angle": 45.0
    }]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_barcode_full():
    app, canvas = get_canvas()
    scene = [{
        "type": "barcode",
        "x_mm": 40.0,
        "y_mm": 45.0,
        "w_mm": 100.0,
        "h_mm": 30.0,
        "variable": "barcode_var",
        "angle": 0.0
    }]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_qrcode_full():
    app, canvas = get_canvas()
    scene = [{
        "type": "qrcode",
        "x_mm": 50.0,
        "y_mm": 55.0,
        "w_mm": 40.0,
        "h_mm": 40.0,
        "variable": "qr_var"
    }]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_multiple_mixed_objects():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0},
        {"type": "text", "x_mm": 50.0, "y_mm": 50.0, "text": "Test"},
        {"type": "barcode", "x_mm": 100.0, "y_mm": 100.0, "w_mm": 80.0, "h_mm": 25.0}
    ]
    canvas._restore_scene(scene)
    assert len(canvas._items) >= 3
    canvas.destroy()

def test_restore_with_variables():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0, "variable": "var1"},
        {"type": "text", "x_mm": 50.0, "y_mm": 50.0, "text": "Test", "variable": "var2"}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_with_angles():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0, "angle": 15.0},
        {"type": "rect", "x_mm": 50.0, "y_mm": 50.0, "w_mm": 30.0, "h_mm": 20.0, "angle": 90.0},
        {"type": "rect", "x_mm": 90.0, "y_mm": 90.0, "w_mm": 30.0, "h_mm": 20.0, "angle": 180.0}
    ]
    canvas._restore_scene(scene)
    assert len(canvas._items) >= 3
    canvas.destroy()

def test_restore_with_colors():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0, "outline": "#FF0000"},
        {"type": "rect", "x_mm": 50.0, "y_mm": 50.0, "w_mm": 30.0, "h_mm": 20.0, "outline": "#00FF00"},
        {"type": "text", "x_mm": 90.0, "y_mm": 90.0, "text": "T", "fill": "#0000FF"}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_large_scene():
    app, canvas = get_canvas()
    scene = []
    for i in range(20):
        scene.append({
            "type": "rect",
            "x_mm": float(i * 10),
            "y_mm": float(i * 10),
            "w_mm": 25.0,
            "h_mm": 20.0
        })
    canvas._restore_scene(scene)
    assert len(canvas._items) >= 20
    canvas.destroy()

def test_restore_edge_positions():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 0.0, "y_mm": 0.0, "w_mm": 10.0, "h_mm": 10.0},
        {"type": "rect", "x_mm": 280.0, "y_mm": 380.0, "w_mm": 10.0, "h_mm": 10.0}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_tiny_objects():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 1.0, "h_mm": 1.0},
        {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "w_mm": 0.5, "h_mm": 0.5}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_huge_objects():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 250.0, "h_mm": 350.0}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_with_fractional_positions():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.5, "y_mm": 15.7, "w_mm": 30.3, "h_mm": 20.9},
        {"type": "text", "x_mm": 50.1, "y_mm": 50.2, "text": "Test"}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_with_negative_angles():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0, "angle": -45.0},
        {"type": "rect", "x_mm": 50.0, "y_mm": 50.0, "w_mm": 30.0, "h_mm": 20.0, "angle": -90.0}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_with_large_angles():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0, "angle": 360.0},
        {"type": "rect", "x_mm": 50.0, "y_mm": 50.0, "w_mm": 30.0, "h_mm": 20.0, "angle": 720.0}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_text_empty_content():
    app, canvas = get_canvas()
    scene = [
        {"type": "text", "x_mm": 10.0, "y_mm": 10.0, "text": ""}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_text_long_content():
    app, canvas = get_canvas()
    scene = [
        {"type": "text", "x_mm": 10.0, "y_mm": 10.0, "text": "A" * 100}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_text_special_chars():
    app, canvas = get_canvas()
    scene = [
        {"type": "text", "x_mm": 10.0, "y_mm": 10.0, "text": "Test!@#$%^&*()"},
        {"type": "text", "x_mm": 50.0, "y_mm": 50.0, "text": "Тест123"}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_overlapping_objects():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        {"type": "rect", "x_mm": 30.0, "y_mm": 30.0, "w_mm": 50.0, "h_mm": 50.0},
        {"type": "rect", "x_mm": 50.0, "y_mm": 50.0, "w_mm": 50.0, "h_mm": 50.0}
    ]
    canvas._restore_scene(scene)
    assert len(canvas._items) >= 3
    canvas.destroy()

def test_restore_identical_objects():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0},
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0}
    ]
    canvas._restore_scene(scene)
    canvas.destroy()

def test_restore_scene_twice():
    app, canvas = get_canvas()
    scene = [
        {"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0}
    ]
    canvas._restore_scene(scene)
    count1 = len(canvas._items)
    canvas._restore_scene(scene)
    count2 = len(canvas._items)
    canvas.destroy()

def test_restore_after_clear():
    app, canvas = get_canvas()
    scene1 = [{"type": "rect", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 20.0}]
    canvas._restore_scene(scene1)
    canvas._items = {}
    scene2 = [{"type": "text", "x_mm": 50.0, "y_mm": 50.0, "text": "Test"}]
    canvas._restore_scene(scene2)
    canvas.destroy()

def test_restore_different_rect_sizes():
    app, canvas = get_canvas()
    scene = []
    for i in range(1, 11):
        scene.append({
            "type": "rect",
            "x_mm": float(i * 20),
            "y_mm": 10.0,
            "w_mm": float(i * 5),
            "h_mm": float(i * 3)
        })
    canvas._restore_scene(scene)
    assert len(canvas._items) >= 10
    canvas.destroy()

def test_restore_rotated_grid():
    app, canvas = get_canvas()
    scene = []
    for i in range(5):
        for j in range(5):
            scene.append({
                "type": "rect",
                "x_mm": float(i * 40),
                "y_mm": float(j * 40),
                "w_mm": 30.0,
                "h_mm": 30.0,
                "angle": float((i + j) * 15)
            })
    canvas._restore_scene(scene)
    assert len(canvas._items) >= 25
    canvas.destroy()
