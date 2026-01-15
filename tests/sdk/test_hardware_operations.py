import unittest
from pathlib import Path

from ezcad_sdk import EzcadSDK, LMC1Error


class TestHardwareOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk_path = Path(__file__).parent.parent.parent / "sdk"
        
    def setUp(self):
        self.ezd = EzcadSDK()
        self.ezd.initialize(test_mode=True)
        
    def tearDown(self):
        if self.ezd.initialized:
            self.ezd.close()
    
    def test_laser_on_off(self):
        result = self.ezd.laser_on(True)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])
        
        result = self.ezd.laser_on(False)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])
    
    def test_get_current_position(self):
        err, position = self.ezd.get_current_position()
        self.assertIn(err, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])
        
        if err == LMC1Error.SUCCESS:
            x, y = position
            self.assertIsInstance(x, float)
            self.assertIsInstance(y, float)
    
    def test_goto_position(self):
        result = self.ezd.goto_position(10.0, 20.0)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])
    
    def test_read_port(self):
        err, data = self.ezd.read_port()
        self.assertIn(err, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])
        
        if err == LMC1Error.SUCCESS:
            self.assertIsInstance(data, int)
            self.assertGreaterEqual(data, 0)
            self.assertLessEqual(data, 65535)
    
    def test_write_port(self):
        result = self.ezd.write_port(0x00FF)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])
        
        result = self.ezd.write_port(0x0000)
        self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])
    
    def test_position_sequence(self):
        positions = [
            (0.0, 0.0),
            (10.0, 10.0),
            (20.0, 0.0),
            (0.0, 20.0)
        ]
        
        for x, y in positions:
            result = self.ezd.goto_position(x, y)
            self.assertIn(result, [LMC1Error.SUCCESS, LMC1Error.NODEVICE])


if __name__ == "__main__":
    unittest.main()
