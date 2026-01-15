import logging
from pathlib import Path

from src.core.state import get_sdk_client

logger = logging.getLogger(__name__)

TEXT_X_OFFSET = -0.15
TEXT_Y_OFFSET = 0.0


def convert_to_ezd_coords(x_mm: float, y_mm: float, jig_w_mm: float, jig_h_mm: float) -> tuple[float, float]:
    ezd_x = x_mm - (jig_w_mm / 2)
    ezd_y = (jig_h_mm / 2) - y_mm
    return ezd_x, ezd_y


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

        entity_index = 0
        for item in items:
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
        font_size_pt = float(item.get("font_size_pt", 12))
        height_mm = font_size_pt * 0.3528
        angle = float(item.get("angle", 0.0))

        self.client.set_font(
            font_name=font_family,
            height=height_mm,
            width=height_mm,
            char_angle=0.0,
            char_space=0.0,
            line_space=0.0,
            equal_char_width=False,
        )

        self.client.add_text(
            text=text,
            name=name,
            x=x_mm + TEXT_X_OFFSET,
            y=y_mm + TEXT_Y_OFFSET,
            z=0.0,
            align=6,
            angle=0.0,
            pen=0,
            hatch=False,
        )

        if angle != 0.0:
            self.client.rotate_entity(name=name, center_x=x_mm, center_y=y_mm, angle=-angle)

    def _add_rect_text_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float):
        label = str(item.get("label", ""))
        if not label:
            return

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        w_mm = float(item.get("w_mm", 0.0))
        h_mm = float(item.get("h_mm", 0.0))
        x_mm, y_mm = convert_to_ezd_coords(x_mm_orig, y_mm_orig, jig_w_mm, jig_h_mm)
        angle = float(item.get("angle", 0.0))
        font_family = str(item.get("label_font_family", "Arial"))
        font_size_pt = float(item.get("label_font_size", 10))
        height_mm = font_size_pt * 0.3528

        center_x = x_mm + w_mm / 2
        center_y = y_mm + h_mm / 2

        self.client.set_font(
            font_name=font_family,
            height=height_mm,
            width=height_mm,
            char_angle=0.0,
            char_space=0.0,
            line_space=0.0,
            equal_char_width=False,
        )

        self.client.add_text(
            text=label,
            name=name,
            x=center_x,
            y=center_y,
            z=0.0,
            align=8,
            angle=0.0,
            pen=0,
            hatch=False,
        )

        if angle != 0.0:
            self.client.rotate_entity(name=name, center_x=center_x, center_y=center_y, angle=-angle)

    def _add_image_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float):
        path = str(item.get("path", ""))
        if not path or not Path(path).exists():
            logger.warning(f"Image path not found: {path}")
            return

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        w_mm = float(item.get("w_mm", 0.0))
        h_mm = float(item.get("h_mm", 0.0))
        x_mm, y_mm = convert_to_ezd_coords(x_mm_orig, y_mm_orig, jig_w_mm, jig_h_mm)
        angle = float(item.get("angle", 0.0))

        self.client.add_file(
            filename=path,
            name=name,
            x=x_mm,
            y=y_mm,
            z=0.0,
            align=6,
            ratio=1.0,
            pen=0,
            hatch=False,
        )

        error, size = self.client.get_entity_size(name=name)
        if error == 0:
            current_w = size["max_x"] - size["min_x"]
            current_h = size["max_y"] - size["min_y"]
            
            if current_w > 0 and current_h > 0:
                scale_x = w_mm / current_w
                scale_y = h_mm / current_h
                self.client.scale_entity(
                    name=name,
                    center_x=x_mm,
                    center_y=y_mm,
                    scale_x=scale_x,
                    scale_y=scale_y
                )

        if angle != 0.0:
            center_x = x_mm + w_mm / 2
            center_y = y_mm + h_mm / 2
            self.client.rotate_entity(name=name, center_x=center_x, center_y=center_y, angle=-angle)

    def _add_barcode_entity(self, item: dict, name: str, jig_w_mm: float, jig_h_mm: float):
        label = str(item.get("label", ""))
        if not label:
            return

        x_mm_orig = float(item.get("x_mm", 0.0))
        y_mm_orig = float(item.get("y_mm", 0.0))
        w_mm = float(item.get("w_mm", 0.0))
        h_mm = float(item.get("h_mm", 0.0))
        x_mm, y_mm = convert_to_ezd_coords(x_mm_orig, y_mm_orig, jig_w_mm, jig_h_mm)
        angle = float(item.get("angle", 0.0))
        font_family = str(item.get("label_font_family", "Arial"))
        font_size_pt = float(item.get("label_font_size", 10))

        self.client.add_barcode(
            text=label,
            name=name,
            x=x_mm,
            y=y_mm,
            z=0.0,
            align=6,
            pen=0,
            hatch=False,
            barcode_type=17,
            attrib=0,
            height=h_mm,
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
            text_height=font_size_pt * 0.3528,
            text_width=font_size_pt * 0.3528,
            text_offset_x=0.0,
            text_offset_y=0.0,
            text_space=0.0,
            text_font=font_family,
        )

        if angle != 0.0:
            center_x = x_mm + w_mm / 2
            center_y = y_mm + h_mm / 2
            self.client.rotate_entity(name=name, center_x=center_x, center_y=center_y, angle=-angle)

    def reset(self):
        self._initialized = False
