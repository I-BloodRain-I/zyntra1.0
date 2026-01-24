import logging
from pathlib import Path

from src.core.state import get_sdk_client

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
    max_iterations: int = 5
) -> tuple[float, float]:
    width_sdk = initial_width
    height_sdk = initial_height
    
    for i in range(max_iterations):
        client.set_font(font_name=font_family, height=height_sdk, width=width_sdk, equal_char_width=False)
        client.add_text(text=text, name=name, x=x, y=y, z=z, align=8, angle=0.0, pen=0, hatch=False)
        
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
            self.client.initialize()
            self._initialized = True

    def export_scene(
        self,
        items: list[dict],
        output_path: str,
        jig_w_mm: float = 0.0,
        jig_h_mm: float = 0.0,
        clear_before: bool = True,
    ) -> bool:
        self._ensure_initialized()
        
        if clear_before:
            self.client.clear_all()

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

            if item_type == "text":
                self._add_text_entity(item, entity_name, jig_w_mm, jig_h_mm)
            elif item_type == "rect":
                self._add_rect_text_entity(item, entity_name, jig_w_mm, jig_h_mm)
            elif item_type == "image":
                self._add_image_entity(item, entity_name, jig_w_mm, jig_h_mm)
            elif item_type == "barcode":
                self._add_barcode_entity(item, entity_name, jig_w_mm, jig_h_mm)

        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if output_file.exists():
            output_file.unlink()

        self.client.save_file(filename=str(output_file))
        logger.info(f"EZD file saved: {output_file}")
        return True

    def _add_text_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float):
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

        logger.debug(f"Adding text '{text}': z={z}, width_mm={width_mm}, height_mm={height_mm}, font={font_family}")

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
            angle=angle
        )
        
        logger.debug(f"Final SDK params: width={width_sdk:.3f}, height={height_sdk:.3f}")

        if angle != 0.0:
            error, size = self.client.get_entity_size(name=name)
            if error == 0:
                actual_center_x = (size["min_x"] + size["max_x"]) / 2
                actual_center_y = (size["min_y"] + size["max_y"]) / 2
                logger.debug(f"Rotating text '{text}' by {angle} degrees")
                self.client.rotate_entity(name=name, center_x=actual_center_x, center_y=actual_center_y, angle=angle)

    def _add_rect_text_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float):
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

        logger.debug(f"Adding rect text '{label}': z={z}, width_mm={width_mm}, height_mm={height_mm}, font={font_family}")
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
            angle=angle
        )
        
        logger.debug(f"Final SDK params: width={width_sdk:.3f}, height={height_sdk:.3f}")

        if angle != 0.0:
            error, size = self.client.get_entity_size(name=name)
            if error == 0:
                actual_center_x = (size["min_x"] + size["max_x"]) / 2
                actual_center_y = (size["min_y"] + size["max_y"]) / 2
                self.client.rotate_entity(name=name, center_x=actual_center_x, center_y=actual_center_y, angle=angle)

    def _add_image_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float):
        path = str(item.get("path", ""))
        if not path or not Path(path).exists():
            logger.warning(f"Image path not found: {path}")
            return

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        w_mm = float(item.get("w_mm", 0.0))
        h_mm = float(item.get("h_mm", 0.0))
        
        center_x_orig = x_mm_orig + w_mm / 2
        center_y_orig = y_mm_orig + h_mm / 2
        target_center_x, target_center_y = convert_to_ezd_coords(center_x_orig, center_y_orig, jig_w_mm, jig_h_mm)
        
        angle = float(item.get("angle", 0.0))
        z = float(item.get("z", 0.0))

        logger.debug(f"Adding image: z={z}, path={path}, angle={angle}")
        logger.debug("Original coords (top-left): x_mm={:.3f}, y_mm={:.3f}, w_mm={:.3f}, h_mm={:.3f}".format(x_mm_orig, y_mm_orig, w_mm, h_mm))
        logger.debug("Target center (EZD): x_mm={:.3f}, y_mm={:.3f}".format(target_center_x, target_center_y))

        self.client.add_file(
            filename=path,
            name=name,
            x=0,
            y=0,
            z=z,
            align=0,
            ratio=1.0,
            pen=0,
            hatch=False,
        )

        error, size = self.client.get_entity_size(name=name)
        if error == 0:
            current_w = size["max_x"] - size["min_x"]
            current_h = size["max_y"] - size["min_y"]
            actual_center_x = (size["min_x"] + size["max_x"]) / 2
            actual_center_y = (size["min_y"] + size["max_y"]) / 2
            
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
            dx = target_center_x - actual_center_x
            dy = target_center_y - actual_center_y
            if abs(dx) > 0.001 or abs(dy) > 0.001:
                self.client.move_entity(name=name, dx=dx, dy=dy)

        if angle != 0.0:
            error, size = self.client.get_entity_size(name=name)
            if error == 0:
                actual_center_x = (size["min_x"] + size["max_x"]) / 2
                actual_center_y = (size["min_y"] + size["max_y"]) / 2
                self.client.rotate_entity(name=name, center_x=actual_center_x, center_y=actual_center_y, angle=angle)

    def _add_barcode_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float):
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

        logger.debug(f"Adding barcode '{label}': z={z}, angle={angle}, font_size={font_size_pt}pt")

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
            hatch=False,
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
