import os
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

from src.core.state import get_sdk_client
from src.canvas.pen_settings import PenCollection

logger = logging.getLogger(__name__)

TEXT_X_OFFSET = 0.0
TEXT_Y_OFFSET = 0.0


def convert_to_ezd_coords(x_mm: float, y_mm: float, jig_w_mm: float, jig_h_mm: float) -> tuple[float, float]:
    ezd_x = x_mm - (jig_w_mm / 2)
    ezd_y = (jig_h_mm / 2) - y_mm
    return ezd_x, ezd_y


def adjust_text_size_iterative(
    client, 
    text: str, 
    name: str, 
    target_width_mm: float, 
    target_height_mm: float,                            
    font_family: str, 
    initial_width: float, 
    initial_height: float, 
    x: float, 
    y: float, 
    z: float, 
    angle: float, 
    max_iterations: int = 5,
    hatch: bool = False
) -> tuple[float, float]:
    width_sdk = initial_width
    height_sdk = initial_height
    
    for i in range(max_iterations):
        client.set_font(font_name=font_family, height=height_sdk, width=width_sdk, equal_char_width=False)
        client.add_text(text=text, name=name, x=x, y=y, z=z, align=8, angle=0.0, pen=0, hatch=hatch)
        
        error, size = client.get_entity_size(name=name)
        if error != 0:
            logger.warning(f"Failed to get entity size on iteration {i}")
            break
            
        actual_width = size["max_x"] - size["min_x"]
        actual_height = size["max_y"] - size["min_y"]
        
        width_error = abs(actual_width - target_width_mm)
        height_error = abs(actual_height - target_height_mm)
        
        if width_error < 0.1 and height_error < 0.1:
            logger.debug(f"Converged after {i+1} iterations: w={actual_width:.2f}, h={actual_height:.2f}")
            return width_sdk, height_sdk
        
        if actual_width > 0:
            width_sdk *= (target_width_mm / actual_width)
        if actual_height > 0:
            height_sdk *= (target_height_mm / actual_height)
        
        client.delete_entity(name=name)
        logger.debug(f"Iteration {i+1}: actual w={actual_width:.2f}, h={actual_height:.2f}, adjusting sdk w={width_sdk:.3f}, h={height_sdk:.3f}")
    
    return width_sdk, height_sdk


