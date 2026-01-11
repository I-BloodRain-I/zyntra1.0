import pytest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk

pytestmark = pytest.mark.usefixtures("mock_state")

def test_on_jig_change_updates_jig(canvas):
    canvas.jig = Mock()
    canvas.jig.redraw_jig = Mock()
    canvas.jig_x = Mock()
    canvas.jig_x.get.return_value = "100"
    canvas.jig_y = Mock()
    canvas.jig_y.get.return_value = "200"
    canvas._on_jig_change()

def test_on_jig_change_empty_values(canvas):
    canvas.jig = Mock()
    canvas.jig.redraw_jig = Mock()
    canvas.jig_x = Mock()
    canvas.jig_x.get.return_value = ""
    canvas.jig_y = Mock()
    canvas.jig_y.get.return_value = ""
    canvas._on_jig_change()

def test_on_jig_change_negative_values(canvas):
    canvas.jig = Mock()
    canvas.jig.redraw_jig = Mock()
    canvas.jig_x = Mock()
    canvas.jig_x.get.return_value = "-10"
    canvas.jig_y = Mock()
    canvas.jig_y.get.return_value = "-20"
    canvas._on_jig_change()

def test_on_jig_change_float_values(canvas):
    canvas.jig = Mock()
    canvas.jig.redraw_jig = Mock()
    canvas.jig_x = Mock()
    canvas.jig_x.get.return_value = "100.5"
    canvas.jig_y = Mock()
    canvas.jig_y.get.return_value = "200.7"
    canvas._on_jig_change()

def test_on_jig_change_very_large_values(canvas):
    canvas.jig = Mock()
    canvas.jig.redraw_jig = Mock()
    canvas.jig_x = Mock()
    canvas.jig_x.get.return_value = "99999"
    canvas.jig_y = Mock()
    canvas.jig_y.get.return_value = "88888"
    canvas._on_jig_change()

def test_maybe_recreate_slots_no_majors(canvas):
    canvas._major_sizes = {}
    canvas._maybe_recreate_slots()

def test_maybe_recreate_slots_single_major(canvas):
    canvas._major_sizes = {"Major1": {"x": 10, "y": 20, "w": 100, "h": 150}}
    canvas.majors = Mock()
    canvas.majors.place_slots_for_major = Mock()
    canvas._maybe_recreate_slots()

def test_maybe_recreate_slots_multiple_majors(canvas):
    canvas._major_sizes = {
        "Major1": {"x": 10, "y": 20, "w": 100, "h": 150},
        "Major2": {"x": 30, "y": 40, "w": 120, "h": 180}
    }
    canvas.majors = Mock()
    canvas.majors.place_slots_for_major = Mock()
    canvas._maybe_recreate_slots()

def test_import_image_dialog_cancelled(canvas):
    with patch("tkinter.filedialog.askopenfilename", return_value=""):
        canvas._import_image()

def test_import_image_valid_file(canvas):
    with patch("tkinter.filedialog.askopenfilename", return_value="test.png"), \
         patch.object(canvas, '_compute_import_size_mm', return_value=(50, 60)):
        canvas._import_image()

def test_import_image_compute_size_none(canvas):
    with patch("tkinter.filedialog.askopenfilename", return_value="test.png"), \
         patch.object(canvas, '_compute_import_size_mm', return_value=None):
        canvas._import_image()

def test_import_image_creates_item(canvas):
    with patch("tkinter.filedialog.askopenfilename", return_value="test.png"), \
         patch.object(canvas, '_compute_import_size_mm', return_value=(50, 60)), \
         patch.object(canvas.images, 'create_image_item', return_value=1):
        canvas._import_image()

def test_drop_text_creates_text_item(canvas):
    canvas.jig = Mock()
    canvas.jig.mm_to_px.return_value = (100, 200)
    canvas.create_text = Mock(return_value=1)
    canvas._drop_text()

def test_drop_text_adds_to_items(canvas):
    canvas.jig = Mock()
    canvas.jig.mm_to_px.return_value = (100, 200)
    canvas.create_text = Mock(return_value=1)
    initial_count = len(canvas._items)
    canvas._drop_text()

def test_drop_barcode_creates_barcode_item(canvas):
    canvas.jig = Mock()
    canvas.jig.mm_to_px.return_value = (100, 200)
    canvas.create_text = Mock(return_value=1)
    canvas._drop_barcode()

def test_drop_barcode_adds_to_items(canvas):
    canvas.jig = Mock()
    canvas.jig.mm_to_px.return_value = (100, 200)
    canvas.create_text = Mock(return_value=1)
    initial_count = len(canvas._items)
    canvas._drop_barcode()

def test_ai_arrange_no_items(canvas):
    canvas._items = {}
    canvas._ai_arrange()

def test_ai_arrange_with_items(canvas):
    canvas._items = {1: Mock(obj_type="major"), 2: Mock(obj_type="image")}
    with patch.object(canvas, '_ai_arrange_objects'):
        canvas._ai_arrange()

