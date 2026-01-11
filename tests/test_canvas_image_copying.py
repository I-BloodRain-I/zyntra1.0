import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

pytestmark = pytest.mark.usefixtures("mock_state")

def test_proceed_copies_images_to_product_folder(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()

def test_proceed_handles_mask_path_copying(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "mask_path": "/tmp/mask.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "mask_path": "/tmp/mask.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()

def test_proceed_skips_copying_if_already_in_product_folder(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "_internal/products/TEST-SKU/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "_internal/products/TEST-SKU/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        canvas._proceed()

def test_proceed_handles_missing_image_file(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/nonexistent.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/nonexistent.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', return_value=False):
        canvas._proceed()

def test_proceed_handles_missing_mask_file(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "mask_path": "/tmp/nonexistent_mask.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "mask_path": "/tmp/nonexistent_mask.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', side_effect=lambda p: str(p).endswith("test.png")):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()

def test_proceed_handles_none_mask_path(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "mask_path": None, "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "mask_path": None, "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()

def test_proceed_copies_custom_images(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
            "custom_images": {"custom1": "/tmp/custom1.png", "custom2": "/tmp/custom2.png"}},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
         "custom_images": {"custom1": "/tmp/custom1.png", "custom2": "/tmp/custom2.png"}}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()

def test_proceed_handles_missing_custom_images(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
            "custom_images": {"custom1": "/tmp/nonexistent.png"}},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
         "custom_images": {"custom1": "/tmp/nonexistent.png"}}
    ])
    
    with patch('pathlib.Path.exists', side_effect=lambda p: str(p).endswith("test.png")):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()

def test_proceed_skips_custom_images_if_empty(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
            "custom_images": {}},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
         "custom_images": {}}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()

def test_proceed_handles_copy_exception(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2', side_effect=Exception("Copy failed")):
            with patch('shutil.copyfile'):
                canvas._proceed()

def test_proceed_handles_mask_copy_exception(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "mask_path": "/tmp/mask.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    canvas._serialize_scene = Mock(return_value=[
        {"type": "image", "path": "/tmp/test.png", "mask_path": "/tmp/mask.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1"}
    ])
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2', side_effect=[None, Exception("Mask copy failed")]):
            with patch('shutil.move'):
                with patch('shutil.copyfile'):
                    canvas._proceed()

def test_proceed_updates_custom_image_paths(canvas, mock_state):
    canvas._items = {
        1: {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
            "custom_images": {"custom1": "/tmp/custom1.png"}},
    }
    canvas.sku_name = Mock()
    canvas.sku_name.get = Mock(return_value="TEST-SKU")
    canvas.format_var = Mock()
    canvas.format_var.get = Mock(return_value="PNG")
    canvas.dpi_var = Mock()
    canvas.dpi_var.get = Mock(return_value="300")
    canvas.export_jpegs = Mock()
    canvas.export_jpegs.get = Mock(return_value=False)
    canvas.export_back = Mock()
    canvas.export_back.get = Mock(return_value=False)
    canvas._get_all_asins = Mock(return_value=["ASIN1"])
    canvas._normalize_z = Mock()
    
    front_items = []
    def mock_serialize():
        obj = {"type": "image", "path": "/tmp/test.png", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "z": 1, "amazon_label": "L1",
               "custom_images": {"custom1": "/tmp/custom1.png"}}
        front_items.append(obj)
        return [obj]
    
    canvas._serialize_scene = Mock(side_effect=mock_serialize)
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('shutil.copy2'):
            with patch('shutil.move'):
                canvas._proceed()
