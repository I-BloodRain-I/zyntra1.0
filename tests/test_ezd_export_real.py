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
    text_x_mm = 10.0
    text_y_mm = 20.0
    items = [
        {
            "type": "text",
            "text": "TestText",
            "x_mm": text_x_mm,
            "y_mm": text_y_mm,
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
    
    expected_center_x = text_x_mm - jig_w_mm / 2
    expected_center_y = jig_h_mm / 2 - text_y_mm
    actual_center_x = (size["min_x"] + size["max_x"]) / 2
    actual_center_y = (size["min_y"] + size["max_y"]) / 2
    
    print(f"\nText: expected center=({expected_center_x}, {expected_center_y})")
    print(f"Text: actual center=({actual_center_x:.4f}, {actual_center_y:.4f})")
    
    assert abs(actual_center_x - expected_center_x) < 0.5
    assert abs(actual_center_y - expected_center_y) < 0.5


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
    
    img_x_mm = 11.0
    img_y_mm = 13.6666
    img_w_mm = 38.0
    img_h_mm = 38.0
    
    items = [
        {
            "type": "image",
            "path": str(image_path),
            "x_mm": img_x_mm,
            "y_mm": img_y_mm,
            "w_mm": img_w_mm,
            "h_mm": img_h_mm,
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
    
    actual_center_x = (size["min_x"] + size["max_x"]) / 2
    actual_center_y = (size["min_y"] + size["max_y"]) / 2
    actual_w = size["max_x"] - size["min_x"]
    actual_h = size["max_y"] - size["min_y"]
    
    center_x_orig = img_x_mm + img_w_mm / 2
    center_y_orig = img_y_mm + img_h_mm / 2
    expected_center_x = center_x_orig - jig_w_mm / 2
    expected_center_y = jig_h_mm / 2 - center_y_orig
    
    print(f"\nExpected center: ({expected_center_x:.4f}, {expected_center_y:.4f}), w={img_w_mm}, h={img_h_mm}")
    print(f"Actual center:   ({actual_center_x:.4f}, {actual_center_y:.4f}), w={actual_w:.4f}, h={actual_h:.4f}")
    
    assert abs(actual_center_x - expected_center_x) < 0.5, f"X center mismatch: expected {expected_center_x}, got {actual_center_x}"
    assert abs(actual_center_y - expected_center_y) < 0.5, f"Y center mismatch: expected {expected_center_y}, got {actual_center_y}"
    assert abs(actual_w - img_w_mm) < 0.5, f"Width mismatch: expected {img_w_mm}, got {actual_w}"
    assert abs(actual_h - img_h_mm) < 0.5, f"Height mismatch: expected {img_h_mm}, got {actual_h}"


def test_multiple_entities(exporter, sdk, tmp_path):
    jig_w_mm = 200.0
    jig_h_mm = 100.0
    text1_x = 5.0
    text1_y = 5.0
    text2_x = 15.0
    text2_y = 25.0
    
    items = [
        {
            "type": "text",
            "text": "Text1",
            "x_mm": text1_x,
            "y_mm": text1_y,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0
        },
        {
            "type": "text",
            "text": "Text2",
            "x_mm": text2_x,
            "y_mm": text2_y,
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
    expected_center_x1 = text1_x - jig_w_mm / 2
    expected_center_y1 = jig_h_mm / 2 - text1_y
    actual_center_x1 = (size1["min_x"] + size1["max_x"]) / 2
    actual_center_y1 = (size1["min_y"] + size1["max_y"]) / 2
    assert abs(actual_center_x1 - expected_center_x1) < 0.5
    assert abs(actual_center_y1 - expected_center_y1) < 0.5
    
    error, name2 = sdk.get_entity_name(index=1)
    assert error == 0
    error, size2 = sdk.get_entity_size(name=name2)
    assert error == 0
    expected_center_x2 = text2_x - jig_w_mm / 2
    expected_center_y2 = jig_h_mm / 2 - text2_y
    actual_center_x2 = (size2["min_x"] + size2["max_x"]) / 2
    actual_center_y2 = (size2["min_y"] + size2["max_y"]) / 2
    assert abs(actual_center_x2 - expected_center_x2) < 0.5
    assert abs(actual_center_y2 - expected_center_y2) < 0.5
