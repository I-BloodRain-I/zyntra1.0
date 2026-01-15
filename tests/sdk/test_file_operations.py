import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error, AlignMode


class TestFileOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_path = Path(__file__).parent.parent.parent / "sdk"
        cls.test_files_dir = Path(__file__).parent / "test_files"
        cls.test_files_dir.mkdir(exist_ok=True)
        
        cls.sample_ezd = cls.test_files_dir / "sample.ezd"
        cls._create_sample_ezd(cls.sample_ezd)
        
    @classmethod
    def _create_sample_ezd(cls, filepath):
        ezd = EzcadSDK()
        ezd.initialize(test_mode=True)
        ezd.clear_all()
        ezd.add_text("Sample", "sample_text", 10, 10)
        ezd.save_file(str(filepath))
        ezd.close()
    
    def setUp(self):
        self.ezd = EzcadSDK()
        self.ezd.initialize(test_mode=True)
        self.ezd.clear_all()
        
    def tearDown(self):
        if self.ezd.initialized:
            self.ezd.close()
    
    @classmethod
    def tearDownClass(cls):
        for file in cls.test_files_dir.glob("*.ezd"):
            if file != cls.sample_ezd:
                file.unlink(missing_ok=True)
        cls.sample_ezd.unlink(missing_ok=True)
    
    def test_add_ezd_file(self):
        result = self.ezd.add_file(
            filename=str(self.sample_ezd),
            name="imported_ezd",
            x=20.0,
            y=30.0,
            ratio=1.0
        )
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertGreater(self.ezd.get_entity_count(), 0)
    
    def test_add_file_with_scale(self):
        result = self.ezd.add_file(
            filename=str(self.sample_ezd),
            name="scaled_file",
            x=10.0,
            y=10.0,
            ratio=2.0
        )
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_file_with_alignment(self):
        alignments = [
            AlignMode.BOTTOM_LEFT,
            AlignMode.MIDDLE_CENTER,
            AlignMode.TOP_RIGHT
        ]
        
        for i, align in enumerate(alignments):
            result = self.ezd.add_file(
                filename=str(self.sample_ezd),
                name=f"file_align_{i}",
                x=50.0,
                y=50.0,
                align=align,
                ratio=1.0
            )
            self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_file_with_z_coordinate(self):
        result = self.ezd.add_file(
            filename=str(self.sample_ezd),
            name="file_z",
            x=10.0,
            y=10.0,
            z=5.0,
            ratio=1.0
        )
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_file_z.ezd"
        self.ezd.save_file(str(test_file))
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        
        self.assertGreater(self.ezd.get_entity_count(), 0)
    
    def test_load_nonexistent_file(self):
        result = self.ezd.load_file("nonexistent.ezd")
        self.assertNotEqual(result, LMC1Error.SUCCESS)
    
    def test_save_to_nested_directory(self):
        nested_dir = self.test_files_dir / "nested" / "deep" / "path"
        test_file = nested_dir / "test.ezd"
        
        self.ezd.add_text("Test", "t1", 0, 0)
        result = self.ezd.save_file(str(test_file))
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertTrue(test_file.exists())
        
        import shutil
        shutil.rmtree(self.test_files_dir / "nested", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
