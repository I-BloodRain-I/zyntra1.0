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

def test_create_rect_default():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    assert rid is not None
    canvas.destroy()

def test_create_rect_with_outline():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, outline="#ff0000")
    canvas.destroy()

def test_create_rect_with_text_fill():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, text_fill="#00ff00")
    canvas.destroy()

def test_create_rect_with_angle():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=45.0)
    canvas.destroy()

def test_create_rect_all_params():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, outline="#ff0000", text_fill="#0000ff", angle=30.0)
    canvas.destroy()

def test_create_text_default():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("Text", 50.0, 30.0)
    assert tid is not None
    canvas.destroy()

def test_create_text_with_fill():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("Text", 50.0, 30.0, fill="#ff0000")
    canvas.destroy()

def test_create_text_empty():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("", 50.0, 30.0)
    canvas.destroy()

def test_create_text_long():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("A" * 200, 50.0, 30.0)
    canvas.destroy()

def test_create_text_unicode():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("Привет мир 你好", 50.0, 30.0)
    canvas.destroy()

def test_create_multiple_rects():
    app, canvas = get_canvas()
    for i in range(20):
        canvas._create_rect_at_mm(f"R{i}", 30.0, 20.0, float(i * 15), 10.0)
    canvas.destroy()

def test_create_multiple_texts():
    app, canvas = get_canvas()
    for i in range(20):
        canvas._create_text_at_mm(f"T{i}", float(i * 15), 50.0)
    canvas.destroy()

def test_create_mixed_objects():
    app, canvas = get_canvas()
    for i in range(30):
        if i % 2 == 0:
            canvas._create_rect_at_mm(f"R{i}", 25.0, 20.0, float(i * 10), 10.0)
        else:
            canvas._create_text_at_mm(f"T{i}", float(i * 10), 50.0)
    canvas.destroy()

def test_rect_various_sizes():
    app, canvas = get_canvas()
    sizes = [(10, 10), (50, 30), (100, 50), (200, 100), (5, 5)]
    for i, (w, h) in enumerate(sizes):
        canvas._create_rect_at_mm(f"R{i}", float(w), float(h), 10.0, 10.0)
    canvas.destroy()

def test_rect_various_positions():
    app, canvas = get_canvas()
    positions = [(0, 0), (50, 50), (100, 100), (200, 150), (10, 200)]
    for i, (x, y) in enumerate(positions):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(x), float(y))
    canvas.destroy()

def test_rect_various_angles():
    app, canvas = get_canvas()
    for angle in [0, 15, 30, 45, 60, 75, 90, 120, 180, 270]:
        canvas._create_rect_at_mm(f"R{angle}", 50.0, 30.0, 10.0, 10.0, angle=float(angle))
    canvas.destroy()

def test_rect_various_outlines():
    app, canvas = get_canvas()
    colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"]
    for i, color in enumerate(colors):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, 10.0, float(i * 35), outline=color)
    canvas.destroy()

def test_rect_various_text_fills():
    app, canvas = get_canvas()
    colors = ["white", "red", "blue", "green", "yellow"]
    for i, color in enumerate(colors):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, 10.0, float(i * 35), text_fill=color)
    canvas.destroy()

def test_text_various_fills():
    app, canvas = get_canvas()
    colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff"]
    for i, color in enumerate(colors):
        canvas._create_text_at_mm(f"T{i}", float(i * 20), 50.0, fill=color)
    canvas.destroy()

def test_text_various_positions():
    app, canvas = get_canvas()
    for x in range(0, 200, 20):
        for y in range(0, 150, 30):
            canvas._create_text_at_mm(f"T_{x}_{y}", float(x), float(y))
    canvas.destroy()

def test_rect_grid_layout():
    app, canvas = get_canvas()
    for row in range(5):
        for col in range(8):
            canvas._create_rect_at_mm(f"R{row}_{col}", 30.0, 25.0, float(col * 35), float(row * 30))
    canvas.destroy()

