import ctypes
import threading
import sys
import os
from pathlib import Path
from enum import IntEnum
from typing import Optional


class LMC1Error(IntEnum):
    """Error codes returned by LMC control board operations."""
    SUCCESS = 0
    EZCADRUN = 1
    NOFINDCFGFILE = 2
    NODEVICE = 4
    UNKNOW = 9
    NOINITIAL = 11
    READFILE = 12
    NOFINDFONT = 14
    PARAMERROR = 16
    SAVEFILE = 17
    NOFINDENT = 18
    ENTEXTCOOROVER = 20

    def __str__(self):
        """Convert error code to human-readable message.
        
        Returns:
            Error message string describing the error condition.
        """
        msgs = {
            0: "OK", 
            1: "EZCAD is running", 
            2: "EZCAD.CFG not found", 
            4: "No device", 
            9: "Unknown error",
            11: "Not initialized",
            12: "File read error",
            14: "Font not found",
            16: "Parameter error",
            17: "File save error",
            18: "Entity not found",
            20: "Entity text coordinate overflow"
        }
        return msgs.get(self.value, f"Error {self.value}")


class AlignMode(IntEnum):
    """Text and object alignment modes for positioning entities."""
    BOTTOM_LEFT = 0
    BOTTOM_CENTER = 1
    BOTTOM_RIGHT = 2
    MIDDLE_RIGHT = 3
    MIDDLE_CENTER = 8
    MIDDLE_LEFT = 7
    TOP_RIGHT = 4
    TOP_CENTER = 5
    TOP_LEFT = 6


class BarcodeType(IntEnum):
    """Supported barcode types for barcode generation."""
    CODE_39 = 0
    CODE_93 = 1
    CODE_128A = 2
    CODE_128B = 3
    CODE_128C = 4
    CODE_128_OPT = 5
    EAN_128A = 6
    EAN_128B = 7
    EAN_128C = 8
    EAN_13 = 9
    EAN_8 = 10
    UPC_A = 11
    UPC_E = 12
    CODE_25 = 13
    INTERLEAVED_25 = 14
    CODABAR = 15
    PDF417 = 16
    DATA_MATRIX = 17
    USER_DEFINED = 18


class BarcodeAttribute(IntEnum):
    """Barcode attribute flags for controlling barcode rendering options."""
    REVERSE = 0x0008
    HUMAN_READ = 0x1000
    CHECK_NUM = 0x0004
    PDF417_SHORT_MODE = 0x0040
    DATAMTX_DOT_MODE = 0x0080
    CIRCLE_MODE = 0x0100


class HatchAttribute(IntEnum):
    """Hatch attribute flags for controlling fill pattern behavior."""
    ALL_CALC = 0x01
    BI_DIR = 0x08
    EDGE = 0x02
    LOOP = 0x10


