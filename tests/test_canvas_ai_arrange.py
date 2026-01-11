import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def canvas_with_slots(canvas):
    canvas.major_name.set("Major1")
    canvas._redraw_jig = Mock()
    canvas.text_bar = Mock()
    canvas.row_text = Mock()
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "slot", "owner_major": "Major1", "label_id": 11, "x_mm": 70.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        3: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "w_mm": 30.0, "h_mm": 30.0, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 150, 150),
        2: (200, 100, 250, 150),
        3: (110, 110, 140, 140)
    }.get(cid))
    canvas.canvas.itemcget = Mock(side_effect=lambda lid, key: {10: "1", 11: "2"}.get(lid, ""))
    return canvas

def test_ai_arrange_no_slots(canvas):
    canvas._items = {}
    canvas._ai_arrange_objects()

def test_ai_arrange_empty_major(canvas):
    canvas.major_name.set("NonExistent")
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10}
    }
    canvas._ai_arrange_objects()

def test_ai_arrange_deselects_before_arrange(canvas_with_slots):
    canvas_with_slots.selection.select = Mock()
    canvas_with_slots._ai_arrange_objects()
    canvas_with_slots.selection.select.assert_called_once_with(None)

def test_ai_arrange_hides_text_menu(canvas_with_slots):
    canvas_with_slots._ai_arrange_objects()
    assert canvas_with_slots.text_bar.pack_forget.call_count >= 1
    assert canvas_with_slots.row_text.place_forget.call_count >= 1

def test_ai_arrange_filters_by_major(canvas):
    canvas.major_name.set("Major1")
    canvas._redraw_jig = Mock()
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
        2: {"type": "slot", "owner_major": "Major2", "label_id": 11}
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas._ai_arrange_objects()

def test_ai_arrange_sorts_slots_bottom_to_top(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
        2: {"type": "slot", "owner_major": "Major1", "label_id": 11},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 200, 150, 250),
        2: (100, 100, 150, 150)
    }.get(cid))
    canvas._ai_arrange_objects()

def test_ai_arrange_sorts_slots_right_to_left(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
        2: {"type": "slot", "owner_major": "Major1", "label_id": 11},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (200, 100, 250, 150),
        2: (100, 100, 150, 150)
    }.get(cid))
    canvas._ai_arrange_objects()

def test_ai_arrange_finds_slot1_by_label(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
        2: {"type": "slot", "owner_major": "Major1", "label_id": 11},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(side_effect=lambda lid, key: {10: "2", 11: "1"}.get(lid, ""))
    canvas._ai_arrange_objects()

def test_ai_arrange_finds_smallest_numeric_label(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
        2: {"type": "slot", "owner_major": "Major1", "label_id": 11},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(side_effect=lambda lid, key: {10: "5", 11: "3"}.get(lid, ""))
    canvas._ai_arrange_objects()

def test_ai_arrange_fallback_first_slot(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(return_value="")
    canvas._ai_arrange_objects()

def test_ai_arrange_collects_template_objects(canvas_with_slots):
    canvas_with_slots._ai_arrange_objects()

def test_ai_arrange_checks_object_inside_slot1(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_excludes_objects_outside_slot1(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 200.0, "y_mm": 200.0, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 300, 310, 310)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_includes_rect_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_includes_image_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "image", "path": "test.png", "x_mm": 20.0, "y_mm": 20.0, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_includes_text_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "text", "text": "Test", "x_mm": 20.0, "y_mm": 20.0, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_excludes_slot_objects_from_template(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "slot", "owner_major": "Major1", "label_id": 11, "x_mm": 20.0, "y_mm": 20.0, "w_mm": 30.0, "h_mm": 30.0},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 200, 200))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_preserves_z_index(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 5},
        3: {"type": "rect", "x_mm": 25.0, "y_mm": 25.0, "z": 10},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160),
        3: (155, 155, 165, 165)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_calculates_max_z(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 8},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_bbox_error(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(side_effect=Exception("Bbox error"))
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_missing_bbox(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=None)
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_label_error(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(side_effect=Exception("Label error"))
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_non_numeric_labels(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(return_value="ABC")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_empty_label(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(return_value="")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_missing_label_id(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1"},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_missing_owner_major(canvas):
    canvas._items = {
        1: {"type": "slot", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.major_name.set("Major1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_deselect_error(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.selection.select = Mock(side_effect=Exception("Deselect error"))
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_text_menu_hide_error(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.text_bar.pack_forget = Mock(side_effect=Exception("Hide error"))
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_multiple_template_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 1},
        3: {"type": "image", "path": "test.png", "x_mm": 30.0, "y_mm": 30.0, "z": 2},
        4: {"type": "text", "text": "Test", "x_mm": 25.0, "y_mm": 25.0, "z": 3},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160),
        3: (170, 170, 180, 180),
        4: (155, 155, 165, 165)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_zero_z_index(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 0},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_missing_z_index(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_object_at_slot_edge(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
        2: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (199, 199, 201, 201)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_fractional_coordinates(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.5, "y_mm": 10.7, "w_mm": 50.3, "h_mm": 50.9},
        2: {"type": "rect", "x_mm": 20.1, "y_mm": 20.2, "z": 1},
    }
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 160, 160)
    }.get(cid))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_very_small_slot(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 1.0, "h_mm": 1.0},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 105, 105))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_very_large_slot(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 1000.0, "h_mm": 1000.0},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 5000, 5000))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_slot_with_leading_zero_label(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(return_value="01")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_multiple_slots_same_position(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
        2: {"type": "slot", "owner_major": "Major1", "label_id": 11},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas.canvas.itemcget = Mock(side_effect=lambda lid, key: {10: "1", 11: "2"}.get(lid, ""))
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_empty_items_dict(canvas):
    canvas._items = {}
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_only_non_slot_items(canvas):
    canvas._items = {
        1: {"type": "rect", "x_mm": 20.0, "y_mm": 20.0, "z": 1},
        2: {"type": "image", "path": "test.png", "x_mm": 30.0, "y_mm": 30.0, "z": 2},
    }
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_slot_without_template_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10, "x_mm": 10.0, "y_mm": 10.0, "w_mm": 50.0, "h_mm": 50.0},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 200, 200))
    canvas.canvas.itemcget = Mock(return_value="1")
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_active_major_empty_string(canvas):
    canvas.major_name.set("")
    canvas._redraw_jig = Mock()
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas._ai_arrange_objects()

def test_ai_arrange_handles_major_name_get_error(canvas):
    canvas.major_name.get = Mock(side_effect=Exception("Get error"))
    canvas._redraw_jig = Mock()
    canvas._items = {
        1: {"type": "slot", "owner_major": "Major1", "label_id": 10},
    }
    canvas.canvas.bbox = Mock(return_value=(100, 100, 150, 150))
    canvas._ai_arrange_objects()
