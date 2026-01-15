import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error, AlignMode


class TestTextOperations(unittest.TestCase):
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
    
    def test_add_text_basic(self):
        result = self.ezd.add_text("Hello", "text1", 10.0, 20.0)
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        count = self.ezd.get_entity_count()
        self.assertEqual(count, 1)
        
        err, name = self.ezd.get_entity_name(0)
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(name, "text1")
    
    def test_add_text_with_parameters(self):
        self.ezd.set_font(
            font_name="Arial",
            height=10.0,
            width=8.0,
            char_angle=0.0,
            char_space=1.0,
            line_space=2.0
        )
        
        result = self.ezd.add_text(
            text="Test Text",
            name="text_param",
            x=15.0,
            y=25.0,
            z=5.0,
            align=AlignMode.MIDDLE_CENTER,
            angle=0.5,
            pen=1
        )
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        err, size = self.ezd.get_entity_size("text_param")
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(size["z"], 5.0)
    
    def test_change_text(self):
        self.ezd.add_text("Original", "text1", 0, 0)
        
        result = self.ezd.change_text("text1", "Modified")
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_change_text.ezd"
        self.ezd.save_file(str(test_file))
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        
        err, text = self.ezd.get_text("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(text, "Modified")
    
    def test_get_text(self):
        test_text = "GetTextTest"
        self.ezd.add_text(test_text, "text1", 0, 0)
        
        err, retrieved_text = self.ezd.get_text("text1")
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(retrieved_text, test_text)
    
    def test_add_multiple_texts(self):
        texts = [
            ("Text1", "t1", 0, 0),
            ("Text2", "t2", 10, 10),
            ("Text3", "t3", 20, 20),
        ]
        
        for text, name, x, y in texts:
            result = self.ezd.add_text(text, name, x, y)
            self.assertEqual(result, LMC1Error.SUCCESS)
        
        count = self.ezd.get_entity_count()
        self.assertEqual(count, len(texts))
        
        for i, (text, name, _, _) in enumerate(texts):
            err, entity_name = self.ezd.get_entity_name(i)
            self.assertEqual(err, LMC1Error.SUCCESS)
            self.assertEqual(entity_name, name)


if __name__ == "__main__":
    unittest.main()