def test_text_grid_layout():
    app, canvas = get_canvas()
    for row in range(5):
        for col in range(10):
            canvas._create_text_at_mm(f"T{row}{col}", float(col * 30), float(row * 35))
    canvas.destroy()

def test_rect_angle_0():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=0.0)
    canvas.destroy()

def test_rect_angle_90():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=90.0)
    canvas.destroy()

def test_rect_angle_180():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=180.0)
    canvas.destroy()

def test_rect_angle_270():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=270.0)
    canvas.destroy()

def test_rect_angle_360():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=360.0)
    canvas.destroy()

def test_rect_angle_negative():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=-45.0)
    canvas.destroy()

def test_rect_angle_large():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0, angle=720.0)
    canvas.destroy()

def test_rect_zero_size():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 0.0, 0.0, 10.0, 10.0)
    canvas.destroy()

def test_rect_tiny_size():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 1.0, 1.0, 10.0, 10.0)
    canvas.destroy()

def test_rect_huge_size():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 500.0, 400.0, 10.0, 10.0)
    canvas.destroy()

def test_rect_fractional_size():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.5, 30.3, 10.0, 10.0)
    canvas.destroy()

def test_rect_fractional_position():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.7, 10.9)
    canvas.destroy()

def test_rect_negative_position():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, -10.0, -10.0)
    canvas.destroy()

def test_text_negative_position():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("T", -10.0, -10.0)
    canvas.destroy()

def test_text_fractional_position():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("T", 50.5, 30.7)
    canvas.destroy()

def test_text_special_chars():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("!@#$%^&*()", 50.0, 30.0)
    canvas.destroy()

def test_text_numbers():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("1234567890", 50.0, 30.0)
    canvas.destroy()

def test_text_multiline():
    app, canvas = get_canvas()
    tid = canvas._create_text_at_mm("Line1\nLine2\nLine3", 50.0, 30.0)
    canvas.destroy()

def test_rect_label_short():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("A", 50.0, 30.0, 10.0, 10.0)
    canvas.destroy()

def test_rect_label_long():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("VeryLongLabelText" * 5, 50.0, 30.0, 10.0, 10.0)
    canvas.destroy()

def test_rect_label_empty():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("", 50.0, 30.0, 10.0, 10.0)
    canvas.destroy()

def test_rect_label_numbers():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("12345", 50.0, 30.0, 10.0, 10.0)
    canvas.destroy()

def test_rect_label_unicode():
    app, canvas = get_canvas()
    rid = canvas._create_rect_at_mm("日本語文字", 50.0, 30.0, 10.0, 10.0)
    canvas.destroy()

def test_items_dict_populated():
    app, canvas = get_canvas()
    initial = len(canvas._items)
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    assert len(canvas._items) > initial
    canvas.destroy()

def test_items_dict_multiple():
    app, canvas = get_canvas()
    initial = len(canvas._items)
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 30.0, 20.0, float(i * 15), 10.0)
    assert len(canvas._items) >= initial + 10
    canvas.destroy()

def test_zoom_affects_creation():
    app, canvas = get_canvas()
    canvas._zoom = 1.5
    rid = canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    canvas.destroy()

def test_zoom_various_levels():
    app, canvas = get_canvas()
    for zoom in [0.5, 0.8, 1.0, 1.5, 2.0]:
        canvas._zoom = zoom
        canvas._create_rect_at_mm(f"R{zoom}", 40.0, 30.0, 10.0, 10.0)
    canvas.destroy()

def test_serialize_after_create():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    scene = canvas._serialize_scene()
    assert len(scene) > 0
    canvas.destroy()

def test_serialize_multiple():
    app, canvas = get_canvas()
    for i in range(15):
        canvas._create_rect_at_mm(f"R{i}", 30.0, 20.0, float(i * 10), 10.0)
    scene = canvas._serialize_scene()
    assert len(scene) >= 15
    canvas.destroy()

