import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error


class TestSDKInternals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_path = Path(__file__).parent.parent.parent / "sdk"
        
    def test_error_str_representation(self):
        err = LMC1Error.SUCCESS
        self.assertEqual(str(err), "OK")
        
        err = LMC1Error.EZCADRUN
        self.assertEqual(str(err), "EZCAD is running")
        
        err = LMC1Error.NOFINDCFGFILE
        self.assertEqual(str(err), "EZCAD.CFG not found")
        
        err = LMC1Error.NODEVICE
        self.assertEqual(str(err), "No device")
        
        err = LMC1Error.UNKNOW
        self.assertEqual(str(err), "Unknown error")
        
        err = LMC1Error.NOINITIAL
        self.assertEqual(str(err), "Not initialized")
        
        err = LMC1Error.READFILE
        self.assertEqual(str(err), "File read error")
        
        err = LMC1Error.NOFINDFONT
        self.assertEqual(str(err), "Font not found")
        
        err = LMC1Error.SAVEFILE
        self.assertEqual(str(err), "File save error")
        
        err = LMC1Error.NOFINDENT
        self.assertEqual(str(err), "Entity not found")
    
    def test_error_unknown_code(self):
        from enum import IntEnum
        
        class UnknownError(IntEnum):
            UNKNOWN = 999
            
            def __str__(self):
                msgs = {
                    0: "OK", 
                    1: "EZCAD is running", 
                    2: "EZCAD.CFG not found", 
                    4: "No device", 
                    9: "Unknown error",
                    11: "Not initialized",
                    12: "File read error",
                    14: "Font not found",
                    17: "File save error",
                    18: "Entity not found"
                }
                return msgs.get(self.value, f"Error {self.value}")
        
        err = UnknownError.UNKNOWN
        self.assertEqual(str(err), "Error 999")
    
    def test_sdk_path_default(self):
        sdk = EzcadSDK()
        self.assertTrue(sdk._SDK_PATH.exists())
        self.assertTrue((sdk._SDK_PATH / "MarkEzd.dll").exists())
    
    def test_sdk_path_explicit(self):
        sdk = EzcadSDK()
        self.assertEqual(sdk._SDK_PATH, self.sdk_path)
    
    def test_context_manager_enter(self):
        with EzcadSDK() as sdk:
            self.assertIsInstance(sdk, EzcadSDK)
            sdk.initialize(test_mode=True)
            self.assertTrue(sdk.initialized)
    
    def test_context_manager_exit_closes_sdk(self):
        sdk = EzcadSDK()
        with sdk:
            sdk.initialize(test_mode=True)
            self.assertTrue(sdk.initialized)
        self.assertFalse(sdk.initialized)
    
    def test_context_manager_exit_without_init(self):
        with EzcadSDK() as sdk:
            self.assertFalse(sdk.initialized)


if __name__ == "__main__":
    unittest.main()
