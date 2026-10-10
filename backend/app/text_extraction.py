"""Step 1 of the pipeline: turn an uploaded PDF or image into text, page by page.

- Text-based PDFs (most portal downloads) -> pdfplumber, which keeps table rows on one line.
- Scanned PDFs (pages with almost no text layer) -> render with PyMuPDF, then Tesseract OCR.
- Images (PNG/JPG) -> Pillow + Tesseract OCR.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import pdfplumber
import pymupdf
import pytesseract
from PIL import Image, ImageOps

import os

if os.getenv("TESSERACT_CMD"):  # e.g. Windows installs that aren't on PATH
    pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]

MIN_CHARS_FOR_TEXT_LAYER = 40
# Tuned for small hosting instances (e.g. Render free: 512 MB RAM, a fraction of a CPU).
OCR_DPI = int(os.getenv("OCR_DPI", "200"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "10"))
MAX_IMAGE_SIDE = 2600  # downscale large phone photos before OCR


@dataclass
class PageText:
    page: int
    text: str
    method: str  # "pdf-text" or "ocr"


@dataclass
class TextResult:
    pages: list[PageText] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def method(self) -> str:
        methods = sorted({p.method for p in self.pages})
        return "+".join(methods) if methods else "none"


def _ocr_image(img: Image.Image) -> str:
    gray = ImageOps.grayscale(img)
    # --psm 6 treats the page as a uniform block, which keeps table rows together.
    return pytesseract.image_to_string(gray, config="--psm 6")


def extract_text(data: bytes, filename: str, content_type: str | None = None) -> TextResult:
    name = (filename or "").lower()
    is_pdf = name.endswith(".pdf") or (content_type or "").endswith("pdf") or data[:4] == b"%PDF"
    result = TextResult()

    if is_pdf:
        # Process one page at a time and release it, so memory stays flat on long PDFs.
        with pdfplumber.open(io.BytesIO(data)) as pdf, pymupdf.open(stream=data, filetype="pdf") as doc:
            n_pages = len(pdf.pages)
            if n_pages > MAX_PAGES:
                result.warnings.append(f"{filename} has {n_pages} pages; only the first {MAX_PAGES} were read.")
            for i in range(min(n_pages, MAX_PAGES)):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                page.close()
                if len(text.strip()) >= MIN_CHARS_FOR_TEXT_LAYER:
                    result.pages.append(PageText(i + 1, text, "pdf-text"))
                    continue
                # Scanned page: rasterize in grayscale and OCR it.
                pix = doc[i].get_pixmap(dpi=OCR_DPI, colorspace=pymupdf.csGRAY, alpha=False)
                img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
                del pix
                result.pages.append(PageText(i + 1, _ocr_image(img), "ocr"))
                del img
    else:
        try:
            img = Image.open(io.BytesIO(data))
            img = ImageOps.exif_transpose(img)
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"Could not open {filename} as an image or PDF: {exc}")
            return result
        result.pages.append(PageText(1, _ocr_image(img), "ocr"))

    if not result.full_text.strip():
        result.warnings.append(f"No readable text found in {filename}.")
    return result
