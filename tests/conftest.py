import os
import sys
import tkinter as tk
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

_original_photoimage = tk.PhotoImage

def _dummy_photoimage_constructor(**kwargs):
    return None

@pytest.fixture(scope="session", autouse=True)
def patch_photoimage():
    tk.PhotoImage = _dummy_photoimage_constructor
    yield
    tk.PhotoImage = _original_photoimage

@pytest.fixture(scope="session", autouse=True)
def patch_filedialog():
    with patch('tkinter.filedialog.askopenfilename', return_value=''):
        with patch('tkinter.filedialog.askopenfilenames', return_value=[]):
            with patch('tkinter.filedialog.asksaveasfilename', return_value=''):
                with patch('tkinter.filedialog.askdirectory', return_value=''):
                    yield

@pytest.fixture
def mock_tk_root():
    try:
        root = tk.Tk()
        root.withdraw()
        yield root
        root.destroy()
    except:
        from collections import defaultdict
        root = Mock()
        root.withdraw = Mock()
        root.destroy = Mock()
        root.winfo_width = Mock(return_value=1920)
        root.winfo_height = Mock(return_value=1080)
        root.winfo_screenwidth = Mock(return_value=1920)
        root.winfo_screenheight = Mock(return_value=1080)
        root._last_child_ids = defaultdict(int)
        root.tk = Mock()
        yield root

@pytest.fixture
def mock_app(mock_tk_root):
    app = Mock()
    app.master = mock_tk_root
    app.is_fullscreen = False
    app.toggle_fullscreen = Mock()
    app.navigate = Mock()
    return app

@pytest.fixture
def mock_state():
    from src.core import state
    original_state = {}
    for attr in dir(state):
        if not attr.startswith('_'):
            original_state[attr] = getattr(state, attr, None)
    
    state.is_failed = False
    state.error_message = ""
    state.sku_name = "Test SKU"
    state.pkg_x = "296.0"
    state.pkg_y = "394.5831"
    
    yield state
    
    for attr, value in original_state.items():
        setattr(state, attr, value)

@pytest.fixture
def mock_canvas_dependencies(monkeypatch):
    mock_jig = Mock()
    mock_slots = Mock()
    mock_majors = Mock()
    mock_images = Mock()
    mock_exporter = Mock()
    mock_fonts = Mock()
    mock_custom_images = Mock()
    
    mock_jig.scaled_pt = Mock(return_value=10)
    mock_jig.update_all_text_fonts = Mock()
    mock_jig.update_rect_overlay = Mock()
    mock_jig.jig_rect_px = Mock(return_value=(0, 0, 100, 100))
    mock_jig.jig_inner_rect_px = Mock(return_value=(5, 5, 95, 95))
    mock_jig.item_outline_half_px = Mock(return_value=1)
    mock_jig.update_scrollregion = Mock()
    mock_jig.center_view = Mock()
    mock_jig.redraw_jig = Mock()
    mock_jig.zoom_step = Mock()
    
    mock_images.rotated_bounds_px = Mock(return_value=(0, 0, 100, 100))
    mock_images.rotated_bounds_mm = Mock(return_value=(0, 0, 10, 10))
    mock_images.render_photo = Mock(return_value=Mock())
    mock_images.create_image_item = Mock(return_value=1)
    
    mock_slots.create_slot_at_mm = Mock(return_value=1)
    mock_slots.place_slots = Mock()
    mock_slots.renumber_slots = Mock()
    
    mock_majors.update_major_rect = Mock()
    mock_majors.update_all_majors = Mock()
    mock_majors.place_slots_all_majors = Mock()
    mock_majors.remove_slots_for_major = Mock()
    mock_majors.place_slots_for_major = Mock()
    
    mock_exporter.render_scene_to_pdf = Mock()
    mock_exporter.render_jig_to_svg = Mock()
    mock_exporter.render_scene_to_svg = Mock()
    mock_exporter.render_single_pattern_svg = Mock()
    
    return {
        'jig': mock_jig,
        'slots': mock_slots,
        'majors': mock_majors,
        'images': mock_images,
        'exporter': mock_exporter,
        'fonts': mock_fonts,
        'custom_images': mock_custom_images
    }

@pytest.fixture
def canvas(mock_app, mock_tk_root, mock_canvas_dependencies):
    from src.screens.nonsticker.canvas import NStickerCanvasScreen
    
    canvas_screen = NStickerCanvasScreen(mock_tk_root, mock_app)
    canvas_screen.jig = mock_canvas_dependencies['jig']
    canvas_screen.jig.redraw_jig = Mock()
    canvas_screen.slots = mock_canvas_dependencies['slots']
    canvas_screen.majors = mock_canvas_dependencies['majors']
    canvas_screen.images = mock_canvas_dependencies['images']
    canvas_screen.exporter = mock_canvas_dependencies['exporter']
    canvas_screen._items = {}
    canvas_screen._majors = {}
    canvas_screen._major_sizes = {}
    canvas_screen._scene_store = {"front": [], "back": []}
    canvas_screen._asin_objects = {}
    canvas_screen.selection = Mock()
    canvas_screen.selection._normalize_z = Mock()
    yield canvas_screen

@pytest.fixture
def temp_test_dir(tmp_path):
    products_dir = tmp_path / "products"
    products_dir.mkdir()
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    return {
        'products': str(products_dir),
        'fonts': str(fonts_dir),
        'output': str(output_dir),
        'base': str(tmp_path)
    }
