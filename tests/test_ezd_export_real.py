import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.canvas.ezd_export import EzdExporter
from src.canvas.pen_settings import PenSettings, PenCollection
from src.sdk.sdk_client import SDKClient


@pytest.fixture(scope="module")
def sdk():
    SDKClient.reset()
    client = SDKClient()
    client.initialize()
    yield client
    SDKClient.reset()


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


def test_pen_settings_applied(exporter, sdk, tmp_path):
    jig_w_mm = 100.0
    jig_h_mm = 100.0
    
    pen_collection = PenCollection()
    
    pen1 = pen_collection.get_pen(1)
    pen1.speed = 1500.0
    pen1.power = 50.0
    pen1.frequency = 55.0
    pen1.loop_count = 2
    pen1.jump_speed = 5000.0
    pen1.jump_position_tc = 600.0
    pen1.jump_dist_tc = 150.0
    pen1.start_tc = -250.0
    pen1.laser_off_tc = 250.0
    pen1.end_tc = 350.0
    pen1.polygon_tc = 120.0
    pen1.end_compensate = 10.0
    pen1.acc_distance = 5.0
    pen1.time_per_point = 0.5
    pen1.vector_point_mode = True
    pen1.pulse_per_point = 3
    pen_collection.set_pen(1, pen1)
    
    pen2 = pen_collection.get_pen(2)
    pen2.speed = 2000.0
    pen2.power = 60.0
    pen2.frequency = 40.0
    pen2.wobble_enabled = True
    pen2.wobble_diameter = 2.5
    pen2.wobble_distance = 0.8
    pen_collection.set_pen(2, pen2)
    
    pen3 = pen_collection.get_pen(3)
    pen_collection.set_pen(3, pen3)
    
    items = [
        {
            "type": "text",
            "text": "Pen1",
            "x_mm": 20.0,
            "y_mm": 20.0,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0,
            "pen": 1
        },
        {
            "type": "text",
            "text": "Pen2Wobble",
            "x_mm": 40.0,
            "y_mm": 40.0,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0,
            "pen": 2
        },
        {
            "type": "text",
            "text": "Pen3Hatch",
            "x_mm": 60.0,
            "y_mm": 60.0,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0,
            "pen": 3
        }
    ]
    
    output_file = tmp_path / "test_all_pen_features.ezd"
    result = exporter.export_scene(
        items, 
        str(output_file), 
        jig_w_mm=jig_w_mm, 
        jig_h_mm=jig_h_mm, 
        pen_collection=pen_collection
    )
    
    assert result is True
    assert output_file.exists()
    assert output_file.stat().st_size > 0
    
    sdk.load_file(filename=str(output_file))
    count = sdk.get_entity_count()
    assert count == 3
    
    error1, params1 = sdk.get_pen_param(pen_no=1)
    assert error1 == 0
    assert params1["loop_count"] == 2
    assert abs(params1["speed"] - 1500.0) < 0.01
    assert abs(params1["power"] - 50.0) < 0.01
    assert abs(params1["current"] - 0.0) < 0.01
    assert params1["frequency"] == 55000
    assert abs(params1["pulse_width"] - 0.0) < 0.01
    assert params1["start_tc"] == -250
    assert params1["laser_off_tc"] == 250
    assert params1["end_tc"] == 350
    assert params1["polygon_tc"] == 120
    assert abs(params1["jump_speed"] - 5000.0) < 0.01
    assert params1["jump_pos_tc"] == 600
    assert params1["jump_dist_tc"] == 150
    assert abs(params1["end_comp"] - 10.0) < 0.01
    assert abs(params1["acc_dist"] - 5.0) < 0.01
    assert abs(params1["point_time"] - 0.5) < 0.01
    assert params1["pulse_point_mode"] is True
    assert params1["pulse_num"] == 3
    assert abs(params1["fly_speed"] - 0.0) < 0.01
    
    error2, params2 = sdk.get_pen_param_wobble(pen_no=2)
    assert error2 == 0
    assert abs(params2["speed"] - 2000.0) < 0.01
    assert abs(params2["power"] - 60.0) < 0.01
    assert params2["frequency"] == 40000
    assert params2["wobble_mode"] is True
    assert abs(params2["wobble_diameter"] - 2.5) < 0.01
    assert abs(params2["wobble_distance"] - 0.8) < 0.01


