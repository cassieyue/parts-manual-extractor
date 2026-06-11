#!/usr/bin/env python3
"""
Analyze and prepare a parts manual PDF for transcription.

Usage: python3 process_pdf.py <pdf_path> [output_dir]

Output (JSON to stdout):
  {
    "page_count": 150,
    "is_image_based": true,
    "needs_split": true,
    "chunks": [
      { "index": 1, "pages": "1-100", "path": "/path/to/chunk_01_pages_1-100.pdf" },
      { "index": 2, "pages": "101-150", "path": "/path/to/chunk_02_pages_101-150.pdf" }
    ],
    "output_dir": "/path/to/output"
  }

If is_image_based is true, chunks are OCR'd text files (.txt).
If is_image_based is false, chunks are split PDF files (.pdf) — or the original if ≤ 100 pages.
"""

import sys
import os
import json
from pathlib import Path


def analyze_pdf(pdf_path: str) -> dict:
    from pypdf import PdfReader

    path = Path(pdf_path)
    if not path.exists():
        return {"error": f"File not found: {pdf_path}"}

    reader = PdfReader(str(path))
    page_count = len(reader.pages)

    # Detect image-based: sample first 3 pages, if total extracted text < 100 chars → image-based
    sample_text = ""
    for i in range(min(3, page_count)):
        try:
            sample_text += reader.pages[i].extract_text() or ""
        except Exception:
            pass

    is_image_based = len(sample_text.strip()) < 100

    return {
        "page_count": page_count,
        "is_image_based": is_image_based,
        "needs_split": page_count > 100,
    }


def process_pdf(pdf_path: str, output_dir: str = None) -> dict:
    from pypdf import PdfReader, PdfWriter

    path = Path(pdf_path)
    if not path.exists():
        return {"error": f"File not found: {pdf_path}"}

    if output_dir is None:
        output_dir = path.parent / f"{path.stem}_chunks"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(path))
    page_count = len(reader.pages)

    # Detect image-based
    sample_text = ""
    for i in range(min(3, page_count)):
        try:
            sample_text += reader.pages[i].extract_text() or ""
        except Exception:
            pass
    is_image_based = len(sample_text.strip()) < 100

    result = {
        "page_count": page_count,
        "is_image_based": is_image_based,
        "needs_split": page_count > 100,
        "chunks": [],
        "output_dir": str(output_dir),
    }

    chunk_size = 100

    if is_image_based:
        # OCR each chunk via pdf2image + pytesseract, save as .txt
        from pdf2image import convert_from_path
        import pytesseract

        for chunk_idx, start in enumerate(range(0, page_count, chunk_size)):
            end = min(start + chunk_size, page_count)
            print(f"OCR pages {start+1}–{end}...", file=sys.stderr)

            images = convert_from_path(
                str(path), first_page=start + 1, last_page=end, dpi=200
            )

            chunk_text = ""
            for page_offset, img in enumerate(images):
                page_num = start + page_offset + 1
                text = pytesseract.image_to_string(img)
                chunk_text += f"\n\n--- PAGE {page_num} ---\n{text}"

            chunk_file = output_dir / f"chunk_{chunk_idx+1:02d}_pages_{start+1}-{end}.txt"
            chunk_file.write_text(chunk_text, encoding="utf-8")

            result["chunks"].append({
                "index": chunk_idx + 1,
                "pages": f"{start+1}-{end}",
                "path": str(chunk_file),
                "type": "ocr_text",
            })

    else:
        # Text-based PDF — split into 100-page chunks
        if page_count <= chunk_size:
            # No split needed — return original
            result["chunks"].append({
                "index": 1,
                "pages": f"1-{page_count}",
                "path": str(path),
                "type": "pdf",
            })
        else:
            for chunk_idx, start in enumerate(range(0, page_count, chunk_size)):
                end = min(start + chunk_size, page_count)
                writer = PdfWriter()
                for page_idx in range(start, end):
                    writer.add_page(reader.pages[page_idx])

                chunk_file = output_dir / f"chunk_{chunk_idx+1:02d}_pages_{start+1}-{end}.pdf"
                with open(chunk_file, "wb") as f:
                    writer.write(f)

                result["chunks"].append({
                    "index": chunk_idx + 1,
                    "pages": f"{start+1}-{end}",
                    "path": str(chunk_file),
                    "type": "pdf",
                })

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: process_pdf.py <pdf_path> [output_dir]"}))
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    # If only --analyze flag, just report metadata without processing
    if pdf_path == "--analyze":
        pdf_path = sys.argv[2]
        result = analyze_pdf(pdf_path)
    else:
        result = process_pdf(pdf_path, output_dir)

    print(json.dumps(result, indent=2))
