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

# Zoom and view operations
def test_zoom_in():
    app, canvas = get_canvas()
    canvas._zoom_step(1)
    canvas.destroy()

def test_zoom_out():
    app, canvas = get_canvas()
    canvas._zoom_step(-1)
    canvas.destroy()

def test_zoom_cycle():
    app, canvas = get_canvas()
    for _ in range(5):
        canvas._zoom_step(1)
    for _ in range(5):
        canvas._zoom_step(-1)
    canvas.destroy()

def test_redraw_jig():
    app, canvas = get_canvas()
    canvas._redraw_jig()
    canvas.destroy()

def test_update_scrollregion():
    app, canvas = get_canvas()
    canvas._update_scrollregion()
    canvas.destroy()

def test_center_view():
    app, canvas = get_canvas()
    canvas._center_view()
    canvas.destroy()

def test_zoom_with_objects():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(i*50), float(i*40))
    canvas._zoom_step(1)
    canvas._zoom_step(-1)
    canvas.destroy()

def test_redraw_with_objects():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(i*50), float(i*40))
    canvas._redraw_jig()
    canvas.destroy()

def test_multiple_redraws():
    app, canvas = get_canvas()
    for _ in range(10):
        canvas._redraw_jig()
        canvas._update_scrollregion()
        canvas._center_view()
    canvas.destroy()

def test_ai_arrange_empty():
    app, canvas = get_canvas()
    canvas._ai_arrange()
    canvas.destroy()

def test_ai_arrange_single():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 40.0, 30.0, 10.0, 10.0)
    canvas._ai_arrange()
    canvas.destroy()

def test_ai_arrange_multiple():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 35.0, 25.0, float(i*15), float(i*12))
    canvas._ai_arrange()
    canvas.destroy()

def test_ai_arrange_objects():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 35.0, 25.0, float(i*15), float(i*12))
    canvas._ai_arrange_objects()
    canvas.destroy()

def test_arrange_majors_empty():
    app, canvas = get_canvas()
    canvas._arrange_majors()
    canvas.destroy()

def test_arrange_majors():
    app, canvas = get_canvas()
    canvas._arrange_majors()
    canvas.destroy()

def test_update_all_majors():
    app, canvas = get_canvas()
    canvas._update_all_majors()
    canvas.destroy()

def test_renumber_slots():
    app, canvas = get_canvas()
    canvas._renumber_slots()
    canvas.destroy()

def test_place_slots_all_majors():
    app, canvas = get_canvas()
    canvas._place_slots_all_majors()
    canvas.destroy()
