"""Suchgebiete: Rhein-Sieg-Kreis, Bonn, Köln und Umgebung."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    key: str
    name: str            # OSM-Name der Verwaltungsgrenze
    admin_level: str     # OSM admin_level (6 = Kreis / kreisfreie Stadt)
    orte: tuple[str, ...]  # Orte für Google-Suche + Adressfilter


REGIONEN: dict[str, Region] = {
    "rhein-sieg": Region(
        "rhein-sieg", "Rhein-Sieg-Kreis", "6",
        ("Alfter", "Bad Honnef", "Bornheim", "Eitorf", "Hennef", "Königswinter",
         "Lohmar", "Meckenheim", "Much", "Neunkirchen-Seelscheid", "Niederkassel",
         "Rheinbach", "Ruppichteroth", "Sankt Augustin", "Siegburg", "Swisttal",
         "Troisdorf", "Wachtberg", "Windeck"),
    ),
    "bonn": Region(
        "bonn", "Bonn", "6",
        ("Bonn", "Bonn-Bad Godesberg", "Bonn-Beuel", "Bonn-Hardtberg"),
    ),
    "koeln": Region(
        "koeln", "Köln", "6",
        ("Köln-Innenstadt", "Köln-Rodenkirchen", "Köln-Lindenthal", "Köln-Ehrenfeld",
         "Köln-Nippes", "Köln-Chorweiler", "Köln-Porz", "Köln-Kalk", "Köln-Mülheim"),
    ),
    # Optionale Nachbarkreise ("und so weiter")
    "rhein-erft": Region(
        "rhein-erft", "Rhein-Erft-Kreis", "6",
        ("Bergheim", "Bedburg", "Brühl", "Elsdorf", "Erftstadt", "Frechen", "Hürth",
         "Kerpen", "Pulheim", "Wesseling"),
    ),
    "rhein-berg": Region(
        "rhein-berg", "Rheinisch-Bergischer Kreis", "6",
        ("Bergisch Gladbach", "Burscheid", "Kürten", "Leichlingen", "Odenthal",
         "Overath", "Rösrath", "Wermelskirchen"),
    ),
    "ahrweiler": Region(
        "ahrweiler", "Landkreis Ahrweiler", "6",
        ("Bad Neuenahr-Ahrweiler", "Remagen", "Sinzig", "Grafschaft", "Altenahr",
         "Bad Breisig"),
    ),
}

STANDARD = ["rhein-sieg", "bonn", "koeln"]


def auswahl(keys: list[str] | None) -> list[Region]:
    keys = keys or STANDARD
    if keys == ["alle"]:
        return list(REGIONEN.values())
    unbekannt = [k for k in keys if k not in REGIONEN]
    if unbekannt:
        raise SystemExit(
            f"Unbekannte Region(en): {', '.join(unbekannt)}. Verfügbar: {', '.join(REGIONEN)}"
        )
    return [REGIONEN[k] for k in keys]


def ort_basisnamen(regionen: list[Region]) -> set[str]:
    """Ortsnamen, die in einer Adresse vorkommen dürfen ("Köln-Porz" -> "Köln")."""
    namen: set[str] = set()
    for r in regionen:
        for o in r.orte:
            namen.add(o.split("-")[0] if o.startswith(("Köln-", "Bonn-")) else o)
    return namen
