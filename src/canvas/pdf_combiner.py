"""
PDF Combiner Module

This module combines multiple rendered PDFs into larger PDFs (1500mm x 420mm)
based on their sizes. It uses a simple bin-packing algorithm to fit as many
PDFs as possible into each combined PDF.
"""

from __future__ import annotations

import os
import logging
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import cairo
from PIL import Image
import numpy as np
import pikepdf
Image.MAX_IMAGE_PIXELS = 999_999_999_999_999

logger = logging.getLogger(__name__)

# Target size for combined PDFs in mm
COMBINED_PDF_WIDTH_MM = 500.0
COMBINED_PDF_HEIGHT_MM = 1440.0

# Spacing between PDFs in mm
PDF_SPACING_MM = 0.0

# Padding from top-left corner in mm
PADDING_MM = 10.0


@dataclass
class PDFInfo:
    """Information about a rendered PDF"""
    path: str
    width_mm: float
    height_mm: float
    order_range: str  # e.g., "161693-161695"
    side: str  # "front" or "back"
    pdf_order: int = 1  # For when a single order range has multiple PDFs
    dpi: int = 1200  # DPI used to render this PDF
    cmyk: str = "75,0,75,0"  # CMYK color for spot color alternate (C,M,Y,K in 0-100 range)


@dataclass
class PlacedPDF:
    """Information about a PDF placed in the combined sheet"""
    pdf_info: PDFInfo
    x_mm: float
    y_mm: float


