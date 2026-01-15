import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error, AlignMode


class TestBasicOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_path = Path(__file__).parent.parent.parent / "sdk"
        cls.test_files_dir = Path(__file__).parent / "test_files"
        cls.test_files_dir.mkdir(exist_ok=True)
        
    def setUp(self):
        self.ezd = EzcadSDK()
        result = self.ezd.initialize(test_mode=True)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
    def tearDown(self):
        if self.ezd.initialized:
            self.ezd.close()
        for file in self.test_files_dir.glob("*.ezd"):
            file.unlink(missing_ok=True)
    
    def test_initialize_and_close(self):
        self.assertTrue(self.ezd.initialized)
        result = self.ezd.close()
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertFalse(self.ezd.initialized)
    
    def test_clear_all(self):
        self.ezd.add_text("Test", "text1", 0, 0)
        count_before = self.ezd.get_entity_count()
        self.assertGreater(count_before, 0)
        
        result = self.ezd.clear_all()
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        count_after = self.ezd.get_entity_count()
        self.assertEqual(count_after, 0)
    
    def test_save_and_load_file(self):
        test_file = self.test_files_dir / "test_save.ezd"
        
        self.ezd.clear_all()
        self.ezd.add_text("SaveTest", "text1", 10, 20)
        
        result = self.ezd.save_file(str(test_file))
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertTrue(test_file.exists())
        
        self.ezd.clear_all()
        self.assertEqual(self.ezd.get_entity_count(), 0)
        
        result = self.ezd.load_file(str(test_file))
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertEqual(self.ezd.get_entity_count(), 1)
        
        err, name = self.ezd.get_entity_name(0)
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(name, "text1")


if __name__ == "__main__":
    unittest.main()
