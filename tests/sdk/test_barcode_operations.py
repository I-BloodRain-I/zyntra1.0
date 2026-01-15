import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error, BarcodeType, BarcodeAttribute, AlignMode


class TestBarcodeOperations(unittest.TestCase):
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
    
    def test_add_barcode_code39(self):
        result = self.ezd.add_barcode(
            text="123456",
            name="barcode1",
            x=10.0,
            y=10.0,
            barcode_type=BarcodeType.CODE_39,
            height=15.0
        )
        if result == LMC1Error.NOFINDENT:
            self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
        self.assertEqual(result, LMC1Error.SUCCESS)
        self.assertEqual(self.ezd.get_entity_count(), 1)
    
    def test_add_barcode_code128(self):
        result = self.ezd.add_barcode(
            text="ABC123456",
            name="code128",
            x=20.0,
            y=20.0,
            barcode_type=BarcodeType.CODE_128_OPT,
            height=20.0,
            narrow_width=0.5
        )
        if result == LMC1Error.NOFINDENT:
            self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        err, size = self.ezd.get_entity_size("code128")
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertGreater(size["max_x"], size["min_x"])
    
    def test_add_barcode_ean13(self):
        result = self.ezd.add_barcode(
            text="1234567890128",
            name="ean13",
            x=10.0,
            y=10.0,
            barcode_type=BarcodeType.EAN_13,
            height=25.0
        )
        if result == LMC1Error.NOFINDENT:
            self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_barcode_qr_datamatrix(self):
        result = self.ezd.add_barcode(
            text="QR_TEST_DATA_123",
            name="qr_code",
            x=50.0,
            y=50.0,
            barcode_type=BarcodeType.DATA_MATRIX,
            height=30.0,
            narrow_width=1.0
        )
        if result == LMC1Error.NOFINDENT:
            self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_qr.ezd"
        self.ezd.save_file(str(test_file))
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        self.assertEqual(self.ezd.get_entity_count(), 1)
    
    def test_add_barcode_with_human_readable(self):
        result = self.ezd.add_barcode(
            text="12345",
            name="barcode_hr",
            x=10.0,
            y=10.0,
            barcode_type=BarcodeType.CODE_39,
            attrib=BarcodeAttribute.HUMAN_READ,
            height=20.0,
            text_height=3.0,
            text_width=2.0
        )
        if result == LMC1Error.NOFINDENT:
            self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
        self.assertEqual(result, LMC1Error.SUCCESS)
    
    def test_add_multiple_barcodes(self):
        barcodes = [
            ("123", "bc1", BarcodeType.CODE_39),
            ("456", "bc2", BarcodeType.CODE_93),
            ("789", "bc3", BarcodeType.CODE_128_OPT),
        ]
        
        for i, (text, name, bc_type) in enumerate(barcodes):
            result = self.ezd.add_barcode(
                text=text,
                name=name,
                x=i * 30.0,
                y=10.0,
                barcode_type=bc_type,
                height=15.0
            )
            if result == LMC1Error.NOFINDENT:
                self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
            self.assertEqual(result, LMC1Error.SUCCESS)
        
        self.assertEqual(self.ezd.get_entity_count(), len(barcodes))
    
    def test_barcode_save_and_load(self):
        result = self.ezd.add_barcode(
            text="SAVE_LOAD_TEST",
            name="bc_save",
            x=25.0,
            y=25.0,
            z=3.0,
            barcode_type=BarcodeType.CODE_128_OPT,
            height=18.0
        )
        if result == LMC1Error.NOFINDENT:
            self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
        self.assertEqual(result, LMC1Error.SUCCESS)
        
        test_file = self.test_files_dir / "test_barcode_save.ezd"
        self.ezd.save_file(str(test_file))
        
        err, size_before = self.ezd.get_entity_size("bc_save")
        z_before = size_before["z"]
        
        self.ezd.clear_all()
        self.ezd.load_file(str(test_file))
        
        err, size_after = self.ezd.get_entity_size("bc_save")
        self.assertEqual(err, LMC1Error.SUCCESS)
        self.assertEqual(size_after["z"], z_before)
    
    def test_barcode_with_alignment(self):
        alignments = [
            (AlignMode.BOTTOM_LEFT, "bc_bl"),
            (AlignMode.MIDDLE_CENTER, "bc_mc"),
            (AlignMode.TOP_RIGHT, "bc_tr"),
        ]
        
        for align, name in alignments:
            result = self.ezd.add_barcode(
                text="TEST",
                name=name,
                x=50.0,
                y=50.0,
                align=align,
                barcode_type=BarcodeType.CODE_39,
                height=15.0
            )
            if result == LMC1Error.NOFINDENT:
                self.skipTest("lmc1_AddBarcodeToLib not available in DLL")
            self.assertEqual(result, LMC1Error.SUCCESS)
        
        self.assertEqual(self.ezd.get_entity_count(), len(alignments))


if __name__ == "__main__":
    unittest.main()
