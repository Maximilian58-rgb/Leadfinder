"""Export als Excel (mehrere Ranking-Blätter) und CSV."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import website_check as wc
from .categories import KATEGORIEN
from .models import Lead

SPALTEN = [
    ("Rang", 6), ("Score", 7), ("Betrieb", 34), ("Kategorie", 28), ("Einfachheit (1-10)", 11),
    ("Website-Status", 26), ("Telefon", 18), ("E-Mail", 30), ("Website", 32),
    ("Mängel der Website", 60), ("Adresse", 34), ("Ort", 16), ("Google-Sterne", 8),
    ("Bewertungen", 9), ("Quelle", 14), ("Karte", 12),
]
STATUS_FARBEN = {
    wc.STATUS_KEINE: "C6EFCE", wc.STATUS_SOCIAL: "D9EAD3", wc.STATUS_KAPUTT: "FFEB9C",
    wc.STATUS_SCHLECHT: "FCE4D6", wc.STATUS_MITTEL: "FFF2CC", wc.STATUS_GUT: "EDEDED",
}
KOPF = PatternFill("solid", fgColor="1F4E78")


def sortiert(leads: list[Lead]) -> list[Lead]:
    return sorted(leads, key=lambda l: (-l.lead_score, -l.einfachheit, l.name.lower()))


def _zeile(i: int, l: Lead) -> list:
    return [i, l.lead_score, l.name, l.kategorie, l.einfachheit, l.website_status,
            l.telefon, l.email, l.final_url or l.website, "; ".join(l.website_maengel),
            l.adresse, l.ort, l.bewertung, l.anzahl_bewertungen, l.quelle, l.maps_link]


def _blatt(wb: Workbook, titel: str, leads: list[Lead]) -> None:
    ws = wb.create_sheet(titel[:31])
    ws.append([s for s, _ in SPALTEN])
    for c, (_, breite) in enumerate(SPALTEN, 1):
        ws.column_dimensions[get_column_letter(c)].width = breite
        zelle = ws.cell(1, c)
        zelle.font, zelle.fill = Font(bold=True, color="FFFFFF"), KOPF
        zelle.alignment = Alignment(wrap_text=True, vertical="center")
    for i, l in enumerate(sortiert(leads), 1):
        ws.append(_zeile(i, l))
        r = ws.max_row
        farbe = STATUS_FARBEN.get(l.website_status)
        if farbe:
            ws.cell(r, 6).fill = PatternFill("solid", fgColor=farbe)
        if l.telefon:
            ws.cell(r, 7).hyperlink = "tel:" + "".join(ch for ch in l.telefon if ch.isdigit() or ch == "+")
        if l.email:
            ws.cell(r, 8).hyperlink = "mailto:" + l.email
        web = l.final_url or l.website
        if web:
            ws.cell(r, 9).hyperlink = wc.normalisiere_url(web)
        if l.maps_link:
            ws.cell(r, 16).value = "Karte"
            ws.cell(r, 16).hyperlink = l.maps_link
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = ws.dimensions


def _uebersicht(wb: Workbook, leads: list[Lead]) -> None:
    ws = wb.active
    ws.title = "Kategorien-Ranking"
    kopf = ["Rang", "Kategorie", "Einfachheit (1-10)", "Warum einfach/schwer",
            "Betriebe gesamt", "Keine Website", "Nur Social/Verzeichnis", "Kaputt/Platzhalter",
            "Schlechte Website", "Verbesserungswürdig", "Gute Website",
            "Mit Telefon", "Mit E-Mail", "Ø Lead-Score", "Verkaufschancen*"]
    ws.append(kopf)
    pro_kat: dict[str, list[Lead]] = defaultdict(list)
    for l in leads:
        pro_kat[l.kategorie_key].append(l)
    zeilen = []
    for k in KATEGORIEN:
        ls = pro_kat.get(k.key, [])
        st = Counter(l.website_status for l in ls)
        chancen = sum(st[s] for s in wc.STATUS_REIHENFOLGE[:4])
        zeilen.append([k.name, k.einfachheit, k.begruendung, len(ls),
                       st[wc.STATUS_KEINE], st[wc.STATUS_SOCIAL], st[wc.STATUS_KAPUTT],
                       st[wc.STATUS_SCHLECHT], st[wc.STATUS_MITTEL], st[wc.STATUS_GUT],
                       sum(1 for l in ls if l.telefon), sum(1 for l in ls if l.email),
                       round(sum(l.lead_score for l in ls) / len(ls), 1) if ls else 0,
                       chancen])
    zeilen.sort(key=lambda z: (-z[1], -z[-1]))
    for i, z in enumerate(zeilen, 1):
        ws.append([i] + z)
    breiten = [6, 36, 11, 60, 10, 10, 12, 12, 11, 13, 10, 10, 10, 10, 13]
    for c, b in enumerate(breiten, 1):
        ws.column_dimensions[get_column_letter(c)].width = b
        zelle = ws.cell(1, c)
        zelle.font, zelle.fill = Font(bold=True, color="FFFFFF"), KOPF
        zelle.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 45
    ws.freeze_panes = "C2"
    ws.append([])
    ws.append(["", "* Verkaufschancen = Keine Website + Nur Social + Kaputt + Schlechte Website"])
    ws.append(["", "Lead-Score (0–100) = Website-Chance (max 45) + Einfachheit×3 (max 30) "
                   "+ Telefon 12 + E-Mail 8 + Bewertungen bis 5"])


def exportiere(leads: list[Lead], ordner: Path) -> tuple[Path, Path]:
    ordner.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    _uebersicht(wb, leads)
    _blatt(wb, "Alle Leads (Ranking)", leads)
    _blatt(wb, "Mit Telefon + E-Mail", [l for l in leads if l.telefon and l.email
                                        and l.website_status != wc.STATUS_GUT])
    for status in wc.STATUS_REIHENFOLGE:
        _blatt(wb, status.replace("/", "-"), [l for l in leads if l.website_status == status])
    for k in sorted(KATEGORIEN, key=lambda k: -k.einfachheit):
        ls = [l for l in leads if l.kategorie_key == k.key]
        if ls:
            _blatt(wb, f"{k.einfachheit} - {k.name}".replace("/", "-"), ls)
    xlsx = ordner / "leads.xlsx"
    wb.save(xlsx)

    csv_pfad = ordner / "leads.csv"
    with csv_pfad.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([s for s, _ in SPALTEN])
        for i, l in enumerate(sortiert(leads), 1):
            w.writerow(_zeile(i, l))
    return xlsx, csv_pfad
