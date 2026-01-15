import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error, HatchAttribute, AlignMode


class TestAdvancedOperations(unittest.TestCase):
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
    
    def test_set_hatch_parameters(self):
        result = self.ezd.set_hatch(
            enable_contour=True,
            enable_hatch1=1,
            pen_no1=0,
            hatch_attrib1=HatchAttribute.BI_DIR | HatchAttribute.EDGE,
            edge_dist1=0.1,
            line_dist1=0.5,
            start_offset1=0.0,
            end_offset1=0.0,
            angle1=0.0,
            enable_hatch2=0,
            pen_no2=0,
            hatch_attrib2=0,
            edge_dist2=0.0,
            line_dist2=0.0,
            start_offset2=0.0,
            end_offset2=0.0,
            angle2=0.0
        )
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        points = [
            (0.0, 0.0),
            (20.0, 0.0),
            (20.0, 20.0),
            (0.0, 20.0),
            (0.0, 0.0)
        ]
        self.ezd.add_curve(points, "hatched_rect", pen=0, hatch=True)
        
        test_file = self.test_files_dir / "test_hatch.ezd"
        self.ezd.save_file(str(test_file))
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        self.assertEqual(self.ezd.get_entity_count(), 1)
    
    def test_complex_entity_workflow(self):
        self.ezd.add_text("Original", "text1", 10.0, 10.0)
        
        err, size_original = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        
        self.ezd.copy_entity("text1", "text2")
        self.assertEqual(self.ezd.get_entity_count(), 2)
        
        self.ezd.move_entity("text2", 50.0, 0.0)
        
        self.ezd.scale_entity("text2", 60.0, 10.0, 1.5, 1.5)
        
        self.ezd.rotate_entity("text2", 60.0, 10.0, 45.0)
        
        test_file = self.test_files_dir / "test_complex.ezd"
        self.ezd.save_file(str(test_file))
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        self.assertEqual(self.ezd.get_entity_count(), 2)
    
    def test_mixed_entities_workflow(self):
        self.ezd.add_text("Text Entity", "text1", 10.0, 10.0)
        
        points = [(30.0, 30.0), (50.0, 30.0), (50.0, 50.0), (30.0, 50.0), (30.0, 30.0)]
        self.ezd.add_curve(points, "curve1", pen=0)
        
        bc_result = self.ezd.add_barcode("123456", "barcode1", 70.0, 70.0)
        
        if bc_result == LMC1Error.NOFINDENT:
            expected_count = 2
        else:
            expected_count = 3
        
        self.assertEqual(self.ezd.get_entity_count(), expected_count)
        
        test_file = self.test_files_dir / "test_mixed.ezd"
        self.ezd.save_file(str(test_file))
        
        for i in range(self.ezd.get_entity_count()):
            err, name = self.ezd.get_entity_name(i)
            self.assertEqual(err, LMC1Error.SUCCESS)
            self.assertIn(name, ["text1", "curve1", "barcode1"])
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        self.assertEqual(self.ezd.get_entity_count(), expected_count)
    
    def test_entity_transformation_chain(self):
        self.ezd.add_text("Transform", "t1", 0.0, 0.0)
        
        test_file = self.test_files_dir / "test_transform_chain.ezd"
        
        transformations = [
            ("move", lambda: self.ezd.move_entity("t1", 10.0, 10.0)),
            ("scale", lambda: self.ezd.scale_entity("t1", 10.0, 10.0, 2.0, 2.0)),
            ("rotate", lambda: self.ezd.rotate_entity("t1", 10.0, 10.0, 30.0)),
            ("mirror", lambda: self.ezd.mirror_entity("t1", 10.0, 10.0, True, False)),
        ]
        
        for name, transform_func in transformations:
            result = transform_func()
            self.assertEqual(result, LMC1Error.SUCCESS)
            
            self.ezd.save_file(str(test_file))
            self.ezd.clear_all()
            self.ezd.load_file(str(test_file))
            self.assertEqual(self.ezd.get_entity_count(), 1)
    
    def test_alignment_modes(self):
        alignments = [
            AlignMode.BOTTOM_LEFT,
            AlignMode.BOTTOM_CENTER,
            AlignMode.BOTTOM_RIGHT,
            AlignMode.MIDDLE_LEFT,
            AlignMode.MIDDLE_CENTER,
            AlignMode.MIDDLE_RIGHT,
            AlignMode.TOP_LEFT,
            AlignMode.TOP_CENTER,
            AlignMode.TOP_RIGHT,
        ]
        
        for i, align in enumerate(alignments):
            self.ezd.add_text(
                f"A{i}",
                f"text_{i}",
                50.0,
                50.0,
                align=align
            )
        
        self.assertEqual(self.ezd.get_entity_count(), len(alignments))
        
        test_file = self.test_files_dir / "test_alignments.ezd"
        self.ezd.save_file(str(test_file))
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        self.assertEqual(self.ezd.get_entity_count(), len(alignments))


if __name__ == "__main__":
    unittest.main()
