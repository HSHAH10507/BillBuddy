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
OCR_DPI = 300


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
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text_pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(pdf.pages)]
        doc = pymupdf.open(stream=data, filetype="pdf")
        for page_no, text in text_pages:
            if len(text.strip()) >= MIN_CHARS_FOR_TEXT_LAYER:
                result.pages.append(PageText(page_no, text, "pdf-text"))
                continue
            # Scanned page: rasterize and OCR it.
            pix = doc[page_no - 1].get_pixmap(dpi=OCR_DPI)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            result.pages.append(PageText(page_no, _ocr_image(img), "ocr"))
        doc.close()
    else:
        try:
            img = Image.open(io.BytesIO(data))
            img = ImageOps.exif_transpose(img)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"Could not open {filename} as an image or PDF: {exc}")
            return result
        result.pages.append(PageText(1, _ocr_image(img), "ocr"))

    if not result.full_text.strip():
        result.warnings.append(f"No readable text found in {filename}.")
    return result
