"""Compatibility facade for OCR helpers and extraction logic."""

from business_bridge.adapters.ocr_detection import (  # noqa: F401
    TENDER_EXPECTED_FIELDS,
    add_detected_item,
    build_extraction_record,
    calculate_overall_confidence,
    clean_extracted_pages,
    extract_regex_items,
)
from business_bridge.adapters.ocr_extractors import (  # noqa: F401
    extract_text_from_csv,
    extract_text_from_docx,
    extract_text_from_file,
    extract_text_from_image,
    extract_text_from_pdf,
    extract_text_from_xlsx,
    preprocess_image_for_ocr,
    render_pdf_page_to_image,
    run_ocr,
)
from business_bridge.adapters.ocr_text import (  # noqa: F401
    clean_value,
    detect_file_type,
    normalize_text,
    read_text_file,
    safe_preview,
)
