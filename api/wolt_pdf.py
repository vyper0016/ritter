"""
Wolt invoices are a page or two of order details followed by ~10 pages of terms of service.
OCR providers bill per page, so only send the pages that hold the order.
"""
import os
import re
import tempfile
from contextlib import contextmanager
from typing import Iterator

from pypdf import PdfReader, PdfWriter

from api.log import get_logger

log = get_logger(__name__)

WOLT_MARKERS = ("wolt enterprises", "wolt.com")
# Last line of the order table, e.g. "Total in EUR (incl. VAT)  31.38"
ORDER_TOTAL_LINE = re.compile(r"\bTotal in [A-Z]{3}\b")


def is_pdf(file_path: str) -> bool:
    with open(file_path, "rb") as f:
        return f.read(5) == b"%PDF-"


def is_wolt_text(page_texts: list[str]) -> bool:
    text = "\n".join(page_texts).lower()
    return any(marker in text for marker in WOLT_MARKERS)


def order_page_count(page_texts: list[str]) -> int | None:
    """Number of leading pages up to and including the order total; None if not found."""
    for i, text in enumerate(page_texts):
        if ORDER_TOTAL_LINE.search(text):
            return i + 1
    return None


@contextmanager
def pruned_wolt_pdf(file_path: str) -> Iterator[tuple[str, bool]]:
    """
    Yield (path, is_wolt). For a Wolt invoice PDF, path is a temporary copy holding only the
    order pages (same file name, in a temporary directory). Otherwise path is file_path unchanged.
    """
    reader = None
    page_texts: list[str] = []
    try:
        if is_pdf(file_path):
            reader = PdfReader(file_path)
            page_texts = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        log.warning("Could not read %s as PDF — sending it unchanged", file_path, exc_info=True)
        reader = None

    if reader is None:
        yield file_path, False
        return

    if not is_wolt_text(page_texts):
        yield file_path, False
        return

    keep = order_page_count(page_texts)
    if keep is None or keep >= len(page_texts):
        if keep is None:
            log.warning("Wolt invoice %s: order total not found — sending all %d pages", file_path, len(page_texts))
        yield file_path, True
        return

    writer = PdfWriter()
    for page in reader.pages[:keep]:
        writer.add_page(page)
    with tempfile.TemporaryDirectory() as tmp_dir:
        pruned_path = os.path.join(tmp_dir, os.path.basename(file_path))
        with open(pruned_path, "wb") as f:
            writer.write(f)
        log.info("Wolt invoice %s: sending %d of %d pages", file_path, keep, len(page_texts))
        yield pruned_path, True
