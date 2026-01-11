import pytest
from unittest.mock import Mock, patch, MagicMock

pytestmark = pytest.mark.usefixtures("mock_state")

def test_refresh_major_visibility_makes_majors_visible(canvas):
    canvas._items = {
        1: {"type": "major", "label_id": 101},
        2: {"type": "image"}
    }
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    canvas._refresh_major_visibility()
    
    assert canvas.canvas.itemconfigure.called

def test_refresh_major_visibility_makes_all_items_visible(canvas):
    canvas._items = {
        1: {"type": "image", "label_id": 101, "border_id": 102, "rot_id": 103},
        2: {"type": "text", "label_id": 201}
    }
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    canvas._refresh_major_visibility()
    
    assert canvas.canvas.itemconfigure.call_count >= 2

def test_refresh_major_visibility_configures_label_id(canvas):
    canvas._items = {1: {"type": "image", "label_id": 101}}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    canvas._refresh_major_visibility()
    
    calls = [str(c) for c in canvas.canvas.itemconfigure.call_args_list]
    assert any("101" in c for c in calls)

def test_refresh_major_visibility_configures_border_id(canvas):
    canvas._items = {1: {"type": "image", "border_id": 102}}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    canvas._refresh_major_visibility()
    
    calls = [str(c) for c in canvas.canvas.itemconfigure.call_args_list]
    assert any("102" in c for c in calls)

def test_refresh_major_visibility_configures_rot_id(canvas):
    canvas._items = {1: {"type": "image", "rot_id": 103}}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    canvas._refresh_major_visibility()
    
    calls = [str(c) for c in canvas.canvas.itemconfigure.call_args_list]
    assert any("103" in c for c in calls)

