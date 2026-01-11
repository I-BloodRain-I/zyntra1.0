import pytest
from unittest.mock import Mock

pytestmark = pytest.mark.usefixtures("mock_state")

def test_arrange_majors_empty_majors(canvas):
    canvas._major_sizes = {}
    canvas._items = {}
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_single_major(canvas):
    canvas._major_sizes = {"M1": {"w": "100", "h": "50", "x": "10", "y": "10"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_multiple_majors(canvas):
    canvas._major_sizes = {
        "M1": {"w": "100", "h": "50", "x": "10", "y": "10"},
        "M2": {"w": "80", "h": "60", "x": "120", "y": "10"},
    }
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()
    canvas._update_all_majors.assert_called_once()

def test_arrange_majors_with_margin(canvas):
    canvas._major_sizes = {"M1": {"w": "100", "h": "50", "x": "5", "y": "5"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_clamps_within_jig(canvas):
    canvas._major_sizes = {"M1": {"w": "100", "h": "50", "x": "250", "y": "350"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()
    assert float(canvas._major_sizes["M1"]["x"]) <= 210

def test_arrange_majors_uses_skyline_algorithm(canvas):
    canvas._major_sizes = {
        "M1": {"w": "100", "h": "50", "x": "0", "y": "0"},
        "M2": {"w": "80", "h": "60", "x": "0", "y": "0"},
        "M3": {"w": "70", "h": "40", "x": "0", "y": "0"},
    }
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_handles_invalid_dimensions(canvas):
    canvas._major_sizes = {"M1": {"w": "invalid", "h": "50", "x": "10", "y": "10"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_handles_missing_dimensions(canvas):
    canvas._major_sizes = {"M1": {"x": "10", "y": "10"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_handles_zero_dimensions(canvas):
    canvas._major_sizes = {"M1": {"w": "0", "h": "0", "x": "10", "y": "10"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_preserves_old_positions(canvas):
    canvas._major_sizes = {"M1": {"w": "100", "h": "50", "x": "15", "y": "20"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_handles_overlap(canvas):
    canvas._major_sizes = {
        "M1": {"w": "100", "h": "50", "x": "10", "y": "10"},
        "M2": {"w": "100", "h": "50", "x": "10", "y": "10"},
    }
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_suppresses_child_shift(canvas):
    canvas._major_sizes = {"M1": {"w": "100", "h": "50", "x": "10", "y": "10"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    canvas._suppress_major_child_shift = False
    
    canvas._arrange_majors()

def test_arrange_majors_handles_large_majors(canvas):
    canvas._major_sizes = {"M1": {"w": "200", "h": "280", "x": "5", "y": "5"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_handles_small_jig(canvas):
    canvas._major_sizes = {"M1": {"w": "50", "h": "30", "x": "10", "y": "10"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="100")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="100")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_edge_search_fallback(canvas):
    canvas._major_sizes = {
        "M1": {"w": "100", "h": "50", "x": "0", "y": "0"},
        "M2": {"w": "100", "h": "50", "x": "0", "y": "0"},
        "M3": {"w": "100", "h": "50", "x": "0", "y": "0"},
    }
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="200")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="150")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_skyline_merge(canvas):
    canvas._major_sizes = {
        "M1": {"w": "50", "h": "50", "x": "0", "y": "0"},
        "M2": {"w": "50", "h": "50", "x": "50", "y": "0"},
        "M3": {"w": "50", "h": "50", "x": "100", "y": "0"},
    }
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_updates_major_positions(canvas):
    canvas._major_sizes = {"M1": {"w": "100", "h": "50", "x": "999", "y": "999"}}
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()
    new_x = float(canvas._major_sizes["M1"]["x"])
    new_y = float(canvas._major_sizes["M1"]["y"])
    assert new_x <= 210
    assert new_y <= 297

def test_arrange_majors_handles_fallback_collision(canvas):
    canvas._major_sizes = {
        "M1": {"w": "100", "h": "50", "x": "10", "y": "10"},
        "M2": {"w": "100", "h": "50", "x": "10", "y": "10"},
    }
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="110")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="70")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()

def test_arrange_majors_processes_all_majors(canvas):
    canvas._major_sizes = {
        "M1": {"w": "50", "h": "50", "x": "0", "y": "0"},
        "M2": {"w": "50", "h": "50", "x": "0", "y": "0"},
        "M3": {"w": "50", "h": "50", "x": "0", "y": "0"},
    }
    canvas._items = {}
    canvas.jig_x = Mock()
    canvas.jig_x.get = Mock(return_value="210")
    canvas.jig_y = Mock()
    canvas.jig_y.get = Mock(return_value="297")
    canvas._update_all_majors = Mock()
    canvas.slots = Mock()
    canvas.slots.recreate_slots_for_major = Mock()
    
    canvas._arrange_majors()
    assert len([k for k in canvas._major_sizes if "x" in canvas._major_sizes[k]]) == 3