def test_clear_after_create():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    canvas._clear_scene(keep_slots=False)
    assert len(canvas._items) == 0
    canvas.destroy()

def test_create_after_clear():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 50.0, 30.0, 10.0, 10.0)
    canvas._clear_scene(keep_slots=False)
    canvas._create_rect_at_mm("R2", 40.0, 25.0, 20.0, 20.0)
    canvas.destroy()

def test_redraw_after_create():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    canvas._redraw_jig()
    canvas.destroy()

def test_center_view_after_create():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 100.0, 100.0)
    canvas._center_view()
    canvas.destroy()

def test_update_scrollregion_after_create():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 200.0, 150.0)
    canvas._update_scrollregion()
    canvas.destroy()

def test_zoom_step_with_objects():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    canvas._zoom_step(1)
    canvas._zoom_step(-1)
    canvas.destroy()

def test_dense_object_creation():
    app, canvas = get_canvas()
    for x in range(20):
        for y in range(15):
            canvas._create_rect_at_mm(f"R{x}_{y}", 8.0, 8.0, float(x * 10), float(y * 10))
    canvas.destroy()

def test_sparse_object_creation():
    app, canvas = get_canvas()
    positions = [(10, 10), (150, 80), (250, 200), (50, 300)]
    for i, (x, y) in enumerate(positions):
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(x), float(y))
    canvas.destroy()

def test_circular_pattern():
    app, canvas = get_canvas()
    import math
    for i in range(12):
        angle_deg = i * 30
        x = 150 + 80 * math.cos(math.radians(angle_deg))
        y = 150 + 80 * math.sin(math.radians(angle_deg))
        canvas._create_rect_at_mm(f"R{i}", 20.0, 20.0, x, y)
    canvas.destroy()

def test_diagonal_pattern():
    app, canvas = get_canvas()
    for i in range(20):
        canvas._create_rect_at_mm(f"R{i}", 15.0, 15.0, float(i * 12), float(i * 12))
    canvas.destroy()

def test_alternating_sizes():
    app, canvas = get_canvas()
    for i in range(15):
        if i % 2 == 0:
            canvas._create_rect_at_mm(f"R{i}", 50.0, 30.0, float(i * 20), 10.0)
        else:
            canvas._create_rect_at_mm(f"R{i}", 30.0, 50.0, float(i * 20), 10.0)
    canvas.destroy()

def test_alternating_angles():
    app, canvas = get_canvas()
    for i in range(10):
        angle = 0.0 if i % 2 == 0 else 45.0
        canvas._create_rect_at_mm(f"R{i}", 40.0, 30.0, float(i * 25), 10.0, angle=angle)
    canvas.destroy()

def test_mixed_text_and_rects():
    app, canvas = get_canvas()
    for i in range(20):
        x = float(i * 15)
        canvas._create_rect_at_mm(f"R{i}", 25.0, 20.0, x, 10.0)
        canvas._create_text_at_mm(f"T{i}", x + 12.5, 30.0)
    canvas.destroy()

def test_text_above_rects():
    app, canvas = get_canvas()
    for i in range(10):
        x = float(i * 30)
        canvas._create_rect_at_mm(f"R{i}", 25.0, 25.0, x, 50.0)
        canvas._create_text_at_mm(f"Label{i}", x + 12.5, 40.0)
    canvas.destroy()

