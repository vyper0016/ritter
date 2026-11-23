import os

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from api.veryfi_ocr import VeryfiProvider
from api.wolt_pdf import order_page_count, pruned_wolt_pdf


def make_pdf(path, pages: list[list[str]]):
    """Write a PDF with one page per entry, each line drawn as extractable text."""
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    for lines in pages:
        page = writer.add_blank_page(width=595, height=842)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        })
        body = "".join(f"({line}) Tj 0 -14 Td " for line in lines)
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 11 Tf 50 800 Td {body}ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    with open(path, "wb") as f:
        writer.write(f)
    return str(path)


ORDER_PAGE = [
    "Acceptance of order / Invoice #298949674",
    "Venue Pablos - Tacos & Burritos",
    "Burrito Tomato Spiced Pulled Chicken 7% 1 12.80 12.80",
    "Delivery 7% 1 3.99 3.99",
    "Total in EUR (incl. VAT) 16.79",
]
TERMS_PAGE = [
    "Seller details: Wolt Enterprises Deutschland GmbH",
    "I. General Terms",
    "Email address: support@wolt.com.",
]
MORE_TERMS = ["5. Assignment", "Wolt shall be entitled to assign all or any of its rights"]


def page_texts(path):
    return [p.extract_text() for p in PdfReader(path).pages]


def test_order_page_count():
    assert order_page_count(["items", "Total in EUR (incl. VAT) 31.38", "terms"]) == 2
    assert order_page_count(["Total in PLN 50.00", "terms"]) == 1
    assert order_page_count(["no total here", "terms"]) is None


def test_wolt_pdf_keeps_only_order_page(tmp_path):
    path = make_pdf(tmp_path / "wolt rechnung.pdf", [ORDER_PAGE, TERMS_PAGE, MORE_TERMS, MORE_TERMS])
    with pruned_wolt_pdf(path) as (pruned, is_wolt):
        assert is_wolt
        assert pruned != path
        assert os.path.basename(pruned) == "wolt rechnung.pdf"
        texts = page_texts(pruned)
        assert len(texts) == 1
        assert "Total in EUR" in texts[0]
    assert not os.path.exists(pruned)
    assert len(PdfReader(path).pages) == 4  # original untouched


def test_wolt_pdf_long_order_keeps_all_order_pages(tmp_path):
    first = ORDER_PAGE[:3]
    second = ORDER_PAGE[3:]
    path = make_pdf(tmp_path / "w.pdf", [first, second, TERMS_PAGE, MORE_TERMS])
    with pruned_wolt_pdf(path) as (pruned, is_wolt):
        assert is_wolt
        assert len(page_texts(pruned)) == 2


def test_wolt_pdf_without_total_sent_unchanged(tmp_path):
    path = make_pdf(tmp_path / "w.pdf", [ORDER_PAGE[:3], TERMS_PAGE])
    with pruned_wolt_pdf(path) as (pruned, is_wolt):
        assert is_wolt
        assert pruned == path


def test_other_pdf_sent_unchanged(tmp_path):
    path = make_pdf(tmp_path / "dm.pdf", [["dm-drogerie markt", "Summe 7,15"], ["AGB"]])
    with pruned_wolt_pdf(path) as (pruned, is_wolt):
        assert not is_wolt
        assert pruned == path


def test_image_sent_unchanged(tmp_path):
    path = tmp_path / "bon.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0 not a pdf")
    with pruned_wolt_pdf(str(path)) as (pruned, is_wolt):
        assert not is_wolt
        assert pruned == str(path)


def test_broken_pdf_sent_unchanged(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7\ngarbage")
    with pruned_wolt_pdf(str(path)) as (pruned, is_wolt):
        assert not is_wolt
        assert pruned == str(path)


def test_error_inside_block_propagates(tmp_path):
    path = make_pdf(tmp_path / "w.pdf", [ORDER_PAGE, TERMS_PAGE])
    with pytest.raises(ValueError):
        with pruned_wolt_pdf(path):
            raise ValueError("veryfi down")


class RecordingClient:
    def __init__(self):
        self.page_counts = []

    def process_document(self, file_path, delete_after_processing=True):
        self.page_counts.append(len(PdfReader(file_path).pages))
        return {
            "line_items": [
                {"order": 0, "description": "Burrito", "quantity": 1.0, "price": 0.0, "total": 0.0},
                {"order": 1, "description": "Burrito", "quantity": 1.0, "price": 12.8, "total": 12.8},
            ],
            # Veryfi no longer sees the seller details page, so it may not name Wolt
            "vendor": {"name": "Pablos"},
            "ship_to": {"name": "Pablos - Tacos & Burritos"},
            "payment": {},
            "meta": {"ocr_score": 0.9},
            "total": 12.8,
        }


def test_provider_sends_pruned_wolt_pdf(tmp_path):
    path = make_pdf(tmp_path / "w.pdf", [ORDER_PAGE, TERMS_PAGE, MORE_TERMS])
    client = RecordingClient()
    receipt = VeryfiProvider(client).process_document(path)
    assert client.page_counts == [1]
    assert receipt.vendor.name == "Wolt - Pablos - Tacos & Burritos"
    assert [(i.description, i.total) for i in receipt.line_items] == [("Burrito", 12.8)]
