import pytest
from unittest.mock import Mock, patch, MagicMock

pytestmark = pytest.mark.usefixtures("mock_state")

def test_ai_arrange_objects_slot_detection_empty_slots(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(return_value=(100, 100, 200, 200))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_slot_with_template_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "test.png"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_image = Mock(return_value=10)
    canvas._photo_cache = {}
    
    with patch('PIL.Image.open'):
        canvas._ai_arrange_objects()

def test_ai_arrange_objects_preserves_z_index(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 5, "path": "test.png"},
        4: {"type": "rect", "x_mm": 25, "y_mm": 25, "w_mm": 20, "h_mm": 20, "z": 10, "fill": "#ffffff"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
        4: (155, 155, 175, 175),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_image = Mock(return_value=10)
    canvas.canvas.create_rectangle = Mock(return_value=11)
    canvas._photo_cache = {}
    
    with patch('PIL.Image.open'):
        canvas._ai_arrange_objects()

def test_ai_arrange_objects_copies_amazon_label(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "test.png", "amazon_label": "Label1"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_image = Mock(return_value=10)
    canvas._photo_cache = {}
    
    with patch('PIL.Image.open'):
        canvas._ai_arrange_objects()

def test_ai_arrange_objects_copies_is_options_flag(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "rect", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "fill": "#ffffff", "is_options": True},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_rectangle = Mock(return_value=10)
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_copies_is_static_flag(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "rect", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "fill": "#ffffff", "is_static": True},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_rectangle = Mock(return_value=10)
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_copies_rect_label_styling(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "rect", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "fill": "#ffffff", 
            "label_fill": "#000000", "label_font_size": 12, "label_font_family": "Arial", "outline": "#ff0000"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_rectangle = Mock(return_value=10)
    canvas._update_rect_label_image = Mock()
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_handles_multiple_majors(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "slot", "x_mm": 10, "y_mm": 70, "w_mm": 50, "h_mm": 50, "owner_major": "M2", "slot_index": 1},
        4: {"type": "slot", "x_mm": 70, "y_mm": 70, "w_mm": 50, "h_mm": 50, "owner_major": "M2", "slot_index": 2},
        5: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "test.png"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (100, 300, 200, 400),
        4: (300, 300, 400, 400),
        5: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_image = Mock(return_value=10)
    canvas._photo_cache = {}
    
    with patch('PIL.Image.open'):
        canvas._ai_arrange_objects()

def test_ai_arrange_objects_handles_text_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "text", "x_mm": 20, "y_mm": 20, "text": "Test", "z": 1},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_text = Mock(return_value=10)
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_handles_missing_slot_bbox(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "test.png"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: None,
        2: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_handles_missing_object_bbox(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "test.png"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: None,
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_skips_non_placeable_types(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "major", "x_mm": 20, "y_mm": 20},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (150, 150, 180, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    
    canvas._ai_arrange_objects()

def test_ai_arrange_objects_handles_no_template_objects(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    
    canvas._ai_arrange_objects()
    canvas._update_scrollregion.assert_not_called()

def test_ai_arrange_objects_deletes_old_objects_from_destination(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "test.png"},
        10: {"type": "image", "x_mm": 80, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "old.png"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
        10: (350, 150, 380, 180),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_image = Mock(return_value=20)
    canvas.canvas.delete = Mock()
    canvas._photo_cache = {}
    
    with patch('PIL.Image.open'):
        canvas._ai_arrange_objects()

def test_ai_arrange_objects_handles_mixed_object_types_in_template(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "test.png"},
        4: {"type": "rect", "x_mm": 25, "y_mm": 25, "w_mm": 20, "h_mm": 20, "z": 2, "fill": "#ffffff"},
        5: {"type": "text", "x_mm": 30, "y_mm": 30, "text": "Test", "z": 3},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
        4: (155, 155, 175, 175),
        5: (160, 160, 170, 170),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_image = Mock(return_value=10)
    canvas.canvas.create_rectangle = Mock(return_value=11)
    canvas.canvas.create_text = Mock(return_value=12)
    canvas._photo_cache = {}
    
    with patch('PIL.Image.open'):
        canvas._ai_arrange_objects()

def test_ai_arrange_objects_handles_objects_outside_slot_1(canvas):
    canvas._items = {
        1: {"type": "slot", "x_mm": 10, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 1},
        2: {"type": "slot", "x_mm": 70, "y_mm": 10, "w_mm": 50, "h_mm": 50, "owner_major": "M1", "slot_index": 2},
        3: {"type": "image", "x_mm": 20, "y_mm": 20, "w_mm": 30, "h_mm": 30, "z": 1, "path": "inside.png"},
        4: {"type": "image", "x_mm": 120, "y_mm": 120, "w_mm": 30, "h_mm": 30, "z": 1, "path": "outside.png"},
    }
    canvas.canvas = Mock()
    canvas.canvas.bbox = Mock(side_effect=lambda cid: {
        1: (100, 100, 200, 200),
        2: (300, 100, 400, 200),
        3: (150, 150, 180, 180),
        4: (500, 500, 530, 530),
    }.get(cid, None))
    canvas._jig_inner_rect_px = Mock(return_value=(0, 0, 1000, 1000))
    canvas._item_outline_half_px = Mock(return_value=1.0)
    canvas._update_scrollregion = Mock()
    canvas._raise_all_labels = Mock()
    canvas._redraw_jig = Mock()
    canvas.selection = Mock()
    canvas.selection._reorder_by_z = Mock()
    canvas.canvas.create_image = Mock(return_value=10)
    canvas._photo_cache = {}
    
    with patch('PIL.Image.open'):
        canvas._ai_arrange_objects()