def test_large_scene():
    app, canvas = get_canvas()
    for i in range(100):
        canvas._create_rect_at_mm(f"R{i}", 15.0, 15.0, float(i % 20 * 15), float(i // 20 * 20))
    canvas.destroy()

def test_very_large_scene():
    app, canvas = get_canvas()
    for i in range(200):
        canvas._create_rect_at_mm(f"R{i}", 10.0, 10.0, float(i % 30 * 10), float(i // 30 * 15))
    canvas.destroy()

def test_rapid_creation():
    app, canvas = get_canvas()
    for i in range(50):
        canvas._create_rect_at_mm(f"R{i}", 20.0, 20.0, 10.0, 10.0)
    canvas.destroy()

def test_rapid_creation_and_clear():
    app, canvas = get_canvas()
    for _ in range(10):
        for i in range(10):
            canvas._create_rect_at_mm(f"R{i}", 20.0, 20.0, float(i * 15), 10.0)
        canvas._clear_scene(keep_slots=False)
    canvas.destroy()

def test_create_serialize_restore():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 30.0, 20.0, float(i * 20), 10.0)
    scene = canvas._serialize_scene()
    canvas._clear_scene(keep_slots=False)
    canvas._restore_scene(scene)
    canvas.destroy()

def test_multiple_serialize_cycles():
    app, canvas = get_canvas()
    for i in range(5):
        canvas._create_rect_at_mm(f"R{i}", 30.0, 20.0, float(i * 25), 10.0)
    for _ in range(5):
        scene = canvas._serialize_scene()
        canvas._clear_scene(keep_slots=False)
        canvas._restore_scene(scene)
    canvas.destroy()

def test_incremental_creation():
    app, canvas = get_canvas()
    for i in range(20):
        canvas._create_rect_at_mm(f"R{i}", 25.0, 20.0, float(i * 15), 10.0)
        if i % 5 == 0:
            scene = canvas._serialize_scene()
    canvas.destroy()

def test_aspect_ratios():
    app, canvas = get_canvas()
    ratios = [(1, 1), (2, 1), (1, 2), (3, 1), (1, 3), (4, 3), (16, 9)]
    for i, (w, h) in enumerate(ratios):
        canvas._create_rect_at_mm(f"R{i}", float(w * 15), float(h * 15), 10.0, float(i * 40))
    canvas.destroy()

def test_thin_rects():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("Thin1", 100.0, 2.0, 10.0, 10.0)
    canvas._create_rect_at_mm("Thin2", 2.0, 100.0, 120.0, 10.0)
    canvas.destroy()

def test_square_rects():
    app, canvas = get_canvas()
    for i, size in enumerate([10, 20, 30, 40, 50]):
        canvas._create_rect_at_mm(f"Square{i}", float(size), float(size), float(i * 55), 10.0)
    canvas.destroy()

def test_tall_rects():
    app, canvas = get_canvas()
    for i in range(5):
        canvas._create_rect_at_mm(f"Tall{i}", 20.0, float(80 + i * 15), float(i * 25), 10.0)
    canvas.destroy()

def test_wide_rects():
    app, canvas = get_canvas()
    for i in range(5):
        canvas._create_rect_at_mm(f"Wide{i}", float(80 + i * 15), 20.0, 10.0, float(i * 25))
    canvas.destroy()

def test_nested_layout():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("Outer", 100.0, 100.0, 50.0, 50.0)
    canvas._create_rect_at_mm("Middle", 70.0, 70.0, 65.0, 65.0)
    canvas._create_rect_at_mm("Inner", 40.0, 40.0, 80.0, 80.0)
    canvas.destroy()

def test_adjacent_rects():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 50.0, 30.0, 10.0, 10.0)
    canvas._create_rect_at_mm("R2", 50.0, 30.0, 60.0, 10.0)
    canvas._create_rect_at_mm("R3", 50.0, 30.0, 110.0, 10.0)
    canvas.destroy()

def test_overlapping_rects():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R1", 50.0, 30.0, 10.0, 10.0)
    canvas._create_rect_at_mm("R2", 50.0, 30.0, 30.0, 20.0)
    canvas._create_rect_at_mm("R3", 50.0, 30.0, 20.0, 15.0)
    canvas.destroy()

def test_text_at_boundaries():
    app, canvas = get_canvas()
    canvas._create_text_at_mm("TL", 0.0, 0.0)
    canvas._create_text_at_mm("TR", 280.0, 0.0)
    canvas._create_text_at_mm("BL", 0.0, 380.0)
    canvas._create_text_at_mm("BR", 280.0, 380.0)
    canvas.destroy()

def test_rect_at_boundaries():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("TL", 30.0, 30.0, 0.0, 0.0)
    canvas._create_rect_at_mm("TR", 30.0, 30.0, 260.0, 0.0)
    canvas._create_rect_at_mm("BL", 30.0, 30.0, 0.0, 360.0)
    canvas._create_rect_at_mm("BR", 30.0, 30.0, 260.0, 360.0)
    canvas.destroy()

def test_center_objects():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("C1", 40.0, 30.0, 130.0, 180.0)
    canvas._create_text_at_mm("Center", 150.0, 195.0)
    canvas.destroy()

def test_random_layout():
    app, canvas = get_canvas()
    import random
    random.seed(42)
    for i in range(30):
        x = random.uniform(0, 250)
        y = random.uniform(0, 350)
        w = random.uniform(15, 50)
        h = random.uniform(15, 50)
        canvas._create_rect_at_mm(f"R{i}", w, h, x, y)
    canvas.destroy()

def test_grid_with_gaps():
    app, canvas = get_canvas()
    for row in range(4):
        for col in range(6):
            canvas._create_rect_at_mm(f"R{row}_{col}", 30.0, 25.0, float(col * 45), float(row * 35))
    canvas.destroy()

def test_tight_grid():
    app, canvas = get_canvas()
    for row in range(8):
        for col in range(12):
            canvas._create_rect_at_mm(f"R{row}_{col}", 20.0, 18.0, float(col * 22), float(row * 20))
    canvas.destroy()

def test_staggered_layout():
    app, canvas = get_canvas()
    for row in range(5):
        offset = 15.0 if row % 2 == 0 else 0.0
        for col in range(8):
            canvas._create_rect_at_mm(f"R{row}_{col}", 25.0, 22.0, float(col * 32 + offset), float(row * 28))
    canvas.destroy()

def test_diagonal_text():
    app, canvas = get_canvas()
    for i in range(15):
        canvas._create_text_at_mm(f"D{i}", float(i * 18), float(i * 22))
    canvas.destroy()

def test_horizontal_text_line():
    app, canvas = get_canvas()
    for i in range(15):
        canvas._create_text_at_mm(f"H{i}", float(i * 18), 100.0)
    canvas.destroy()

def test_vertical_text_line():
    app, canvas = get_canvas()
    for i in range(15):
        canvas._create_text_at_mm(f"V{i}", 100.0, float(i * 22))
    canvas.destroy()

def test_cross_pattern():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"H{i}", 20.0, 15.0, float(i * 25), 180.0)
        canvas._create_rect_at_mm(f"V{i}", 15.0, 20.0, 140.0, float(i * 32))
    canvas.destroy()

def test_frame_pattern():
    app, canvas = get_canvas()
    for i in range(10):
        x = float(i * 25)
        canvas._create_rect_at_mm(f"T{i}", 20.0, 15.0, x, 10.0)
        canvas._create_rect_at_mm(f"B{i}", 20.0, 15.0, x, 360.0)
    for i in range(12):
        y = float(i * 30)
        canvas._create_rect_at_mm(f"L{i}", 15.0, 20.0, 10.0, y)
        canvas._create_rect_at_mm(f"R{i}", 15.0, 20.0, 260.0, y)
    canvas.destroy()

def test_checkerboard_pattern():
    app, canvas = get_canvas()
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                canvas._create_rect_at_mm(f"R{row}_{col}", 25.0, 22.0, float(col * 27), float(row * 24))
    canvas.destroy()

def test_spiral_pattern():
    app, canvas = get_canvas()
    import math
    for i in range(20):
        angle = i * 30
        radius = 20 + i * 8
        x = 140 + radius * math.cos(math.radians(angle))
        y = 190 + radius * math.sin(math.radians(angle))
        canvas._create_rect_at_mm(f"R{i}", 18.0, 18.0, x, y)
    canvas.destroy()

def test_wave_pattern():
    app, canvas = get_canvas()
    import math
    for i in range(30):
        x = float(i * 9)
        y = 180 + 60 * math.sin(i * 0.5)
        canvas._create_rect_at_mm(f"R{i}", 8.0, 8.0, x, y)
    canvas.destroy()

def test_star_pattern():
    app, canvas = get_canvas()
    import math
    for i in range(10):
        angle = i * 36
        radius = 80 if i % 2 == 0 else 40
        x = 140 + radius * math.cos(math.radians(angle - 90))
        y = 190 + radius * math.sin(math.radians(angle - 90))
        canvas._create_rect_at_mm(f"R{i}", 15.0, 15.0, x, y)
    canvas.destroy()

def test_complex_workflow():
    app, canvas = get_canvas()
    canvas._zoom = 1.3
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 35.0, 25.0, float(i * 28), 10.0, angle=float(i * 18))
    for i in range(5):
        canvas._create_text_at_mm(f"Label{i}", float(i * 55), 50.0, fill="#ff0000")
    scene = canvas._serialize_scene()
    canvas._redraw_jig()
    canvas._center_view()
    canvas._zoom_step(1)
    canvas.destroy()

