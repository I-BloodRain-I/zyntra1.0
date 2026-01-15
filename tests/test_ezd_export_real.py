import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.canvas.ezd_export import EzdExporter
from src.sdk.sdk_client import SDKClient


@pytest.fixture
def sdk():
    client = SDKClient()
    client.initialize()
    yield client


@pytest.fixture
def exporter():
    return EzdExporter()


def test_text_coordinates(exporter, sdk, tmp_path):
    jig_w_mm = 200.0
    jig_h_mm = 100.0
    items = [
        {
            "type": "text",
            "text": "TestText",
            "x_mm": 10.0,
            "y_mm": 20.0,
            "font_family": "Arial",
            "font_size_pt": 12,
            "angle": 0.0
        }
    ]
    
    output_file = Path("test_text.ezd").resolve()
    exporter.export_scene(items, str(output_file), jig_w_mm=jig_w_mm, jig_h_mm=jig_h_mm)
    
    sdk.load_file(filename=str(output_file))
    error, name = sdk.get_entity_name(index=0)
    assert error == 0
    
    error, size = sdk.get_entity_size(name=name)
    assert error == 0
    
    expected_x = jig_w_mm - 10.0
    expected_y = jig_h_mm - 20.0
    print(f"\nText: expected x={expected_x}, y={expected_y}")
    print(f"Text: actual x={size['min_x']:.4f}, y={size['min_y']:.4f}")
    
    assert abs(size["min_x"] - expected_x) < 0.5
    assert abs(size["min_y"] - expected_y) < 0.5


def test_image_coordinates_and_size(exporter, sdk, tmp_path):
    jig_w_mm = 200.0
    jig_h_mm = 100.0
    product_file = Path(__file__).parent.parent / "_internal" / "products" / "Dogtag1.json"
    if not product_file.exists():
        pytest.skip("Dogtag1 product not found")
    
    import json
    with open(product_file) as f:
        product = json.load(f)
    
    asin_objects = product.get("ASINObjects", {})
    if not asin_objects:
        pytest.skip("No ASIN objects")
    
    first_asin = list(asin_objects.values())[0]
    frontside = first_asin.get("Frontside", [])
    if not frontside:
        pytest.skip("No frontside majors")
    
    slots = frontside[0].get("slots", [])
    if not slots:
        pytest.skip("No slots")
    
    objects = slots[0].get("objects", [])
    images = [obj for obj in objects if obj.get("type") == "image"]
    if not images:
        pytest.skip("No images in slot")
    
    image_obj = images[0]
    image_path = Path(__file__).parent.parent / "_internal" / "products" / image_obj["path"]
    
    if not image_path.exists():
        pytest.skip(f"Image file not found: {image_path}")
    
    items = [
        {
            "type": "image",
            "path": str(image_path),
            "x_mm": 11.0,
            "y_mm": 13.6666,
            "w_mm": 38.0,
            "h_mm": 38.0,
            "angle": 0.0
        }
    ]
    
    output_file = tmp_path / "test_image.ezd"
    exporter.export_scene(items, str(output_file), jig_w_mm=jig_w_mm, jig_h_mm=jig_h_mm)
    
    sdk.load_file(filename=str(output_file))
    error, name = sdk.get_entity_name(index=0)
    assert error == 0
    
    error, size = sdk.get_entity_size(name=name)
    assert error == 0
    
    actual_x = size["min_x"]
    actual_y = size["min_y"]
    actual_w = size["max_x"] - size["min_x"]
    actual_h = size["max_y"] - size["min_y"]
    
    expected_x = jig_w_mm - 11.0 - 38.0
    expected_y = jig_h_mm - 13.6666 - 38.0
    print(f"\nExpected: x={expected_x}, y={expected_y}, w={38.0}, h={38.0}")
    print(f"Actual:   x={actual_x:.4f}, y={actual_y:.4f}, w={actual_w:.4f}, h={actual_h:.4f}")
    
    assert abs(actual_x - expected_x) < 0.5, f"X coordinate mismatch: expected {expected_x}, got {actual_x}"
    assert abs(actual_y - expected_y) < 0.5, f"Y coordinate mismatch: expected {expected_y}, got {actual_y}"
    assert abs(actual_w - 38.0) < 0.5, f"Width mismatch: expected 38.0, got {actual_w}"
    assert abs(actual_h - 38.0) < 0.5, f"Height mismatch: expected 38.0, got {actual_h}"


def test_multiple_entities(exporter, sdk, tmp_path):
    jig_w_mm = 200.0
    jig_h_mm = 100.0
    items = [
        {
            "type": "text",
            "text": "Text1",
            "x_mm": 5.0,
            "y_mm": 5.0,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0
        },
        {
            "type": "text",
            "text": "Text2",
            "x_mm": 15.0,
            "y_mm": 25.0,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0
        }
    ]
    
    output_file = tmp_path / "test_multiple.ezd"
    exporter.export_scene(items, str(output_file), jig_w_mm=jig_w_mm, jig_h_mm=jig_h_mm)
    
    sdk.load_file(filename=str(output_file))
    count = sdk.get_entity_count()
    assert count == 2
    
    error, name1 = sdk.get_entity_name(index=0)
    assert error == 0
    error, size1 = sdk.get_entity_size(name=name1)
    assert error == 0
    expected_x1 = jig_w_mm - 5.0
    expected_y1 = jig_h_mm - 5.0
    assert abs(size1["min_x"] - expected_x1) < 0.5
    assert abs(size1["min_y"] - expected_y1) < 0.5
    
    error, name2 = sdk.get_entity_name(index=1)
    assert error == 0
    error, size2 = sdk.get_entity_size(name=name2)
    assert error == 0
    expected_x2 = jig_w_mm - 15.0
    expected_y2 = jig_h_mm - 25.0
    assert abs(size2["min_x"] - expected_x2) < 0.5
    assert abs(size2["min_y"] - expected_y2) < 0.5
