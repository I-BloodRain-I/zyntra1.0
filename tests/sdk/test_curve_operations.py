import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error


class TestCurveOperations(unittest.TestCase):
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
    
    def test_add_curve_simple(self):
        points = [(0.0, 0.0), (10.0, 10.0), (20.0, 0.0)]
        
        result = self.ezd.add_curve(points, "curve1", pen=0)
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertEqual(self.ezd.get_entity_count(), 1)
    
    def test_add_curve_rectangle(self):
        points = [
            (0.0, 0.0),
            (50.0, 0.0),
            (50.0, 30.0),
            (0.0, 30.0),
            (0.0, 0.0)
        ]
        
        result = self.ezd.add_curve(points, "rectangle", pen=0)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        err, size = self.ezd.get_entity_size("rectangle")
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertAlmostEqual(size["min_x"], 0.0, places=1)
        self.assertAlmostEqual(size["min_y"], 0.0, places=1)
        self.assertAlmostEqual(size["max_x"], 50.0, places=1)
        self.assertAlmostEqual(size["max_y"], 30.0, places=1)
    
    def test_add_curve_circle_approximation(self):
        import math
        segments = 36
        radius = 25.0
        center_x, center_y = 50.0, 50.0
        
        points = [
            (
                center_x + radius * math.cos(2 * math.pi * i / segments),
                center_y + radius * math.sin(2 * math.pi * i / segments)
            )
            for i in range(segments + 1)
        ]
        
        result = self.ezd.add_curve(points, "circle", pen=0)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        err, size = self.ezd.get_entity_size("circle")
        self.assertEqual(err, LMC1Error.SUCCESS)
        
        width = size["max_x"] - size["min_x"]
        height = size["max_y"] - size["min_y"]
        self.assertAlmostEqual(width, 2 * radius, places=0)
        self.assertAlmostEqual(height, 2 * radius, places=0)
    
    def test_add_curve_with_hatch(self):
        points = [
            (0.0, 0.0),
            (30.0, 0.0),
            (30.0, 30.0),
            (0.0, 30.0),
            (0.0, 0.0)
        ]
        
        result = self.ezd.add_curve(points, "filled_rect", pen=0, hatch=True)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_curve_hatch.ezd"
        self.ezd.save_file(str(test_file))
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        self.assertEqual(self.ezd.get_entity_count(), 1)
    
    def test_add_multiple_curves(self):
        curves = [
            ([(0.0, 0.0), (10.0, 10.0)], "curve1"),
            ([(20.0, 20.0), (30.0, 30.0)], "curve2"),
            ([(40.0, 40.0), (50.0, 50.0)], "curve3"),
        ]
        
        for points, name in curves:
            result = self.ezd.add_curve(points, name, pen=0)
            self.assertEqual(result, LMC1Error.SUCCESS)
        
        self.assertEqual(self.ezd.get_entity_count(), len(curves))
    
    def test_curve_save_and_load(self):
        points = [
            (5.0, 5.0),
            (15.0, 5.0),
            (15.0, 15.0),
            (5.0, 15.0),
            (5.0, 5.0)
        ]
        
        self.ezd.add_curve(points, "test_curve", pen=0)
        
        test_file = self.test_files_dir / "test_curve_save.ezd"
        self.ezd.save_file(str(test_file))
        
        err, size_before = self.ezd.get_entity_size("test_curve")
        
        self.ezd.clear_all()
        self.assertEqual(self.ezd.get_entity_count(), 0)
        
        self.ezd.load_file(str(test_file))
        self.assertEqual(self.ezd.get_entity_count(), 1)
        
        err, size_after = self.ezd.get_entity_size("test_curve")
        self.assertAlmostEqual(size_before["min_x"], size_after["min_x"], places=2)
        self.assertAlmostEqual(size_before["max_x"], size_after["max_x"], places=2)


if __name__ == "__main__":
    unittest.main()