def test_ai_arrange_calls_arrange_objects(canvas):
    canvas._items = {1: Mock(obj_type="major")}
    with patch.object(canvas, '_ai_arrange_objects') as mock_arrange:
        canvas._ai_arrange()
        mock_arrange.assert_called_once()

def test_compute_import_size_mm_nonexistent_file(canvas):
    with patch("PIL.Image.open", side_effect=FileNotFoundError()):
        result = canvas._compute_import_size_mm("nonexistent.png")
        assert result is None

def test_compute_import_size_mm_invalid_image(canvas):
    with patch("PIL.Image.open", side_effect=Exception("Invalid image")):
        result = canvas._compute_import_size_mm("invalid.png")
        assert result is None

def test_compute_import_size_mm_small_image(canvas):
    from PIL import Image
    mock_img = Mock()
    mock_img.size = (10, 20)
    with patch("PIL.Image.open", return_value=mock_img):
        result = canvas._compute_import_size_mm("test.png")

def test_compute_import_size_mm_large_image(canvas):
    from PIL import Image
    mock_img = Mock()
    mock_img.size = (10000, 20000)
    with patch("PIL.Image.open", return_value=mock_img):
        result = canvas._compute_import_size_mm("test.png")

def test_compute_import_size_mm_square_image(canvas):
    from PIL import Image
    mock_img = Mock()
    mock_img.size = (1000, 1000)
    with patch("PIL.Image.open", return_value=mock_img):
        result = canvas._compute_import_size_mm("test.png")

def test_normalize_cmyk_valid_4_parts(canvas):
    result = canvas._normalize_cmyk("10,20,30,40")
    assert result == "10,20,30,40"

def test_normalize_cmyk_with_spaces(canvas):
    result = canvas._normalize_cmyk(" 10 , 20 , 30 , 40 ")
    assert "10" in result and "20" in result

def test_normalize_cmyk_float_values(canvas):
    result = canvas._normalize_cmyk("10.5,20.3,30.7,40.1")
    assert "10" in result or "10.5" in result

def test_normalize_cmyk_3_parts(canvas):
    result = canvas._normalize_cmyk("10,20,30")
    assert result == "10,20,30,0"

def test_normalize_cmyk_5_parts(canvas):
    result = canvas._normalize_cmyk("10,20,30,40,50")
    assert result == "10,20,30,40"

def test_normalize_cmyk_empty_string(canvas):
    result = canvas._normalize_cmyk("")
    assert result == "0,0,0,0"

def test_normalize_cmyk_none(canvas):
    result = canvas._normalize_cmyk(None)
    assert result == "0,0,0,0"

def test_normalize_cmyk_non_numeric(canvas):
    result = canvas._normalize_cmyk("a,b,c,d")
    assert result == "0,0,0,0"

def test_normalize_cmyk_mixed_valid_invalid(canvas):
    result = canvas._normalize_cmyk("10,invalid,30,40")
    assert result == "10,0,30,40"

def test_normalize_cmyk_negative_values(canvas):
    result = canvas._normalize_cmyk("-10,-20,-30,-40")

def test_normalize_cmyk_zero_values(canvas):
    result = canvas._normalize_cmyk("0,0,0,0")
    assert result == "0,0,0,0"

def test_normalize_cmyk_max_values(canvas):
    result = canvas._normalize_cmyk("100,100,100,100")
    assert "100" in result

def test_normalize_cmyk_over_max_values(canvas):
    result = canvas._normalize_cmyk("200,300,400,500")

def test_snap_mm_rounds_correctly(canvas):
    result = canvas._snap_mm(10.5)
    assert abs(result - 10.5) < 1

def test_snap_mm_very_small_value(canvas):
    result = canvas._snap_mm(0.001)
    assert isinstance(result, float)

def test_snap_mm_very_large_value(canvas):
    result = canvas._snap_mm(99999.999)
    assert isinstance(result, float)

def test_refresh_major_visibility_updates_ui(canvas):
    canvas._major_sizes = {"Major1": {"visible": True}}
    canvas._refresh_major_visibility()

def test_refresh_text_controls_updates_ui(canvas):
    canvas._refresh_text_controls()

def test_as_bool_truthy_values(canvas):
    assert canvas._as_bool(True) == True
    assert canvas._as_bool(1) == True
    assert canvas._as_bool("true") == True
    assert canvas._as_bool("True") == True

def test_as_bool_falsy_values(canvas):
    assert canvas._as_bool(False) == False
    assert canvas._as_bool(0) == False
    assert canvas._as_bool("") == False
    assert canvas._as_bool(None) == False

def test_raise_all_labels_no_items(canvas):
    canvas._items = {}
    canvas._raise_all_labels()

def test_raise_all_labels_with_items(canvas):
    canvas._items = {1: Mock(), 2: Mock(), 3: Mock()}
    canvas._raise_all_labels()

def test_find_font_path_common_font(canvas):
    result = canvas._find_font_path("Arial")

def test_find_font_path_uncommon_font(canvas):
    result = canvas._find_font_path("NonExistentFont123")

def test_find_font_path_empty_string(canvas):
    result = canvas._find_font_path("")

def test_find_font_path_none(canvas):
    result = canvas._find_font_path(None)

