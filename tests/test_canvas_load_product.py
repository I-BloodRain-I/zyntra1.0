import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import json

pytestmark = pytest.mark.usefixtures("mock_state")

@pytest.fixture
def mock_product_data():
    return {
        "ASINs": [["ASIN123", 100]],
        "SkuName": "TestSKU",
        "Scene": {
            "jig": {"width_mm": 100, "height_mm": 200, "cmyk": "10,20,30,40"},
            "step": {},
            "origin": {},
            "slot_size": {},
            "object_cmyk": "5,10,15,20",
            "export_files": ["File 1", "File 2"],
            "front": [],
            "back": []
        }
    }

def test_maybe_load_saved_product_no_product(canvas):
    from src.core import state
    state.saved_product = None
    canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_empty_product(canvas):
    from src.core import state
    state.saved_product = ""
    canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_whitespace_product(canvas):
    from src.core import state
    state.saved_product = "   "
    canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_nonexistent_file(canvas):
    from src.core import state
    state.saved_product = "NonExistentProduct"
    canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_loads_asins(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas.sku_var.get() == "ASIN123"

def test_maybe_load_saved_product_loads_sku_name(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas.sku_name_var.get() == "TestSKU"

def test_maybe_load_saved_product_empty_asins(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [], "SkuName": "Test", "Scene": {}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_none_asins(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": None, "SkuName": "Test", "Scene": {}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_loads_jig_dimensions(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas.jig_x.get() == "100"
    assert canvas.jig_y.get() == "200"

def test_maybe_load_saved_product_loads_jig_cmyk(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas.jig_cmyk = Mock()
    canvas.jig_cmyk.get = Mock(return_value="0,0,0,0")
    canvas.jig_cmyk.set = Mock()
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    canvas.jig_cmyk.set.assert_called_once()

def test_maybe_load_saved_product_invalid_jig_cmyk(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas.jig_cmyk = Mock()
    canvas.jig_cmyk.get = Mock(return_value="0,0,0,0")
    canvas.jig_cmyk.set = Mock()
    
    data = {"Scene": {"jig": {"cmyk": "10,20"}}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas._jig_cmyk_invalid == True

def test_maybe_load_saved_product_loads_object_cmyk(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas.obj_cmyk = Mock()
    canvas.obj_cmyk.get = Mock(return_value="0,0,0,0")
    canvas.obj_cmyk.set = Mock()
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    canvas.obj_cmyk.set.assert_called_once()

def test_maybe_load_saved_product_invalid_object_cmyk(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas.obj_cmyk = Mock()
    canvas.obj_cmyk.get = Mock(return_value="0,0,0,0")
    canvas.obj_cmyk.set = Mock()
    
    data = {"Scene": {"object_cmyk": "10,20,30"}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas._obj_cmyk_invalid == True

def test_maybe_load_saved_product_loads_export_files(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas.export_file_var = Mock()
    canvas._export_file_combo = Mock()
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas._export_files_list == ["File 1", "File 2"]

def test_maybe_load_saved_product_empty_export_files(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"Scene": {"export_files": []}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_none_export_files(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"Scene": {"export_files": None}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_malformed_json(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text("{}")
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_asin_with_mirror_flag(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {
        "ASINs": [["ASIN123", 100, True]],
        "Scene": {}
    }
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas._asin_mirror.get("ASIN123") == True

def test_maybe_load_saved_product_asin_without_mirror_flag(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {
        "ASINs": [["ASIN123", 100]],
        "Scene": {}
    }
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_asin_mirror_false(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {
        "ASINs": [["ASIN123", 100, False]],
        "Scene": {}
    }
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas._asin_mirror.get("ASIN123") == False

def test_maybe_load_saved_product_multiple_asins(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {
        "ASINs": [
            ["ASIN1", 100, True],
            ["ASIN2", 200, False],
            ["ASIN3", 300]
        ],
        "Scene": {}
    }
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas._asin_mirror.get("ASIN1") == True
    assert canvas._asin_mirror.get("ASIN2") == False

def test_maybe_load_saved_product_invalid_asin_format(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {
        "ASINs": ["invalid", 123, None],
        "Scene": {}
    }
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_none_cmyk_values(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas.jig_cmyk = Mock()
    canvas.jig_cmyk.get = Mock(return_value="0,0,0,0")
    canvas.jig_cmyk.set = Mock()
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {"jig": {"cmyk": None}}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas._jig_cmyk_invalid == False

def test_maybe_load_saved_product_cmyk_with_spaces(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas.jig_cmyk = Mock()
    canvas.jig_cmyk.get = Mock(return_value="0,0,0,0")
    canvas.jig_cmyk.set = Mock()
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {"jig": {"cmyk": "10 , 20 , 30 , 40"}}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_missing_scene(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]]}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_none_scene(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": None}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_missing_jig(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_none_jig(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {"jig": None}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_unicode_product_name(canvas, tmp_path):
    from src.core import state
    state.saved_product = "Тестовий_Продукт"
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {}}
    product_file = tmp_path / "Тестовий_Продукт.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_special_chars_product_name(canvas, tmp_path):
    from src.core import state
    state.saved_product = "Product@#$"
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {}}
    product_file = tmp_path / "Product@#$.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_suppresses_major_traces(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas._suppress_major_traces = False
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_file_read_error(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text("{}")
    product_file.chmod(0o000)
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    product_file.chmod(0o644)

def test_maybe_load_saved_product_empty_json(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]]}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_missing_sku_name(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]]}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas.sku_name_var.get() == "TestProduct"

def test_maybe_load_saved_product_none_sku_name(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]], "SkuName": None}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert canvas.sku_name_var.get() == "TestProduct"

def test_maybe_load_saved_product_empty_sku_name(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]], "SkuName": ""}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_sets_state_asins(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert state.asins == [["ASIN123", 100]]

def test_maybe_load_saved_product_sets_state_sku_name(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    assert state.sku_name == "TestSKU"

def test_maybe_load_saved_product_export_file_combo_update(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas._export_file_combo = Mock()
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    canvas._export_file_combo.configure.assert_called_once()

def test_maybe_load_saved_product_export_file_selector_update(canvas, mock_product_data, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    canvas._export_file_selector_left = Mock()
    
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(mock_product_data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
    
    canvas._export_file_selector_left.configure.assert_called_once()

def test_maybe_load_saved_product_negative_dimensions(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {"jig": {"width_mm": -10, "height_mm": -20}}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()

def test_maybe_load_saved_product_very_large_dimensions(canvas, tmp_path):
    from src.core import state
    state.saved_product = "TestProduct"
    
    data = {"ASINs": [["ASIN123", 100]], "Scene": {"jig": {"width_mm": 99999.99, "height_mm": 88888.88}}}
    product_file = tmp_path / "TestProduct.json"
    product_file.write_text(json.dumps(data))
    
    with patch("src.screens.nonsticker.canvas.PRODUCTS_PATH", tmp_path):
        canvas._maybe_load_saved_product()