def test_full_lifecycle():
    app, canvas = get_canvas()
    for i in range(15):
        canvas._create_rect_at_mm(f"R{i}", 30.0, 22.0, float(i * 18), 10.0)
    scene1 = canvas._serialize_scene()
    canvas._clear_scene(keep_slots=False)
    canvas._restore_scene(scene1)
    for i in range(10):
        canvas._create_text_at_mm(f"T{i}", float(i * 26), 50.0)
    scene2 = canvas._serialize_scene()
    canvas._clear_scene(keep_slots=False)
    canvas._restore_scene(scene2)
    canvas.destroy()

def test_edge_cases():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("Zero", 0.0, 0.0, 0.0, 0.0)
    canvas._create_rect_at_mm("Huge", 500.0, 500.0, 0.0, 0.0)
    canvas._create_rect_at_mm("Neg", 30.0, 30.0, -50.0, -50.0)
    canvas._create_text_at_mm("", 50.0, 50.0)
    canvas._create_text_at_mm("X" * 300, 100.0, 100.0)
    canvas.destroy()

def test_state_persistence():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 10.0, 10.0)
    count1 = len(canvas._items)
    scene = canvas._serialize_scene()
    canvas._clear_scene(keep_slots=False)
    count2 = len(canvas._items)
    canvas._restore_scene(scene)
    count3 = len(canvas._items)
    assert count2 == 0
    assert count3 == count1
    canvas.destroy()

def test_zoom_cycle():
    app, canvas = get_canvas()
    canvas._create_rect_at_mm("R", 50.0, 30.0, 50.0, 50.0)
    for _ in range(3):
        canvas._zoom_step(1)
    for _ in range(3):
        canvas._zoom_step(-1)
    canvas.destroy()

def test_redraw_cycle():
    app, canvas = get_canvas()
    for i in range(10):
        canvas._create_rect_at_mm(f"R{i}", 25.0, 20.0, float(i * 25), 10.0)
        canvas._redraw_jig()
    canvas.destroy()

def test_memory_stress():
    app, canvas = get_canvas()
    for batch in range(5):
        for i in range(30):
            canvas._create_rect_at_mm(f"B{batch}_R{i}", 18.0, 18.0, float(i * 9), float(batch * 60))
        canvas._clear_scene(keep_slots=False)
    canvas.destroy()

def test_performance_baseline():
    app, canvas = get_canvas()
    for i in range(100):
        canvas._create_rect_at_mm(f"R{i}", 15.0, 15.0, float(i % 20 * 14), float(i // 20 * 20))
    canvas.destroy()
