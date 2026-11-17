from pathlib import Path

import pytest
from openpyxl import load_workbook

from leadfinder import scoring
from leadfinder import website_check as wc
from leadfinder.__main__ import pruefe_websites
from leadfinder.categories import KATEGORIEN, kategorie_fuer_tags
from leadfinder.export import exportiere
from leadfinder.models import Lead
from leadfinder.regions import REGIONEN
from leadfinder.sources import google_places, osm

ALTE_SEITE = """<html><head><title>Startseite</title>
<meta name="generator" content="Microsoft FrontPage 4.0"></head>
<body><center><font face="Arial">Willkommen bei Malerbetrieb Muster</font></center>
<table><tr><td>a</td></tr></table><table><tr><td>b</td></tr></table>
<table><tr><td>c</td></tr></table><table><tr><td>d</td></tr></table>
<p>Kontakt: info (at) maler-muster (punkt) de, Tel. 02241 / 123456</p>
<p>&copy; 2011 Malerbetrieb Muster</p></body></html>"""

MODERNE_SEITE = """<!doctype html><html lang="de"><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Ihr Fliesenleger in Bonn"><title>Fliesen Beispiel – Bonn</title>
</head><body><header><nav><a href="/impressum">Impressum</a>
<a href="/datenschutz">Datenschutz</a></nav></header><main>""" + \
    "<p>" + "Wir verlegen Fliesen in Bad und Küche mit Erfahrung. " * 30 + "</p>" + \
    """<a href="mailto:info@fliesen-beispiel.de">Mail</a><a href="tel:+49228999999">Anrufen</a>
</main><footer>© 2026 Fliesen Beispiel</footer></body></html>"""


def test_alte_seite_ist_schlecht():
    a = wc.bewerte_html(ALTE_SEITE, "http://maler-muster.de/", 1.0, jahr_heute=2026)
    assert a.status == wc.STATUS_SCHLECHT
    assert any("HTTPS" in m for m in a.maengel)
    assert any("mobil" in m for m in a.maengel)
    assert any("2011" in m for m in a.maengel)
    assert "info@maler-muster.de" in a.emails
    assert a.telefone


def test_moderne_seite_ist_gut():
    a = wc.bewerte_html(MODERNE_SEITE, "https://fliesen-beispiel.de/", 0.8, jahr_heute=2026)
    assert a.status == wc.STATUS_GUT, a.maengel
    assert a.emails == ["info@fliesen-beispiel.de"]
    assert a.telefone == ["+49228999999"]


def test_platzhalter():
    html = "<html><body><h1>Diese Domain steht zum Verkauf</h1>" + "x " * 200 + \
           "<p>Domain is for sale</p></body></html>"
    assert wc.bewerte_html(html, "https://x.de").status == wc.STATUS_KAPUTT


@pytest.mark.parametrize("url,erwartet", [
    ("https://www.facebook.com/malermuster", True),
    ("instagram.com/gartenbau", True),
    ("https://www.gelbeseiten.de/gsbiz/123", True),
    ("www.maler-muster.de", False),
])
def test_social(url, erwartet):
    assert wc.ist_social(url) is erwartet


def test_pruefe_ohne_url_und_social():
    assert wc.pruefe("").status == wc.STATUS_KEINE
    assert wc.pruefe("https://facebook.com/x").status == wc.STATUS_SOCIAL


def test_beste_email():
    assert wc.beste_email(["max@gmail.com", "info@firma.de", "buchhaltung@firma.de"],
                          "https://www.firma.de") == "info@firma.de"


def test_kategorie_zuordnung():
    assert kategorie_fuer_tags({"craft": "gardener"}).key == "garten"
    assert kategorie_fuer_tags({"craft": "plumber;hvac"}).key == "heizung"
    assert kategorie_fuer_tags({"shop": "supermarket"}) is None


def test_einfachheit_bereich_und_keys_eindeutig():
    assert all(1 <= k.einfachheit <= 10 for k in KATEGORIEN)
    assert len({k.key for k in KATEGORIEN}) == len(KATEGORIEN)


def test_overpass_query():
    q = osm.build_query(REGIONEN["rhein-sieg"], KATEGORIEN[:3])
    assert '"name"="Rhein-Sieg-Kreis"' in q and "gardener" in q and "out center tags" in q


def test_osm_element():
    el = {"type": "node", "id": 1, "lat": 50.8, "lon": 7.2, "tags": {
        "name": "Gartenbau Beispiel", "craft": "gardener", "phone": "+49 2241 1",
        "addr:street": "Hauptstr.", "addr:housenumber": "1", "addr:postcode": "53721",
        "addr:city": "Siegburg"}}
    l = osm.element_zu_lead(el, {"garten"})
    assert l.name == "Gartenbau Beispiel" and l.einfachheit == 9
    assert l.adresse == "Hauptstr. 1, 53721 Siegburg"
    assert osm.element_zu_lead({**el, "tags": {"craft": "gardener"}}, {"garten"}) is None


