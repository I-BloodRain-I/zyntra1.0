import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import pytest


def test_render_scene_to_svg_creates_file():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    mock_screen._rotated_bounds_mm = Mock(return_value=(10.0, 10.0))
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "slot", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0, "label": "Slot 1", "z": 0},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    assert os.path.exists(temp_path)
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert '<?xml version="1.0"' in content
    assert '<svg xmlns=' in content
    assert 'width="100.000mm"' in content
    assert 'height="100.000mm"' in content
    assert 'class="slot"' in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_with_text():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "text", "x_mm": 20.0, "y_mm": 20.0, "text": "Hello World", "fill": "#ffffff",
         "font_size_pt": 12, "font_family": "Myriad Pro", "angle": 0, "z": 1,
         "text_width_mm": 30.0, "text_height_mm": 10.0},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<text" in content
    assert "Hello World" in content
    assert 'font-family="Myriad Pro"' in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_with_rect():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "rect", "x_mm": 15.0, "y_mm": 15.0, "w_mm": 30.0, "h_mm": 20.0,
         "label": "Test Label", "outline": "#d0d0d0", "label_fill": "#17a24b",
         "label_font_size": 10, "label_font_family": "Myriad Pro", "angle": 0, "z": 2},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<text" in content
    assert "Test Label" in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_with_barcode():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "barcode", "x_mm": 25.0, "y_mm": 25.0, "w_mm": 40.0, "h_mm": 15.0,
         "label": "BC001", "outline": "#000000", "label_fill": "#000000",
         "label_font_size": 8, "label_font_family": "Myriad Pro", "angle": 0, "z": 3},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<image" in content
    assert "data:image/png;base64," in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_with_rotated_text():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "text", "x_mm": 50.0, "y_mm": 50.0, "text": "Rotated", "fill": "#ff0000",
         "font_size_pt": 14, "font_family": "Myriad Pro", "angle": 45.0, "z": 1,
         "text_width_mm": 20.0, "text_height_mm": 10.0},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<text" in content
    assert "Rotated" in content
    assert "transform=" in content
    assert "rotate(" in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_z_order():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "slot", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 20.0, "h_mm": 20.0, "label": "Third", "z": 30},
        {"type": "slot", "x_mm": 10.0, "y_mm": 40.0, "w_mm": 20.0, "h_mm": 20.0, "label": "First", "z": 10},
        {"type": "slot", "x_mm": 10.0, "y_mm": 70.0, "w_mm": 20.0, "h_mm": 20.0, "label": "Second", "z": 20},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    first_pos = content.find("First")
    second_pos = content.find("Second")
    third_pos = content.find("Third")
    
    assert first_pos < second_pos < third_pos
    
    os.unlink(temp_path)


def test_render_scene_to_svg_slot_xml_escaping():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "slot", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 20.0, "h_mm": 20.0,
         "label": "Test <>&\"'", "z": 1},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "&lt;" in content
    assert "&gt;" in content
    assert "&amp;" in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_mixed_objects():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    mock_screen._rotated_bounds_mm = Mock(return_value=(20.0, 20.0))
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "slot", "x_mm": 5.0, "y_mm": 5.0, "w_mm": 40.0, "h_mm": 40.0, "label": "S1", "z": 0},
        {"type": "text", "x_mm": 10.0, "y_mm": 10.0, "text": "Text1", "fill": "#fff",
         "font_size_pt": 12, "font_family": "Myriad Pro", "angle": 0, "z": 1,
         "text_width_mm": 20.0, "text_height_mm": 10.0},
        {"type": "rect", "x_mm": 50.0, "y_mm": 10.0, "w_mm": 20.0, "h_mm": 15.0,
         "label": "Rect1", "outline": "#17a24b", "label_fill": "#fff",
         "label_font_size": 10, "label_font_family": "Myriad Pro", "angle": 0, "z": 2},
        {"type": "barcode", "x_mm": 10.0, "y_mm": 60.0, "w_mm": 30.0, "h_mm": 10.0,
         "label": "BC1", "outline": "#000", "label_fill": "#000",
         "label_font_size": 8, "label_font_family": "Myriad Pro", "angle": 0, "z": 3},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert 'class="slot"' in content
    assert "Text1" in content
    assert "Rect1" in content
    assert "<image" in content
    
    os.unlink(temp_path)


def test_svg_export_delegate_exists():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    assert hasattr(exporter, "render_scene_to_svg")
    assert callable(exporter.render_scene_to_svg)


def test_render_scene_to_svg_with_loaded_image():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    test_image = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    
    items = [
        {"type": "image", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 30.0,
         "path": "", "loaded_image": test_image, "angle": 0, "z": 1},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<image" in content
    assert "xlink:href=" in content
    assert "data:image/png;base64," in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_with_rotated_image():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    test_image = Image.new("RGBA", (100, 100), (0, 255, 0, 255))
    
    items = [
        {"type": "image", "x_mm": 20.0, "y_mm": 20.0, "w_mm": 25.0, "h_mm": 25.0,
         "path": "", "loaded_image": test_image, "angle": 90.0, "z": 1},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<image" in content
    assert 'transform="rotate(-90' in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_barcode_with_rotation():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "barcode", "x_mm": 25.0, "y_mm": 25.0, "w_mm": 40.0, "h_mm": 15.0,
         "label": "ROTATE90", "angle": 90.0, "z": 3},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=150)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<image" in content
    assert "data:image/png;base64," in content
    
    os.unlink(temp_path)


def test_render_scene_to_svg_dpi_parameter():
    from src.canvas.export import PdfExporter
    
    mock_screen = Mock()
    exporter = PdfExporter(mock_screen)
    
    items = [
        {"type": "barcode", "x_mm": 10.0, "y_mm": 10.0, "w_mm": 30.0, "h_mm": 15.0,
         "label": "DPI_TEST", "z": 1},
    ]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as f:
        temp_path = f.name
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=72)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content_72 = f.read()
    
    exporter.render_scene_to_svg(temp_path, items, 100.0, 100.0, dpi=300)
    
    with open(temp_path, "r", encoding="utf-8") as f:
        content_300 = f.read()
    
    assert len(content_300) > len(content_72)
    
    os.unlink(temp_path)
