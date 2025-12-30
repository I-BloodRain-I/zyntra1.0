from PIL import Image
import math

# load original
im = Image.open("original.png").convert("RGBA")
placement_x = 85
placement_y = 0
placement_w = 242
placement_h = 400

buyer_pos_x = 56
buyer_pos_y = 0

scale = 0.0992063492063492
angle_deg = 0
# placement_x = 85
# placement_y = 0
# placement_w = 242
# placement_h = 400

# buyer_pos_x = 90.60474386104326
# buyer_pos_y = 68.03177289579531

# scale = 0.17025586249818608
# angle_deg = 0

from PIL import Image, ImageDraw, ImageChops, ImageFilter
import math

def _transform_amazon_image(
        im: Image.Image,
        scale: float,
        angle_deg: float,
        place_xy: tuple[float, float],
        mask_rect: tuple[int, int, int, int],
        canvas_size: tuple[int, int] = (2000, 2000),
        rotate_resample: str = "bilinear",
        apply_unsharp: bool = True,
        unsharp_radius: float = 0.6,
        unsharp_percent: int = 80,
        unsharp_threshold: int = 2,
    ) -> Image.Image:
        """
        1) If scale<1, resize with Lanczos (best for downscale) to improve crispness.
        2) Premultiply alpha to minimize dark/bright fringes at transparency edges.
        3) Apply affine transform (rotation + translation only) so that ORIGINAL TL maps to place_xy.
        4) Unpremultiply alpha back to straight RGBA.
        5) Mask the canvas (outside mask -> transparent).
        6) Optional UnsharpMask for extra crispness.
        """
        assert 0 < scale <= 1, "scale must be in (0,1]."
        im.save("original.png")
        # --- ORIGINAL LOAD ---
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        im.save("dbg_1_original_rgba.png")

        # 1) SCALE
        W, H = im.size
        canvas_size = (int(W * 2.0), int(H * 2.0))
        print(f"canvas size: {canvas_size}")
        # new_w = max(1, int(round(W * scale)))
        # new_h = max(1, int(round(H * scale)))
        new_w = W
        new_h = H
        # lanczos = Image.Resampling.LANCZOS

        # im_scaled = im.resize((new_w, new_h), lanczos)
        im_scaled = im
        # im_scaled.save("dbg_2_scaled.png")

        # SPLIT TO CHANNELS (RGB+A)
        r, g, b, a = im_scaled.split()
        r.save("dbg_3_r.png")
        g.save("dbg_4_g.png")
        b.save("dbg_5_b.png")
        a.save("dbg_6_alpha_original.png")

        # 2) MATRIX
        theta = math.radians(angle_deg)
        c_, s_ = math.cos(theta), math.sin(theta)
        px, py = place_xy
        print(f"place_xy: {px}, {py}")
        # px /= (scale * 3)
        # py /= (scale * 3)
        # px /= scale
        # py /= scale
        # print(f"place_xy scaled: {px}, {py}")
        k = 1.0

        inv_a =  c_ / k
        inv_b =  s_ / k
        inv_d = -s_ / k
        inv_e =  c_ / k
        inv_c = -(inv_a * px + inv_b * py)
        inv_f = -(inv_d * px + inv_e * py)

        matrix = (inv_a, inv_b, inv_c, inv_d, inv_e, inv_f)

        canvas_w, canvas_h = canvas_size

        # resampler
        if rotate_resample == "bicubic":
            resamp = Image.Resampling.BICUBIC
        elif rotate_resample == "nearest":
            resamp = Image.Resampling.NEAREST
        else:
            resamp = Image.Resampling.BILINEAR

        # --- 3) TRANSFORM RGB CHANNELS SEPARATELY ---
        warped_r = r.transform(
            (canvas_w, canvas_h),
            Image.Transform.AFFINE,
            matrix,
            resample=resamp,
            fillcolor=0,
        )
        warped_r.save("dbg_7_warped_r.png")

        warped_g = g.transform(
            (canvas_w, canvas_h),
            Image.Transform.AFFINE,
            matrix,
            resample=resamp,
            fillcolor=0,
        )
        warped_g.save("dbg_8_warped_g.png")

        warped_b = b.transform(
            (canvas_w, canvas_h),
            Image.Transform.AFFINE,
            matrix,
            resample=resamp,
            fillcolor=0,
        )
        warped_b.save("dbg_9_warped_b.png")

        # --- 4) TRANSFORM ALPHA SEPARATELY ---
        warped_a = a.transform(
            (canvas_w, canvas_h),
            Image.Transform.AFFINE,
            matrix,
            resample=resamp,
            fillcolor=0,
        )
        warped_a.save("dbg_10_warped_alpha.png")

        # MERGE INTO CLEAN RGBA (NO ARTIFACTS)
        warped = Image.merge("RGBA", (warped_r, warped_g, warped_b, warped_a))
        warped.save("dbg_11_merged_rgba_no_fringe.png")

        # 5) APPLY RECTANGULAR MASK
        mx, my, mw, mh = mask_rect
        print(f"mask rect: {mx}, {my}, {mw}, {mh}")
        # mx /= scale
        # my /= scale
        mw /= scale
        mh /= scale
        print(f"mask rect scaled: {mx}, {my}, {mw}, {mh}")
        rect_mask = Image.new("L", (canvas_w, canvas_h), 0)
        ImageDraw.Draw(rect_mask).rectangle([mx, my, mx + mw, my + mh], fill=255)
        rect_mask.save("dbg_12_rect_mask.png")

        # multiply alpha
        final_alpha = ImageChops.multiply(warped_a, rect_mask)
        final_alpha.save("dbg_13_final_alpha_masked.png")

        out = Image.merge("RGBA", (warped_r, warped_g, warped_b, final_alpha))
        out.save("dbg_14_final_rgba_before_sharpen.png")

        # 6) SHARPEN
        if apply_unsharp:
            out = out.filter(ImageFilter.UnsharpMask(
                radius=unsharp_radius,
                percent=unsharp_percent,
                threshold=unsharp_threshold
            ))
            out.save("dbg_15_final_sharpened.png")

        # 7) CROP
        result = out.crop((mx, my, mx + mw, my + mh))
        result.save("dbg_16_result_cropped.png")

        return result

img2 = _transform_amazon_image(
    im,
    scale,
    angle_deg,
    (placement_x, placement_y),
    (buyer_pos_x, buyer_pos_y, placement_w, placement_h)).save("test_final_crop_normal.png")