class DLLFunctionLoader:
    """Helper class for setting up DLL function signatures and return types."""
    
    @staticmethod
    def setup_dll_functions(dll: ctypes.WinDLL):
        """Configure argument types and return types for all DLL functions.
        
        Args:
            dll: The loaded MarkEzd.dll library instance.
        """
        dll.lmc1_Initial.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p]
        dll.lmc1_Initial.restype = ctypes.c_int
        
        dll.lmc1_Close.restype = ctypes.c_int
        
        dll.lmc1_LoadEzdFile.argtypes = [ctypes.c_wchar_p]
        dll.lmc1_LoadEzdFile.restype = ctypes.c_int
        
        dll.lmc1_Mark.argtypes = [ctypes.c_bool]
        dll.lmc1_Mark.restype = ctypes.c_int
        
        dll.lmc1_MarkEntity.argtypes = [ctypes.c_wchar_p]
        dll.lmc1_MarkEntity.restype = ctypes.c_int
        
        dll.lmc1_MarkEntityFly.argtypes = [ctypes.c_wchar_p]
        dll.lmc1_MarkEntityFly.restype = ctypes.c_int
        
        dll.lmc1_ClearEntLib.restype = ctypes.c_int
        
        dll.lmc1_SaveEntLibToFile.argtypes = [ctypes.c_wchar_p]
        dll.lmc1_SaveEntLibToFile.restype = ctypes.c_int
        
        dll.lmc1_SetFontParam.argtypes = [
            ctypes.c_wchar_p, ctypes.c_double, ctypes.c_double,
            ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_bool
        ]
        dll.lmc1_SetFontParam.restype = ctypes.c_int
        
        dll.lmc1_SetHatchParam.argtypes = [
            ctypes.c_bool, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double
        ]
        dll.lmc1_SetHatchParam.restype = ctypes.c_int
        
        dll.lmc1_AddTextToLib.argtypes = [
            ctypes.c_wchar_p, ctypes.c_wchar_p,
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_bool
        ]
        dll.lmc1_AddTextToLib.restype = ctypes.c_int
        
        dll.lmc1_AddFileToLib.argtypes = [
            ctypes.c_wchar_p, ctypes.c_wchar_p,
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_int, ctypes.c_double, ctypes.c_int, ctypes.c_bool
        ]
        dll.lmc1_AddFileToLib.restype = ctypes.c_int
        
        dll.lmc1_AddCurveToLib.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.c_int,
            ctypes.c_wchar_p, ctypes.c_int, ctypes.c_int
        ]
        dll.lmc1_AddCurveToLib.restype = ctypes.c_int
        
        dll.lmc1_AddBarCodeToLib.argtypes = [
            ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_double,
            ctypes.c_double, ctypes.c_double, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_ushort, ctypes.c_double, ctypes.c_double,
            ctypes.c_double * 4, ctypes.c_double * 4,
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_double, ctypes.c_double,
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_wchar_p
        ]
        dll.lmc1_AddBarCodeToLib.restype = ctypes.c_int
        
        dll.lmc1_ChangeTextByName.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        dll.lmc1_ChangeTextByName.restype = ctypes.c_int
        
        dll.lmc1_GetTextByName.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        dll.lmc1_GetTextByName.restype = ctypes.c_int
        
        dll.lmc1_GetEntityCount.restype = ctypes.c_int
        
        dll.lmc1_GetEntityName.argtypes = [ctypes.c_int, ctypes.c_wchar_p]
        dll.lmc1_GetEntityName.restype = ctypes.c_int
        
        dll.lmc1_GetEntSize.argtypes = [
            ctypes.c_wchar_p,
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double)
        ]
        dll.lmc1_GetEntSize.restype = ctypes.c_int
        
        dll.lmc1_MoveEnt.argtypes = [ctypes.c_wchar_p, ctypes.c_double, ctypes.c_double]
        dll.lmc1_MoveEnt.restype = ctypes.c_int
        
        dll.lmc1_ScaleEnt.argtypes = [
            ctypes.c_wchar_p, ctypes.c_double, ctypes.c_double,
            ctypes.c_double, ctypes.c_double
        ]
        dll.lmc1_ScaleEnt.restype = ctypes.c_int
        
        dll.lmc1_MirrorEnt.argtypes = [
            ctypes.c_wchar_p, ctypes.c_double, ctypes.c_double,
            ctypes.c_bool, ctypes.c_bool
        ]
        dll.lmc1_MirrorEnt.restype = ctypes.c_int
        
        dll.lmc1_RotateEnt.argtypes = [
            ctypes.c_wchar_p, ctypes.c_double, ctypes.c_double, ctypes.c_double
        ]
        dll.lmc1_RotateEnt.restype = ctypes.c_int
        
        dll.lmc1_DeleteEnt.argtypes = [ctypes.c_wchar_p]
        dll.lmc1_DeleteEnt.restype = ctypes.c_int
        
        dll.lmc1_CopyEnt.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        dll.lmc1_CopyEnt.restype = ctypes.c_int
        
        dll.lmc1_ChangeEntName.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        dll.lmc1_ChangeEntName.restype = ctypes.c_int
        
        dll.lmc1_ReadPort.argtypes = [ctypes.POINTER(ctypes.c_ushort)]
        dll.lmc1_ReadPort.restype = ctypes.c_int
        
        dll.lmc1_WritePort.argtypes = [ctypes.c_ushort]
        dll.lmc1_WritePort.restype = ctypes.c_int
        
        dll.lmc1_LaserOn.argtypes = [ctypes.c_bool]
        dll.lmc1_LaserOn.restype = ctypes.c_int
        
        dll.lmc1_GetCurCoor.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
        dll.lmc1_GetCurCoor.restype = ctypes.c_int
        
        dll.lmc1_GotoPos.argtypes = [ctypes.c_double, ctypes.c_double]
        dll.lmc1_GotoPos.restype = ctypes.c_int
        
        dll.lmc1_MarkLine.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int]
        dll.lmc1_MarkLine.restype = ctypes.c_int
        
        dll.lmc1_MarkPoint.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int]
        dll.lmc1_MarkPoint.restype = ctypes.c_int
        
        dll.lmc1_RedLightMark.restype = ctypes.c_int


