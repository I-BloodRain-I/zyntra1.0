import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error, AlignMode


class TestEntityOperations(unittest.TestCase):
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
    
    def test_get_entity_count(self):
        self.assertEqual(self.ezd.get_entity_count(), 0)
        
        self.ezd.add_text("Test1", "t1", 0, 0)
        self.assertEqual(self.ezd.get_entity_count(), 1)
        
        self.ezd.add_text("Test2", "t2", 10, 10)
        self.assertEqual(self.ezd.get_entity_count(), 2)
    
    def test_get_entity_name(self):
        names = ["entity1", "entity2", "entity3"]
        for i, name in enumerate(names):
            self.ezd.add_text(f"Text{i}", name, i * 10, i * 10)
        
        for i, expected_name in enumerate(names):
            err, name = self.ezd.get_entity_name(i)
            self.assertEqual(err, LMC1Error.SUCCESS)
            self.assertEqual(name, expected_name)
    
    def test_get_entity_size(self):
        self.ezd.add_text("Test", "text1", 10.0, 20.0, z=5.0)
        
        err, size = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(size["z"], 5.0)
        self.assertIsInstance(size["min_x"], float)
        self.assertIsInstance(size["min_y"], float)
        self.assertIsInstance(size["max_x"], float)
        self.assertIsInstance(size["max_y"], float)
    
    def test_get_all_entities_size(self):
        self.ezd.add_text("Test1", "t1", 0, 0)
        self.ezd.add_text("Test2", "t2", 100, 100)
        
        err, size = self.ezd.get_entity_size(None)
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertGreater(size["max_x"], size["min_x"])
        self.assertGreater(size["max_y"], size["min_y"])
    
    def test_delete_entity(self):
        self.ezd.add_text("Test1", "t1", 0, 0)
        self.ezd.add_text("Test2", "t2", 10, 10)
        self.assertEqual(self.ezd.get_entity_count(), 2)
        
        result = self.ezd.delete_entity("t1")
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertEqual(self.ezd.get_entity_count(), 1)
        
        err, name = self.ezd.get_entity_name(0)
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(name, "t2")
    
    def test_copy_entity(self):
        self.ezd.add_text("Original", "original", 10, 20)
        
        result = self.ezd.copy_entity("original", "copy")
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertEqual(self.ezd.get_entity_count(), 2)
        
        err, text1 = self.ezd.get_text("original")
        err, text2 = self.ezd.get_text("copy")
        self.assertEqual(text1, text2)
    
    def test_rename_entity(self):
        self.ezd.add_text("Test", "old_name", 0, 0)
        
        result = self.ezd.rename_entity("old_name", "new_name")
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        err, name = self.ezd.get_entity_name(0)
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(name, "new_name")
    
    def test_move_entity(self):
        self.ezd.add_text("Test", "text1", 10.0, 20.0)
        
        err, size_before = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        
        result = self.ezd.move_entity("text1", 5.0, 10.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_move.ezd"
        self.ezd.save_file(str(test_file))
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        
        err, size_after = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        
        self.assertAlmostEqual(size_after["min_x"], size_before["min_x"] + 5.0, places=2)
        self.assertAlmostEqual(size_after["min_y"], size_before["min_y"] + 10.0, places=2)
    
    def test_scale_entity(self):
        self.ezd.add_text("Test", "text1", 10.0, 10.0)
        
        err, size_before = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        width_before = size_before["max_x"] - size_before["min_x"]
        
        result = self.ezd.scale_entity("text1", 10.0, 10.0, 2.0, 2.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_scale.ezd"
        self.ezd.save_file(str(test_file))
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        
        err, size_after = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        width_after = size_after["max_x"] - size_after["min_x"]
        
        self.assertGreaterEqual(width_after, width_before)
    
    def test_rotate_entity(self):
        self.ezd.add_text("Test", "text1", 10.0, 10.0)
        
        err, size_before = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        
        result = self.ezd.rotate_entity("text1", 10.0, 10.0, 45.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_rotate.ezd"
        self.ezd.save_file(str(test_file))
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        
        err, size_after = self.ezd.get_entity_size("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
    
    def test_mirror_entity(self):
        self.ezd.add_text("Test", "text1", 10.0, 10.0)
        
        result = self.ezd.mirror_entity("text1", 10.0, 10.0, True, False)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_mirror.ezd"
        self.ezd.save_file(str(test_file))
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        
        self.assertEqual(self.ezd.get_entity_count(), 1)


if __name__ == "__main__":
    unittest.main()