def test_pen_settings_with_wobble(exporter, sdk, tmp_path):
    jig_w_mm = 100.0
    jig_h_mm = 100.0
    
    pen_collection = PenCollection()
    pen66 = pen_collection.get_pen(66)
    pen66.speed = 2500.0
    pen66.power = 80.0
    pen66.frequency = 50.0
    pen66.loop_count = 2
    pen66.jump_speed = 5000.0
    pen66.jump_position_tc = 500.0
    pen66.jump_dist_tc = 600.0
    pen66.start_tc = 100.0
    pen66.laser_off_tc = 200.0
    pen66.end_tc = 300.0
    pen66.polygon_tc = 150.0
    pen66.wobble_enabled = True
    pen66.wobble_diameter = 1.5
    pen66.wobble_distance = 0.2
    pen_collection.set_pen(66, pen66)
    
    items = [
        {
            "type": "text",
            "text": "WobbleTest",
            "x_mm": 50.0,
            "y_mm": 50.0,
            "font_family": "Arial",
            "font_size_pt": 12,
            "angle": 0.0,
            "pen": 66
        }
    ]
    
    output_file = tmp_path / "test_pen_wobble.ezd"
    result = exporter.export_scene(
        items, 
        str(output_file), 
        jig_w_mm=jig_w_mm, 
        jig_h_mm=jig_h_mm, 
        pen_collection=pen_collection
    )
    
    assert result is True
    assert output_file.exists()
    
    sdk.load_file(filename=str(output_file))
    
    error, params = sdk.get_pen_param_wobble(pen_no=66)
    assert error == 0
    
    assert abs(params["speed"] - 2500.0) < 0.01
    assert abs(params["power"] - 80.0) < 0.01
    assert params["frequency"] == 50000
    assert params["loop_count"] == 2
    assert abs(params["jump_speed"] - 5000.0) < 0.01
    assert params["jump_pos_tc"] == 500
    assert params["jump_dist_tc"] == 600
    assert params["start_tc"] == 100
    assert params["laser_off_tc"] == 200
    assert params["end_tc"] == 300
    assert params["polygon_tc"] == 150
    assert params["wobble_mode"] is True
    assert abs(params["wobble_diameter"] - 1.5) < 0.001
    assert abs(params["wobble_distance"] - 0.2) < 0.001


def test_entity_pen_assignment(exporter, sdk, tmp_path):
    jig_w_mm = 100.0
    jig_h_mm = 100.0
    
    items = [
        {
            "type": "text",
            "text": "Pen10Text",
            "x_mm": 25.0,
            "y_mm": 25.0,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0,
            "pen": 10
        },
        {
            "type": "text",
            "text": "Pen20Text",
            "x_mm": 75.0,
            "y_mm": 75.0,
            "font_family": "Arial",
            "font_size_pt": 10,
            "angle": 0.0,
            "pen": 20
        }
    ]
    
    output_file = tmp_path / "test_entity_pen.ezd"
    result = exporter.export_scene(items, str(output_file), jig_w_mm=jig_w_mm, jig_h_mm=jig_h_mm)
    
    assert result is True
    assert output_file.exists()
    
    sdk.load_file(filename=str(output_file))
    count = sdk.get_entity_count()
    assert count == 2
    
    error, name0 = sdk.get_entity_name(index=0)
    assert error == 0
    set_result0 = sdk.set_entity_pen(entity_name=name0, pen_no=10)
    assert set_result0 == 0
    
    error, name1 = sdk.get_entity_name(index=1)
    assert error == 0
    set_result1 = sdk.set_entity_pen(entity_name=name1, pen_no=20)
    assert set_result1 == 0


def test_all_pen_parameters(sdk):
    pen_no = 77
    
    set_result = sdk.set_pen_param(
        pen_no=pen_no,
        loop_count=5,
        speed=1800.0,
        power=65.0,
        current=2.5,
        frequency=40000,
        pulse_width=8.0,
        start_tc=120,
        laser_off_tc=180,
        end_tc=280,
        polygon_tc=380,
        jump_speed=3500.0,
        jump_pos_tc=450,
        jump_dist_tc=550,
        end_comp=0.15,
        acc_dist=0.25,
        point_time=0.8,
        pulse_point_mode=True,
        pulse_num=10,
        fly_speed=1200.0
    )
    assert set_result == 0
    
    get_result, params = sdk.get_pen_param(pen_no=pen_no)
    assert get_result == 0
    
    assert params["loop_count"] == 5
    assert abs(params["speed"] - 1800.0) < 0.01
    assert abs(params["power"] - 65.0) < 0.01
    assert abs(params["current"] - 2.5) < 0.01
    assert params["frequency"] == 40000
    assert abs(params["pulse_width"] - 8.0) < 0.01
    assert params["start_tc"] == 120
    assert params["laser_off_tc"] == 180
    assert params["end_tc"] == 280
    assert params["polygon_tc"] == 380
    assert abs(params["jump_speed"] - 3500.0) < 0.01
    assert params["jump_pos_tc"] == 450
    assert params["jump_dist_tc"] == 550
    assert abs(params["end_comp"] - 0.15) < 0.01
    assert abs(params["acc_dist"] - 0.25) < 0.01
    assert abs(params["point_time"] - 0.8) < 0.01
    assert params["pulse_point_mode"] is True
    assert params["pulse_num"] == 10
    assert abs(params["fly_speed"] - 1200.0) < 0.01


