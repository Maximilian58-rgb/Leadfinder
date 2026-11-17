"""Lead-Score (0–100): Verkaufschance × Einfachheit × Erreichbarkeit."""
from __future__ import annotations

import re

from . import website_check as wc
from .models import Lead

CHANCE = {
    wc.STATUS_KEINE: 45,
    wc.STATUS_SOCIAL: 42,
    wc.STATUS_KAPUTT: 40,
    wc.STATUS_SCHLECHT: 33,
    wc.STATUS_MITTEL: 18,
    wc.STATUS_GUT: 3,
}


def lead_score(l: Lead) -> int:
    score = CHANCE.get(l.website_status, 20)
    score += l.einfachheit * 3                      # max 30
    if l.telefon:
        score += 12
    if l.email:
        score += 8
    # Aktiver Betrieb mit Kundenbewertungen = zahlungsfähig & sichtbar
    if l.anzahl_bewertungen:
        score += 5 if l.anzahl_bewertungen >= 20 else 3 if l.anzahl_bewertungen >= 5 else 1
    if l.website_status == wc.STATUS_SCHLECHT:
        score += min(5, max(0, l.website_maengel_punkte - 7))
    return max(0, min(100, score))


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(gmbh|ug|e\.?k\.?|kg|ohg|gbr|inh\.?|& co\.?|co\.?)\b", " ", s)
    return re.sub(r"[^a-z0-9äöüß]", "", s)


def _tel_norm(t: str) -> str:
    d = re.sub(r"\D", "", t or "")
    if d.startswith("49"):
        d = "0" + d[2:]
    elif d.startswith("0049"):
        d = "0" + d[4:]
    return d


def dedupliziere(leads: list[Lead]) -> list[Lead]:
    """Führt Treffer aus OSM und Google zusammen (Name+Ort, Telefon oder Domain)."""
    ergebnis: list[Lead] = []
    index: dict[str, Lead] = {}
    for l in leads:
        schluessel = [f"n:{_norm(l.name)}|{_norm(l.ort)}"]
        if _tel_norm(l.telefon):
            schluessel.append("t:" + _tel_norm(l.telefon))
        if l.website and not wc.ist_social(l.website):
            schluessel.append("w:" + wc._domain(wc.normalisiere_url(l.website)))
        vorhanden = next((index[k] for k in schluessel if k in index), None)
        if vorhanden:
            for feld in ("telefon", "email", "website", "strasse", "plz", "ort", "maps_link"):
                if not getattr(vorhanden, feld) and getattr(l, feld):
                    setattr(vorhanden, feld, getattr(l, feld))
            if l.anzahl_bewertungen and not vorhanden.anzahl_bewertungen:
                vorhanden.bewertung, vorhanden.anzahl_bewertungen = l.bewertung, l.anzahl_bewertungen
            if l.quelle not in vorhanden.quelle:
                vorhanden.quelle += " + " + l.quelle
            ziel = vorhanden
        else:
            ergebnis.append(l)
            ziel = l
        for k in schluessel:
            index.setdefault(k, ziel)
    return ergebnis
