"""Parser tests."""
from datetime import date

from custom_components.magic_pass import parser

from .fixtures import MARKERS, opening_page


def test_parse_rows():
    rows = parser.parse_rows(opening_page())
    assert [r["name"] for r in rows] == ["Charmey", "Villars-Gryon", "Les Rochers - de - Naye"]
    charmey = rows[0]
    assert charmey["state"] == "Fermé"
    assert charmey["kind"] == "close"
    assert (charmey["lifts_open"], charmey["lifts_total"]) == (0, 7)
    assert (charmey["km_open"], charmey["km_total"]) == (0.0, 29.2)
    assert "19.12.2026" in charmey["info"]
    assert rows[1]["state"] == "Ouvert" and rows[1]["lifts_open"] == 2


def test_regions():
    assert parser.parse_region_filters(opening_page()) == [("10", "Fribourg"), ("8", "Vaud")]


def test_match_destination():
    dests = parser.parse_map(MARKERS)["destinations"]
    assert parser.match_destination("charmey-14", dests) == "charmey"
    assert parser.match_destination("les-rochers--de--naye-90", dests) == "les-rochers-de-naye"
    assert parser.match_destination("ste-croix-les-rasses-2772", {"ste-croixles-rasses": [0, 0]}) == "ste-croixles-rasses"
    assert parser.match_destination("unknown-1", dests) is None


def test_trail_stats():
    data = parser.parse_map(MARKERS)
    stats = parser.trail_stats(data["destinations"], data["trails"])
    assert stats["charmey"] == {"n": 2, "vb": 1}
    assert stats["villars-gryon"] == {"n": 1, "vb": 1}


def test_next_opening():
    today = date(2026, 11, 20)
    assert parser.next_opening("Été : 01.07 - 31.10.2026 · Hiver : 28.11 - 28.03.2027", today) == "28.11"
    assert parser.next_opening("19.12.2026 - 07.03.2027 · Week-ends + 05.12 - 13.12.2026", today) == "05.12"
    assert parser.next_opening("", today) == ""


def test_score():
    closed = {"open": False, "pct_open": 0}
    assert parser.score(closed) == 0.0
    st = {"open": True, "pct_open": 50, "weather": {"snow72": 10, "code": 0}, "travel": 45}
    assert parser.score(st) == 6.5
