import pytest
from unittest.mock import Mock, patch, MagicMock, call
from tkinter import messagebox
import threading

pytestmark = pytest.mark.usefixtures("mock_state")

def test_proceed_no_asins_shows_warning(canvas, mock_state):
    canvas._asin_list = []
    canvas.sku_name_var.set("TestProduct")
    
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once_with("Missing ASINs", "Please add at least one ASIN before proceeding.")

def test_proceed_none_asin_list_shows_warning(canvas, mock_state):
    canvas._asin_list = None
    canvas.sku_name_var.set("TestProduct")
    
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once()

def test_proceed_empty_sku_name_shows_warning(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("")
    
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once_with("Missing ASIN", "Please select an ASIN name before proceeding.")

def test_proceed_short_sku_name_shows_warning(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("AB")
    
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        mock_warn.assert_called_once_with("Invalid ASIN", "ASIN name is too short.")

def test_proceed_sets_state_sku_name(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    mock_state.sku_name = ""
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert mock_state.sku_name == "TestProduct"

def test_proceed_invalid_jig_cmyk_shows_error(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._jig_cmyk_invalid = True
    
    with patch.object(messagebox, 'showerror') as mock_err:
        canvas._proceed()
        assert mock_err.called
        args = mock_err.call_args[0]
        assert "Invalid CMYK" in args[0]
        assert "Jig CMYK" in args[1]

def test_proceed_both_cmyk_invalid_shows_both_messages(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._jig_cmyk_invalid = True
    canvas._obj_cmyk_invalid = True
    
    with patch.object(messagebox, 'showerror') as mock_err:
        canvas._proceed()
        assert mock_err.called
        args = mock_err.call_args[0]
        assert "Jig CMYK" in args[1]
        assert "Object CMYK" in args[1]

def test_proceed_jig_cmyk_wrong_length_shows_error(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._jig_cmyk_invalid = False
    canvas.jig_cmyk = Mock()
    canvas.jig_cmyk.get = Mock(return_value="10,20,30")
    
    with patch.object(messagebox, 'showerror') as mock_err:
        canvas._proceed()
        assert mock_err.called

def test_proceed_sets_state_pkg_dimensions(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas.jig_x.set("100")
    canvas.jig_y.set("150")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert mock_state.pkg_x == "100"
    assert mock_state.pkg_y == "150"

def test_proceed_serializes_current_scene(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "test.png"},
        {"type": "slot", "label": "Slot1"}
    ])
    canvas._scene_store = {"front": [], "back": []}
    canvas._current_side = "front"
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert canvas._serialize_scene.called
    assert len(canvas._scene_store["front"]) == 1
    assert canvas._scene_store["front"][0]["type"] == "image"

def test_proceed_collects_slots_separately(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "test.png"},
        {"type": "slot", "label": "Slot1"},
        {"type": "slot", "label": "Slot2"}
    ])
    canvas._scene_store = {"front": [], "back": []}
    canvas._current_side = "front"
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert canvas._serialize_scene.called

def test_proceed_parses_jig_dimensions_float(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas.jig_x.set("100.5")
    canvas.jig_y.set("150.7")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()

def test_proceed_jig_dimensions_invalid_uses_default(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas.jig_x.set("invalid")
    canvas.jig_y.set("invalid")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()

def test_proceed_validates_missing_amazon_label_for_images(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {
        "ASIN1": {
            "front": [{"type": "image", "amazon_label": "", "is_static": False}],
            "back": []
        }
    }
    canvas._save_current_asin_objects = Mock()
    
    with patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        assert mock_warn.called
        args = mock_warn.call_args[0]
        assert "Missing Amazon label" in args[0]

def test_proceed_skips_validation_for_static_objects(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {
        "ASIN1": {
            "front": [{"type": "image", "amazon_label": "", "is_static": True}],
            "back": []
        }
    }
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'), patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        for call_args in mock_warn.call_args_list:
            assert "Missing Amazon label" not in call_args[0][0]

def test_proceed_skips_validation_for_slots(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {
        "ASIN1": {
            "front": [{"type": "slot", "amazon_label": ""}],
            "back": []
        }
    }
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'), patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        for call_args in mock_warn.call_args_list:
            assert "Missing Amazon label" not in call_args[0][0]

def test_proceed_skips_validation_for_barcodes(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {
        "ASIN1": {
            "front": [{"type": "barcode", "amazon_label": ""}],
            "back": []
        }
    }
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'), patch.object(messagebox, 'showwarning') as mock_warn:
        canvas._proceed()
        for call_args in mock_warn.call_args_list:
            assert "Missing Amazon label" not in call_args[0][0]

def test_proceed_calls_save_current_asin_objects(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    canvas._save_current_asin_objects.assert_called()

def test_proceed_calls_normalize_z(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    canvas.selection._normalize_z.assert_called_once()

def test_proceed_sets_is_processing_true(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    mock_state.is_processing = False
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert mock_state.is_processing == True

def test_proceed_starts_worker_thread(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread') as mock_thread:
        canvas._proceed()
        mock_thread.assert_called_once()
        assert mock_thread.call_args[1]['daemon'] == True

def test_proceed_navigates_to_results_screen(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    canvas.app.show_screen = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    canvas.app.show_screen.assert_called_once()

def test_proceed_parses_export_formats_from_format_var(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="pdf,png")
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert hasattr(canvas, '_export_formats')

def test_proceed_defaults_format_to_pdf(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert hasattr(canvas, '_export_formats')
    assert 'pdf' in canvas._export_formats

def test_proceed_parses_dpi_from_dpi_var(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="600")
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert hasattr(canvas, '_export_dpi')
    assert canvas._export_dpi == 600

def test_proceed_defaults_dpi_to_1200(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert hasattr(canvas, '_export_dpi')
    assert canvas._export_dpi == 1200

def test_proceed_sets_is_cancelled_false(canvas, mock_state):
    canvas._asin_list = ["ASIN1"]
    canvas.sku_name_var.set("TestProduct")
    canvas._serialize_scene = Mock(return_value=[])
    canvas._scene_store = {"front": [], "back": []}
    canvas._asin_objects = {"ASIN1": {"front": [], "back": []}}
    canvas._save_current_asin_objects = Mock()
    canvas.selection = Mock()
    canvas.selection._normalize_z = Mock()
    canvas._export_files_list = ["File 1"]
    canvas.exporter = Mock()
    canvas.app = Mock()
    mock_state.is_cancelled = True
    
    with patch('threading.Thread'):
        canvas._proceed()
    
    assert mock_state.is_cancelled == False