class EzcadSDK:
    """Singleton SDK wrapper for EZCAD laser marking system.
    
    This class provides a Python interface to the MarkEzd.dll library for controlling
    laser marking operations. It implements the singleton pattern to ensure only one
    instance interacts with the hardware at a time.
    """
    _instance = None
    _lock = threading.Lock()
    
    @staticmethod
    def _get_sdk_path():
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent
        return base_path / "sdk"
    
    _SDK_PATH = _get_sdk_path.__func__() 

    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of EzcadSDK exists (singleton pattern).
        
        Returns:
            The singleton EzcadSDK instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_init_done", False):
            return
        with self.__class__._lock:
            if getattr(self, "_init_done", False):
                return
            self._init_done = True

        self.dll = None
        self.initialized = False
        self.dll = self._load_dll()
    
    def _load_dll(self):
        dll = ctypes.WinDLL(str(self._SDK_PATH / "MarkEzd.dll"))
        DLLFunctionLoader.setup_dll_functions(dll)
        return dll
    
    def initialize(self, test_mode: bool = False) -> LMC1Error:
        """Initialize the LMC control board.
        
        Must be called before any other operations. Loads configuration from EZCAD.CFG.
        
        Args:
            test_mode: If True, runs in test mode without requiring hardware.
            
        Returns:
            Error code indicating success or failure.
        """
        result = self.dll.lmc1_Initial(str(self._SDK_PATH), int(test_mode), None)
        self.initialized = (result == 0)
        return LMC1Error(result)
    
    def close(self) -> LMC1Error:
        """Close the LMC control board connection.
        
        Should be called when exiting the program to properly release hardware resources.
        
        Returns:
            Error code indicating success or failure.
        """
        result = self.dll.lmc1_Close()
        self.initialized = False
        return LMC1Error(result)
    
    def load_file(self, filename: str) -> LMC1Error:
        """Load an EZD file and clear all objects in the database.
        
        Opens an EZD file that was created by EZCAD as a template. Process parameters
        are loaded from the file.
        
        Args:
            filename: Path to the .ezd file to load.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_LoadEzdFile(filename))
    
    def save_file(self, filename: str) -> LMC1Error:
        """Save all objects in the database to an EZD file.
        
        Args:
            filename: Path where the .ezd file will be saved.
            
        Returns:
            Error code indicating success or failure.
        """
        file_path = Path(filename).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return LMC1Error(self.dll.lmc1_SaveEntLibToFile(str(file_path)))
    
    def mark(self, fly_mark: bool = False) -> LMC1Error:
        """Mark all data in the database.
        
        Begins marking operation. Function blocks until marking is complete.
        
        Args:
            fly_mark: If True, enables marking on the fly (for moving production lines).
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_Mark(fly_mark))
    
    def mark_entity(self, entity_name: str) -> LMC1Error:
        """Mark a specific named object in the database.
        
        Marks only the specified entity. Function blocks until marking is complete.
        
        Args:
            entity_name: Name of the entity to mark.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_MarkEntity(entity_name))
    
    def mark_entity_fly(self, entity_name: str) -> LMC1Error:
        """Mark a specific named object in fly marking mode.
        
        Marks the specified entity on a moving production line. Function blocks until complete.
        
        Args:
            entity_name: Name of the entity to mark on the fly.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_MarkEntityFly(entity_name))
    
    def clear_all(self) -> LMC1Error:
        """Clear all objects from the entity library database.
        
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_ClearEntLib())
    
    def set_hatch(
        self,
        enable_contour: bool,
        enable_hatch1: int,
        pen_no1: int,
        hatch_attrib1: int,
        edge_dist1: float,
        line_dist1: float,
        start_offset1: float,
        end_offset1: float,
        angle1: float,
        enable_hatch2: int,
        pen_no2: int,
        hatch_attrib2: int,
        edge_dist2: float,
        line_dist2: float,
        start_offset2: float,
        end_offset2: float,
        angle2: float
    ) -> LMC1Error:
        """Set hatch fill parameters for subsequent objects.
        
        Configures two independent hatch layers with contour control. Parameters apply
        to objects added after this call.
        
        Args:
            enable_contour: Enable marking of object contour.
            enable_hatch1: Enable first hatch layer.
            pen_no1: Pen number for first hatch (0-255).
            hatch_attrib1: First hatch attributes (combination of HatchAttribute flags).
            edge_dist1: Distance between hatch lines and contour for first hatch.
            line_dist1: Distance between hatch lines for first hatch.
            start_offset1: Start offset for first hatch lines.
            end_offset1: End offset for first hatch lines.
            angle1: Hatch angle in degrees for first hatch.
            enable_hatch2: Enable second hatch layer.
            pen_no2: Pen number for second hatch (0-255).
            hatch_attrib2: Second hatch attributes (combination of HatchAttribute flags).
            edge_dist2: Distance between hatch lines and contour for second hatch.
            line_dist2: Distance between hatch lines for second hatch.
            start_offset2: Start offset for second hatch lines.
            end_offset2: End offset for second hatch lines.
            angle2: Hatch angle in degrees for second hatch.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(
            self.dll.lmc1_SetHatchParam(
                enable_contour, enable_hatch1, pen_no1, hatch_attrib1,
                edge_dist1, line_dist1, start_offset1, end_offset1, angle1,
                enable_hatch2, pen_no2, hatch_attrib2,
                edge_dist2, line_dist2, start_offset2, end_offset2, angle2
            )
        )
    
    def set_font(
        self, 
        font_name: str = "Arial", 
        height: float = 5.0, 
        width: float = 5.0,
        char_angle: float = 0.0,
        char_space: float = 0.0,
        line_space: float = 0.0,
        equal_char_width: bool = False
    ) -> LMC1Error:
        """Set font parameters for subsequent text objects.
        
        Configures font settings that will be applied to text entities added after this call.
        
        Args:
            font_name: Name of the font to use.
            height: Character height in mm.
            width: Character width in mm.
            char_angle: Character rotation angle in degrees.
            char_space: Spacing between characters in mm.
            line_space: Spacing between lines in mm.
            equal_char_width: If True, all characters have equal width.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(
            self.dll.lmc1_SetFontParam(
                font_name, height, width, char_angle, char_space, line_space, equal_char_width
            )
        )
    
    def add_text(
        self, 
        text: str, 
        name: str, 
        x: float, 
        y: float, 
        z: float = 0.0,
        align: int = AlignMode.MIDDLE_CENTER,
        angle: float = 0.0,
        pen: int = 0, 
        hatch: bool = False
    ) -> LMC1Error:
        """Add a text object to the entity library.
        
        Creates a text entity with specified content and positioning. Uses current font settings.
        
        Args:
            text: Text content to display.
            name: Unique name identifier for this entity.
            x: X coordinate position in mm.
            y: Y coordinate position in mm.
            z: Z coordinate position in mm.
            align: Text alignment mode (use AlignMode enum values).
            angle: Rotation angle in degrees.
            pen: Pen number to use (0-255).
            hatch: If True, enables hatch filling for the text.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(
            self.dll.lmc1_AddTextToLib(
                text, name, x, y, z, align, angle, pen, hatch
            )
        )
    
    def add_file(
        self,
        filename: str,
        name: str,
        x: float,
        y: float,
        z: float = 0.0,
        align: int = AlignMode.MIDDLE_CENTER,
        ratio: float = 1.0,
        pen: int = 0,
        hatch: bool = False
    ) -> LMC1Error:
        """Add a file (vector graphics) to the entity library.
        
        Imports an external file (DXF, PLT, etc.) as an entity.
        
        Args:
            filename: Path to the file to import.
            name: Unique name identifier for this entity.
            x: X coordinate position in mm.
            y: Y coordinate position in mm.
            z: Z coordinate position in mm.
            align: Alignment mode (use AlignMode enum values).
            ratio: Scale ratio for the imported file.
            pen: Pen number to use (0-255).
            hatch: If True, enables hatch filling.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(
            self.dll.lmc1_AddFileToLib(
                filename, name, x, y, z, align, ratio, pen, hatch
            )
        )
    
    def add_curve(
        self,
        points: list[tuple[float, float]],
        name: str,
        pen: int = 0,
        hatch: bool = False
    ) -> LMC1Error:
        """Add a curve (polyline) to the entity library.
        
        Creates a curve entity from a series of coordinate points.
        
        Args:
            points: List of (x, y) coordinate tuples defining the curve path.
            name: Unique name identifier for this entity.
            pen: Pen number to use (0-255).
            hatch: If True, enables hatch filling for closed curves.
            
        Returns:
            Error code indicating success or failure.
        """
        pt_count = len(points)
        pt_array = (ctypes.c_double * (pt_count * 2))()
        for i, (px, py) in enumerate(points):
            pt_array[i * 2] = px
            pt_array[i * 2 + 1] = py
        return LMC1Error(
            self.dll.lmc1_AddCurveToLib(pt_array, pt_count, name, pen, hatch)
        )
    
    def add_barcode(
        self,
        text: str,
        name: str,
        x: float,
        y: float,
        z: float = 0.0,
        align: int = AlignMode.MIDDLE_CENTER,
        pen: int = 0,
        hatch: bool = False,
        barcode_type: int = BarcodeType.CODE_128_OPT,
        attrib: int = 0,
        height: float = 10.0,
        narrow_width: float = 0.5,
        bar_width_scale: tuple[float, float, float, float] = (1.0, 2.0, 3.0, 4.0),
        space_width_scale: tuple[float, float, float, float] = (1.0, 2.0, 3.0, 4.0),
        mid_char_space: float = 1.0,
        quiet_left: float = 2.0,
        quiet_mid: float = 0.0,
        quiet_right: float = 2.0,
        quiet_top: float = 0.0,
        quiet_bottom: float = 0.0,
        row: int = 0,
        col: int = 0,
        check_level: int = 0,
        size_mode: int = 0,
        text_height: float = 2.0,
        text_width: float = 2.0,
        text_offset_x: float = 0.0,
        text_offset_y: float = 0.0,
        text_space: float = 0.0,
        text_font: str = "Arial"
    ) -> LMC1Error:
        """Add a barcode to the entity library.
        
        Creates a barcode entity with extensive customization options.
        
        Args:
            text: Barcode content/data.
            name: Unique name identifier for this entity.
            x: X coordinate position in mm.
            y: Y coordinate position in mm.
            z: Z coordinate position in mm.
            align: Alignment mode (use AlignMode enum values).
            pen: Pen number to use (0-255).
            hatch: If True, enables hatch filling.
            barcode_type: Barcode type (use BarcodeType enum values).
            attrib: Barcode attributes (combination of BarcodeAttribute flags).
            height: Barcode height in mm.
            narrow_width: Width of narrow bars in mm.
            bar_width_scale: Width scale factors for 4 bar widths.
            space_width_scale: Width scale factors for 4 space widths.
            mid_char_space: Space between characters in mm.
            quiet_left: Left quiet zone width in mm.
            quiet_mid: Middle quiet zone width in mm.
            quiet_right: Right quiet zone width in mm.
            quiet_top: Top quiet zone height in mm.
            quiet_bottom: Bottom quiet zone height in mm.
            row: Number of rows (for 2D barcodes like PDF417).
            col: Number of columns (for 2D barcodes).
            check_level: Error correction level.
            size_mode: Size mode for 2D barcodes.
            text_height: Human-readable text height in mm.
            text_width: Human-readable text width in mm.
            text_offset_x: X offset for human-readable text in mm.
            text_offset_y: Y offset for human-readable text in mm.
            text_space: Character spacing for human-readable text in mm.
            text_font: Font name for human-readable text.
            
        Returns:
            Error code indicating success or failure.
        """
        bar_scale = (ctypes.c_double * 4)(*bar_width_scale)
        space_scale = (ctypes.c_double * 4)(*space_width_scale)
        
        return LMC1Error(
            self.dll.lmc1_AddBarCodeToLib(
                text, name, x, y, z, align, pen, int(hatch),
                barcode_type, attrib, height, narrow_width,
                bar_scale, space_scale,
                mid_char_space, quiet_left, quiet_mid, quiet_right,
                quiet_top, quiet_bottom,
                row, col, check_level, size_mode,
                text_height, text_width, text_offset_x, text_offset_y, text_space,
                text_font
            )
        )

    def change_text(self, name: str, new_text: str) -> LMC1Error:
        """Change the content of a text entity by name.
        
        Modifies the text content of an existing text entity without changing other properties.
        
        Args:
            name: Name of the text entity to modify.
            new_text: New text content to set.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_ChangeTextByName(name, new_text))
    
    def get_text(self, name: str) -> tuple[LMC1Error, str]:
        """Get the text content of a text entity by name.
        
        Args:
            name: Name of the text entity to query.
            
        Returns:
            Tuple of (error_code, text_content).
        """
        buffer = ctypes.create_unicode_buffer(256)
        result = self.dll.lmc1_GetTextByName(name, buffer)
        return LMC1Error(result), buffer.value
    
    def get_entity_count(self) -> int:
        """Get the total number of entities in the database.
        
        Returns:
            Total count of objects in the entity library.
        """
        return self.dll.lmc1_GetEntityCount()
    
    def get_entity_name(self, index: int) -> tuple[LMC1Error, str]:
        """Get the name of an entity by its index.
        
        Args:
            index: Entity index (0 to entity_count-1).
            
        Returns:
            Tuple of (error_code, entity_name).
        """
        buffer = ctypes.create_unicode_buffer(256)
        result = self.dll.lmc1_GetEntityName(index, buffer)
        return LMC1Error(result), buffer.value
    
    def get_entity_size(self, name: Optional[str] = None) -> tuple[LMC1Error, dict]:
        """Get the bounding box dimensions of an entity.
        
        Returns the minimum and maximum coordinates that define the entity's bounding box.
        
        Args:
            name: Name of the entity. If None, gets size of all entities combined.
            
        Returns:
            Tuple of (error_code, size_dict) where size_dict contains keys:
            min_x, min_y, max_x, max_y, z.
        """
        min_x = ctypes.c_double()
        min_y = ctypes.c_double()
        max_x = ctypes.c_double()
        max_y = ctypes.c_double()
        z = ctypes.c_double()
        result = self.dll.lmc1_GetEntSize(
            name, 
            ctypes.byref(min_x), ctypes.byref(min_y),
            ctypes.byref(max_x), ctypes.byref(max_y),
            ctypes.byref(z)
        )
        return LMC1Error(result), {
            "min_x": min_x.value,
            "min_y": min_y.value,
            "max_x": max_x.value,
            "max_y": max_y.value,
            "z": z.value
        }
    
    def move_entity(self, name: str, dx: float, dy: float) -> LMC1Error:
        """Move an entity by specified distances.
        
        Args:
            name: Name of the entity to move.
            dx: Distance to move in X direction (mm).
            dy: Distance to move in Y direction (mm).
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_MoveEnt(name, dx, dy))
    
    def scale_entity(
        self, 
        name: str, 
        center_x: float, 
        center_y: float, 
        scale_x: float, 
        scale_y: float
    ) -> LMC1Error:
        """Scale an entity around a center point.
        
        Args:
            name: Name of the entity to scale.
            center_x: X coordinate of scaling center (mm).
            center_y: Y coordinate of scaling center (mm).
            scale_x: Scale factor in X direction.
            scale_y: Scale factor in Y direction.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_ScaleEnt(name, center_x, center_y, scale_x, scale_y))
    
    def mirror_entity(
        self, 
        name: str, 
        center_x: float, 
        center_y: float, 
        mirror_x: bool, 
        mirror_y: bool
    ) -> LMC1Error:
        """Mirror an entity around a center point.
        
        Args:
            name: Name of the entity to mirror.
            center_x: X coordinate of mirror center (mm).
            center_y: Y coordinate of mirror center (mm).
            mirror_x: If True, mirror horizontally.
            mirror_y: If True, mirror vertically.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_MirrorEnt(name, center_x, center_y, mirror_x, mirror_y))
    
    def rotate_entity(
        self, 
        name: str, 
        center_x: float, 
        center_y: float, 
        angle: float
    ) -> LMC1Error:
        """Rotate an entity around a center point.
        
        Args:
            name: Name of the entity to rotate.
            center_x: X coordinate of rotation center (mm).
            center_y: Y coordinate of rotation center (mm).
            angle: Rotation angle in degrees.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_RotateEnt(name, center_x, center_y, angle))
    
    def delete_entity(self, name: str) -> LMC1Error:
        """Delete an entity from the database.
        
        Args:
            name: Name of the entity to delete.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_DeleteEnt(name))
    
    def copy_entity(self, name: str, new_name: str) -> LMC1Error:
        """Copy an entity and give it a new name.
        
        Args:
            name: Name of the entity to copy.
            new_name: Name for the copied entity.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_CopyEnt(name, new_name))
    
    def rename_entity(self, name: str, new_name: str) -> LMC1Error:
        """Rename an entity.
        
        If multiple entities have the same name, all will be renamed.
        
        Args:
            name: Current name of the entity.
            new_name: New name for the entity.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_ChangeEntName(name, new_name))
    
    def read_port(self) -> tuple[LMC1Error, int]:
        """Read data from the input port of the LMC1 board.
        
        Returns:
            Tuple of (error_code, port_data) where port_data is 16-bit input value.
        """
        data = ctypes.c_ushort()
        result = self.dll.lmc1_ReadPort(ctypes.byref(data))
        return LMC1Error(result), data.value
    
    def write_port(self, data: int) -> LMC1Error:
        """Write data to the output port of the LMC1 board.
        
        Args:
            data: 16-bit value to write to output port. Bit=0 is low, Bit=1 is high.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_WritePort(data))
    
    def laser_on(self, enabled: bool) -> LMC1Error:
        """Control laser emission on/off.
        
        Args:
            enabled: True to turn laser on, False to turn it off.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_LaserOn(enabled))
    
    def get_current_position(self) -> tuple[LMC1Error, tuple[float, float]]:
        """Get the current position of the galvanometer head.
        
        Returns:
            Tuple of (error_code, (x, y)) where x and y are current coordinates in mm.
        """
        x = ctypes.c_double()
        y = ctypes.c_double()
        result = self.dll.lmc1_GetCurCoor(ctypes.byref(x), ctypes.byref(y))
        return LMC1Error(result), (x.value, y.value)
    
    def goto_position(self, x: float, y: float) -> LMC1Error:
        """Move the galvanometer head to a specified position without marking.
        
        Args:
            x: Target X coordinate in mm.
            y: Target Y coordinate in mm.
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_GotoPos(x, y))
    
    def mark_line(self, x1: float, y1: float, x2: float, y2: float, pen: int = 0) -> LMC1Error:
        """Mark a line from start point to end point.
        
        Args:
            x1: Starting point X coordinate in mm.
            y1: Starting point Y coordinate in mm.
            x2: End point X coordinate in mm.
            y2: End point Y coordinate in mm.
            pen: Pen number to use (0-255).
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_MarkLine(x1, y1, x2, y2, pen))
    
    def mark_point(self, x: float, y: float, delay: float, pen: int = 0) -> LMC1Error:
        """Mark a point at a specified location with laser on for specified duration.
        
        Args:
            x: X coordinate of point in mm.
            y: Y coordinate of point in mm.
            delay: Marking time duration in milliseconds.
            pen: Pen number to use (0-255).
            
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_MarkPoint(x, y, delay, pen))
    
    def red_light_mark(self) -> LMC1Error:
        """Mark the contour using indicated red light for preview/alignment.
        
        Shows the marking position without actually marking. The red light preview
        shows the actual marking result path including circles and other shapes.
        
        Returns:
            Error code indicating success or failure.
        """
        return LMC1Error(self.dll.lmc1_RedLightMark())
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.initialized:
            self.close()