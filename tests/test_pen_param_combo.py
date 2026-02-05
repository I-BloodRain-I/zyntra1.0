import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.sdk.sdk_client import SDKClient


@pytest.fixture(scope="module")
def sdk():
    SDKClient.reset()
    client = SDKClient()
    client.initialize()
    yield client
    SDKClient.reset()


def test_set_pen_param_then_wobble_preserves_advanced_params(sdk):
    pen_no = 99
    
    result1 = sdk.set_pen_param(
        pen_no=pen_no,
        loop_count=3,
        speed=2000.0,
        power=60.0,
        current=1.5,
        frequency=45,
        pulse_width=5.0,
        start_tc=150,
        laser_off_tc=250,
        end_tc=350,
        polygon_tc=450,
        jump_speed=4500.0,
        jump_pos_tc=650,
        jump_dist_tc=750,
        end_comp=5.5,
        acc_dist=7.5,
        point_time=0.75,
        pulse_point_mode=True,
        pulse_num=4,
        fly_speed=1500.0
    )
    assert result1 == 0
    
    result2 = sdk.set_pen_param_wobble(
        pen_no=pen_no,
        loop_count=3,
        speed=2000.0,
        power=60.0,
        current=1.5,
        frequency=45,
        pulse_width=5.0,
        start_tc=150,
        laser_off_tc=250,
        end_tc=350,
        polygon_tc=450,
        jump_speed=4500.0,
        jump_pos_tc=650,
        jump_dist_tc=750,
        spi_wave=2,
        wobble_mode=True,
        wobble_diameter=2.5,
        wobble_distance=1.2
    )
    assert result2 == 0
    
    error1, params1 = sdk.get_pen_param(pen_no=pen_no)
    assert error1 == 0
    
    assert params1["loop_count"] == 3
    assert abs(params1["speed"] - 2000.0) < 0.01
    assert abs(params1["power"] - 60.0) < 0.01
    assert params1["frequency"] == 45
    assert params1["start_tc"] == 150
    assert params1["end_tc"] == 350
    assert abs(params1["jump_speed"] - 4500.0) < 0.01
    assert params1["jump_pos_tc"] == 650
    assert params1["jump_dist_tc"] == 750
    
    assert abs(params1["end_comp"] - 5.5) < 0.01
    assert abs(params1["acc_dist"] - 7.5) < 0.01
    assert abs(params1["point_time"] - 0.75) < 0.01
    assert params1["pulse_point_mode"] is True
    assert params1["pulse_num"] == 4
    
    error2, params2 = sdk.get_pen_param_wobble(pen_no=pen_no)
    assert error2 == 0
    
    assert params2["wobble_mode"] is True
    assert abs(params2["wobble_diameter"] - 2.5) < 0.01
    assert abs(params2["wobble_distance"] - 1.2) < 0.01