def test_pen_param_wobble(sdk):
    pen_no = 88
    
    set_result = sdk.set_pen_param_wobble(
        pen_no=pen_no,
        loop_count=3,
        speed=2200.0,
        power=70.0,
        current=1.5,
        frequency=35000,
        pulse_width=15.0,
        start_tc=200,
        laser_off_tc=300,
        end_tc=400,
        polygon_tc=500,
        jump_speed=5000.0,
        jump_pos_tc=600,
        jump_dist_tc=700,
        spi_wave=3,
        wobble_mode=True,
        wobble_diameter=1.5,
        wobble_distance=0.1
    )
    assert set_result == 0
    
    get_result, params = sdk.get_pen_param_wobble(pen_no=pen_no)
    assert get_result == 0
    
    assert params["loop_count"] == 3
    assert abs(params["speed"] - 2200.0) < 0.01
    assert abs(params["power"] - 70.0) < 0.01
    assert abs(params["current"] - 1.5) < 0.01
    assert params["frequency"] == 35000
    assert abs(params["pulse_width"] - 15.0) < 0.01
    assert params["start_tc"] == 200
    assert params["laser_off_tc"] == 300
    assert params["end_tc"] == 400
    assert params["polygon_tc"] == 500
    assert abs(params["jump_speed"] - 5000.0) < 0.01
    assert params["jump_pos_tc"] == 600
    assert params["jump_dist_tc"] == 700
    assert params["spi_wave"] == 3
    assert params["wobble_mode"] is True
    assert abs(params["wobble_diameter"] - 1.5) < 0.001
    assert abs(params["wobble_distance"] - 0.1) < 0.001


def test_hatch_param_enable_contour(sdk):
    result = sdk.set_hatch_param(
        enable_contour=True,
        enable_hatch1=False,
        enable_hatch2=False
    )
    assert result == 0


def test_hatch_param_hatch1_settings(sdk):
    result = sdk.set_hatch_param(
        enable_contour=True,
        enable_hatch1=True,
        pen_no1=5,
        hatch_attrib1=0x08,
        edge_dist1=0.05,
        line_dist1=0.1,
        start_offset1=0.02,
        end_offset1=0.03,
        angle1=0.785398,
        enable_hatch2=False
    )
    assert result == 0


def test_hatch_param_hatch2_settings(sdk):
    result = sdk.set_hatch_param(
        enable_contour=False,
        enable_hatch1=True,
        pen_no1=3,
        hatch_attrib1=0x01,
        edge_dist1=0.08,
        line_dist1=0.15,
        start_offset1=0.0,
        end_offset1=0.0,
        angle1=0.0,
        enable_hatch2=True,
        pen_no2=7,
        hatch_attrib2=0x10,
        edge_dist2=0.1,
        line_dist2=0.2,
        start_offset2=0.05,
        end_offset2=0.05,
        angle2=1.5708
    )
    assert result == 0


def test_hatch_param_all_attributes(sdk):
    from src.sdk.ezcad_sdk import HatchAttribute
    
    attrib1 = HatchAttribute.ALL_CALC | HatchAttribute.BI_DIR | HatchAttribute.EDGE
    attrib2 = HatchAttribute.LOOP
    
    result = sdk.set_hatch_param(
        enable_contour=True,
        enable_hatch1=True,
        pen_no1=10,
        hatch_attrib1=attrib1,
        edge_dist1=0.02,
        line_dist1=0.08,
        start_offset1=0.01,
        end_offset1=0.01,
        angle1=0.523599,
        enable_hatch2=True,
        pen_no2=15,
        hatch_attrib2=attrib2,
        edge_dist2=0.03,
        line_dist2=0.12,
        start_offset2=0.02,
        end_offset2=0.02,
        angle2=1.0472
    )
    assert result == 0