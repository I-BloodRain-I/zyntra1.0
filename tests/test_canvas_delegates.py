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

def test_jig_controller_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, "jig")
    assert canvas.jig is not None
    canvas.destroy()

def test_slots_manager_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, "slots")
    assert canvas.slots is not None
    canvas.destroy()

def test_majors_manager_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, "majors")
    assert canvas.majors is not None
    canvas.destroy()

def test_images_manager_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, "images")
    assert canvas.images is not None
    canvas.destroy()

def test_exporter_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, "exporter")
    assert canvas.exporter is not None
    canvas.destroy()

def test_scaled_pt_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_scaled_pt")
    assert callable(canvas._scaled_pt)
    canvas.destroy()

def test_update_scrollregion_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_update_scrollregion")
    assert callable(canvas._update_scrollregion)
    canvas.destroy()

def test_center_view_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_center_view")
    assert callable(canvas._center_view)
    canvas.destroy()

def test_redraw_jig_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_redraw_jig")
    assert callable(canvas._redraw_jig)
    canvas.destroy()

def test_zoom_step_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_zoom_step")
    assert callable(canvas._zoom_step)
    canvas.destroy()

def test_rotated_bounds_px_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_rotated_bounds_px")
    assert callable(canvas._rotated_bounds_px)
    canvas.destroy()

def test_rotated_bounds_mm_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_rotated_bounds_mm")
    assert callable(canvas._rotated_bounds_mm)
    canvas.destroy()

def test_render_photo_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_render_photo")
    assert callable(canvas._render_photo)
    canvas.destroy()

def test_create_image_item_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "create_image_item")
    assert callable(canvas.create_image_item)
    canvas.destroy()

def test_create_slot_at_mm_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_create_slot_at_mm")
    assert callable(canvas._create_slot_at_mm)
    canvas.destroy()

def test_place_slots_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_place_slots")
    assert callable(canvas._place_slots)
    canvas.destroy()

def test_renumber_slots_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_renumber_slots")
    assert callable(canvas._renumber_slots)
    canvas.destroy()

def test_update_major_rect_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_update_major_rect")
    assert callable(canvas._update_major_rect)
    canvas.destroy()

def test_update_all_majors_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_update_all_majors")
    assert callable(canvas._update_all_majors)
    canvas.destroy()

def test_place_slots_all_majors_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_place_slots_all_majors")
    assert callable(canvas._place_slots_all_majors)
    canvas.destroy()

def test_remove_slots_for_major_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_remove_slots_for_major")
    assert callable(canvas._remove_slots_for_major)
    canvas.destroy()

def test_place_slots_for_major_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_place_slots_for_major")
    assert callable(canvas._place_slots_for_major)
    canvas.destroy()

def test_render_scene_to_pdf_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_render_scene_to_pdf")
    assert callable(canvas._render_scene_to_pdf)
    canvas.destroy()

def test_render_jig_to_svg_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_render_jig_to_svg")
    assert callable(canvas._render_jig_to_svg)
    canvas.destroy()

def test_render_single_pattern_svg_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_render_single_pattern_svg")
    assert callable(canvas._render_single_pattern_svg)
    canvas.destroy()

def test_items_dict_initialized():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_items")
    assert isinstance(canvas._items, dict)
    canvas.destroy()

def test_majors_dict_initialized():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_majors")
    assert isinstance(canvas._majors, dict)
    canvas.destroy()

def test_scene_store_initialized():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_scene_store")
    assert isinstance(canvas._scene_store, dict)
    canvas.destroy()

def test_left_bar_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, "left_bar")
    assert canvas.left_bar is not None
    canvas.destroy()

def test_canvas_widget_exists():
    app, canvas = get_canvas()
    assert hasattr(canvas, "canvas")
    assert canvas.canvas is not None
    canvas.destroy()

def test_update_all_text_fonts_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_update_all_text_fonts")
    assert callable(canvas._update_all_text_fonts)
    canvas.destroy()

def test_update_rect_overlay_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_update_rect_overlay")
    assert callable(canvas._update_rect_overlay)
    canvas.destroy()

def test_jig_rect_px_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_jig_rect_px")
    assert callable(canvas._jig_rect_px)
    canvas.destroy()

def test_jig_inner_rect_px_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_jig_inner_rect_px")
    assert callable(canvas._jig_inner_rect_px)
    canvas.destroy()

def test_item_outline_half_px_delegate():
    app, canvas = get_canvas()
    assert hasattr(canvas, "_item_outline_half_px")
    assert callable(canvas._item_outline_half_px)
    canvas.destroy()
