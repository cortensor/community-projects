"""Offline tests for the multilingual glossary."""

from fixbrief.glossary import GLOSSARY, known_terms, lookup, translate_terms
from fixbrief.models import Language


def test_glossary_covers_four_languages():
    for term, entry in GLOSSARY.items():
        assert set(entry.keys()) == set(Language), term
        assert all(entry[lang].strip() for lang in Language), term


def test_lookup_known_terms():
    assert lookup("charging port", Language.ES) == "puerto de carga"
    assert lookup("battery", Language.PT) == "bateria"
    assert lookup("not charging", Language.AR) == "لا يشحن"
    assert lookup(" Charging Port ", Language.EN) == "charging port"


def test_lookup_unknown_term_returns_none():
    assert lookup("flux capacitor", Language.ES) is None


def test_translate_terms_passthrough_unknown():
    out = translate_terms(["battery", "flux capacitor"], Language.ES)
    assert out["battery"] == "batería"
    assert out["flux capacitor"] == "flux capacitor"


def test_known_terms_sorted_and_nonempty():
    terms = known_terms()
    assert len(terms) >= 25
    assert terms == sorted(terms)