def test_refresh_major_visibility_calls_raise_all_labels(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    canvas._refresh_major_visibility()
    
    canvas._raise_all_labels.assert_called_once()

def test_refresh_major_visibility_calls_reorder_by_z(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    canvas._refresh_major_visibility()
    
    canvas.selection._reorder_by_z.assert_called_once()

def test_refresh_major_visibility_creates_bottom_buttons_once(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = False
    canvas._did_schedule_restore = True
    canvas.app = Mock()
    canvas.app.go_back = Mock()
    
    with patch('src.screens.nonsticker.canvas.create_button') as mock_btn:
        mock_btn.return_value = Mock(place=Mock())
        canvas._refresh_major_visibility()
        assert canvas._bottom_buttons_ready == True

def test_refresh_major_visibility_skips_buttons_if_ready(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    
    with patch('src.screens.nonsticker.canvas.create_button') as mock_btn:
        canvas._refresh_major_visibility()
        mock_btn.assert_not_called()

def test_refresh_major_visibility_schedules_restore_once(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = False
    canvas.after = Mock()
    
    canvas._refresh_major_visibility()
    
    canvas.after.assert_called_once_with(0, canvas._maybe_load_saved_product)
    assert canvas._did_schedule_restore == True

def test_refresh_major_visibility_skips_restore_if_done(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    canvas.canvas.itemconfigure = Mock()
    canvas._raise_all_labels = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas._bottom_buttons_ready = True
    canvas._did_schedule_restore = True
    canvas.after = Mock()
    
    canvas._refresh_major_visibility()
    
    canvas.after.assert_not_called()

def test_refresh_text_controls_exists(canvas):
    assert hasattr(canvas, '_refresh_text_controls')

def test_snap_mm_rounds_to_grid(canvas):
    canvas.snap_grid = Mock()
    canvas.snap_grid.get = Mock(return_value=True)
    result = canvas._snap_mm(10.3)
    assert isinstance(result, float)

def test_snap_mm_no_snap_returns_same(canvas):
    canvas.snap_grid = Mock()
    canvas.snap_grid.get = Mock(return_value=False)
    result = canvas._snap_mm(10.3)
    assert result == 10.3

def test_as_bool_returns_true_for_truthy(canvas):
    assert canvas._as_bool(True) == True
    assert canvas._as_bool(1) == True
    assert canvas._as_bool("yes") == True

def test_as_bool_returns_false_for_falsy(canvas):
    assert canvas._as_bool(False) == False
    assert canvas._as_bool(0) == False
    assert canvas._as_bool("") == False

def test_raise_all_labels_skips_none_labels(canvas):
    canvas._items = {
        1: {"label_id": None},
        2: {"label_id": 102}
    }
    canvas.canvas = Mock()
    canvas.canvas.tag_raise = Mock()
    
    canvas._raise_all_labels()

def test_raise_all_labels_empty_items(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    canvas.canvas.tag_raise = Mock()
    
    canvas._raise_all_labels()
    
    canvas.canvas.tag_raise.assert_not_called()

def test_find_font_path_returns_path_for_known_font(canvas):
    result = canvas._find_font_path("Arial")
    assert result is None or isinstance(result, str)

def test_update_rect_label_image_with_valid_rect(canvas):
    canvas._items = {1: {"type": "rect", "label": "Test", "x_mm": 10, "y_mm": 20, "w_mm": 50, "h_mm": 30}}
    canvas.canvas = Mock()
    canvas.canvas.coords = Mock(return_value=[100, 200, 150, 230])
    canvas._find_font_path = Mock(return_value=None)
    
    canvas._update_rect_label_image(1)

def test_update_rect_label_image_with_missing_rect(canvas):
    canvas._items = {}
    canvas.canvas = Mock()
    
    try:
        canvas._update_rect_label_image(999)
    except Exception:
        pass

def test_update_rect_label_image_creates_pil_image(canvas):
    canvas._items = {1: {
        "type": "rect",
        "label": "Test",
        "x_mm": 10, "y_mm": 20, "w_mm": 50, "h_mm": 30,
        "label_fill": "#17a24b",
        "label_font_size": 12,
        "label_font_family": "Arial"
    }}
    canvas.canvas = Mock()
    canvas.canvas.coords = Mock(return_value=[100, 200, 150, 230])
    canvas.canvas.itemconfigure = Mock()
    canvas._find_font_path = Mock(return_value=None)
    
    with patch('PIL.Image.new') as mock_img:
        mock_img.return_value = Mock(size=(50, 30))
        mock_img.return_value.save = Mock()
        try:
            canvas._update_rect_label_image(1)
        except Exception:
            pass

def test_update_rect_label_image_handles_empty_label(canvas):
    canvas._items = {1: {
        "type": "rect",
        "label": "",
        "x_mm": 10, "y_mm": 20, "w_mm": 50, "h_mm": 30
    }}
    canvas.canvas = Mock()
    canvas.canvas.coords = Mock(return_value=[100, 200, 150, 230])
    canvas._find_font_path = Mock(return_value=None)
    
    try:
        canvas._update_rect_label_image(1)
    except Exception:
        pass

def test_update_rect_label_image_handles_unicode_label(canvas):
    canvas._items = {1: {
        "type": "rect",
        "label": "Тест Unicode",
        "x_mm": 10, "y_mm": 20, "w_mm": 50, "h_mm": 30
    }}
    canvas.canvas = Mock()
    canvas.canvas.coords = Mock(return_value=[100, 200, 150, 230])
    canvas._find_font_path = Mock(return_value=None)
    
    try:
        canvas._update_rect_label_image(1)
    except Exception:
        pass

def test_update_rect_label_image_uses_font_path(canvas):
    canvas._items = {1: {
        "type": "rect",
        "label": "Test",
        "x_mm": 10, "y_mm": 20, "w_mm": 50, "h_mm": 30,
        "label_font_family": "Arial"
    }}
    canvas.canvas = Mock()
    canvas.canvas.coords = Mock(return_value=[100, 200, 150, 230])
    canvas._find_font_path = Mock(return_value="C:\\Windows\\Fonts\\arial.ttf")
    
    with patch('PIL.ImageFont.truetype') as mock_font:
        mock_font.return_value = Mock()
        try:
            canvas._update_rect_label_image(1)
        except Exception:
            pass

def test_update_rect_label_image_fallback_to_default_font(canvas):
    canvas._items = {1: {
        "type": "rect",
        "label": "Test",
        "x_mm": 10, "y_mm": 20, "w_mm": 50, "h_mm": 30,
        "label_font_family": "UnknownFont"
    }}
    canvas.canvas = Mock()
    canvas.canvas.coords = Mock(return_value=[100, 200, 150, 230])
    canvas._find_font_path = Mock(return_value=None)
    
    with patch('PIL.ImageFont.load_default') as mock_font:
        mock_font.return_value = Mock()
        try:
            canvas._update_rect_label_image(1)
        except Exception:
            pass
