import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error


class TestMarkingOperations(unittest.TestCase):
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
    
    def test_mark_all(self):
        self.ezd.add_text("Test", "text1", 10, 10)
        
        result = self.ezd.mark(fly_mark=False)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.UNKNOW, LMC1Error.NODEVICE])
    
    def test_mark_entity(self):
        self.ezd.add_text("Test1", "text1", 10, 10)
        self.ezd.add_text("Test2", "text2", 20, 20)
        
        result = self.ezd.mark_entity("text1")
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_mark_entity_fly(self):
        self.ezd.add_text("FlyTest", "text1", 10, 10)
        
        result = self.ezd.mark_entity_fly("text1")
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_mark_nonexistent_entity(self):
        result = self.ezd.mark_entity("nonexistent")
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NOFINDENT])
    
    def test_red_light_mark(self):
        self.ezd.add_text("Test", "text1", 10, 10)
        
        result = self.ezd.red_light_mark()
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_mark_line(self):
        result = self.ezd.mark_line(0.0, 0.0, 10.0, 10.0, pen=0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_mark_point(self):
        result = self.ezd.mark_point(5.0, 5.0, delay=10.0, pen=0)
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_mark_multiple_entities(self):
        entities = ["e1", "e2", "e3"]
        for i, name in enumerate(entities):
            self.ezd.add_text(f"Text{i}", name, i * 10.0, i * 10.0)
        
        for name in entities:
            result = self.ezd.mark_entity(name)
            self.assertEqual(result, LMC1Error.SUCCESS)


if __name__ == "__main__":
    unittest.main()
