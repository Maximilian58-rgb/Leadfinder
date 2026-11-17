"""Branchen-Kategorien mit Einfachheits-Bewertung für den Website-Bau.

`einfachheit`: 1 (aufwendig) bis 10 (sehr einfach zu erstellen).
Bewertet wird, wie schnell sich eine überzeugende Website bauen lässt:
wenige Seiten, Standard-Aufbau (Leistungen / Referenzen / Kontakt), kaum
Sonderfunktionen (Buchung, Shop, Konfigurator, viel Fachinhalt).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kategorie:
    key: str
    name: str
    einfachheit: int
    begruendung: str
    # OSM-Tags: Liste von (tag, wert)
    osm: tuple[tuple[str, str], ...] = ()
    # Suchbegriffe für Google Places ("<begriff> in <Ort>")
    google: tuple[str, ...] = ()


KATEGORIEN: list[Kategorie] = [
    Kategorie(
        "garten", "Gartenpflege / Garten- & Landschaftsbau", 9,
        "One-Pager mit Leistungen, Vorher/Nachher-Galerie, Einzugsgebiet, Kontakt.",
        (("craft", "gardener"), ("craft", "landscaper"), ("craft", "landscape_gardener")),
        ("Gartenpflege", "Garten- und Landschaftsbau", "Gärtner"),
    ),
    Kategorie(
        "hausmeister", "Hausmeisterservice", 9,
        "Leistungsliste + Kontaktformular, kaum Bildmaterial nötig.",
        (("craft", "caretaker"), ("office", "property_maintenance")),
        ("Hausmeisterservice",),
    ),
    Kategorie(
        "reinigung", "Gebäudereinigung", 9,
        "Standard-Leistungsseiten (Unterhalts-, Glas-, Grundreinigung), Anfrageformular.",
        (("craft", "cleaning"), ("office", "cleaning_company"), ("shop", "cleaning")),
        ("Gebäudereinigung", "Reinigungsfirma"),
    ),
    Kategorie(
        "maler", "Maler & Lackierer", 9,
        "Klassische Handwerker-Seite: Leistungen, Referenzbilder, Kontakt.",
        (("craft", "painter"),),
        ("Malerbetrieb", "Maler und Lackierer"),
    ),
    Kategorie(
        "schornstein", "Schornsteinfeger", 9,
        "Sehr wenig Inhalt: Kehrbezirk, Leistungen, Kontakt.",
        (("craft", "chimney_sweeper"),),
        ("Schornsteinfeger",),
    ),
    Kategorie(
        "fliesen", "Fliesenleger", 8,
        "Leistungen + große Bildergalerie (Bäder), sonst schlicht.",
        (("craft", "tiler"),),
        ("Fliesenleger",),
    ),
    Kategorie(
        "boden", "Bodenleger / Parkett", 8,
        "Leistungen, Materialien, Galerie, Kontakt.",
        (("craft", "floorer"), ("craft", "parquet_layer")),
        ("Bodenleger", "Parkettleger"),
    ),
    Kategorie(
        "schluessel", "Schlüsseldienst", 8,
        "One-Pager mit Notdienst-Nummer prominent, Preise, Einsatzgebiet.",
        (("craft", "locksmith"), ("shop", "locksmith")),
        ("Schlüsseldienst",),
    ),
    Kategorie(
        "glaser", "Glaserei", 8,
        "Überschaubares Leistungsspektrum, Galerie, Kontakt.",
        (("craft", "glaziery"),),
        ("Glaserei",),
    ),
    Kategorie(
        "steinmetz", "Steinmetz", 8,
        "Galerie (Grabmale, Treppen, Küchenplatten) + Kontakt.",
        (("craft", "stonemason"),),
        ("Steinmetz",),
    ),
    Kategorie(
        "polsterer", "Raumausstatter / Polsterer", 8,
        "Galerie-lastig, wenige Unterseiten.",
        (("craft", "upholsterer"), ("craft", "interior_decorator")),
        ("Raumausstatter", "Polsterei"),
    ),
    Kategorie(
        "tischler", "Schreiner / Tischler", 7,
        "Referenzprojekte (Möbel, Küchen, Treppen) brauchen gute Projektgalerie.",
        (("craft", "carpenter"), ("craft", "joiner"), ("craft", "cabinet_maker")),
        ("Schreinerei", "Tischlerei"),
    ),
    Kategorie(
        "dach", "Dachdecker / Zimmerer", 7,
        "Leistungen (Steildach, Flachdach, Solar), Referenzen, Förderhinweise.",
        (("craft", "roofer"), ("craft", "carpenter_roof")),
        ("Dachdecker", "Zimmerei"),
    ),
    Kategorie(
        "bau", "Maurer / Stuckateur / Bauunternehmen", 7,
        "Projekt-Referenzen, mehrere Leistungsbereiche.",
        (("craft", "builder"), ("craft", "bricklayer"), ("craft", "plasterer")),
        ("Bauunternehmen", "Maurer", "Stuckateur", "Trockenbau"),
    ),
    Kategorie(
        "elektro", "Elektriker", 7,
        "Mehrere Leistungsbereiche (Smart Home, PV, E-Mobilität), Notdienst.",
        (("craft", "electrician"),),
        ("Elektriker", "Elektroinstallation"),
    ),
    Kategorie(
        "metall", "Metallbau / Schlosserei", 7,
        "Referenzgalerie (Geländer, Tore, Treppen), Kontakt.",
        (("craft", "metal_construction"), ("craft", "blacksmith")),
        ("Metallbau", "Schlosserei"),
    ),
    Kategorie(
        "fenster", "Fenster / Rollläden / Sonnenschutz", 7,
        "Produktübersichten nötig, sonst Standard.",
        (("craft", "window_construction"), ("craft", "sun_protection"), ("craft", "shutter")),
        ("Rollladenbau", "Fensterbau", "Sonnenschutz Markisen"),
    ),
    Kategorie(
        "umzug", "Umzugsunternehmen", 7,
        "Leistungen, Preisrechner optional, Anfrageformular.",
        (("office", "moving_company"), ("shop", "moving_company")),
        ("Umzugsunternehmen",),
    ),
    Kategorie(
        "lebensmittel", "Bäcker / Metzger", 6,
        "Filialen, Öffnungszeiten, Sortiment/Wochenangebote – regelmäßige Pflege.",
        (("shop", "bakery"), ("shop", "butcher"), ("craft", "bakery"), ("craft", "butcher")),
        ("Bäckerei", "Metzgerei"),
    ),
    Kategorie(
        "heizung", "Heizung / Sanitär / Klima (SHK)", 6,
        "Viele Leistungsbereiche (Bad, Heizung, Wärmepumpe), Notdienst, Förderinfos.",
        (("craft", "plumber"), ("craft", "hvac"), ("craft", "heating_engineer"),
         ("craft", "sanitary")),
        ("Heizung Sanitär", "Installateur", "Wärmepumpe Installateur"),
    ),
    Kategorie(
        "friseur", "Friseur", 6,
        "Preisliste, Team, Galerie – idealerweise Online-Terminbuchung.",
        (("shop", "hairdresser"),),
        ("Friseur",),
    ),
    Kategorie(
        "kosmetik", "Kosmetik / Nagelstudio", 6,
        "Preisliste, Behandlungen, Online-Buchung gewünscht.",
        (("shop", "beauty"),),
        ("Kosmetikstudio", "Nagelstudio"),
    ),
    Kategorie(
        "kfz", "Kfz-Werkstatt", 5,
        "Viele Leistungen, Marken, Terminbuchung, ggf. Fahrzeugbörse.",
        (("shop", "car_repair"), ("craft", "car_repair")),
        ("Autowerkstatt", "Kfz Werkstatt"),
    ),
]

KATEGORIE_BY_KEY = {k.key: k for k in KATEGORIEN}


def osm_lookup() -> dict[tuple[str, str], Kategorie]:
    out: dict[tuple[str, str], Kategorie] = {}
    for k in KATEGORIEN:
        for tag in k.osm:
            out.setdefault(tag, k)
    return out


def kategorie_fuer_tags(tags: dict) -> Kategorie | None:
    lookup = osm_lookup()
    for key in ("craft", "shop", "office"):
        val = tags.get(key)
        if not val:
            continue
        for v in str(val).split(";"):
            k = lookup.get((key, v.strip()))
            if k:
                return k
    return None


def auswahl(keys: list[str] | None) -> list[Kategorie]:
    if not keys or keys == ["alle"]:
        return list(KATEGORIEN)
    unbekannt = [k for k in keys if k not in KATEGORIE_BY_KEY]
    if unbekannt:
        raise SystemExit(
            f"Unbekannte Kategorie(n): {', '.join(unbekannt)}. "
            f"Verfügbar: {', '.join(KATEGORIE_BY_KEY)}"
        )
    return [KATEGORIE_BY_KEY[k] for k in keys]
