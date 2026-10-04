"""
Document & Image Reader Utility for AI Girl.
Extracts rich structured text and content from:
- Images (PNG, JPG, JPEG, WEBP, GIF, BMP, SVG)
- PDF Documents (PDF)
- Word Documents (DOCX, DOC)
- Excel Spreadsheets (XLSX, XLS, CSV)
- PowerPoint Presentations (PPTX, PPT)
- Source Code & Text files (PY, JS, TS, HTML, CSS, JSON, SQL, etc.)
"""

import io
import csv
import base64
from typing import Tuple, Optional


def extract_pdf_content(file_bytes: bytes, max_pages: int = 50) -> str:
    """Extract readable text from PDF bytes using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)

        extracted = []
        for i in range(pages_to_read):
            page_text = reader.pages[i].extract_text() or ""
            if page_text.strip():
                extracted.append(f"--- [Page {i + 1} of {total_pages}] ---\n{page_text.strip()}")

        if not extracted:
            return "[PDF scanned or contains only images / no selectable text]"

        summary_header = f"[PDF Document: {total_pages} total pages]\n\n"
        return summary_header + "\n\n".join(extracted)
    except Exception as e:
        return f"[PDF parsing error: {e}]"


def extract_docx_content(file_bytes: bytes) -> str:
    """Extract paragraphs and tables from DOCX bytes using python-docx."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        parts = []

        # Extract paragraphs with heading markers
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style and "Heading" in p.style.name:
                parts.append(f"\n### {text}")
            else:
                parts.append(text)

        # Extract tables
        for t_idx, table in enumerate(doc.tables):
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_rows.append(" | ".join(row_cells))
            if table_rows:
                parts.append(f"\n[Table {t_idx + 1}]:\n" + "\n".join(table_rows))

        if not parts:
            return "[DOCX document is empty]"

        return "[Word Document (.docx)]\n\n" + "\n".join(parts)
    except Exception as e:
        return f"[DOCX parsing error: {e}]"


def extract_excel_content(file_bytes: bytes, max_rows: int = 150) -> str:
    """Extract structured sheet data from Excel XLSX bytes using openpyxl."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        parts = [f"[Excel Workbook: {len(wb.sheetnames)} Sheet(s): {', '.join(wb.sheetnames)}]"]

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            parts.append(f"\n--- Sheet: '{sheet_name}' (Rows: {sheet.max_row}, Cols: {sheet.max_column}) ---")

            rows_data = []
            for r_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                if r_idx >= max_rows:
                    parts.append(f"... [{sheet.max_row - max_rows} additional rows omitted]")
                    break
                # Filter empty rows
                filtered_row = [str(cell) if cell is not None else "" for cell in row]
                if any(filtered_row):
                    rows_data.append(" | ".join(filtered_row))

            if rows_data:
                parts.append("\n".join(rows_data))
            else:
                parts.append("[Empty Sheet]")

        return "\n".join(parts)
    except Exception as e:
        return f"[Excel parsing error: {e}]"


def extract_pptx_content(file_bytes: bytes) -> str:
    """Extract slides, titles, bullet points, and tables from PPTX using python-pptx."""
    try:
        import pptx
        prs = pptx.Presentation(io.BytesIO(file_bytes))
        total_slides = len(prs.slides)
        parts = [f"[PowerPoint Presentation: {total_slides} Slide(s)]"]

        for idx, slide in enumerate(prs.slides, start=1):
            slide_texts = []
            title_text = ""

            # Try to grab title if present
            if slide.shapes.title and slide.shapes.title.text:
                title_text = slide.shapes.title.text.strip()

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        txt = para.text.strip()
                        if txt and txt != title_text:
                            slide_texts.append(f"• {txt}")
                elif shape.has_table:
                    for row in shape.table.rows:
                        row_vals = [c.text.strip() for c in row.cells]
                        slide_texts.append(" | ".join(row_vals))

            slide_header = f"\n--- [Slide {idx}: {title_text or 'Untitled'}] ---"
            parts.append(slide_header)
            if slide_texts:
                parts.append("\n".join(slide_texts))
            elif not title_text:
                parts.append("[Visual / Image slide without text]")

        return "\n".join(parts)
    except Exception as e:
        return f"[PowerPoint parsing error: {e}]"


def extract_csv_content(file_bytes: bytes, max_rows: int = 200) -> str:
    """Extract and format CSV data."""
    try:
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = []
        for idx, row in enumerate(reader):
            if idx >= max_rows:
                rows.append("... [additional rows truncated]")
                break
            rows.append(" | ".join(row))
        return f"[CSV Spreadsheet Data ({len(rows)} rows)]\n\n" + "\n".join(rows)
    except Exception as e:
        return f"[CSV parsing error: {e}]"


def parse_attachment_file(name: str, file_bytes: bytes, mime_type: str = "") -> Tuple[Optional[dict], Optional[str]]:
    """
    Parses a single file attachment.
    Returns: (multimodal_payload_dict_or_None, extracted_text_str_or_None)
    """
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    # Image formats
    image_mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "svg": "image/svg+xml",
    }

    if ext in image_mime_map:
        media_type = image_mime_map[ext]
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        image_payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{b64}"
            }
        }
        return image_payload, f"Attached image: {name}"

    # Audio formats
    audio_format_map = {
        "wav": "wav", "mp3": "mp3", "mpeg": "mp3", "aac": "aac",
        "ogg": "ogg", "flac": "flac", "m4a": "m4a", "webm": "webm",
    }
    if ext in audio_format_map:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        audio_payload = {
            "type": "input_audio",
            "input_audio": {
                "data": b64,
                "format": audio_format_map[ext]
            }
        }
        return audio_payload, f"Attached audio recording: {name}"

    # Document formats
    if ext == "pdf":
        text = extract_pdf_content(file_bytes)
        return None, f"=== Contents of {name} (PDF) ===\n{text}"

    if ext in ["docx", "doc"]:
        text = extract_docx_content(file_bytes)
        return None, f"=== Contents of {name} (Word DOCX) ===\n{text}"

    if ext in ["xlsx", "xls"]:
        text = extract_excel_content(file_bytes)
        return None, f"=== Contents of {name} (Excel Spreadsheet) ===\n{text}"

    if ext == "csv":
        text = extract_csv_content(file_bytes)
        return None, f"=== Contents of {name} (CSV) ===\n{text}"

    if ext in ["pptx", "ppt"]:
        text = extract_pptx_content(file_bytes)
        return None, f"=== Contents of {name} (PowerPoint Presentation) ===\n{text}"

    # Code and Text formats
    text_extensions = {
        "txt", "md", "json", "xml", "yaml", "yml", "log", "py", "js", "ts",
        "jsx", "tsx", "html", "css", "scss", "sql", "sh", "bat", "ps1",
        "c", "cpp", "h", "hpp", "java", "rs", "go", "php", "rb", "env", "ini", "conf"
    }

    if ext in text_extensions or mime_type.startswith("text/"):
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
        return None, f"=== Contents of {name} ({ext.upper()} file) ===\n{text}"

    # Fallback attempt as text
    try:
        text = file_bytes.decode("utf-8-sig")
        return None, f"=== Contents of {name} ===\n{text}"
    except Exception:
        return None, f"[Binary file {name} ({len(file_bytes)} bytes) attached]"
