"""Export als Excel (eine lange Unternehmensliste) und CSV.

Aufbau: links der Name des Betriebs, rechts daneben Adresse, Telefon, E-Mail,
Website und die Einschätzung. Sortiert nach Verkaufschance (beste zuerst),
nicht nach Branche – über den Filter in der Kopfzeile lässt sich jede Spalte
umsortieren oder filtern.
"""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import website_check as wc
from .models import Lead

SPALTEN = [
    ("Unternehmen", 42),
    ("Straße", 30),
    ("PLZ", 8),
    ("Ort", 20),
    ("Telefon", 20),
    ("E-Mail", 36),
    ("Website", 36),
    ("Website-Status", 30),
    ("Branche", 30),
    ("Mängel der Website", 70),
    ("Lead-Score", 10),
]
STATUS_FARBEN = {
    wc.STATUS_KEINE: "C6EFCE", wc.STATUS_SOCIAL: "D9EAD3", wc.STATUS_KAPUTT: "FFEB9C",
    wc.STATUS_SCHLECHT: "FCE4D6", wc.STATUS_MITTEL: "FFF2CC", wc.STATUS_GUT: "EDEDED",
}
KOPF = PatternFill("solid", fgColor="1F4E78")
LINIE = Border(right=Side(style="medium", color="1F4E78"))


def sortiert(leads: list[Lead]) -> list[Lead]:
    return sorted(leads, key=lambda l: (-l.lead_score, l.name.lower()))


def _zeile(l: Lead) -> list:
    return [l.name, l.strasse, l.plz, l.ort, l.telefon, l.email, l.final_url or l.website,
            l.website_status, l.kategorie, "; ".join(l.website_maengel), l.lead_score]


def exportiere(leads: list[Lead], ordner: Path) -> tuple[Path, Path]:
    ordner.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Unternehmen"
    ws.append([s for s, _ in SPALTEN])
    for c, (_, breite) in enumerate(SPALTEN, 1):
        ws.column_dimensions[get_column_letter(c)].width = breite
        zelle = ws.cell(1, c)
        zelle.font, zelle.fill = Font(bold=True, color="FFFFFF"), KOPF
        zelle.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 22

    fett = Font(bold=True)
    for l in sortiert(leads):
        ws.append(_zeile(l))
        r = ws.max_row
        ws.cell(r, 1).font = fett
        ws.cell(r, 1).border = LINIE
        farbe = STATUS_FARBEN.get(l.website_status)
        if farbe:
            ws.cell(r, 8).fill = PatternFill("solid", fgColor=farbe)
        if l.telefon:
            ws.cell(r, 5).hyperlink = "tel:" + "".join(
                ch for ch in l.telefon if ch.isdigit() or ch == "+")
        if l.email:
            ws.cell(r, 6).hyperlink = "mailto:" + l.email
        web = l.final_url or l.website
        if web:
            ws.cell(r, 7).hyperlink = wc.normalisiere_url(web)
    ws.cell(1, 1).border = LINIE
    ws.freeze_panes = "B2"          # Name bleibt beim Scrollen nach rechts stehen
    ws.auto_filter.ref = ws.dimensions

    xlsx = ordner / "leads.xlsx"
    wb.save(xlsx)

    csv_pfad = ordner / "leads.csv"
    with csv_pfad.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([s for s, _ in SPALTEN])
        for l in sortiert(leads):
            w.writerow(_zeile(l))
    return xlsx, csv_pfad