class PDFCombiner:
    """Combines multiple rendered PDFs into larger sheets"""
    
    def __init__(self, output_dir: Path):
        """
        Initialize the PDF combiner.
        
        Args:
            output_dir: Directory where combined PDFs will be saved
        """
        self.output_dir = output_dir
        self.pending_pdfs: List[PDFInfo] = []
        self.combined_count = 0
        
    def add_pdf(self, pdf_info: PDFInfo) -> None:
        """
        Add a PDF to the pending list.
        
        Args:
            pdf_info: Information about the PDF to add
        """
        self.pending_pdfs.append(pdf_info)
        logger.debug(f"Added PDF to pending list: {pdf_info.path} ({pdf_info.width_mm}x{pdf_info.height_mm}mm), cmyk={pdf_info.cmyk}")
        
    def _simple_pack(self, pdfs: List[PDFInfo]) -> List[List[PlacedPDF]]:
        """
        Simple bin-packing algorithm: pack PDFs into sheets row by row.
        
        Args:
            pdfs: List of PDFs to pack
            
        Returns:
            List of sheets, where each sheet is a list of placed PDFs
        """
        logger.info(f"Packing {len(pdfs)} PDFs into sheets ({COMBINED_PDF_WIDTH_MM}x{COMBINED_PDF_HEIGHT_MM}mm)")
        
        sheets: List[List[PlacedPDF]] = []
        current_sheet: List[PlacedPDF] = []
        
        current_x = PADDING_MM
        current_y = PADDING_MM
        row_height = 0.0
        
        for i, pdf in enumerate(pdfs):
            logger.debug(f"Packing PDF {i+1}/{len(pdfs)}: {pdf.width_mm}x{pdf.height_mm}mm at ({current_x}, {current_y})")
            pdf_width = pdf.width_mm + PDF_SPACING_MM
            pdf_height = pdf.height_mm + PDF_SPACING_MM
            
            # Check if PDF fits in current row (accounting for padding)
            if current_x + pdf.width_mm <= COMBINED_PDF_WIDTH_MM - PADDING_MM:
                # Place in current row
                current_sheet.append(PlacedPDF(pdf, current_x, current_y))
                logger.debug(f"  -> Placed in current row at ({current_x}, {current_y})")
                current_x += pdf_width
                row_height = max(row_height, pdf_height)
            else:
                # Move to next row
                current_x = PADDING_MM
                current_y += row_height
                row_height = pdf_height
                logger.debug(f"  -> Moving to next row at y={current_y}")
                
                # Check if we need a new sheet (accounting for padding)
                if current_y + pdf.height_mm > COMBINED_PDF_HEIGHT_MM - PADDING_MM:
                    # Start new sheet
                    logger.debug(f"  -> Starting new sheet (current_y {current_y} + pdf height {pdf.height_mm} > limit {COMBINED_PDF_HEIGHT_MM - PADDING_MM})")
                    if current_sheet:
                        sheets.append(current_sheet)
                        logger.info(f"  -> Completed sheet {len(sheets)} with {len(current_sheet)} PDFs")
                    current_sheet = []
                    current_x = PADDING_MM
                    current_y = PADDING_MM
                    row_height = pdf_height
                
                # Place PDF
                current_sheet.append(PlacedPDF(pdf, current_x, current_y))
                logger.debug(f"  -> Placed at ({current_x}, {current_y})")
                current_x += pdf_width
        
        # Add last sheet if not empty
        if current_sheet:
            sheets.append(current_sheet)
            logger.info(f"Completed final sheet {len(sheets)} with {len(current_sheet)} PDFs")
        
        logger.info(f"Total sheets created: {len(sheets)}, Total PDFs placed: {sum(len(sheet) for sheet in sheets)}")
            
        return sheets
    
    def _add_spot_color_borders(
        self,
        pdf_path: str,
        placed_pdfs: List[PlacedPDF],
        mm_to_pt: float
    ) -> None:
        """
        Add spot color borders to a combined PDF using pikepdf.
        
        Args:
            pdf_path: Path to the PDF file
            placed_pdfs: List of PDFs with their positions
            mm_to_pt: Conversion factor from mm to points
        """
        logger.info(f"Adding spot color borders to {pdf_path}")
        
        # Open the PDF with pikepdf (allow overwriting since we're modifying in place)
        pdf = pikepdf.Pdf.open(pdf_path, allow_overwriting_input=True)
        
        if len(pdf.pages) == 0:
            logger.warning("PDF has no pages")
            pdf.close()
            return
        
        page = pdf.pages[0]  # We only have one page
        
        # Define the spot color "cutcontourperf"
        spot_color_name = "cutcontourperf"
        
        # Border width in points (1mm)
        border_width_pt = 1.0 * mm_to_pt
        
        # Get CMYK from first PDF (all should have same color from same jig)
        cmyk_str = placed_pdfs[0].pdf_info.cmyk if placed_pdfs else "75,0,75,0"
        logger.info(f"Raw CMYK string from PDFInfo: '{cmyk_str}'")
        
        # Parse CMYK string (format: "C,M,Y,K" in 0-100 range)
        def parse_cmyk(cmyk_str: str) -> Tuple[float, float, float, float]:
            try:
                parts = [p.strip() for p in str(cmyk_str or "").split(",")]
                if len(parts) < 4:
                    parts += ["0"] * (4 - len(parts))
                elif len(parts) > 4:
                    parts = parts[:4]
                c, m, y, k = [float(p or 0) for p in parts]
                # Normalize to 0-1 range (assuming input is 0-100)
                c = max(0.0, min(1.0, c / 100.0))
                m = max(0.0, min(1.0, m / 100.0))
                y = max(0.0, min(1.0, y / 100.0))
                k = max(0.0, min(1.0, k / 100.0))
                return (c, m, y, k)
            except Exception:
                logger.warning(f"Failed to parse CMYK '{cmyk_str}', using black")
                return (0.0, 0.0, 0.0, 1.0)
        
        c, m, y, k = parse_cmyk(cmyk_str)
        logger.info(f"Using CMYK color for spot color alternate: C={c:.2f}, M={m:.2f}, Y={y:.2f}, K={k:.2f}")
        
        # Create the Separation color space
        # [/Separation /Name /AlternateSpace /TintTransform]
        # The tint transform converts from 0-1 tint to the CMYK alternate color space
        # PostScript function: Takes tint (0-1) from stack, outputs C M Y K values (4 values)
        # The function receives 'tint' on the stack and must leave C M Y K on the stack
        # Simplified approach: We want tint * [C M Y K] = [C*tint M*tint Y*tint K*tint]
        # Stack: tint -> C*tint M*tint Y*tint K*tint
        tint_function_code = (
            f"{{ "  # Start function
            f"dup dup dup "  # Duplicate tint 3 times: [tint tint tint tint]
            f"{c} mul 4 1 roll "  # [C*tint tint tint tint]
            f"{m} mul 3 1 roll "  # [C*tint M*tint tint tint]
            f"{y} mul exch "  # [C*tint M*tint Y*tint tint]
            f"{k} mul "  # [C*tint M*tint Y*tint K*tint]
            f"}}"  # End function
        ).encode('latin-1')
        
        logger.debug(f"Tint function code: {tint_function_code.decode('latin-1')}")
        
        tint_transform = pikepdf.Stream(pdf, tint_function_code)
        tint_transform.FunctionType = 4
        tint_transform.Domain = [0, 1]
        tint_transform.Range = [0, 1, 0, 1, 0, 1, 0, 1]  # For DeviceCMYK (4 components)
        
        separation_colorspace = pikepdf.Array([
            pikepdf.Name.Separation,
            pikepdf.Name("/" + spot_color_name),  # pikepdf.Name() handles the / prefix automatically
            pikepdf.Name.DeviceCMYK,
            tint_transform
        ])
        
        # Add ColorSpace to page resources
        if pikepdf.Name.Resources not in page:
            page.Resources = pikepdf.Dictionary()
        
        if pikepdf.Name.ColorSpace not in page.Resources:
            page.Resources.ColorSpace = pikepdf.Dictionary()
        
        # Add our spot color to the ColorSpace dictionary
        page.Resources.ColorSpace.SpotColor = separation_colorspace
        
        # Build content stream to draw rectangles with spot color
        content_lines = []
        
        for placed in placed_pdfs:
            x_pt = placed.x_mm * mm_to_pt
            y_pt = placed.y_mm * mm_to_pt
            width_pt = placed.pdf_info.width_mm * mm_to_pt
            height_pt = placed.pdf_info.height_mm * mm_to_pt
            
            # Add drawing commands for this rectangle
            content_lines.append(b"q")  # Save graphics state
            content_lines.append(b"/SpotColor CS")  # Set STROKE color space (uppercase CS for stroke)
            content_lines.append(b"1 SCN")  # Set STROKE color (100% tint, uppercase SCN for stroke)
            content_lines.append(f"{border_width_pt:.4f} w".encode())  # Set line width
            content_lines.append(
                f"{x_pt:.4f} {y_pt:.4f} {width_pt:.4f} {height_pt:.4f} re".encode()
            )  # Draw rectangle
            content_lines.append(b"S")  # Stroke
            content_lines.append(b"Q")  # Restore graphics state
            
            logger.debug(f"Added spot color border at ({x_pt:.2f}, {y_pt:.2f}) {width_pt:.2f}x{height_pt:.2f}pt")
        
        # Append to existing page content
        if pikepdf.Name.Contents in page:
            # Get existing content
            existing_content = page.Contents.read_bytes()
            # Append new content
            new_content = existing_content + b"\n" + b"\n".join(content_lines) + b"\n"
            # Update content stream
            page.Contents = pikepdf.Stream(pdf, new_content)
        else:
            # Create new content stream
            page.Contents = pikepdf.Stream(pdf, b"\n".join(content_lines))
        
        # Save the PDF
        pdf.save(pdf_path)
        pdf.close()
        
        logger.info(f"Added {len(placed_pdfs)} spot color borders with name '{spot_color_name}'")
    
    def _render_combined_pdf(
        self, 
        placed_pdfs: List[PlacedPDF], 
        output_path: str,
        dpi: int = 1200
    ) -> None:
        """
        Render a combined PDF with multiple PDFs placed on it using Cairo directly.
        
        Args:
            placed_pdfs: List of PDFs with their positions
            output_path: Path where the combined PDF will be saved
            dpi: DPI for rendering (should match the DPI of source PDFs)
        """
        # Convert mm to points (1 inch = 72 points = 25.4 mm)
        mm_to_pt = 72.0 / 25.4
        width_pt = COMBINED_PDF_WIDTH_MM * mm_to_pt
        height_pt = COMBINED_PDF_HEIGHT_MM * mm_to_pt
        
        logger.info(f"Creating combined PDF: {width_pt:.2f}x{height_pt:.2f}pt (at {dpi} DPI)")
        
        # Create PDF surface at the target size
        surface = cairo.PDFSurface(output_path, width_pt, height_pt)
        context = cairo.Context(surface)
        
        # Fill background with white
        context.set_source_rgb(1, 1, 1)
        context.paint()
        
        # Place each PDF
        placed_count = 0
        for placed in placed_pdfs:
            try:
                pdf_path = placed.pdf_info.path
                
                # Try to find corresponding PNG
                png_path = pdf_path.replace('.pdf', '.png')
                if not os.path.exists(png_path):
                    logger.warning(f"PNG not found for {pdf_path}, skipping")
                    continue
                
                logger.debug(f"Loading PNG: {png_path}")
                
                # Load the PNG image
                pdf_img = Image.open(png_path)
                
                # Convert to RGB if needed
                if pdf_img.mode == "RGBA":
                    # Create white background
                    background = Image.new("RGB", pdf_img.size, (255, 255, 255))
                    background.paste(pdf_img, mask=pdf_img.split()[3])
                    pdf_img = background
                elif pdf_img.mode != "RGB":
                    pdf_img = pdf_img.convert("RGB")
                
                # Get image dimensions
                img_width, img_height = pdf_img.size
                
                logger.debug(f"Image size: {img_width}x{img_height}px")
                
                # Convert PIL image to numpy array for Cairo
                arr = np.array(pdf_img)
                
                # Create Cairo image surface
                # Cairo expects BGRA format
                arr_bgra = np.zeros((img_height, img_width, 4), dtype=np.uint8)
                arr_bgra[:, :, 2] = arr[:, :, 0]  # R
                arr_bgra[:, :, 1] = arr[:, :, 1]  # G
                arr_bgra[:, :, 0] = arr[:, :, 2]  # B
                arr_bgra[:, :, 3] = 255           # A (fully opaque)
                
                # Create Cairo image surface
                stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, img_width)
                img_surface = cairo.ImageSurface.create_for_data(
                    arr_bgra, cairo.FORMAT_ARGB32, img_width, img_height, stride
                )
                
                # Calculate position in points
                x_pt = placed.x_mm * mm_to_pt
                y_pt = placed.y_mm * mm_to_pt
                
                # Calculate the scale needed to fit the image at the correct size
                # The PNG was rendered at high DPI, we need to scale it to the correct physical size
                target_width_pt = placed.pdf_info.width_mm * mm_to_pt
                target_height_pt = placed.pdf_info.height_mm * mm_to_pt
                
                scale_x = target_width_pt / img_width
                scale_y = target_height_pt / img_height
                
                logger.debug(f"Placing at ({x_pt:.2f}, {y_pt:.2f})pt, scale: ({scale_x:.4f}, {scale_y:.4f})")
                
                # Save context state
                context.save()
                
                # Move to position and scale
                context.translate(x_pt, y_pt)
                context.scale(scale_x, scale_y)
                
                # Draw the image
                context.set_source_surface(img_surface, 0, 0)
                
                # Use high-quality filtering
                pattern = context.get_source()
                pattern.set_filter(cairo.FILTER_BEST)
                
                context.paint()
                
                # Restore context state
                context.restore()
                
                placed_count += 1
                
            except Exception as e:
                logger.exception(f"Failed to place PDF {placed.pdf_info.path}: {e}")
                continue
        
        logger.info(f"Placed {placed_count}/{len(placed_pdfs)} PDFs on combined sheet")
        
        # Finish the PDF
        surface.finish()
        
        try:
            with pikepdf.open(output_path, allow_overwriting_input=True) as pdf:
                page = pdf.pages[0]
                page.Rotate = (int(page.get("/Rotate", 0)) + 270) % 360
                pdf.save(output_path)
            logger.info(f"Rotated final single-page PDF {output_path} by 90 degrees")
        except Exception as e:
            logger.exception(f"Failed to rotate PDF: {e}")

        logger.info(f"Combined PDF saved to {output_path}")
        
        # Add spot color borders using PyMuPDF
        try:
            self._add_spot_color_borders(output_path, placed_pdfs, mm_to_pt)
        except Exception as e:
            logger.exception(f"Failed to add spot color borders: {e}")
    
    def combine_pending(self, force: bool = False) -> List[str]:
        """
        Combine pending PDFs into larger sheets.
        
        Args:
            force: If True, combine even if there's only one PDF
            
        Returns:
            List of paths to combined PDFs
        """
        if not self.pending_pdfs:
            return []
        
        if not force and len(self.pending_pdfs) < 2:
            logger.debug("Not enough PDFs to combine yet")
            return []
        
        # Separate PDFs by side (front/back) to avoid mixing them
        pdfs_by_side = {}
        for pdf in self.pending_pdfs:
            side = pdf.side
            if side not in pdfs_by_side:
                pdfs_by_side[side] = []
            pdfs_by_side[side].append(pdf)
        
        logger.info(f"Grouping PDFs by side: {', '.join(f'{side}={len(pdfs)}' for side, pdfs in pdfs_by_side.items())}")
        
        combined_paths = []
        
        # Process each side separately
        for side, pdfs in pdfs_by_side.items():
            if not pdfs:
                continue
                
            # Pack PDFs into sheets
            sheets = self._simple_pack(pdfs)
            
            logger.info(f"Created {len(sheets)} sheet(s) for {side} side")
            
            for sheet_num, sheet in enumerate(sheets, start=1):
                self.combined_count += 1
                
                # Generate output filename
                # Use the order ranges from the PDFs in this sheet
                order_ranges = sorted(set(p.pdf_info.order_range for p in sheet))
                if len(order_ranges) == 1:
                    range_str = order_ranges[0]
                else:
                    # Multiple order ranges in one sheet
                    first_order = min(int(r.split('-')[0]) for r in order_ranges)
                    last_order = max(int(r.split('-')[1]) for r in order_ranges)
                    range_str = f"{first_order}-{last_order}"
                
                # Include side and sheet number in filename to avoid overwrites
                # Only add sheet number if there are multiple sheets for this side
                if len(sheets) > 1:
                    output_filename = f"COMBINED_{range_str}_{side}_sheet{sheet_num}.pdf"
                else:
                    output_filename = f"COMBINED_{range_str}_{side}.pdf"
                    
                output_path = str(self.output_dir / output_filename)
                
                # Render the combined PDF
                # Use DPI from first PDF in sheet
                dpi = sheet[0].pdf_info.dpi if sheet else 1200
                try:
                    self._render_combined_pdf(sheet, output_path, dpi=dpi)
                    combined_paths.append(output_path)
                    logger.info(f"Created combined PDF: {output_filename} with {len(sheet)} PDFs")
                except Exception as e:
                    logger.exception(f"Failed to create combined PDF {output_filename}: {e}")
                    continue
        
        # Clear pending list
        self.pending_pdfs.clear()
        
        return combined_paths
    
    def finalize(self) -> List[str]:
        """
        Combine all remaining pending PDFs.
        
        Returns:
            List of paths to combined PDFs
        """
        return self.combine_pending(force=True)
