import pytest
from api.veryfi_ocr import VeryfiProvider


def veryfi_item(order, description, total, text):
    return {"order": order, "description": description, "quantity": 1.0, "price": total, "total": total, "type": "product", "text": text}


# Trimmed from a real Veryfi response for a dm online invoice ("dm rechnung.pdf")
DM_ITEMS = [
    veryfi_item(0, "Rexona", 3.95, "Rexona\t\t\t\t\t\t\t3,95 € (1)\t\t\t1\t\t3,95 €"),
    veryfi_item(1, "Antitranspirant Deostick Maximum Protection, 50 ml\n€ je 1 l.", 79.0, "Antitranspirant Deostick Maximum Protection, 50 ml\t79,00 € je 1 l"),
    veryfi_item(2, "Selfie Project", 1.95, "Selfie Project\t\t\t\t\t\t1,95 € (1)\t\t\t1\t\t1,95 €"),
    veryfi_item(3, "Anti Pickel Patches Pimple Sterne, 20 St\n€ je 1 St.", 0.1, "Anti Pickel Patches Pimple Sterne, 20 St\t\t\t0,10 € je 1 St"),
    veryfi_item(4, "dmBio", 1.25, "dmBio\t\t\t\t\t\t\t1,25 €\t(2)\t\t\t1\t\t1,25 €"),
    veryfi_item(5, "Sonnenblumenkerne, 500 g, Bio\n€ je 1 kg.", 2.5, "Sonnenblumenkerne, 500 g, Bio\t\t\t\t2,50 € je 1 kg"),
]


def test_dm_base_price_lines_merged_into_previous_item():
    items = VeryfiProvider.parse_line_items(DM_ITEMS)
    assert [i.description for i in items] == [
        "Rexona Antitranspirant Deostick Maximum Protection, 50 ml",
        "Selfie Project Anti Pickel Patches Pimple Sterne, 20 St",
        "dmBio Sonnenblumenkerne, 500 g, Bio",
    ]


def test_dm_keeps_item_price_not_base_price():
    items = VeryfiProvider.parse_line_items(DM_ITEMS)
    assert [i.total for i in items] == pytest.approx([3.95, 1.95, 1.25])
    assert sum(i.total for i in items) == pytest.approx(7.15)


def test_weight_line_not_merged():
    # Aldi weight info is already part of the item text; must stay one item
    aldi = [
        veryfi_item(0, "Zucchini", 0.48, "783855 Zucchini\t\t0,48 A\n0,562 kg x\t0,85 EUR/kg"),
        veryfi_item(1, "Bananen", 1.19, "123456 Bananen\t\t1,19 A"),
    ]
    items = VeryfiProvider.parse_line_items(aldi)
    assert [i.description for i in items] == ["Zucchini", "Bananen"]


def test_base_price_line_without_previous_item_kept():
    items = VeryfiProvider.merge_base_price_lines([DM_ITEMS[1]])
    assert len(items) == 1


def test_merge_does_not_mutate_response():
    response = [dict(i) for i in DM_ITEMS[:2]]
    VeryfiProvider.merge_base_price_lines(response)
    assert response[0]["description"] == "Rexona"


def wolt_item(order, description, total, type_="food"):
    return {"order": order, "description": description, "quantity": 1.0, "price": total, "total": total, "type": type_}


# Line items Veryfi returned for a real Wolt invoice ("wolt rechnung.pdf")
WOLT_ITEMS = [
    wolt_item(0, "Burrito Tomato Spiced Pulled Chicken", 0.0),
    wolt_item(1, "Burrito Tomato Spiced Pulled Chicken", 12.8),
    wolt_item(2, "Deine 1. Salsa: Sour Cream", 0.0),
    wolt_item(3, "Deine 2. Salsa: Guacamole", 0.0),
    wolt_item(4, "Burrito Pulled Lemon Chicken", 0.0),
    wolt_item(5, "Burrito Pulled Lemon Chicken", 12.8),
    wolt_item(6, "Deine 1. Salsa: Sour Cream", 0.0),
    wolt_item(7, "Deine 2. Salsa: Guacamole", 0.0),
    wolt_item(8, "Delivery", 3.99, "delivery"),
    wolt_item(9, "Service fee", 1.79, "fee"),
]

WOLT_VENDOR = {"name": "Wolt", "web": "wolt.com", "raw_name": "Wolt Enterprises Deutschland GmbH"}


def veryfi_response(line_items, vendor, **extra):
    return {
        "line_items": [dict(i) for i in line_items],
        "vendor": dict(vendor),
        "payment": {"payment_type": None},
        "meta": {"ocr_score": 0.9},
        "date": "2026-11-22 19:50:00",
        "total": round(sum(i["total"] for i in line_items), 2),
        "ocr_text": "...",
        **extra,
    }


class FakeVeryfiClient:
    def __init__(self, response):
        self.response = response

    def process_document(self, file_path, delete_after_processing=True):
        return self.response


def process(response):
    return VeryfiProvider(FakeVeryfiClient(response)).process_document("x.pdf")


def test_wolt_drops_zero_items():
    receipt = process(veryfi_response(WOLT_ITEMS, WOLT_VENDOR, ship_to={"name": "Pablos - Tacos & Burritos"}))
    assert [(i.description, i.total) for i in receipt.line_items] == [
        ("Burrito Tomato Spiced Pulled Chicken", 12.8),
        ("Burrito Pulled Lemon Chicken", 12.8),
        ("Delivery", 3.99),
        ("Service fee", 1.79),
    ]
    assert sum(i.total for i in receipt.line_items) == pytest.approx(31.38)
    assert receipt.total == pytest.approx(31.38)


def test_wolt_vendor_name_includes_restaurant():
    receipt = process(veryfi_response(WOLT_ITEMS, WOLT_VENDOR, ship_to={"name": " Pablos - Tacos & Burritos "}))
    assert receipt.vendor.name == "Wolt - Pablos - Tacos & Burritos"


@pytest.mark.parametrize("ship_to", [None, {}, {"name": None}, {"name": "  "}])
def test_wolt_vendor_name_without_restaurant(ship_to):
    receipt = process(veryfi_response(WOLT_ITEMS, WOLT_VENDOR, ship_to=ship_to))
    assert receipt.vendor.name == "Wolt"


def test_wolt_detected_by_website():
    vendor = {"name": "Wolt Enterprises Deutschland GmbH", "web": "https://wolt.com"}
    receipt = process(veryfi_response(WOLT_ITEMS, vendor, ship_to={"name": "Pablos"}))
    assert receipt.vendor.name == "Wolt - Pablos"
    assert len(receipt.line_items) == 4


def test_zero_items_kept_for_other_vendors():
    receipt = process(veryfi_response(WOLT_ITEMS[:4], {"name": "Pablos"}, ship_to={"name": "Someone"}))
    assert receipt.vendor.name == "Pablos"
    assert len(receipt.line_items) == 4


def test_wolt_keeps_discounts():
    items = WOLT_ITEMS + [wolt_item(10, "Wolt+ Rabatt", -2.0, "discount")]
    receipt = process(veryfi_response(items, WOLT_VENDOR))
    assert receipt.line_items[-1].total == -2.0
    assert len(receipt.line_items) == 5
