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
