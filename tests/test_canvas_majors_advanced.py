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

def test_arrange_majors_with_objects():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 50.0, 40.0, 10.0, 10.0)
    canvas._create_rect_at_mm("R2", 50.0, 40.0, 60.0, 10.0)
    canvas._arrange_majors()
    canvas.destroy()

def test_arrange_majors_single_object():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("Single", 80.0, 60.0, 50.0, 50.0)
    canvas._arrange_majors()
    canvas.destroy()

def test_arrange_majors_many_objects():
    app, canvas = get_canvas()
    for i in range(15):
        canvas._create_rect_at_mm(f"R{i}", 30.0, 25.0, float(i * 15), float(i * 12))
    canvas._arrange_majors()
    canvas.destroy()

def test_arrange_majors_various_sizes():
    app, canvas = get_canvas()
    sizes = [(20, 15), (40, 30), (60, 45), (30, 25), (50, 40)]
    for i, (w, h) in enumerate(sizes):
        canvas._create_rect_at_mm(f"R{i}", float(w), float(h), float(i * 40), 10.0)
    canvas._arrange_majors()
    canvas.destroy()

def test_arrange_majors_tight_fit():
    app, canvas = get_canvas()
    for i in range(20):
        canvas._create_rect_at_mm(f"R{i}", 25.0, 20.0, 10.0, 10.0)
    canvas._arrange_majors()
    canvas.destroy()

def test_arrange_majors_after_delete():
    app, canvas = get_canvas()
    cid1 = canvas._create_rect_at_mm("R1", 50.0, 40.0, 10.0, 10.0)
    cid2 = canvas._create_rect_at_mm("R2", 50.0, 40.0, 70.0, 10.0)
    if cid1 in canvas._items:
        canvas._items.pop(cid1, None)
    canvas._arrange_majors()
    canvas.destroy()

def test_update_all_majors_empty():
    app, canvas = get_canvas()
    canvas._update_all_majors()
    canvas.destroy()

def test_update_all_majors_with_major():
    app, canvas = get_canvas()
    canvas.major_w.set("120.0")
    canvas.major_h.set("180.0")
    canvas._update_all_majors()
    canvas.destroy()

def test_update_all_majors_multiple_times():
    app, canvas = get_canvas()
    canvas._update_all_majors()
    canvas._update_all_majors()
    canvas._update_all_majors()
    canvas.destroy()

def test_place_slots_with_major():
    app, canvas = get_canvas()
    canvas.major_w.set("100.0")
    canvas.major_h.set("150.0")
    canvas.slot_w.set("20.0")
    canvas.slot_h.set("25.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()

def test_place_slots_small_slots():
    app, canvas = get_canvas()
    canvas.slot_w.set("10.0")
    canvas.slot_h.set("12.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()

def test_place_slots_large_slots():
    app, canvas = get_canvas()
    canvas.slot_w.set("50.0")
    canvas.slot_h.set("60.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()

def test_place_slots_with_step():
    app, canvas = get_canvas()
    canvas.step_x.set("25.0")
    canvas.step_y.set("30.0")
    canvas.slot_w.set("20.0")
    canvas.slot_h.set("25.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()

def test_place_slots_with_origin():
    app, canvas = get_canvas()
    canvas.origin_x.set("15.0")
    canvas.origin_y.set("20.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()

def test_renumber_slots_empty():
    app, canvas = get_canvas()
    canvas._renumber_slots()
    canvas.destroy()

def test_renumber_slots_with_slots():
    app, canvas = get_canvas()
    canvas._create_slot_at_mm("1", 20.0, 20.0, 10.0, 10.0)
    canvas._create_slot_at_mm("2", 20.0, 20.0, 30.0, 10.0)
    canvas._create_slot_at_mm("3", 20.0, 20.0, 50.0, 10.0)
    canvas._renumber_slots()
    canvas.destroy()

def test_place_slots_multiple_majors():
    app, canvas = get_canvas()
    canvas._major_sizes["Major size 2"] = {
        "x": "10", "y": "10", "w": "80", "h": "100",
        "step_x": "25", "step_y": "30",
        "origin_x": "5", "origin_y": "5",
        "slot_w": "20", "slot_h": "25"
    }
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()

def test_arrange_with_rotated_objects():
    app, canvas = get_canvas()
    cid1 = canvas._create_rect_at_mm("R1", 50.0, 40.0, 10.0, 10.0)
    cid2 = canvas._create_rect_at_mm("R2", 50.0, 40.0, 70.0, 10.0)
    if cid1 in canvas._items:
        canvas._items[cid1]["angle"] = 45.0
    canvas._arrange_majors()
    canvas.destroy()

def test_major_rect_update():
    app, canvas = get_canvas()
    canvas.major_x.set("20.0")
    canvas.major_y.set("30.0")
    canvas.major_w.set("150.0")
    canvas.major_h.set("200.0")
    canvas._update_major_rect(name=canvas.major_name.get())
    canvas.destroy()

def test_major_rect_at_edge():
    app, canvas = get_canvas()
    canvas.major_x.set("0.0")
    canvas.major_y.set("0.0")
    canvas._update_major_rect(name=canvas.major_name.get())
    canvas.destroy()

def test_slot_placement_pattern():
    app, canvas = get_canvas()
    canvas.major_w.set("200.0")
    canvas.major_h.set("250.0")
    canvas.slot_w.set("25.0")
    canvas.slot_h.set("30.0")
    canvas.step_x.set("27.0")
    canvas.step_y.set("32.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()

def test_arrange_after_major_change():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 50.0, 40.0, 10.0, 10.0)
    canvas.major_w.set("120.0")
    canvas.major_h.set("160.0")
    canvas._arrange_majors()
    canvas.destroy()

def test_slot_placement_after_size_change():
    app, canvas = get_canvas()
    canvas.slot_w.set("20.0")
    canvas.slot_h.set("25.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.slot_w.set("30.0")
    canvas.slot_h.set("35.0")
    canvas._place_slots_all_majors(silent=True)
    canvas.destroy()
