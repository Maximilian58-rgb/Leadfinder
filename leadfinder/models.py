from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Lead:
    name: str
    kategorie_key: str
    kategorie: str
    einfachheit: int
    quelle: str
    strasse: str = ""
    plz: str = ""
    ort: str = ""
    telefon: str = ""
    email: str = ""
    website: str = ""
    bewertung: float | None = None      # Google-Sterne
    anzahl_bewertungen: int | None = None
    maps_link: str = ""
    lat: float | None = None
    lon: float | None = None
    kette: bool = False                 # Filialkette (Marke) -> kein Lead
    # Ergebnisse der Website-Prüfung
    website_status: str = ""            # siehe website_check.STATUS_*
    website_maengel: list[str] = field(default_factory=list)
    website_maengel_punkte: int = 0
    final_url: str = ""
    # Ranking
    lead_score: int = 0

    @property
    def adresse(self) -> str:
        teil2 = " ".join(x for x in (self.plz, self.ort) if x)
        return ", ".join(x for x in (self.strasse, teil2) if x)