class EzdExporter:

    def __init__(self):
        self._initialized = False

    @property
    def client(self):
        return get_sdk_client()

    def _ensure_initialized(self):
        if not self._initialized:
            print("[DEBUG] Calling SDK initialize...")
            result = self.client.initialize()
            print(f"[DEBUG] SDK initialize() returned: {result}")
            logger.info(f"SDK initialize() returned: {result}")
            self._initialized = True

    def _convert_svg_to_dxf(self, svg_path: str) -> Optional[str]:

        inkscape_path = os.path.join(os.path.dirname(__file__), "..", "..", "_internal", "converter", "App", "Inkscape", "bin", "inkscape.com")
        inkscape_path = os.path.abspath(inkscape_path)
        
        if not os.path.exists(inkscape_path):
            raise RuntimeError(f"Inkscape not found at: {inkscape_path}")
        
        dxf_path = tempfile.mktemp(suffix=".dxf")
        
        cmd = [
            inkscape_path,
            "--batch-process",
            svg_path,
            "--export-type=dxf",
            f"--export-filename={dxf_path}"
        ]
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW | subprocess.STARTF_USESTDHANDLES
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        )
        
        if result.returncode != 0:
            logger.error(f"Inkscape conversion failed: {result.stderr}")
            return None
        
        if not os.path.exists(dxf_path):
            logger.error(f"DXF file not created: {dxf_path}")
            return None
        
        logger.info(f"Inkscape converted SVG to DXF: {dxf_path}")
        return dxf_path

    def _apply_pen_settings(self, pen_collection: PenCollection):
        for pen_no in range(256):
            pen = pen_collection.get_pen(pen_no)
            
            self.client.set_pen_param(
                pen_no=pen_no,
                loop_count=pen.loop_count,
                speed=pen.speed,
                power=pen.power,
                current=0.0,
                frequency=int(pen.frequency * 1000),
                pulse_width=0.0,
                start_tc=int(pen.start_tc),
                laser_off_tc=int(pen.laser_off_tc),
                end_tc=int(pen.end_tc),
                polygon_tc=int(pen.polygon_tc),
                jump_speed=pen.jump_speed,
                jump_pos_tc=int(pen.jump_position_tc),
                jump_dist_tc=int(pen.jump_dist_tc),
                end_comp=pen.end_compensate,
                acc_dist=pen.acc_distance,
                point_time=pen.time_per_point,
                pulse_point_mode=pen.vector_point_mode,
                pulse_num=pen.pulse_per_point,
                fly_speed=0.0
            )
            
            if pen.wobble_enabled:
                self.client.set_pen_param_wobble(
                    pen_no=pen_no,
                    loop_count=pen.loop_count,
                    speed=pen.speed,
                    power=pen.power,
                    current=0.0,
                    frequency=int(pen.frequency * 1000),
                    pulse_width=0.0,
                    start_tc=int(pen.start_tc),
                    laser_off_tc=int(pen.laser_off_tc),
                    end_tc=int(pen.end_tc),
                    polygon_tc=int(pen.polygon_tc),
                    jump_speed=pen.jump_speed,
                    jump_pos_tc=int(pen.jump_position_tc),
                    jump_dist_tc=int(pen.jump_dist_tc),
                    spi_wave=0,
                    wobble_mode=True,
                    wobble_diameter=pen.wobble_diameter,
                    wobble_distance=pen.wobble_distance
                )
                logger.debug(f"Applied pen {pen_no} with wobble: wobble_diameter={pen.wobble_diameter}, wobble_distance={pen.wobble_distance}")
            
            logger.debug(f"Applied pen {pen_no}: speed={pen.speed}, power={pen.power}, freq={pen.frequency}")

    def _apply_hatch_settings(self, hatch_settings: dict):
        enable_contour = hatch_settings.get("enable_contour", True)
        hatch1_enabled = hatch_settings.get("hatch1_enabled", False)
        hatch1_pen = hatch_settings.get("hatch1_pen", 0)
        hatch1_edge_dist = hatch_settings.get("hatch1_edge_dist", 0.0)
        hatch1_line_dist = hatch_settings.get("hatch1_line_dist", 0.05)
        hatch1_start_offset = hatch_settings.get("hatch1_start_offset", 0.0)
        hatch1_end_offset = hatch_settings.get("hatch1_end_offset", 0.0)
        hatch1_angle = hatch_settings.get("hatch1_angle", 0.0)
        hatch2_enabled = hatch_settings.get("hatch2_enabled", False)
        hatch2_pen = hatch_settings.get("hatch2_pen", 0)
        hatch2_edge_dist = hatch_settings.get("hatch2_edge_dist", 0.0)
        hatch2_line_dist = hatch_settings.get("hatch2_line_dist", 0.05)
        hatch2_start_offset = hatch_settings.get("hatch2_start_offset", 0.0)
        hatch2_end_offset = hatch_settings.get("hatch2_end_offset", 0.0)
        hatch2_angle = hatch_settings.get("hatch2_angle", 90.0)
        
        self.client.set_hatch_param(
            enable_contour=enable_contour,
            enable_hatch1=hatch1_enabled,
            pen_no1=hatch1_pen,
            edge_dist1=hatch1_edge_dist,
            line_dist1=hatch1_line_dist,
            start_offset1=hatch1_start_offset,
            end_offset1=hatch1_end_offset,
            angle1=hatch1_angle,
            enable_hatch2=hatch2_enabled,
            pen_no2=hatch2_pen,
            edge_dist2=hatch2_edge_dist,
            line_dist2=hatch2_line_dist,
            start_offset2=hatch2_start_offset,
            end_offset2=hatch2_end_offset,
            angle2=hatch2_angle
        )
        logger.debug(f"Applied hatch params: contour={enable_contour}, hatch1={hatch1_enabled} (pen={hatch1_pen}), hatch2={hatch2_enabled} (pen={hatch2_pen})")

    def export_scene(
        self,
        items: list[dict],
        output_path: str,
        jig_w_mm: float = 0.0,
        jig_h_mm: float = 0.0,
        clear_before: bool = True,
        pen_collection: Optional[PenCollection] = None,
    ) -> bool:
        self._ensure_initialized()
        
        if clear_before:
            self.client.clear_all()

        if pen_collection is not None:
            self._apply_pen_settings(pen_collection)

        logger.debug(f"Exporting {len(items)} items to EZD")
        for idx, item in enumerate(items[:3]):
            logger.debug(f"Item {idx}: type={item.get('type')}, z={item.get('z')}, font_size_pt={item.get('font_size_pt')}, angle={item.get('angle')}")

        sorted_items = sorted(items, key=lambda x: x.get("z", 0))

        entity_index = 0
        for item in sorted_items:
            item_type = item.get("type", "")
            if item_type == "slot":
                continue

            entity_name = f"entity_{entity_index}"
            entity_index += 1
            
            pen_no = item.get("pen", item.get("pen_number", 0))
            logger.debug(f"Processing item type={item_type}, pen_no={pen_no} (from item.get('pen') or item.get('pen_number'))")
            
            hatch_settings = item.get("hatch_settings")
            use_hatch = False
            if hatch_settings:
                hatch1_enabled = hatch_settings.get("hatch1_enabled", False)
                hatch2_enabled = hatch_settings.get("hatch2_enabled", False)
                enable_contour = hatch_settings.get("enable_contour", True)
                if hatch1_enabled or hatch2_enabled or not enable_contour:
                    self._apply_hatch_settings(hatch_settings)
                    use_hatch = True

            if item_type == "text":
                self._add_text_entity(item, entity_name, jig_w_mm, jig_h_mm, use_hatch)
            elif item_type == "rect":
                self._add_rect_text_entity(item, entity_name, jig_w_mm, jig_h_mm, use_hatch)
            elif item_type == "image":
                self._add_image_entity(item, entity_name, jig_w_mm, jig_h_mm, use_hatch)
            elif item_type == "barcode":
                self._add_barcode_entity(item, entity_name, jig_w_mm, jig_h_mm, use_hatch)
            
            self.client.set_entity_pen(entity_name=entity_name, pen_no=pen_no)
            logger.debug(f"Set pen {pen_no} for entity '{entity_name}'")

        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if output_file.exists():
            output_file.unlink()

        self.client.save_file(filename=str(output_file))
        logger.info(f"EZD file saved: {output_file}")
        return True

    def _add_text_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float, use_hatch: bool = False):
        text = str(item.get("text", ""))
        if not text:
            return

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        x_mm, y_mm = convert_to_ezd_coords(x_mm_orig, y_mm_orig, jig_w_mm, jig_h_mm)
        font_family = str(item.get("font_family", "Arial"))
        
        width_mm = float(item.get("text_width_mm", 5.0))
        height_mm = float(item.get("text_height_mm", 5.0))
        
        angle = float(item.get("angle", 0.0))
        z = float(item.get("z", 0.0))

        logger.debug(f"Adding text '{text}': z={z}, width_mm={width_mm}, height_mm={height_mm}, font={font_family}, hatch={use_hatch}")

        width_sdk, height_sdk = adjust_text_size_iterative(
            client=self.client,
            text=text,
            name=name,
            target_width_mm=width_mm,
            target_height_mm=height_mm,
            font_family=font_family,
            initial_width=width_mm,
            initial_height=height_mm,
            x=x_mm + TEXT_X_OFFSET,
            y=y_mm + TEXT_Y_OFFSET,
            z=z,
            angle=angle,
            hatch=use_hatch
        )
        
        logger.debug(f"Final SDK params: width={width_sdk:.3f}, height={height_sdk:.3f}")

        if angle != 0.0:
            error, size = self.client.get_entity_size(name=name)
            if error == 0:
                actual_center_x = (size["min_x"] + size["max_x"]) / 2
                actual_center_y = (size["min_y"] + size["max_y"]) / 2
                logger.debug(f"Rotating text '{text}' by {angle} degrees")
                self.client.rotate_entity(name=name, center_x=actual_center_x, center_y=actual_center_y, angle=angle)

    def _add_rect_text_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float, use_hatch: bool = False):
        label = str(item.get("label", ""))
        if not label:
            return

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        w_mm = float(item.get("w_mm", 0.0))
        h_mm = float(item.get("h_mm", 0.0))
        
        center_x_orig = x_mm_orig + w_mm / 2
        center_y_orig = y_mm_orig + h_mm / 2
        
        x_mm, y_mm = convert_to_ezd_coords(center_x_orig, center_y_orig, jig_w_mm, jig_h_mm)
        angle = float(item.get("angle", 0.0))
        font_family = str(item.get("label_font_family", "Arial"))
        font_size_pt = float(item.get("label_font_size", 10))
        
        width_mm = float(item.get("text_width_mm", 5.0))
        height_mm = float(item.get("text_height_mm", 5.0))

        z = float(item.get("z", 0.0))

        logger.debug(f"Adding rect text '{label}': z={z}, width_mm={width_mm}, height_mm={height_mm}, font={font_family}, hatch={use_hatch}")
        logger.debug("Original coords (top-left): x_mm={:.3f}, y_mm={:.3f}, w_mm={:.3f}, h_mm={:.3f}".format(x_mm_orig, y_mm_orig, w_mm, h_mm))
        logger.debug("EZD center coords: x_mm={:.3f}, y_mm={:.3f}".format(x_mm, y_mm))

        width_sdk, height_sdk = adjust_text_size_iterative(
            client=self.client,
            text=label,
            name=name,
            target_width_mm=width_mm,
            target_height_mm=height_mm,
            font_family=font_family,
            initial_width=width_mm,
            initial_height=height_mm,
            x=x_mm,
            y=y_mm,
            z=z,
            angle=angle,
            hatch=use_hatch
        )
        
        logger.debug(f"Final SDK params: width={width_sdk:.3f}, height={height_sdk:.3f}")

        if angle != 0.0:
            error, size = self.client.get_entity_size(name=name)
            if error == 0:
                actual_center_x = (size["min_x"] + size["max_x"]) / 2
                actual_center_y = (size["min_y"] + size["max_y"]) / 2
                self.client.rotate_entity(name=name, center_x=actual_center_x, center_y=actual_center_y, angle=angle)

    def _add_image_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float, use_hatch: bool = False):
        svg_source_path = str(item.get("svg_source_path", "") or "")
        path = str(item.get("path", ""))
        
        logger.info(f"_add_image_entity: svg_source_path='{svg_source_path}', path='{path}'")
        
        file_to_use = ""
        use_svg_vector = False
        
        if svg_source_path and Path(svg_source_path).exists():
            svg_ext = Path(svg_source_path).suffix.lower()
            logger.info(f"SVG source exists, ext={svg_ext}")
            if svg_ext == ".svg":
                dxf_path = self._convert_svg_to_dxf(svg_source_path)
                logger.info(f"Converted to DXF: {dxf_path}")
                if dxf_path and Path(dxf_path).exists():
                    file_to_use = dxf_path
                    use_svg_vector = True
                    logger.debug(f"Using converted DXF for EZD export: {dxf_path}")
                else:
                    raise RuntimeError(f"SVG to DXF conversion failed for: {svg_source_path}")
            else:
                file_to_use = svg_source_path
                use_svg_vector = True
        elif path and Path(path).exists():
            file_to_use = path
        
        if not file_to_use:
            raise RuntimeError(f"Image path not found: path={path}, svg_source_path={svg_source_path}")

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        w_mm = float(item.get("w_mm", 0.0))
        h_mm = float(item.get("h_mm", 0.0))
        
        center_x_orig = x_mm_orig + w_mm / 2
        center_y_orig = y_mm_orig + h_mm / 2
        target_center_x, target_center_y = convert_to_ezd_coords(center_x_orig, center_y_orig, jig_w_mm, jig_h_mm)
        
        angle = float(item.get("angle", 0.0))
        z = float(item.get("z", 0.0))

        logger.debug(f"Adding image: z={z}, path={file_to_use}, angle={angle}, hatch={use_hatch}, vector={use_svg_vector}")
        logger.debug("Original coords (top-left): x_mm={:.3f}, y_mm={:.3f}, w_mm={:.3f}, h_mm={:.3f}".format(x_mm_orig, y_mm_orig, w_mm, h_mm))
        logger.debug("Target center (EZD): x_mm={:.3f}, y_mm={:.3f}".format(target_center_x, target_center_y))

        result = self.client.add_file(
            filename=file_to_use,
            name=name,
            x=0,
            y=0,
            z=z,
            align=0,
            ratio=1.0,
            pen=0,
            hatch=use_hatch,
        )
        
        if result != 0:
            raise RuntimeError(f"add_file failed with error {result} for {file_to_use}")

        logger.info(f"add_file succeeded, getting entity size...")
        error, size = self.client.get_entity_size(name=name)
        logger.info(f"get_entity_size returned error={error}, size={size}")
        
        if error == 0:
            current_w = size["max_x"] - size["min_x"]
            current_h = size["max_y"] - size["min_y"]
            actual_center_x = (size["min_x"] + size["max_x"]) / 2
            actual_center_y = (size["min_y"] + size["max_y"]) / 2
            
            logger.info(f"Current size: w={current_w:.2f}, h={current_h:.2f}, center=({actual_center_x:.2f}, {actual_center_y:.2f})")
            logger.info(f"Target size: w={w_mm:.2f}, h={h_mm:.2f}")
            
            if current_w > 0 and current_h > 0:
                scale_x = w_mm / current_w
                scale_y = h_mm / current_h
                logger.info(f"Scaling: scale_x={scale_x:.3f}, scale_y={scale_y:.3f}")
                self.client.scale_entity(
                    name=name,
                    center_x=actual_center_x,
                    center_y=actual_center_y,
                    scale_x=scale_x,
                    scale_y=scale_y
                )
        else:
            logger.error(f"get_entity_size failed with error {error}, cannot scale/position entity")
        
        error, size = self.client.get_entity_size(name=name)
        if error == 0:
            actual_center_x = (size["min_x"] + size["max_x"]) / 2
            actual_center_y = (size["min_y"] + size["max_y"]) / 2
            dx = target_center_x - actual_center_x
            dy = target_center_y - actual_center_y
            logger.info(f"Moving: dx={dx:.2f}, dy={dy:.2f}, target_center=({target_center_x:.2f}, {target_center_y:.2f})")
            if abs(dx) > 0.001 or abs(dy) > 0.001:
                self.client.move_entity(name=name, dx=dx, dy=dy)

        if angle != 0.0:
            error, size = self.client.get_entity_size(name=name)
            if error == 0:
                actual_center_x = (size["min_x"] + size["max_x"]) / 2
                actual_center_y = (size["min_y"] + size["max_y"]) / 2
                self.client.rotate_entity(name=name, center_x=actual_center_x, center_y=actual_center_y, angle=angle)

    def _add_barcode_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float, use_hatch: bool = False):
        label = str(item.get("label", ""))
        if not label:
            return

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        w_mm = float(item.get("w_mm", 0.0))
        h_mm = float(item.get("h_mm", 0.0))
        
        center_x_orig = x_mm_orig + w_mm / 2
        center_y_orig = y_mm_orig + h_mm / 2
        
        x_mm, y_mm = convert_to_ezd_coords(center_x_orig, center_y_orig, jig_w_mm, jig_h_mm)
        angle = float(item.get("angle", 0.0))
        font_family = str(item.get("label_font_family", "Arial"))
        font_size_pt = float(item.get("label_font_size", 10))
        
        z = float(item.get("z", 0.0))

        logger.debug(f"Adding barcode '{label}': z={z}, angle={angle}, font_size={font_size_pt}pt, hatch={use_hatch}")

        barcode_text_height = font_size_pt * 0.3528
        barcode_text_width = font_size_pt * 0.3528

        self.client.add_barcode(
            text=label,
            name=name,
            x=0,
            y=0,
            z=z,
            align=8,
            pen=0,
            hatch=use_hatch,
            barcode_type=5,
            attrib=0,
            height=10.0,
            narrow_width=0.5,
            bar_width_scale=[1.0, 2.0, 3.0, 4.0],
            space_width_scale=[1.0, 2.0, 3.0, 4.0],
            mid_char_space=1.0,
            quiet_left=2.0,
            quiet_mid=0.0,
            quiet_right=2.0,
            quiet_top=0.0,
            quiet_bottom=0.0,
            row=0,
            col=0,
            check_level=0,
            size_mode=0,
            text_height=barcode_text_height,
            text_width=barcode_text_width,
            text_offset_x=0.0,
            text_offset_y=0.0,
            text_space=0.0,
            text_font=font_family,
        )

        error, size = self.client.get_entity_size(name=name)
        if error == 0:
            current_w = size["max_x"] - size["min_x"]
            current_h = size["max_y"] - size["min_y"]
            actual_center_x = (size["min_x"] + size["max_x"]) / 2
            actual_center_y = (size["min_y"] + size["max_y"]) / 2
            
            logger.debug(f"Barcode initial size: w={current_w:.2f}, h={current_h:.2f}, target: w={w_mm:.2f}, h={h_mm:.2f}")
            
            if current_w > 0 and current_h > 0:
                scale_x = w_mm / current_w
                scale_y = h_mm / current_h
                self.client.scale_entity(
                    name=name,
                    center_x=actual_center_x,
                    center_y=actual_center_y,
                    scale_x=scale_x,
                    scale_y=scale_y
                )
        
        error, size = self.client.get_entity_size(name=name)
        if error == 0:
            actual_center_x = (size["min_x"] + size["max_x"]) / 2
            actual_center_y = (size["min_y"] + size["max_y"]) / 2
            dx = x_mm - actual_center_x
            dy = y_mm - actual_center_y
            if abs(dx) > 0.001 or abs(dy) > 0.001:
                self.client.move_entity(name=name, dx=dx, dy=dy)

        if angle != 0.0:
            error, size = self.client.get_entity_size(name=name)
            if error == 0:
                actual_center_x = (size["min_x"] + size["max_x"]) / 2
                actual_center_y = (size["min_y"] + size["max_y"]) / 2
                self.client.rotate_entity(name=name, center_x=actual_center_x, center_y=actual_center_y, angle=angle)

    def reset(self):
        self._initialized = False