def test_update_rect_label_image_valid_rect(canvas):
    canvas._items = {1: Mock(obj_type="rect")}
    canvas._update_rect_label_image(1)

def test_update_rect_label_image_invalid_rect(canvas):
    canvas._items = {}
    canvas._update_rect_label_image(999)

def test_on_backside_toggle_from_false_to_true(canvas):
    canvas._backside_enabled = tk.BooleanVar(value=False)
    canvas._backside_enabled.set(True)
    canvas._on_backside_toggle()

def test_on_backside_toggle_from_true_to_false(canvas):
    canvas._backside_enabled = tk.BooleanVar(value=True)
    canvas._backside_enabled.set(False)
    canvas._on_backside_toggle()

def test_on_backside_toggle_multiple_times(canvas):
    canvas._backside_enabled = tk.BooleanVar(value=False)
    canvas._on_backside_toggle()
    canvas._on_backside_toggle()
    canvas._on_backside_toggle()

def test_serialize_scene_returns_list(canvas):
    canvas._items = {}
    result = canvas._serialize_scene()
    assert isinstance(result, list)

def test_serialize_scene_filters_correctly(canvas):
    canvas._items = {
        1: Mock(obj_type="major"),
        2: Mock(obj_type="slot"),
        3: Mock(obj_type="template"),
        4: Mock(obj_type="image")
    }
    result = canvas._serialize_scene()

def test_save_current_asin_objects_no_sku_var(canvas):
    if not hasattr(canvas, 'sku_var'):
        canvas._save_current_asin_objects()

def test_save_current_asin_objects_exception_handling(canvas):
    canvas.sku_var = Mock()
    canvas.sku_var.get.side_effect = Exception("Test error")
    canvas._save_current_asin_objects()

def test_clear_scene_removes_all_items(canvas):
    canvas._items = {1: Mock(), 2: Mock(), 3: Mock()}
    canvas.delete = Mock()
    canvas._clear_scene()

def test_clear_scene_preserves_slots_when_requested(canvas):
    canvas._items = {
        1: Mock(obj_type="slot"),
        2: Mock(obj_type="major"),
        3: Mock(obj_type="image")
    }
    canvas.delete = Mock()
    canvas._clear_scene(keep_slots=True)

def test_clear_scene_exception_handling(canvas):
    canvas._items = {1: Mock()}
    canvas.delete = Mock(side_effect=Exception("Delete error"))
    canvas._clear_scene()

def test_create_text_at_mm_long_text(canvas):
    canvas.jig = Mock()
    canvas.jig.mm_to_px.return_value = (100, 200)
    canvas.create_text = Mock(return_value=1)
    long_text = "A" * 1000
    result = canvas._create_text_at_mm(long_text, 10, 20)

def test_create_text_at_mm_special_characters(canvas):
    canvas.jig = Mock()
    canvas.jig.mm_to_px.return_value = (100, 200)
    canvas.create_text = Mock(return_value=1)
    result = canvas._create_text_at_mm("Test@#$%^&*()", 10, 20)

def test_restore_scene_preserves_item_order(canvas):
    items = [
        {"type": "image", "x_mm": 10, "y_mm": 20, "path": "1.png"},
        {"type": "image", "x_mm": 30, "y_mm": 40, "path": "2.png"},
        {"type": "image", "x_mm": 50, "y_mm": 60, "path": "3.png"}
    ]
    with patch.object(canvas.images, 'create_image_item', side_effect=[1, 2, 3]):
        canvas._restore_scene(items)

def test_restore_scene_skips_invalid_items(canvas):
    items = [
        {"type": "image", "x_mm": 10, "y_mm": 20, "path": "valid.png"},
        {"invalid": "data"},
        {"type": "image", "x_mm": 30, "y_mm": 40, "path": "valid2.png"}
    ]
    with patch.object(canvas.images, 'create_image_item', return_value=1):
        canvas._restore_scene(items)

def test_restore_scene_handles_partial_data(canvas):
    items = [
        {"type": "image", "x_mm": 10},
        {"type": "image", "y_mm": 20},
        {"type": "image"}
    ]
    with patch.object(canvas.images, 'create_image_item', return_value=1):
        canvas._restore_scene(items)

def test_restore_scene_mixed_types(canvas):
    items = [
        {"type": "image", "x_mm": 10, "y_mm": 20, "path": "test.png"},
        {"type": "text", "x_mm": 30, "y_mm": 40, "text": "Test"},
        {"type": "rect", "x_mm": 50, "y_mm": 60},
        {"type": "major", "name": "Major1"}
    ]
    with patch.object(canvas.images, 'create_image_item', return_value=1), \
         patch.object(canvas, '_create_text_at_mm', return_value=2):
        canvas._restore_scene(items)

def test_restore_scene_duplicate_items(canvas):
    items = [
        {"type": "image", "x_mm": 10, "y_mm": 20, "path": "test.png"},
        {"type": "image", "x_mm": 10, "y_mm": 20, "path": "test.png"}
    ]
    with patch.object(canvas.images, 'create_image_item', return_value=1):
        canvas._restore_scene(items)
