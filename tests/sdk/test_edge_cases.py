import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error, AlignMode, HatchAttribute


class TestEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_path = Path(__file__).parent.parent.parent / "sdk"
        cls.test_files_dir = Path(__file__).parent / "test_files"
        cls.test_files_dir.mkdir(exist_ok=True)
        
    def setUp(self):
        self.ezd = EzcadSDK()
        self.ezd.initialize(test_mode=True)
        self.ezd.clear_all()
        
    def tearDown(self):
        if self.ezd.initialized:
            self.ezd.close()
        for file in self.test_files_dir.glob("*.ezd"):
            file.unlink(missing_ok=True)
    
    def test_add_text_empty_string(self):
        result = self.ezd.add_text("", "empty_text", 0, 0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_very_long_string(self):
        long_text = "A" * 1000
        result = self.ezd.add_text(long_text, "long_text", 0, 0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_special_characters(self):
        special_text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = self.ezd.add_text(special_text, "special", 0, 0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_unicode_characters(self):
        unicode_text = "Привет Мир 你好世界"
        result = self.ezd.add_text(unicode_text, "unicode", 0, 0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_negative_coordinates(self):
        result = self.ezd.add_text("test", "negative", -100.5, -200.7)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_very_large_coordinates(self):
        result = self.ezd.add_text("test", "large", 9999.9, 9999.9)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_all_alignment_modes(self):
        alignments = [
            AlignMode.BOTTOM_LEFT,
            AlignMode.BOTTOM_CENTER,
            AlignMode.BOTTOM_RIGHT,
            AlignMode.MIDDLE_LEFT,
            AlignMode.MIDDLE_CENTER,
            AlignMode.MIDDLE_RIGHT,
            AlignMode.TOP_LEFT,
            AlignMode.TOP_CENTER,
            AlignMode.TOP_RIGHT
        ]
        for i, align in enumerate(alignments):
            result = self.ezd.add_text("test", f"align_{i}", i * 10, 0, align=align)
            self.assertEqual(result, LMC1Error.SUCCESS)
        
        self.assertEqual(self.ezd.get_entity_count(), 9)
    
    def test_add_text_with_zero_angle(self):
        result = self.ezd.add_text("test", "zero_angle", 0, 0, angle=0.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_with_large_angle(self):
        result = self.ezd.add_text("test", "large_angle", 0, 0, angle=360.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_text_with_negative_angle(self):
        result = self.ezd.add_text("test", "neg_angle", 0, 0, angle=-45.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_change_text_to_empty(self):
        self.ezd.add_text("original", "text1", 0, 0)
        result = self.ezd.change_text("text1", "")
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_change_text_nonexistent_entity(self):
        result = self.ezd.change_text("nonexistent", "new text")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_get_text_nonexistent_entity(self):
        err, text = self.ezd.get_text("nonexistent")
        self.assertIn(err, [LMC1Error.PARAMERROR, LMC1Error.NOFINDENT])
    
    def test_get_entity_size_nonexistent(self):
        err, size = self.ezd.get_entity_size("nonexistent")
        self.assertEqual(err, LMC1Error.NOFINDENT)
    
    def test_get_entity_name_invalid_index(self):
        err, name = self.ezd.get_entity_name(-1)
        self.assertNotEqual(err, LMC1Error.SUCCESS)
        
        err, name = self.ezd.get_entity_name(9999)
        self.assertNotEqual(err, LMC1Error.SUCCESS)
    
    def test_move_entity_nonexistent(self):
        result = self.ezd.move_entity("nonexistent", 10, 10)
        self.assertEqual(result, LMC1Error.NOFINDENT)
    
    def test_scale_entity_nonexistent(self):
        result = self.ezd.scale_entity("nonexistent", 0, 0, 2.0, 2.0)
        self.assertEqual(result, LMC1Error.NOFINDENT)
    
    def test_scale_entity_zero_scale(self):
        self.ezd.add_text("test", "text1", 10, 10)
        result = self.ezd.scale_entity("text1", 0, 0, 0.0, 0.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_mirror_entity_nonexistent(self):
        result = self.ezd.mirror_entity("nonexistent", 0, 0, True, False)
        self.assertEqual(result, LMC1Error.NOFINDENT)
    
    def test_rotate_entity_nonexistent(self):
        result = self.ezd.rotate_entity("nonexistent", 0, 0, 45)
        self.assertEqual(result, LMC1Error.NOFINDENT)
    
    def test_delete_entity_nonexistent(self):
        result = self.ezd.delete_entity("nonexistent")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_copy_entity_nonexistent(self):
        result = self.ezd.copy_entity("nonexistent", "copy")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_copy_entity_duplicate_name(self):
        self.ezd.add_text("test", "text1", 0, 0)
        self.ezd.add_text("test2", "text2", 10, 10)
        result = self.ezd.copy_entity("text1", "text2")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_rename_entity_nonexistent(self):
        result = self.ezd.rename_entity("nonexistent", "newname")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_rename_entity_to_existing_name(self):
        self.ezd.add_text("test1", "text1", 0, 0)
        self.ezd.add_text("test2", "text2", 10, 10)
        result = self.ezd.rename_entity("text1", "text2")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_add_curve_single_point(self):
        result = self.ezd.add_curve([(0, 0)], "single_point")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.ENTEXTCOOROVER])
    
    def test_add_curve_two_points(self):
        result = self.ezd.add_curve([(0, 0), (10, 10)], "two_points")
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_curve_very_many_points(self):
        points = [(i * 0.1, i * 0.1) for i in range(1000)]
        result = self.ezd.add_curve(points, "many_points")
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_set_font_empty_name(self):
        result = self.ezd.set_font("", 5.0, 5.0)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDFONT])
    
    def test_set_font_nonexistent(self):
        result = self.ezd.set_font("NonexistentFont123", 5.0, 5.0)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDFONT])
    
    def test_set_font_zero_size(self):
        result = self.ezd.set_font("Arial", 0.0, 0.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_set_font_negative_size(self):
        result = self.ezd.set_font("Arial", -5.0, -5.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_set_hatch_all_attributes(self):
        attributes = [
            HatchAttribute.ALL_CALC,
            HatchAttribute.BI_DIR,
            HatchAttribute.EDGE,
            HatchAttribute.LOOP,
            HatchAttribute.ALL_CALC | HatchAttribute.BI_DIR,
            HatchAttribute.EDGE | HatchAttribute.LOOP,
        ]
        for attr in attributes:
            result = self.ezd.set_hatch(
                enable_contour=True,
                enable_hatch1=True,
                pen_no1=0,
                hatch_attrib1=attr,
                edge_dist1=0.1,
                line_dist1=0.1,
                start_offset1=0.0,
                end_offset1=0.0,
                angle1=0.0,
                enable_hatch2=False,
                pen_no2=0,
                hatch_attrib2=0,
                edge_dist2=0.0,
                line_dist2=0.0,
                start_offset2=0.0,
                end_offset2=0.0,
                angle2=0.0
            )
            self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_mark_entity_nonexistent(self):
        result = self.ezd.mark_entity("nonexistent")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_mark_entity_fly_nonexistent(self):
        result = self.ezd.mark_entity_fly("nonexistent")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_load_file_empty_path(self):
        result = self.ezd.load_file("")
        self.assertEqual(result, LMC1Error.READFILE)
    
    def test_save_file_empty_path(self):
        result = self.ezd.save_file("")
        self.assertIn(result, [LMC1Error.SAVEFILE, LMC1Error.READFILE])
    
    def test_add_file_empty_path(self):
        result = self.ezd.add_file("", "test", 0, 0)
        self.assertEqual(result, LMC1Error.READFILE)
    
    def test_add_file_nonexistent(self):
        result = self.ezd.add_file("nonexistent_file.ezd", "test", 0, 0)
        self.assertEqual(result, LMC1Error.READFILE)
    
    def test_multiple_clear_all(self):
        self.ezd.add_text("test", "text1", 0, 0)
        self.ezd.clear_all()
        self.assertEqual(self.ezd.get_entity_count(), 0)
        
        self.ezd.clear_all()
        self.assertEqual(self.ezd.get_entity_count(), 0)
        
        self.ezd.clear_all()
        self.assertEqual(self.ezd.get_entity_count(), 0)


if __name__ == "__main__":
    unittest.main()