def test_google_place():
    p = {"id": "x", "displayName": {"text": "Elektro Beispiel"},
         "formattedAddress": "Markt 1, 53757 Sankt Augustin, Deutschland",
         "nationalPhoneNumber": "02241 99999", "rating": 4.8, "userRatingCount": 31}
    l = google_places.place_zu_lead(p, next(k for k in KATEGORIEN if k.key == "elektro"))
    assert l.plz == "53757" and l.ort == "Sankt Augustin" and l.anzahl_bewertungen == 31


def _lead(**kw):
    basis = dict(name="Test", kategorie_key="garten", kategorie="Garten", einfachheit=9,
                 quelle="OpenStreetMap")
    basis.update(kw)
    return Lead(**basis)


def test_dedup_osm_google():
    a = _lead(name="Gartenbau Beispiel GmbH", ort="Siegburg", telefon="02241 123")
    b = _lead(name="Gartenbau Beispiel", ort="Siegburg", email="a@b.de", quelle="Google",
              anzahl_bewertungen=12)
    c = _lead(name="Ganz anders", ort="Bonn", telefon="+49 2241 123")
    out = scoring.dedupliziere([a, b, c])
    assert len(out) == 1
    assert out[0].email == "a@b.de" and "Google" in out[0].quelle


def test_score_reihenfolge():
    keine = _lead(website_status=wc.STATUS_KEINE, telefon="1", email="a@b.de")
    gut = _lead(website_status=wc.STATUS_GUT, telefon="1", email="a@b.de")
    schwer = _lead(website_status=wc.STATUS_KEINE, einfachheit=5, telefon="1", email="a@b.de")
    assert scoring.lead_score(keine) > scoring.lead_score(schwer) > scoring.lead_score(gut)
    assert scoring.lead_score(keine) <= 100


def test_pipeline_und_export(tmp_path: Path, monkeypatch):
    leads = [
        _lead(name="Ohne Website", telefon="02241 1"),
        _lead(name="Nur Facebook", website="https://facebook.com/x", telefon="02241 2"),
        _lead(name="Alte Seite", website="maler-muster.de", kategorie_key="maler",
              kategorie="Maler & Lackierer"),
        _lead(name="Gute Seite", website="https://fliesen-beispiel.de", kategorie_key="fliesen",
              kategorie="Fliesenleger", einfachheit=8),
    ]
    antworten = {
        "http://maler-muster.de": wc.bewerte_html(ALTE_SEITE, "http://maler-muster.de/"),
        "https://fliesen-beispiel.de": wc.bewerte_html(MODERNE_SEITE, "https://fliesen-beispiel.de/"),
    }
    monkeypatch.setattr(wc, "pruefe", lambda u, timeout=12: antworten.get(
        u, wc.Analyse(wc.STATUS_SOCIAL, ["Social"], 0, u)))
    pruefe_websites(leads, tmp_path / "cache.json", threads=2, log=lambda *_: None)
    for l in leads:
        l.lead_score = scoring.lead_score(l)
    status = {l.name: l.website_status for l in leads}
    assert status == {"Ohne Website": wc.STATUS_KEINE, "Nur Facebook": wc.STATUS_SOCIAL,
                      "Alte Seite": wc.STATUS_SCHLECHT, "Gute Seite": wc.STATUS_GUT}
    alte = next(l for l in leads if l.name == "Alte Seite")
    assert alte.email == "info@maler-muster.de" and alte.telefon

    xlsx, csv_pfad = exportiere(leads, tmp_path)
    wb = load_workbook(xlsx)
    assert wb.sheetnames[0] == "Kategorien-Ranking"
    assert "Keine Website" in wb.sheetnames and "Schlechte Website" in wb.sheetnames
    ranking = wb["Alle Leads (Ranking)"]
    top3 = [ranking.cell(r, 3).value for r in (2, 3, 4)]
    assert "Ohne Website" in top3 and "Nur Facebook" in top3
    assert ranking.cell(ranking.max_row, 3).value == "Gute Seite"
    assert csv_pfad.read_text(encoding="utf-8-sig").count("\n") == 5


def test_domain_kandidaten():
    from leadfinder.website_suche import kandidaten
    k = kandidaten("Malerbetrieb Schmitz GmbH", "Siegburg")
    assert "malerbetrieb-schmitz.de" in k and "schmitz-siegburg.de" in k
    assert "malerbetrieb.de" not in k
    assert kandidaten("GmbH", "Bonn") == []


def test_domain_verifikation():
    from leadfinder.website_suche import passt
    l = _lead(name="Gartenbau Beispiel", telefon="+49 2241 123456", strasse="Hauptstraße 5",
              plz="53721", ort="Siegburg")
    assert passt("<p>Tel. 02241 / 12 34 56</p>", l)
    assert passt("<p>Hauptstr. 5, 53721 Siegburg</p>", _lead(strasse="Hauptstraße 5",
                                                            plz="53721", ort="Siegburg"))
    assert not passt("<p>Gartenbau in Köln, Tel. 0221 999999</p>", l)


def test_ketten_entfernen():
    leads = [_lead(name="Kamps", ort=o) for o in ("Köln", "Bonn", "Siegburg")]
    leads += [_lead(name="Marke", kette=True), _lead(name="Gartenbau Einzeln")]
    assert [l.name for l in scoring.entferne_ketten(leads)] == ["Gartenbau Einzeln"]
